import re
import unicodedata
from urllib.parse import urlencode

from bs4 import BeautifulSoup
from tools.http import fetch

BASE_URL = "https://www.themoviedb.org"

# Utils

def _strip_accents(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def _norm(s: str) -> str:
    """
    Normalise une chaîne pour matcher des genres de façon robuste.
    ex: "Science-Fiction & Fantastique" -> "science fiction fantastique"
        "SC" -> "sc"
        "sci-fi" -> "sci fi"
    """
    s = (s or "").strip().lower()
    s = _strip_accents(s)
    s = s.replace("&", " ")
    s = re.sub(r"[_/\\\-]+", " ", s)
    s = re.sub(r"[^a-z0-9\s]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _looks_like_scifi(s: str) -> bool:
    """
    Heuristique pour capter "SC", "sf", "sci fi", etc.
    """
    t = _norm(s)
    if t in {"sf", "sc", "scifi", "sci fi", "sci"}:
        return True
    if "science fiction" in t or "sciencefiction" in t:
        return True
    return False


def _pick_best_genre_id(user_genre: str, genres_map: dict[str, int]) -> int | None:
    """
    Match souple: exact -> contains -> sci-fi heuristic -> overlap mots.
    genres_map: { normalized_genre_name: id }
    """
    if not user_genre:
        return None

    ug = _norm(user_genre)
    if not ug:
        return None

    # 1) exact
    if ug in genres_map:
        return genres_map[ug]

    # 2) inclusion
    for k, gid in genres_map.items():
        if ug in k or k in ug:
            return gid

    # 3) sci-fi (souvent appelé SF/SC/etc.)
    if _looks_like_scifi(ug):
        # on cherche une clé contenant "science fiction"
        for k, gid in genres_map.items():
            if "science fiction" in k:
                return gid
        # TV: "Science-Fiction & Fantastique" => parfois on n'a que fantastique dans la clé normalisée
        for k, gid in genres_map.items():
            if "fantastique" in k:
                return gid

    # 4) overlap mots
    ug_words = set(ug.split())
    best_gid = None
    best_score = 0
    for k, gid in genres_map.items():
        kw = set(k.split())
        score = len(ug_words & kw)
        if score > best_score:
            best_score = score
            best_gid = gid

    return best_gid if best_score >= 1 else None


# Scrape dynamic genre map (cache)

_genre_cache: dict[str, dict[str, int]] = {}  # {"movie": {...}, "tv": {...}}

def _scrape_genres_map(content_type: str) -> dict[str, int]:
    """
    Scrape la liste des genres depuis la page Discover (HTML).
    Pas d'IDs hardcodés.
    """
    key = "tv" if content_type == "series" else "movie"
    if key in _genre_cache:
        return _genre_cache[key]

    url = f"{BASE_URL}/discover/{key}?language=fr-FR"
    html = fetch(url)
    soup = BeautifulSoup(html, "html.parser")

    ul = soup.select_one("ul#with_genres") or soup.find("ul", {"id": "with_genres"})
    genres: dict[str, int] = {}

    if ul:
        for li in ul.select("li[data-value]"):
            gid = li.get("data-value")
            a = li.select_one("a")
            name = a.get_text(strip=True) if a else li.get_text(strip=True)
            if not gid or not name:
                continue
            try:
                genres[_norm(name)] = int(gid)
            except Exception:
                continue

    if not genres:
        raise RuntimeError("TMDB scraping failed: impossible de récupérer la liste des genres (discover page)")

    _genre_cache[key] = genres
    return genres


# Main tool

def search_titles(args: dict) -> dict:
    """
    args (via MCP / orchestrator):
      - type: "movie" | "series"
      - period: "popular" | "recent"
      - genre: str (optionnel)
      - year_min: int (optionnel)
      - year_max: int (optionnel)
      - limit: int (optionnel) -> nombre d'items max
      - max_pages: int (optionnel) -> pages max à scraper
    """
    content_type = (args.get("type") or "movie").strip().lower()
    period = (args.get("period") or "popular").strip().lower()

    user_genre = (args.get("genre") or "").strip()

    # sans limite "par défaut" côté tool (mais contrôlé par max_pages)
    limit = args.get("limit", None)
    try:
        limit = int(limit) if limit is not None and str(limit).strip() else None
    except Exception:
        limit = None

    max_pages = args.get("max_pages", 60)
    try:
        max_pages = int(max_pages)
    except Exception:
        max_pages = 60
    max_pages = max(1, min(max_pages, 300))

    year_min = args.get("year_min", None)
    year_max = args.get("year_max", None)
    try:
        year_min = int(year_min) if year_min is not None and str(year_min).strip() else None
    except Exception:
        year_min = None
    try:
        year_max = int(year_max) if year_max is not None and str(year_max).strip() else None
    except Exception:
        year_max = None

    is_tv = content_type in {"series", "tv", "show"}
    path = "tv" if is_tv else "movie"

    # sort_by
    if is_tv:
        sort_by = "popularity.desc" if period == "popular" else "first_air_date.desc"
    else:
        sort_by = "popularity.desc" if period == "popular" else "primary_release_date.desc"

    # genres dynamiques (scrape)
    genres_map = _scrape_genres_map("series" if is_tv else "movie")
    genre_id = _pick_best_genre_id(user_genre, genres_map) if user_genre else None

    params = {
        "language": "fr-FR",
        "sort_by": sort_by,
        "page": 1,
    }

    # filtre genre
    if genre_id is not None:
        params["with_genres"] = str(genre_id)

    # filtre dates
    if year_min is not None:
        if is_tv:
            params["first_air_date.gte"] = f"{year_min}-01-01"
        else:
            params["primary_release_date.gte"] = f"{year_min}-01-01"

    if year_max is not None:
        if is_tv:
            params["first_air_date.lte"] = f"{year_max}-12-31"
        else:
            params["primary_release_date.lte"] = f"{year_max}-12-31"

    items = []
    source_first = None

    for page in range(1, max_pages + 1):
        params["page"] = page
        url = f"{BASE_URL}/discover/{path}?{urlencode(params)}"
        if source_first is None:
            source_first = url

        html = fetch(url)
        soup = BeautifulSoup(html, "html.parser")

        cards = soup.select("div.card.style_1")
        if not cards:
            cards = soup.select("div.card")

        if not cards:
            break

        for card in cards:
            title_el = card.select_one("h2 a")
            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            href = title_el.get("href")
            full_url = f"{BASE_URL}{href}" if href else None

            score_el = card.select_one("div.user_score_chart")
            rating = score_el.get("data-percent") if score_el else None

            date_el = card.select_one("span.release_date")
            year = None
            if date_el:
                date_txt = date_el.get_text(" ", strip=True)
                m = re.search(r"\b(19\d{2}|20\d{2})\b", date_txt)
                if m:
                    year = m.group(1)

            items.append(
                {
                    "title": title,
                    "year": year,
                    "rating": rating,
                    "url": full_url,
                }
            )

            if limit is not None and len(items) >= limit:
                break

        if limit is not None and len(items) >= limit:
            break

    if not items:
        raise RuntimeError("TMDB scraping failed: aucun résultat (discover)")

    return {
        "items": items if limit is None else items[:limit],
        "source": source_first or f"{BASE_URL}/discover/{path}",
        "applied_filters": {
            "type": "series" if is_tv else "movie",
            "period": period,
            "genre_query": user_genre,
            "genre_id": genre_id,
            "year_min": year_min,
            "year_max": year_max,
            "max_pages": max_pages,
            "limit": limit,
        },
    }