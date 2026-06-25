import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "media.db")

def _load_dotenv():
    path = os.path.join(BASE_DIR, ".env")
    if not os.path.isfile(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        os.environ.setdefault(key.strip(), val.strip())

_load_dotenv()

TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")
TMDB_READ_TOKEN = os.environ.get("TMDB_READ_TOKEN", "")

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")

SAFE_MODE = os.environ.get("SAFE_MODE", "0") == "1"

ADMIN_USERS = {u.strip() for u in os.environ.get("ADMIN_USERS", "").split(",") if u.strip()}

CATEGORIES = {
    "anime":      {"label": "Anime",      "adult": False, "unit": "eps"},
    "manga":      {"label": "Manga",      "adult": False, "unit": "ch"},
    "manhwa":     {"label": "Manhwa",     "adult": False, "unit": "ch"},
    "movie":      {"label": "Movies",     "adult": False, "unit": "min"},
    "drama":      {"label": "Dramas",     "adult": False, "unit": "eps"},
    "webseries":  {"label": "Web Series", "adult": False, "unit": "eps"},
    "sports":     {"label": "Sports",     "adult": False, "unit": "events"},
    "hentai":     {"label": "Hentai",     "adult": True,  "unit": "eps"},
    "adultvideo": {"label": "Adult",      "adult": True,  "unit": "min"},
}

ADULT_TYPES = {k for k, v in CATEGORIES.items() if v["adult"]}

def is_adult_type(t: str) -> bool:
    return t in ADULT_TYPES
