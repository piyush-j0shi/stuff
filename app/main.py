import sqlite3

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

import os

from . import auth, bulk_runner, enrich, importer, queries, store
from .config import ADMIN_USERS, CATEGORIES, SAFE_MODE, SECRET_KEY, is_adult_type
from .db import db, init_db
from .sources import csv_dump, tmdb

app = FastAPI(title="MediaList")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

COVER_COLORS = ["#2e51a2", "#4b6cb7", "#3a7d44", "#8e44ad", "#c0392b",
                "#16a085", "#d35400", "#2c3e50", "#7f8c8d", "#b03a5b"]

def show_adult(request: Request) -> bool:
    if SAFE_MODE:
        return False
    return bool(request.session.get("adult_ok"))

def current_user(request: Request):
    uid = request.session.get("user_id")
    return auth.get_user(uid) if uid else None

def account_is_admin(user):
    if not user:
        return False
    if user["is_admin"] == 1:
        return True
    return bool(ADMIN_USERS and user["username"] in ADMIN_USERS)

def base_ctx(request: Request):
    user = current_user(request)
    is_admin = account_is_admin(user)
    return {
        "request": request,
        "categories": CATEGORIES,
        "user": user,
        "is_admin": is_admin,
        "show_adult": show_adult(request),
        "safe_mode": SAFE_MODE,
        "flash": request.session.pop("flash", None),
    }

@app.on_event("startup")
def startup():
    init_db()

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    adult = show_adult(request)
    season = queries.latest_season_label()
    ctx = base_ctx(request)
    ctx.update({
        "top_airing": queries.top_airing(8, adult),
        "top_upcoming": queries.top_upcoming(6, adult),
        "top_all_time": queries.top_all_time(10, adult),
        "trending_week": queries.trending_week(6, adult),
        "trending_month": queries.trending_month(6, adult),
        "newest": queries.newest(8, adult),
        "seasonal": queries.seasonal(season, 8, adult) if season else [],
        "season_label": season,
    })
    return templates.TemplateResponse("index.html", ctx)

SORTS = {
    "top": ("score DESC, members DESC", "Top Rated"),
    "week": ("trend_week DESC", "Trending This Week"),
    "month": ("trend_month DESC", "Trending This Month"),
    "newest": ("year DESC, id DESC", "Newest"),
    "oldest": ("year ASC", "Oldest"),
    "popular": ("members DESC", "Most Popular"),
}

PER_PAGE = 30

@app.get("/browse/{type_}", response_class=HTMLResponse)
def browse(request: Request, type_: str, sort: str = "top", page: int = 1, cat: str = ""):
    if type_ != "all" and type_ not in CATEGORIES:
        return RedirectResponse("/")
    if is_adult_type(type_) and not show_adult(request):
        return RedirectResponse(f"/age-gate?next=/browse/{type_}")
    order, label = SORTS.get(sort, SORTS["top"])
    cat = cat.strip().lower() or None
    items, total, total_pages = queries.browse_page(
        type_, page, PER_PAGE, show_adult(request), order=order, tag=cat)
    label = "All" if type_ == "all" else CATEGORIES[type_]["label"]
    ctx = base_ctx(request)
    ctx.update({"type_": type_, "type_label": label, "items": items,
                "sort": sort, "sorts": SORTS, "page": max(1, page),
                "total": total, "total_pages": total_pages,
                "categories_list": queries.categories_for(type_, show_adult(request)),
                "active_cat": cat})
    return templates.TemplateResponse("browse.html", ctx)

