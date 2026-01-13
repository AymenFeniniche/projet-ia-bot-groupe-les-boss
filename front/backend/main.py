from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Literal
from pydantic import BaseModel
import httpx

from tools import get_titles, get_filters

TitleType = Literal["movie", "series"]
OrderType = Literal["asc", "desc"]

app = FastAPI(title="IA Bot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/titles")
async def api_titles(
    type: TitleType = Query(..., description="movie ou series"),
    q: str | None = None,
    genre: str | None = None,
    year: int | None = None,
    order: OrderType = "asc",
):
    return await get_titles(
        type,
        q=q,
        genre=genre,
        year=year,
        order=order,
    )

@app.get("/api/filters")
async def api_filters(
    type: TitleType = Query(..., description="movie ou series"),
):
    return await get_filters(type)

@app.get("/ping")
def ping():
    return {"status": "ok"}

class ChatRequest(BaseModel):
    message: str
    model: str | None = "llama3.2"  


@app.post("/api/chat")
async def api_chat(payload: ChatRequest):

    prompt = f"""
Tu es un assistant de recommandation de films/séries.

Règle 1 : si la demande est vague (ex: "conseille-moi un film" sans genre / mood / époque / film vs série),
pose d'abord 2 questions maximum pour préciser (genre, ambiance, époque, durée, pays, film ou série).
Ne donne pas de liste tant que l'utilisateur n'a pas répondu.

Règle 2 : si l'utilisateur donne au moins un critère (genre OU ambiance OU année/époque OU film/série),
alors réponds avec une liste claire (maximum 5).

Format liste :
- Titre — année — genre — 1 raison courte

Important : si tu fais une liste, utilise des puces "-" (pas de paragraphe).

Message utilisateur :
{payload.message}
"""

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            "http://127.0.0.1:11434/api/generate",
            json={
                "model": payload.model or "llama3.2",
                "prompt": prompt,
                "stream": False
            }
        )

    data = response.json()

    return {
        "answer": data.get("response", "").strip()
    }
