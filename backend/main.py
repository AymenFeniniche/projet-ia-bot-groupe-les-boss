from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests

from agent.orchestrator import handle_message
from agent.memory import new_session

# Tools (scraping)
from tools.scrape_search import search_titles
from tools.scrape_details import get_title_details

# MCP registry + execute
from mcp.registry import list_tools
from mcp.execute import execute_tool

app = FastAPI(title="CineAgent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Site vitrine (statique)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def home():
    return {"message": "CineAgent backend running. Open /static/index.html"}


# Ollama health + warm-up
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL_FOR_WARMUP = "qwen3:4b"

@app.on_event("startup")
def warmup_ollama():
    """
    Réchauffe le modèle au démarrage (première réponse plus rapide).
    Ne casse pas l'app si Ollama est éteint.
    """
    try:
        requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": OLLAMA_MODEL_FOR_WARMUP,
                "messages": [{"role": "user", "content": "Bonjour"}],
                "stream": False,
            },
            timeout=10,
        )
        print("🔥 Ollama warm-up OK")
    except Exception as e:
        print("⚠️ Ollama warm-up failed:", e)


@app.get("/api/ollama/health")
def ollama_health():
    """
    Vérifie qu'Ollama tourne + liste les modèles installés.
    Très utile en démo si quelque chose ne répond pas.
    """
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        r.raise_for_status()
        models = [m.get("name") for m in r.json().get("models", [])]
        return {"ok": True, "models": models}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# Sessions + Chat API
class NewSessionResponse(BaseModel):
    session_id: str


@app.post("/api/session/new", response_model=NewSessionResponse)
def api_new_session():
    return {"session_id": new_session()}


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    answer: str
    tool_calls: list
    sources: list


@app.post("/api/chat", response_model=ChatResponse)
def api_chat(req: ChatRequest):
    return handle_message(session_id=req.session_id, user_message=req.message)


@app.get("/api/health")
def health():
    return {"ok": True}


# Debug scraping endpoints
@app.get("/api/debug/search")
def debug_search():
    return search_titles({"limit": 5})


@app.get("/api/debug/details")
def debug_details():
    data = search_titles({"limit": 1})
    items = data.get("items", [])
    if not items:
        return {"error": "No items found in search_titles()", "source": data.get("source")}
    url = items[0].get("url")
    if not url:
        return {"error": "No url in first item", "item": items[0]}
    return get_title_details({"url": url})


# MCP Simulé (outils exposés au modèle)
@app.get("/mcp/tools")
def mcp_tools():
    """
    Retourne la liste des tools + leurs schémas d'entrée.
    Utile en démo + documentation.
    """
    return list_tools()


class MCPExecuteRequest(BaseModel):
    tool: str
    args: dict


@app.post("/mcp/execute")
def mcp_execute(req: MCPExecuteRequest):
    """
    Exécute un tool (scraping live) via la couche MCP.
    Le LLM / orchestrateur doit passer par là (séparation raisonnement/exécution).
    """
    return execute_tool(req.tool, req.args)