@app.get("/item/{item_id}", response_class=HTMLResponse)
def item(request: Request, item_id: int):
    it = queries.get_item(item_id, show_adult(request))
    if not it:
        return HTMLResponse("Not found (or age-restricted).", status_code=404)
    if not it["cast"] and not it["extra"].get("enriched"):
        enrich.enrich(it)
        it = queries.get_item(item_id, show_adult(request))
    my_status = None
    u = current_user(request)
    if u:
        with db() as conn:
            r = conn.execute(
                "SELECT status FROM list_entry WHERE user_id = ? AND media_item_id = ?",
                (u["id"], item_id)).fetchone()
            my_status = r["status"] if r else None
    ctx = base_ctx(request)
    ctx.update({"item": it, "unit": CATEGORIES.get(it["type"], {}).get("unit", "eps"),
                "my_status": my_status})
    return templates.TemplateResponse("item.html", ctx)

@app.post("/item/{item_id}/review")
def post_review(request: Request, item_id: int,
                rating: int = Form(10), body: str = Form(...)):
    u = current_user(request)
    if not u:
        return RedirectResponse("/login", status_code=303)
    body = body.strip()
    if body:
        with db() as conn:
            conn.execute(
                "INSERT INTO review(media_item_id, author, rating, body) VALUES (?,?,?,?)",
                (item_id, u["username"], max(1, min(10, rating)), body))
    return RedirectResponse(f"/item/{item_id}", status_code=303)


@app.get("/search", response_class=HTMLResponse)
def search(request: Request, q: str = ""):
    items = queries.search(q.strip(), 40, show_adult(request)) if q.strip() else []
    ctx = base_ctx(request)
    ctx.update({"q": q, "items": items})
    return templates.TemplateResponse("search.html", ctx)

@app.get("/age-gate", response_class=HTMLResponse)
def age_gate(request: Request, next: str = "/"):
    ctx = base_ctx(request)
    ctx.update({"next": next})
    return templates.TemplateResponse("age_gate.html", ctx)

@app.post("/age-gate")
def age_gate_confirm(request: Request, confirm: str = Form(...), next: str = Form("/")):
    if confirm == "yes" and not SAFE_MODE:
        request.session["adult_ok"] = True
    return RedirectResponse(next, status_code=303)

@app.get("/age-gate/off")
def age_gate_off(request: Request):
    request.session.pop("adult_ok", None)
    return RedirectResponse("/", status_code=303)

@app.get("/register", response_class=HTMLResponse)
def register_form(request: Request):
    return templates.TemplateResponse("auth.html", {**base_ctx(request), "mode": "register", "error": None})

@app.post("/register")
def register(request: Request, username: str = Form(...), password: str = Form(...)):
    try:
        uid = auth.create_user(username.strip(), password)
    except sqlite3.IntegrityError:
        return templates.TemplateResponse(
            "auth.html", {**base_ctx(request), "mode": "register", "error": "Username taken."})
    request.session["user_id"] = uid
    return RedirectResponse("/", status_code=303)

@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse("auth.html", {**base_ctx(request), "mode": "login", "error": None})

@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    u = auth.get_user_by_name(username.strip())
    if not u or not auth.verify_password(password, u["password_hash"]):
        return templates.TemplateResponse(
            "auth.html", {**base_ctx(request), "mode": "login", "error": "Invalid credentials."})
    request.session["user_id"] = u["id"]
    return RedirectResponse("/", status_code=303)

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)

STATUS_LABELS = {"watching": "Watching", "completed": "Completed", "plan": "Plan to Watch",
                 "on_hold": "On Hold", "dropped": "Dropped"}

@app.post("/list/add")
def list_add(request: Request, media_item_id: int = Form(...), status: str = Form("plan")):
    u = current_user(request)
    if not u:
        return RedirectResponse("/login", status_code=303)
    with db() as conn:
        conn.execute(
            """INSERT INTO list_entry(user_id, media_item_id, status)
               VALUES (?, ?, ?)
               ON CONFLICT(user_id, media_item_id)
               DO UPDATE SET status=excluded.status, updated_at=CURRENT_TIMESTAMP""",
            (u["id"], media_item_id, status))
        row = conn.execute("SELECT title FROM media_item WHERE id = ?", (media_item_id,)).fetchone()
    title = row["title"] if row else "Item"
    request.session["flash"] = f'"{title}" added to your list as {STATUS_LABELS.get(status, status)}'
    return RedirectResponse(request.headers.get("referer", "/"), status_code=303)

