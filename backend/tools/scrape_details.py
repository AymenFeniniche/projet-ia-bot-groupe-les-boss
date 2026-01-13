from bs4 import BeautifulSoup
from tools.http import fetch

def get_title_details(args: dict) -> dict:
    url = args["url"]
    html = fetch(url)
    soup = BeautifulSoup(html, "html.parser")

    title_el = soup.select_one("h2 a")
    summary_el = soup.select_one("div.overview p")
    runtime_el = soup.select_one("span.runtime")
    genre_els = soup.select("span.genres a")

    title = title_el.text.strip() if title_el else None
    summary = summary_el.text.strip() if summary_el else None
    runtime = runtime_el.text.strip() if runtime_el else None
    genres = [g.text.strip() for g in genre_els]

    if not title:
        raise RuntimeError("TMDB details scraping failed")

    return {
        "title": title,
        "summary": summary,
        "runtime": runtime,
        "genres": genres,
        "source": url
    }