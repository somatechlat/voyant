import asyncio
import json
import os


def _setup_django() -> None:
    os.environ["VOYANT_SCRAPER_TLS_VERIFY"] = "False"
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voyant_project.settings")

    import django

    django.setup()

    from apps.core.config import get_settings

    settings = get_settings()
    settings.scraper_tls_verify = False

async def search_year_keyword(year, keyword):
    from apps.scraper.activities import ScrapeActivities

    activity = ScrapeActivities()
    url = f"https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/api/search_ocds?year={year}&search={keyword}"

    result = await activity.fetch_page({
        "url": url,
        "engine": "httpx",
        "timeout": 30,
        "capture_json": False
    })

    raw = result.get("html") or result.get("content", "{}")
    try:
        data = json.loads(raw)
        records = data if isinstance(data, list) else data.get("data", [])
        return records
    except Exception:
        return []

async def main():
    keywords = [
        "inteligencia artificial",
        "machine learning",
        "aprendizaje",
        "chatbot",
        "automatizacion",
        "algoritmo",
        "datos",
        "nube",
        "analitica"
    ]
    years = [2026, 2025, 2024]

    print("Searching SERCOP for AI/Tech related procurements...")

    for year in years:
        for keyword in keywords:
            records = await search_year_keyword(year, keyword)
            if records and len(records) > 0:
                print(f"\nFound {len(records)} records for '{keyword}' in {year}")
                print(f"Sample Record from {year}:")
                sample = {
                    "buyer": records[0].get("buyer"),
                    "suppliers": records[0].get("suppliers"),
                    "description": str(records[0].get("description") or "")[:150] + "...",
                    "amount": records[0].get("amount"),
                    "title": records[0].get("title")
                }
                print(json.dumps(sample, indent=2, ensure_ascii=False))
            else:
                print(f"No records for '{keyword}' in {year}")

if __name__ == "__main__":
    _setup_django()
    asyncio.run(main())