MYLIST_SORTS = {
    "recent": "le.updated_at DESC",
    "title": "m.title ASC",
    "score": "le.score DESC",
    "type": "m.type ASC, m.title ASC",
}
LIST_STATUSES = ["watching", "completed", "plan", "on_hold", "dropped"]

@app.get("/mylist", response_class=HTMLResponse)
def mylist(request: Request, status: str = "all", sort: str = "recent"):
    u = current_user(request)
    if not u:
        return RedirectResponse("/login", status_code=303)
    order = MYLIST_SORTS.get(sort, MYLIST_SORTS["recent"])
    where, params = "le.user_id = ?", [u["id"]]
    if status in LIST_STATUSES:
        where += " AND le.status = ?"
        params.append(status)
    with db() as conn:
        rows = conn.execute(
            f"""SELECT m.*, le.status AS my_status, le.score AS my_score, le.progress
                  FROM list_entry le JOIN media_item m ON m.id = le.media_item_id
                 WHERE {where} ORDER BY {order}""", params).fetchall()
    return templates.TemplateResponse("mylist.html", {
        **base_ctx(request), "rows": rows, "statuses": LIST_STATUSES,
        "sorts": MYLIST_SORTS, "cur_status": status, "cur_sort": sort})

def require_admin(request: Request):
    u = current_user(request)
    return u if account_is_admin(u) else None

@app.get("/admin", response_class=HTMLResponse)
def admin_home(request: Request):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=303)
    ctx = base_ctx(request)
    ctx.update({"import_options": importer.options(), "tmdb_ready": tmdb.enabled()})
    return templates.TemplateResponse("admin.html", ctx)

@app.get("/admin/add", response_class=HTMLResponse)
def admin_add_form(request: Request):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse("admin_add.html", {**base_ctx(request), "saved": None})

@app.post("/admin/add", response_class=HTMLResponse)
def admin_add(
    request: Request,
    type_: str = Form(...),
    title: str = Form(...),
    image_url: str = Form(""),
    synopsis: str = Form(""),
    year: str = Form(""),
    season: str = Form(""),
    air_status: str = Form("finished"),
    units_total: str = Form(""),
    score: str = Form(""),
    watch_names: str = Form(""),
    watch_urls: str = Form(""),
    embed_url: str = Form(""),
    is_adult: str = Form(""),
):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=303)

    names = [n.strip() for n in watch_names.splitlines() if n.strip()]
    urls = [u.strip() for u in watch_urls.splitlines() if u.strip()]
    watch = [{"name": n, "url": u} for n, u in zip(names, urls)]

    item = {
        "type": type_, "title": title.strip(), "image_url": image_url.strip() or None,
        "synopsis": synopsis.strip() or None,
        "year": int(year) if year.strip().isdigit() else None,
        "season": season.strip() or None, "air_status": air_status,
        "units_total": int(units_total) if units_total.strip().isdigit() else 0,
        "score": float(score) if score.strip() else 0,
        "where_to_watch": watch,
        "extra": {"embed_url": embed_url.strip()} if embed_url.strip() else {},
        "is_adult": bool(is_adult) or is_adult_type(type_),
        "source": "manual", "source_id": None,
    }
    new_id, created = store.upsert_item(item)
    return templates.TemplateResponse("admin_add.html", {**base_ctx(request), "saved": new_id})

@app.get("/admin/import", response_class=HTMLResponse)
def admin_import_form(request: Request):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=303)
    ctx = base_ctx(request)
    ctx.update({"import_options": importer.options(), "result": None,
                "q": "", "source": "jikan", "type_": "anime"})
    return templates.TemplateResponse("admin_import.html", ctx)

