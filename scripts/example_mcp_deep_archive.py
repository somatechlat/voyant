import asyncio
import os


def _setup_django() -> None:
    os.environ["VOYANT_SCRAPER_TLS_VERIFY"] = "False"
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voyant_project.settings")

    import django

    django.setup()

    from apps.core.config import get_settings

    settings = get_settings()
    settings.scraper_tls_verify = False

async def main():
    from apps.mcp.tools import tool_scrape_deep_archive

    print("Testing Generic MCP Deep Archive Tool on SERCOP...")

    # Example payload for deep archive extraction.
    payload = {
        "url": "https://www.compraspublicas.gob.ec/ProcesoContratacion/compras/PC/informacionProcesoContratacion2.cpe?idSoliCompra=LGhcHDwhCJiQJmiNZFGNrZYC1R-kbyiuOfZWlUNHBo4",
        "interaction_selectors": [
            "#tab1",  # Description
            "#tab2",  # Dates
            "#tab3",  # Products
            "#tab4"   # Files
        ],
        "download_patterns": [
            "descargar",
            "archivo",
            "bajar",
            ".pdf"
        ],
        "target_dir": "COMPRASSCRAPE/LGhcHDwhCJiQJmiNZFGNrZYC1R-kbyiuOfZWlUNHBo4"
    }

    # We call the tool exactly as the MCP SDK would wrap it
    result = await tool_scrape_deep_archive(**payload)

    print("\nMCP tool execution finished.")
    print(f"Final DOM State captured: {len(result.get('interaction_states', {}))} states.")
    print(f"Files Downloaded via Generic Pattern Matching: {len(result.get('files_downloaded', []))}")

    # Check the data dump
    manifest_path = "COMPRASSCRAPE/LGhcHDwhCJiQJmiNZFGNrZYC1R-kbyiuOfZWlUNHBo4/deep_archive_manifest.json"
    if os.path.exists(manifest_path):
        size = os.path.getsize(manifest_path)
        print(f"Manifest saved correctly. Size: {size} bytes")

if __name__ == "__main__":
    _setup_django()
    asyncio.run(main())
