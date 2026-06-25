# MediaList

A **MyAnimeList-style, multi-category media catalog & tracker**. One site for
**anime, manga, manhwa, movies, dramas, web series, sports**, plus age-gated
**hentai** and **adult video**. Browse, search, rate, build a personal list,
and bulk-import real data from public APIs.

Built with **FastAPI + SQLite + vanilla HTML/CSS/JS** (no build step, no JS framework).

---

## Table of contents
1. [Features](#features)
2. [Requirements](#requirements)
3. [Quick start](#quick-start)
4. [Manual setup](#manual-setup)
5. [Configuration (.env)](#configuration-env)
6. [Loading data](#loading-data)
7. [Categories](#categories)
8. [Adult content & safety](#adult-content--safety)
9. [Admin panel](#admin-panel)
10. [Project structure](#project-structure)
11. [Routes reference](#routes-reference)
12. [Troubleshooting](#troubleshooting)

---

## Features
- **One engine, every category** — a single `media_item` table powers all types.
- **MAL-style homepage** — Top Airing / Upcoming sidebars, Seasonal, Top of All
  Time, Newest, Trending This Week/Month.
- **Browse + pagination** — every category and an **All** view, 30/page with a pager.
- **Sorting** — Top Rated, Trending (week/month), Newest, Oldest, Most Popular.
- **Item pages** — description, where-to-watch links, cast, reviews, inline embed player.
- **Picture previews** everywhere (real cover/poster/thumbnail art from the APIs).
- **Accounts + personal list** (watching / completed / plan / on-hold / dropped).
- **Bulk + full-catalog importers** (see [Loading data](#loading-data)).
- **Age-gated adult content**, off by default, with a site-wide SAFE_MODE for demos.
- **Credits & attribution** page for all data sources.

---

## Requirements
- **Python 3.10+** (developed on 3.12)
- Internet access for data imports (the app itself runs offline on seeded data)
- ~a few hundred MB of disk if you run the full Jikan sync

---

## Quick start
From the project folder:

```bash
cd ~/nothing_1
./run.sh
```

`run.sh` creates a virtualenv, installs dependencies, seeds sample data on first
run, and starts the server. Then open:

> **http://127.0.0.1:8000**

Stop the server with **Ctrl+C**. If you get "permission denied", use `bash run.sh`.

---

## Manual setup
If you'd rather do it by hand:

```bash
cd ~/nothing_1
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Seed sample data (first time only)
.venv/bin/python -m app.seed

# Run the dev server (auto-reload)
.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

---

## Configuration (.env)
Copy the example and edit:

```bash
cp .env.example .env
```

| Variable          | Default          | Purpose                                                        |
|-------------------|------------------|----------------------------------------------------------------|
| `TMDB_API_KEY`    | *(empty)*        | Free key from themoviedb.org. **Required** for movies/dramas/web series. |
| `SECRET_KEY`      | `dev-secret...`  | Session-cookie signing secret. Change for anything non-local.  |
| `SAFE_MODE`       | `0`              | `1` hides **all** adult content site-wide, regardless of opt-in. |
| `ADMIN_USERS`     | *(empty)*        | Comma-separated usernames allowed into `/admin`. Empty = any logged-in user. |
| `THESPORTSDB_KEY` | `3`              | TheSportsDB key. The free public test key `3` works out of the box. |

Environment variables are read at startup — restart the server after changing `.env`.

---

## Loading data
The app ships with a small seeded sample. To get a real catalog, use any of these.

### 1. Quick bulk import (top/popular) — no key for Jikan/Sports
Pulls the most popular N pages per category (≈25 items/page):

```bash
.venv/bin/python -m app.bulk_import 8 8 5
#                                    │ │ └ hentai pages
#                                    │ └── manga pages
#                                    └──── anime pages
```
Defaults if you pass no numbers: anime 8, manga 8, hentai 5, movies 8, dramas 5,
web series 5, plus sports teams. Movies/dramas/web series only run if
`TMDB_API_KEY` is set.

### 2. FULL Jikan catalog — every anime, manga & hentai
Walks **every page** of Jikan until exhausted (~28k anime + ~70k manga). It is
**resumable** (checkpointed per page in the `sync_state` table) and takes
roughly **1–1.5 hours** due to API rate limits. Hentai is auto-detected
(Rx rating / genre 12) and flagged 18+.

**Start it** — run from the project folder (`cd ~/nothing_1`):

```bash
# Option A: background (recommended) — keeps running after you close nothing,
# writes output to full_sync.log
nohup .venv/bin/python -m app.full_sync > full_sync.log 2>&1 &

# Option B: foreground — watch it live, Ctrl+C to stop
.venv/bin/python -m app.full_sync
```

**Sync only one type:**
```bash
.venv/bin/python -m app.full_sync anime      # anime (+hentai) only
.venv/bin/python -m app.full_sync manga      # manga only
```

**Watch progress (background run):**
```bash
tail -f full_sync.log
```

**Check how far it's got (reads the checkpoint table):**
```bash
.venv/bin/python -c "import sqlite3; \
print(list(sqlite3.connect('media.db').execute('select job,last_page,done,items from sync_state')))"
```

**Stop a background run:**
```bash
pkill -f app.full_sync
```

**Resume / re-run:**
- Interrupted (Ctrl+C, `pkill`, reboot, crash)? Just start it again — it
  **resumes from the last saved page** automatically.
- Re-running after it finished is a no-op (it's marked `done`).
- Force a fresh full re-pull from page 1:
  ```bash
  .venv/bin/python -m app.full_sync --restart
  ```

> You can run the web server (`./run.sh`) at the same time — the database uses
> WAL mode, so browsing works while the sync writes.

### 3. Movies / Dramas / Web Series (TMDB — key required)
1. Get a free key at **themoviedb.org → Settings → API**.
2. Put `TMDB_API_KEY=...` in `.env` (auto-loaded at startup).
3. Bulk-pull all three (pages are 20 items each, up to 500):
   ```bash
   .venv/bin/python -m app.bulk_tmdb              # 100 pages each (~6,000 items)
   .venv/bin/python -m app.bulk_tmdb 300 200 200  # movies / dramas / webseries pages
   ```
   Or add items one search at a time via **Admin → Import from API**.

### 4. Sports (TheSportsDB — no key needed)
Bulk import pulls teams for major leagues automatically. For one-offs use
**Admin → Import from API** (source TheSportsDB).

### 5. Adult video — Pornhub official embed dump
Pornhub's Webmasters page publishes an official **embed dump** (title, thumbnail
URL, tags, duration, view count, embed code). Two ways to import it:

**a) Small files — Admin UI:** **Admin → Bulk import (dump file)**, give the path.
Good up to a few thousand rows.

**b) Large files (multi-GB) — resumable CLI importer.** The real dump is ~17 GB /
~4.7M rows, so the CLI imports it **a chunk at a time** with a byte-offset
checkpoint — run it whenever you want more data and it continues where it left off:

```bash
# Point it at your file (or set PORNHUB_DUMP in the environment)
export PORNHUB_DUMP=~/Downloads/pornhub.com-db.csv

.venv/bin/python -m app.import_pornhub            # import the NEXT 5,000 rows
.venv/bin/python -m app.import_pornhub 50000      # import the next 50,000 rows
.venv/bin/python -m app.import_pornhub --status   # show progress, import nothing
.venv/bin/python -m app.import_pornhub --reset    # start over from the top
.venv/bin/python -m app.import_pornhub --file /path/to/other.csv
```
- Imports as **Adult video (18+)** with thumbnail previews, inline embeds, view
  counts (used for popularity sort) and a score from up/down votes.
- **Resumable & idempotent**: re-runs continue from the saved byte offset; duplicate
  rows are ignored (`source_id` = embed viewkey).
- Each run is independent — schedule it, loop it, or just run it by hand to "bring
  more data" gradually. ~4.7M rows ≈ a ~3–5 GB database if you import it all.

**Content filtering.** New imports skip rows tagged with any `EXCLUDE_TOKENS`
(default `{"gay"}`) unless they also carry a `KEEP_TOKENS` tag (default
`{"lesbian"}` — lesbian always wins). Edit those sets at the top of
`app/import_pornhub.py` to change the policy. To clean rows already imported:

```bash
.venv/bin/python -m app.import_pornhub --purge   # delete excluded (gay) rows, keep lesbian
```

### Reset the catalog
Delete the database and re-seed:
```bash
rm media.db && .venv/bin/python -m app.seed
```

---

## Categories
`anime`, `manga`, `manhwa`, `movie`, `drama`, `webseries`, `sports`,
and the age-gated `hentai`, `adultvideo`. Categories are defined in
`app/config.py` (`CATEGORIES`) — adding one is mostly a config entry plus an
import adapter.

| Category | Data source |
|---|---|
| Anime / Hentai / Manga | Jikan (MyAnimeList API) |
| Movies / Dramas / Web Series | TMDB |
| Sports | TheSportsDB |
| Manhwa | Jikan (partial) / manual |
| Adult video | Manual entry + Pornhub embed dump |

---

## Adult content & safety
- **Off by default.** A fresh visitor sees no adult content.
- **Age gate.** Adult categories require an 18+ opt-in (toggle in the bar under the nav).
- **SAFE_MODE=1** hides all adult content site-wide regardless of opt-in — use it
  for screen-shares / portfolio demos.
- **No media is hosted here.** Only metadata, links, and providers' official embeds.

---

## Admin panel
The **Admin** panel is **locked down by default** — no account can reach `/admin`
until you create an admin. Make one with the interactive script:

```bash
.venv/bin/python -m app.create_admin
# prompts for Email (validated), Username (checked for duplicates), Password (hidden)
```

That account gets `is_admin = 1`; only admins see the **Admin** link and can open
`/admin` (everyone else is redirected away). You can also grant admin to existing
usernames via the `ADMIN_USERS` env var (comma-separated) as a fallback.

Admin tools:
- **Import from API** — Jikan / TMDB / TheSportsDB by search term.
- **Add manually** — any entry by hand (title, cover URL, description, where-to-watch,
  embed URL). Used for sports and adult video.
- **Bulk import (dump file)** — the Pornhub embed dump (CSV/ZIP).

---

## Project structure
```
nothing_1/
├── run.sh                 # one-command setup + serve
├── requirements.txt
├── .env.example
├── media.db               # SQLite database (generated; gitignored)
├── app/
│   ├── main.py            # FastAPI app + all routes
│   ├── config.py          # categories, settings, env
│   ├── db.py              # SQLite connection + schema
│   ├── queries.py         # read/browse/pagination queries (adult-gated)
│   ├── store.py           # upsert / bulk write
│   ├── auth.py            # register/login (PBKDF2)
│   ├── seed.py            # sample data
│   ├── bulk_import.py     # top/popular bulk importer (CLI)
│   ├── full_sync.py       # full Jikan catalog sync, resumable (CLI)
│   ├── importer.py        # source+type → adapter dispatch
│   └── sources/
│       ├── jikan.py        # anime / manga / hentai
│       ├── tmdb.py         # movies / dramas / web series
│       ├── thesportsdb.py  # sports
│       └── csv_dump.py     # Pornhub embed-dump parser
├── templates/             # Jinja2 (base, index, browse, item, admin, ...)
└── static/                # style.css, app.js
```

---

## Routes reference
| Method | Path | Description |
|---|---|---|
| GET | `/` | Homepage (MAL-style sections) |
| GET | `/browse/{type}` | Category listing; `?sort=&page=`. Use `all` for everything |
| GET | `/item/{id}` | Item detail page |
| GET | `/search?q=` | Search titles |
| GET/POST | `/age-gate` | Enable 18+ content · `/age-gate/off` to disable |
| GET/POST | `/register`, `/login`, GET `/logout` | Accounts |
| POST | `/list/add` | Add/update an item in your list |
| GET | `/mylist` | Your personal list |
| GET | `/admin` | Admin dashboard |
| GET/POST | `/admin/add` | Manual entry |
| GET/POST | `/admin/import` | API import |
| GET/POST | `/admin/import-file` | Bulk dump import |
| GET | `/credits` | Credits & attribution |

---

## Troubleshooting
- **Browser can't reach the site** — `run.sh` must be running in a terminal; keep
  it open. The site is at `http://127.0.0.1:8000`.
- **`./run.sh: permission denied`** — run `bash run.sh`, or `chmod +x run.sh`.
- **Movies/dramas/web series stay empty** — set `TMDB_API_KEY` in `.env` and restart.
- **Imports return "No results"** — for TMDB it usually means the key is missing;
  for Jikan/TheSportsDB it means the search term matched nothing.
- **Jikan import is slow / 429 errors** — expected; Jikan rate-limits to ~60/min.
  The importers throttle and retry automatically.
- **`database is locked`** — rare; the DB uses WAL + a 30s busy timeout. Retry.
- **Adult content not showing** — check `SAFE_MODE` isn't `1`, and that you opted
  in via the age gate.

---

*MediaList is a non-commercial learning/portfolio project. All catalog data,
images, and embeds belong to their respective providers — see `/credits`.*