@app.post("/admin/import", response_class=HTMLResponse)
def admin_import(request: Request, source: str = Form(...), type_: str = Form(...),
                 q: str = Form(...), limit: int = Form(12)):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=303)
    ctx = base_ctx(request)
    ctx.update({"import_options": importer.options(), "q": q,
                "source": source, "type_": type_})
    try:
        fetched = importer.fetch(source, type_, q.strip(), min(limit, 25))
        if not fetched:
            ctx["result"] = {"error": "No results (or TMDB key not set)."}
        else:
            res = store.import_many(fetched)
            ctx["result"] = {"created": res["created"], "updated": res["updated"],
                             "ids": res["ids"], "titles": [f.get("title") for f in fetched]}
    except Exception as e:
        ctx["result"] = {"error": str(e)}
    return templates.TemplateResponse("admin_import.html", ctx)

@app.get("/admin/bulk", response_class=HTMLResponse)
def admin_bulk_form(request: Request):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=303)
    ctx = base_ctx(request)
    ctx.update({"status": bulk_runner.STATUS, "tmdb_ready": tmdb.enabled()})
    return templates.TemplateResponse("admin_bulk.html", ctx)


@app.post("/admin/bulk")
def admin_bulk_run(
    request: Request,
    anime: int = Form(0), manga: int = Form(0), manhwa: int = Form(0),
    hentai: int = Form(0), movies: int = Form(0), dramas: int = Form(0),
    webseries: int = Form(0), sports: int = Form(0),
):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=303)
    counts = {"anime": anime, "manga": manga, "manhwa": manhwa, "hentai": hentai,
              "movies": movies, "dramas": dramas, "webseries": webseries, "sports": sports}
    bulk_runner.start(counts)
    return RedirectResponse("/admin/bulk", status_code=303)


@app.get("/admin/import-file", response_class=HTMLResponse)
def admin_import_file_form(request: Request):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse("admin_import_file.html",
                                      {**base_ctx(request), "result": None, "path": ""})

@app.post("/admin/import-file", response_class=HTMLResponse)
def admin_import_file(request: Request, path: str = Form(...), limit: int = Form(500)):
    if not require_admin(request):
        return RedirectResponse("/login", status_code=303)
    ctx = base_ctx(request)
    ctx["path"] = path
    path = path.strip()
    if not os.path.isfile(path):
        ctx["result"] = {"error": f"File not found: {path}"}
    else:
        try:
            items = csv_dump.parse(path, min(limit, 5000))
            if not items:
                ctx["result"] = {"error": "Parsed 0 usable rows. Check the file/columns."}
            else:
                res = store.import_many(items)
                ctx["result"] = {"created": res["created"], "updated": res["updated"],
                                 "total": len(items)}
        except Exception as e:
            ctx["result"] = {"error": str(e)}
    return templates.TemplateResponse("admin_import_file.html", ctx)

@app.get("/credits", response_class=HTMLResponse)
def credits(request: Request):
    return templates.TemplateResponse("credits.html", base_ctx(request))

@app.get("/cover/{item_id}.svg")
def cover(item_id: int):
    with db() as conn:
        row = conn.execute("SELECT title, type FROM media_item WHERE id = ?", (item_id,)).fetchone()
    title = row["title"] if row else "?"
    color = COVER_COLORS[item_id % len(COVER_COLORS)]
    initials = "".join(w[0] for w in title.split()[:2]).upper() or "?"
    svg = f"""<svg xmlns='http://www.w3.org/2000/svg' width='225' height='320'>
      <rect width='100%' height='100%' fill='{color}'/>
      <text x='50%' y='46%' fill='#ffffff' font-size='64' font-family='Arial'
            text-anchor='middle' font-weight='bold'>{initials}</text>
      <text x='50%' y='90%' fill='#ffffffcc' font-size='15' font-family='Arial'
            text-anchor='middle'>{title[:24]}</text>
    </svg>"""
    return Response(svg, media_type="image/svg+xml")
