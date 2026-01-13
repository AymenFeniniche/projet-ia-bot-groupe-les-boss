import json
import re
import random

from agent.memory import get_session

try:
    from agent.memory import update_prefs
except Exception:
    update_prefs = None

from agent.ollama_client import ollama_chat
from agent.prompts import ROUTER_SYSTEM, ANSWER_SYSTEM
from mcp.execute import execute_tool

MODEL_NAME = "qwen3:4b"


def _safe_json(text: str) -> dict:
    """
    Rend le parsing JSON robuste.
    Extrait le premier bloc { ... } même si le modèle ajoute du texte ou ```json```.
    """
    t = (text or "").strip()

    if t.startswith("```"):
        t = t.strip("`").strip()
        if t.lower().startswith("json"):
            t = t[4:].strip()

    m = re.search(r"\{.*\}", t, re.DOTALL)
    if not m:
        raise ValueError(f"No JSON found in model output: {t[:200]}")
    return json.loads(m.group(0))


def _extract_index_from_text(msg_lower: str) -> int | None:
    m = re.search(r"\b(\d+)\b", msg_lower)
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def _human_followup() -> str:
    options = [
        "Tu veux que je te détaille laquelle ? (numéro ou titre)",
        "Laquelle te tente le plus ? Donne-moi le numéro ou le nom.",
        "Tu veux le synopsis de laquelle ? Tu peux répondre par un numéro (ex: 2) ou le titre.",
        "Tu en vois une qui t’attire ? Dis-moi juste le numéro 🙂",
        "Si tu veux, je peux te résumer celle que tu choisis (numéro ou titre).",
    ]
    return random.choice(options)


