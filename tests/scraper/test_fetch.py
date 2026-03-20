"""
Integration tests for the Web Scraper activities.
No mocks - uses a real local server and Playwright/httpx.
"""

import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from apps.core.config import get_settings
from apps.scraper.activities.fetch_activities import FetchActivities

# --- Local Test Server ---


class TestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        html = """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <h1>Hello Voyant</h1>
                <p id="dynamic">Initial Content</p>
                <script>
                    setTimeout(() => {
                        document.getElementById('dynamic').innerText = 'JS Rendered Content';
                    }, 500);
                </script>
            </body>
        </html>
        """
        self.wfile.write(html.encode("utf-8"))

    def log_message(self, format, *args):
        return  # Silence logging


def run_server(stop_event):
    server = HTTPServer(("localhost", 8888), TestHandler)
    while not stop_event.is_set():
        server.handle_request()
    server.server_close()


@pytest.fixture(scope="module")
def local_server():
    stop_event = threading.Event()
    thread = threading.Thread(target=run_server, args=(stop_event,))
    thread.daemon = True
    thread.start()
    yield "http://localhost:8888"
    stop_event.set()
    # Trigger one last request to break the handle_request loop
    import httpx

    try:
        httpx.get("http://localhost:8888", timeout=0.1)
    except Exception:
        pass
    thread.join(timeout=2)


@pytest.fixture(autouse=True)
def setup_env():
    # Force bypass of SSRF for local server testing
    os.environ["VOYANT_SCRAPER_ALLOW_LOCAL_HOSTS"] = "True"
    # pydantic_settings might have already cached, but get_settings is lru_cached
    get_settings.cache_clear()
    yield


# --- Tests ---


@pytest.mark.asyncio
class TestScraperIntegration:
    """
    Verifies the scraper pipeline using real network and browser stacks.
    """

    async def test_fetch_httpx(self, local_server):
        """Verify static fetch via httpx."""
        activities = FetchActivities()
        result = await activities.fetch_page({"url": local_server, "engine": "httpx"})

        assert result["status_code"] == 200
        assert "Hello Voyant" in result["html"]
        assert "Initial Content" in result["html"]

    async def test_fetch_playwright(self, local_server):
        """Verify dynamic fetch via Playwright."""
        activities = FetchActivities()
        # We use a 1000ms settle_ms to allow the script to run
        result = await activities.fetch_page(
            {"url": local_server, "engine": "playwright", "settle_ms": 1000}
        )

        assert result["status_code"] == 200
        assert "Hello Voyant" in result["html"]
        # Verify JS rendering
        assert "JS Rendered Content" in result["html"]
        assert "Initial Content" not in result["html"]
