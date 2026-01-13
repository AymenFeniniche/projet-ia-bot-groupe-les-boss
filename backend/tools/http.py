import time
import requests

_LAST_CALL = 0.0

def fetch(url: str, timeout: int = 10, min_interval_sec: float = 1.0) -> str:
    global _LAST_CALL
    now = time.time()
    wait = min_interval_sec - (now - _LAST_CALL)
    if wait > 0:
        time.sleep(wait)

    headers = {
        "User-Agent": "CineAgentBot/1.0 (educational; contact: your-email@example.com)",
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    }
    resp = requests.get(url, headers=headers, timeout=timeout)
    _LAST_CALL = time.time()
    resp.raise_for_status()
    return resp.text