def handle_message(session_id: str, user_message: str) -> dict:
    sess = get_session(session_id)
    sess.setdefault("tool_calls", [])
    sess.setdefault("prefs", {"likes": [], "dislikes": [], "fav_genres": []})
    sess.setdefault("last_index", 1)

    tool_calls = []
    sources = []

    msg = (user_message or "").strip()
    msg_lower = msg.lower()

    if update_prefs is not None:
        try:
            update_prefs(sess, msg)
        except Exception:
            pass

    prefs = sess.get("prefs", {})

    # Router (Ollama)
    try:
        route_raw = ollama_chat(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": ROUTER_SYSTEM},
                {
                    "role": "user",
                    "content": f"Préférences connues: {json.dumps(prefs, ensure_ascii=False)}\n\nMessage: {msg}"
                },
            ],
            temperature=0.0,
        )
        route = _safe_json(route_raw)
    except Exception:
        route = {
            "intent": "other",
            "type": None,
            "period": None,
            "genre": None,
            "year_min": None,
            "year_max": None,
            "index": None,
            "title": None,
        }

    intent = route.get("intent", "other") or "other"
    content_type = route.get("type", None)  # "movie" | "series" | None
    period = route.get("period", None)      # "popular" | "recent" | None
    genre = route.get("genre", None) or ""
    year_min = route.get("year_min", None)
    year_max = route.get("year_max", None)

    # defaults raisonnables si l'utilisateur demande une reco sans préciser
    if intent == "recommend":
        if content_type not in {"movie", "series"}:
            content_type = "series" if "série" in msg_lower or "serie" in msg_lower else "movie"
        if period not in {"popular", "recent"}:
            period = "recent" if "récent" in msg_lower or "recent" in msg_lower else "popular"

    # gestion details via numéro
    explicit = _extract_index_from_text(msg_lower)
    if explicit is not None and any(k in msg_lower for k in ["détails", "details", "synopsis", "resume", "résume"]):
        intent = "details"
        index = explicit
    else:
        index = int(route.get("index") or 1)

    if index < 1:
        index = 1

    # intent = recommend
    if intent == "recommend":
        # Scrape large mais affiche qu'un top raisonnable
        DISPLAY_LIMIT = 10

        args = {
            "type": content_type,
            "period": period,
            "genre": genre,
            "year_min": year_min,
            "year_max": year_max,

            # Pagination large
            "max_pages": 60,

            # Pas de limite de résultats côté scraping
            # (le tool utilisera limit=None et paginera jusqu'à max_pages)
            "limit": None,
        }

        tool_calls.append({"tool": "search_titles", "args": args})

        try:
            out = execute_tool("search_titles", args)
        except Exception as e:
            return {
                "answer": f"Erreur lors de l'exécution de search_titles: {e}",
                "tool_calls": tool_calls,
                "sources": [],
            }

        sess["tool_calls"].append({"tool": "search_titles", "args": args, "out": out})

        if out.get("error"):
            return {
                "answer": "Je n’ai pas réussi à récupérer des données live (scraping).",
                "tool_calls": tool_calls,
                "sources": [],
            }

        items_all = out["result"]["items"]
        items = items_all[:DISPLAY_LIMIT]

        for it in items:
            if it.get("url"):
                sources.append(it["url"])

        # Rédaction “humaine” via LLM
        try:
            answer = ollama_chat(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": ANSWER_SYSTEM},
                    {
                        "role": "user",
                        "content":
                            f"Préférences utilisateur: {json.dumps(prefs, ensure_ascii=False)}\n\n"
                            "Tu reçois une liste de contenus (JSON).\n"
                            "Réponds en français, ton naturel.\n"
                            "Affiche une liste numérotée 1..N avec: titre + année si dispo + note si dispo.\n"
                            "Puis termine par UNE phrase de relance humaine (pas 'détails N').\n\n"
                            f"Demande utilisateur: {msg}\n\n"
                            f"Données JSON: {json.dumps(items, ensure_ascii=False)}\n\n"
                            f"Relance suggérée: {_human_followup()}"
                    },
                ],
                temperature=0.2,
            )
        except Exception as e:
            # fallback sans LLM
            lines = ["Voilà ce que j’ai trouvé :"]
            for i, it in enumerate(items, 1):
                title = it.get("title", "Titre")
                year = it.get("year") or "N/A"
                rating = it.get("rating") or "N/A"
                lines.append(f"{i}. {title} ({year}) — note: {rating}")
            lines.append(_human_followup())
            answer = "\n".join(lines)

        return {"answer": answer, "tool_calls": tool_calls, "sources": sources}

    # intent = details
    if intent == "details":
        last_items = None
        for call in reversed(sess["tool_calls"]):
            if call.get("tool") == "search_titles" and not call["out"].get("error"):
                last_items = call["out"]["result"]["items"]
                break

        if not last_items:
            return {
                "answer": "Je n’ai pas de liste récente. Demande-moi une recommandation d’abord 🙂",
                "tool_calls": [],
                "sources": []
            }

        idx = max(0, min(index - 1, len(last_items) - 1))
        url = last_items[idx].get("url")

        if not url:
            return {
                "answer": "Je n’ai pas l’URL de cet élément. Relance une recommandation.",
                "tool_calls": [],
                "sources": []
            }

        sess["last_index"] = idx + 1

        args = {"url": url}
        tool_calls.append({"tool": "get_title_details", "args": args})

        try:
            out = execute_tool("get_title_details", args)
        except Exception as e:
            return {
                "answer": f"Erreur lors de l'exécution de get_title_details: {e}",
                "tool_calls": tool_calls,
                "sources": [url],
            }

        sess["tool_calls"].append({"tool": "get_title_details", "args": args, "out": out})

        if out.get("error"):
            return {
                "answer": "Impossible de récupérer les détails (scraping).",
                "tool_calls": tool_calls,
                "sources": [url]
            }

        details = out["result"]
        sources.append(url)

        try:
            answer = ollama_chat(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": ANSWER_SYSTEM},
                    {
                        "role": "user",
                        "content":
                            "Tu reçois des détails (JSON). Réponds de façon naturelle.\n"
                            "Format conseillé:\n"
                            "- Titre\n- Genres\n- Durée\n- Synopsis\n"
                            "Puis termine par une question simple (ex: 'Tu veux une autre suggestion ?').\n\n"
                            f"Demande utilisateur: {msg}\n\n"
                            f"Données JSON: {json.dumps(details, ensure_ascii=False)}"
                    },
                ],
                temperature=0.2,
            )
        except Exception as e:
            d = details or {}
            title = d.get("title", "Titre")
            genres = ", ".join(d.get("genres", []) or []) or "N/A"
            runtime = d.get("runtime", "N/A")
            summary = d.get("summary", "N/A")
            answer = (
                f"**{title}**\n"
                f"- Genres: {genres}\n"
                f"- Durée: {runtime}\n"
                f"- Synopsis: {summary}\n\n"
                "Tu veux que je te propose autre chose ?"
            )

        return {"answer": answer, "tool_calls": tool_calls, "sources": sources}

    # fallback
    return {
        "answer": "Dis-moi ce que tu as envie de regarder (film ou série), et si tu veux plutôt récent ou populaire 🙂",
        "tool_calls": [],
        "sources": []
    }