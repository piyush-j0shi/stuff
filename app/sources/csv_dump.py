import csv
import gzip
import io
import re
import zipfile

IFRAME_SRC = re.compile(r'src=["\']([^"\']+)["\']', re.I)
VIEWKEY = re.compile(r'viewkey=([A-Za-z0-9]+)', re.I)
IMG_EXT = re.compile(r'\.(jpg|jpeg|png|webp|gif)(\?|$)', re.I)

HEADER_MAP = {
    "title": "title", "video_title": "title",
    "thumb": "thumb", "thumbnail": "thumb", "thumbnail_url": "thumb",
    "default_thumb": "thumb", "image": "thumb",
    "embed": "embed", "embed_code": "embed", "iframe": "embed", "embed_url": "embed",
    "tags": "tags", "categories": "tags", "keywords": "tags",
    "duration": "duration", "length": "duration",
    "url": "url", "link": "url", "video_url": "url",
}

def _open_text(path):
    if path.lower().endswith(".zip"):
        zf = zipfile.ZipFile(path)
        name = next((n for n in zf.namelist() if n.lower().endswith(".csv")), zf.namelist()[0])
        return io.TextIOWrapper(zf.open(name), encoding="utf-8", errors="replace")
    if path.lower().endswith(".gz"):
        return io.TextIOWrapper(gzip.open(path, "rb"), encoding="utf-8", errors="replace")
    return open(path, encoding="utf-8", errors="replace")

def _embed_from(value, url=""):
    if value:
        m = IFRAME_SRC.search(value)
        if m:
            return m.group(1)
        if value.strip().lower().startswith("http"):
            return value.strip()
    for cand in (value, url):
        m = VIEWKEY.search(cand or "")
        if m:
            return f"https://www.pornhub.com/embed/{m.group(1)}"
    return ""

def _looks_like_img(s):
    return bool(s) and s.lower().startswith("http") and bool(IMG_EXT.search(s))

def _row_from_headed(d):
    g = {HEADER_MAP[k.strip().lower()]: v for k, v in d.items()
         if k and k.strip().lower() in HEADER_MAP}
    return _build(g.get("title"), g.get("thumb"), g.get("embed"),
                  g.get("tags"), g.get("url"))

def _row_from_headless(cells):
    title = thumb = embed = url = tags = None
    for c in cells:
        c = (c or "").strip()
        if not c:
            continue
        if ("<iframe" in c.lower() or "/embed/" in c.lower()) and not embed:
            embed = c
        elif _looks_like_img(c) and not thumb:
            thumb = c
        elif c.lower().startswith("http") and not url:
            url = c
        elif "," in c and not tags:
            tags = c
        elif not title:
            title = c
    return _build(title, thumb, embed, tags, url)

def _build(title, thumb, embed, tags, url):
    embed_src = _embed_from(embed, url or "")
    if not title:
        title = (tags or "Adult clip").split(",")[0].strip()[:80] or "Adult clip"
    return {
        "type": "adultvideo",
        "title": title.strip()[:120],
        "image_url": (thumb or "").strip() or None,
        "synopsis": ("Tags: " + tags) if tags else None,
        "air_status": "finished",
        "score": 0, "members": 0,
        "source": "pornhub_dump",
        "source_id": VIEWKEY.search(url or embed or "").group(1)
                     if VIEWKEY.search(url or embed or "") else (embed_src or title)[:80],
        "is_adult": 1,
        "extra": {"embed_url": embed_src} if embed_src else {},
    }

def parse(path, limit=500):
    stream = _open_text(path)
    try:
        sample = stream.read(4096)
        stream.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",|\t;")
        except csv.Error:
            dialect = csv.excel
        first_line = sample.splitlines()[0].lower() if sample else ""
        looks_like_data = any(tok in first_line for tok in ("http", "<iframe", "viewkey"))
        has_header = (not looks_like_data) and bool(
            set(re.split(r"[,|\t;]", first_line)) & set(HEADER_MAP))

        out = []
        if has_header:
            reader = csv.DictReader(stream, dialect=dialect)
            for d in reader:
                out.append(_row_from_headed(d))
                if len(out) >= limit:
                    break
        else:
            reader = csv.reader(stream, dialect=dialect)
            for cells in reader:
                if not cells:
                    continue
                out.append(_row_from_headless(cells))
                if len(out) >= limit:
                    break
        return [r for r in out if r["image_url"] or r["extra"].get("embed_url")]
    finally:
        stream.close()
