import uuid

_SESSIONS = {}


def _default_session():
    return {
        "tool_calls": [],
        "prefs": {"likes": [], "dislikes": [], "fav_genres": []},

        # Slots conversationnels (ce que l'user veut)
        "slots": {
            "type": None,        # "movie" | "series"
            "period": None,      # "popular" | "recent"
            "genre": None,       # ex: "science-fiction"
            "year_min": None,    # ex: 2024
            "year_max": None,    # ex: 2026
        },

        # Etat de dialogue
        "state": {
            "stage": "collecting",       # collecting | recommending | detailing
            "awaiting": None,            # None | "type" | "period" | "genre"
            "genre_skipped": False,      # l'user a dit "peu importe"
        },

        # Mémoire des derniers résultats
        "last_items": [],
        "last_index": 1,
    }


def new_session() -> str:
    sid = str(uuid.uuid4())
    _SESSIONS[sid] = _default_session()
    return sid


def get_session(session_id: str) -> dict:
    if session_id not in _SESSIONS:
        _SESSIONS[session_id] = _default_session()
    return _SESSIONS[session_id]


def update_prefs(session: dict, user_message: str) -> dict:
    """
    Extraction :
    - "j'aime X" => likes
    - "j'aime pas / je n'aime pas X" => dislikes
    - genres connus => fav_genres
    """
    msg = (user_message or "").lower()

    known_genres = [
        "science-fiction", "sf", "action", "comédie", "comedie", "drame", "thriller",
        "horreur", "fantastique", "animation", "aventure", "romance", "mystère", "mystere"
    ]

    if "j'aime pas" in msg or "je n'aime pas" in msg:
        for g in known_genres:
            if g in msg and g not in session["prefs"]["dislikes"]:
                session["prefs"]["dislikes"].append(g)

    if "j'aime" in msg and ("j'aime pas" not in msg) and ("je n'aime pas" not in msg):
        for g in known_genres:
            if g in msg and g not in session["prefs"]["likes"]:
                session["prefs"]["likes"].append(g)

    for g in known_genres:
        if g in msg and g not in session["prefs"]["fav_genres"]:
            session["prefs"]["fav_genres"].append(g)

    return session["prefs"]