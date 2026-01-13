import asyncio
from tools import get_titles, get_filters, scrape_details

async def main():
    data = await get_titles("series", order="asc")
    print("Total:", data["total"])
    print("Exemple:", data["items"][:3])

    print(await get_filters("series"))

    print(await scrape_details("https://www.themoviedb.org/tv/1396-breaking-bad"))

asyncio.run(main())
