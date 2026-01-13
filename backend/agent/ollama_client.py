import requests

OLLAMA_URL = "http://localhost:11434"

def ollama_chat(model: str, messages: list[dict], temperature: float = 0.2) -> str:
    r = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        },
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    return data["message"]["content"]