from tools.scrape_search import search_titles
from tools.scrape_details import get_title_details

TOOLS = {
    "search_titles": {
        "description": "Search movies/series from a public website (live scraping).",
        "input_schema": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["movie", "series"]},
                "period": {"type": "string", "enum": ["popular", "recent"]},
                "genre": {"type": "string"},
                "year_min": {"type": "integer", "minimum": 1900, "maximum": 2100},
                "year_max": {"type": "integer", "minimum": 1900, "maximum": 2100},

                # limit = limite de résultats voulus (optionnel). Si absent, le tool peut paginer largement.
                "limit": {"type": "integer", "minimum": 1},

                # contrôle de pagination (anti-boucle infinie)
                "max_pages": {"type": "integer", "minimum": 1, "maximum": 300}
            },
            "required": ["type", "period"]
        },
        "handler": search_titles
    },
    "get_title_details": {
        "description": "Get details of a specific title (synopsis, genres, etc.) from its URL.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string"}
            },
            "required": ["url"]
        },
        "handler": get_title_details
    }
}

def list_tools():
    public = {}
    for name, meta in TOOLS.items():
        public[name] = {
            "description": meta["description"],
            "input_schema": meta["input_schema"],
        }
    return public