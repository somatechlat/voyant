"""
Voyant Scraper — Fetch Activities.

Temporal activities for web page fetching using Playwright, httpx, and Scrapy.
Pure mechanical execution — NO intelligence, NO LLM, NO decision making.

Extracted from scraper/activities.py (Rule 245 compliance — 949-line split).
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict

from temporalio import activity
from temporalio.exceptions import ApplicationError

from apps.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class FetchActivities:
    """
    Web fetch activities: Playwright, httpx, Scrapy, and deep archive.

    All fetch activities enforce SSRF protection via apps.scraper.security.validate_url.
    Engine selection is configurable per-request.
    """

    @staticmethod
    def _heartbeat_safe(message: str) -> None:
        """Emit Temporal heartbeat only when running inside activity context."""
        try:
            activity.heartbeat(message)
        except RuntimeError:
            # REST/MCP direct execution path (not Temporal activity runtime).
            return

    @activity.defn(name="fetch_page")
    async def fetch_page(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch a web page using a specified engine (Playwright, httpx, or Scrapy).
        This activity is a mechanical executor and includes SSRF protection.

        Args:
            params:
                - url (str): The URL to fetch.
                - engine (str): 'playwright', 'httpx', or 'scrapy'. Defaults to configured default.
                - wait_for (str, optional): CSS selector to wait for before returning content.
                - scroll (bool): Whether to scroll to the bottom of the page.
                - timeout (int): Request timeout in seconds.

        Returns:
            Dict with html, url, status_code, fetched_at.

        Raises:
            ApplicationError: If SSRF protection blocks the URL or the fetch fails.
        """
        from apps.scraper.security import SSRFError, validate_url

        url = params.get("url")
        engine = params.get("engine", settings.scraper_default_engine)
        wait_for = params.get("wait_for")
        scroll = params.get("scroll", False)
        timeout = params.get("timeout", settings.scraper_default_timeout_seconds)
        wait_until = params.get("wait_until") or settings.scraper_playwright_wait_until
        settle_ms = params.get("settle_ms")
        if settle_ms is None:
            settle_ms = settings.scraper_playwright_settle_ms_default
        block_resources = params.get("block_resources")
        if block_resources is None:
            block_resources = settings.scraper_playwright_block_resources_default
        capture_json = params.get(
            "capture_json", settings.scraper_playwright_capture_json_default
        )
        capture_url_contains = params.get("capture_url_contains") or None
        capture_max_bytes = params.get("capture_max_bytes")
        if capture_max_bytes is None:
            capture_max_bytes = settings.scraper_playwright_capture_max_bytes
        capture_max_items = params.get("capture_max_items")
        if capture_max_items is None:
            capture_max_items = settings.scraper_playwright_capture_max_items

        # SSRF Protection (Zero-Bypass)
        try:
            validate_url(url)
        except SSRFError as e:
            raise ApplicationError(f"SSRF blocked: {e}", non_retryable=True)

        self._heartbeat_safe(f"Fetching {url} with {engine}")

        try:
            if engine == "playwright":
                result = await self._fetch_playwright(
                    url,
                    wait_for=wait_for,
                    scroll=scroll,
                    timeout=timeout,
                    wait_until=str(wait_until),
                    settle_ms=int(settle_ms),
                    block_resources=bool(block_resources),
                    capture_json=bool(capture_json),
                    capture_url_contains=capture_url_contains,
                    capture_max_bytes=int(capture_max_bytes),
                    capture_max_items=int(capture_max_items),
                )
            elif engine == "httpx":
                result = await self._fetch_httpx(url, timeout)
            elif engine == "scrapy":
                result = await self._fetch_scrapy(url, timeout)
            else:
                # Default to httpx for unknown engines
                result = await self._fetch_httpx(url, timeout)

            return result

        except ApplicationError:
            raise
        except Exception as e:
            logger.error(f"Fetch failed for {url}: {e}")
            raise ApplicationError(f"Fetch failed: {e}", non_retryable=False)

    async def _fetch_playwright(
        self,
        url: str,
        wait_for: str | None = None,
        scroll: bool = False,
        timeout: int = 30,
        wait_until: str = "domcontentloaded",
        settle_ms: int = 0,
        block_resources: bool = True,
        capture_json: bool = False,
        capture_url_contains: list[str] | None = None,
        capture_max_bytes: int = 524288,
        capture_max_items: int = 25,
    ) -> Dict[str, Any]:
        """Fetch a URL using Playwright to support JavaScript rendering."""
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            captured_json: list[dict[str, Any]] = []
            capture_tasks: set[asyncio.Task] = set()
            capturing_enabled = True

            browser = None
            context = None
            page = None
            response = None
            html = ""

            try:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent=settings.scraper_playwright_user_agent,
                    locale=settings.scraper_playwright_locale,
                )
                page = await context.new_page()

                if block_resources:

                    async def _route_handler(route, request) -> None:
                        try:
                            if request.resource_type in ("image", "media", "font"):
                                await route.abort()
                            else:
                                await route.continue_()
                        except Exception:
                            try:
                                await route.continue_()
                            except Exception:
                                return

                    await page.route("**/*", _route_handler)

                async def _maybe_capture_response(response) -> None:
                    try:
                        if not capture_json:
                            return
                        if len(captured_json) >= capture_max_items:
                            return
                        req = response.request
                        if req.resource_type not in ("xhr", "fetch"):
                            return
                        if response.status < 200 or response.status >= 300:
                            return
                        resp_url = str(response.url)
                        if capture_url_contains and not any(
                            s in resp_url for s in capture_url_contains
                        ):
                            return
                        ct = (response.headers or {}).get("content-type", "")
                        if "json" not in (ct or "").lower():
                            return
                        if len(captured_json) >= capture_max_items:
                            return
                        try:
                            body = await response.text()
                        except Exception:
                            return
                        if body is None or len(body) > capture_max_bytes:
                            return
                        try:
                            parsed = json.loads(body)
                        except Exception:
                            return
                        captured_json.append(
                            {
                                "url": resp_url,
                                "status": response.status,
                                "content_type": ct,
                                "body": parsed,
                            }
                        )
                    except Exception:
                        return

                if capture_json:

                    def _on_response(response) -> None:
                        nonlocal capturing_enabled
                        if not capturing_enabled:
                            return
                        try:
                            task = asyncio.create_task(
                                _maybe_capture_response(response)
                            )
                        except RuntimeError:
                            return
                        capture_tasks.add(task)
                        task.add_done_callback(lambda t: capture_tasks.discard(t))

                    page.on("response", _on_response)

                response = await page.goto(
                    url,
                    wait_until=wait_until,
                    timeout=timeout * 1000,
                )

                if wait_for:
                    await page.wait_for_selector(wait_for, timeout=timeout * 1000)

                if scroll:
                    await page.evaluate(
                        "window.scrollTo(0, document.body.scrollHeight)"
                    )
                    await page.wait_for_timeout(1000)

                if settle_ms and settle_ms > 0:
                    await page.wait_for_timeout(settle_ms)

                html = await page.content()
            finally:
                capturing_enabled = False
                if capture_tasks:
                    try:
                        await asyncio.gather(
                            *list(capture_tasks), return_exceptions=True
                        )
                    except Exception:
                        pass
                for obj in [page, context, browser]:
                    try:
                        if obj is not None:
                            await obj.close()
                    except Exception:
                        pass

            result = {
                "html": html,
                "url": url,
                "status_code": response.status if response else 0,
                "fetched_at": datetime.utcnow().isoformat(),
            }
            if capture_json:
                result["captured_json"] = captured_json
            return result

    @activity.defn(name="deep_archive")
    async def deep_archive(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generic deep archival scrape. Connects to obfuscated SPAs/tabbed interfaces,
        invokes UI clicks programmatically, and intercepts/downloads matching files.

        Args:
            params:
                - url (str): Target URL.
                - interaction_selectors (list[str]): CSS selectors to click.
                - download_patterns (list[str]): URL substring patterns for file detection.
                - target_dir (str): Local directory to store downloaded files.
                - wait_settle_ms (int): Post-interaction settle time in milliseconds.
                - timeout_ms (int): Playwright navigation timeout in milliseconds.
        """
        from pathlib import Path
        from urllib.parse import urljoin

        import httpx
        from playwright.async_api import async_playwright

        from apps.scraper.security import SSRFError, validate_url

        url = params.get("url")
        interaction_selectors = params.get("interaction_selectors", [])
        download_patterns = params.get("download_patterns", [])
        target_dir = params.get("target_dir", "scrapes/unknown")
        wait_settle_ms = params.get("wait_settle_ms", 2000)
        timeout_ms = params.get("timeout_ms", 60000)

        self._heartbeat_safe(f"Deep Archiving: {url}")

        try:
            validate_url(url)
        except SSRFError as e:
            raise ApplicationError(f"SSRF blocked: {e}", non_retryable=True)

        out_dir = Path(target_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        files_dir = out_dir / "files"
        files_dir.mkdir(exist_ok=True)

        extracted_data = {
            "source_url": url,
            "target_dir": target_dir,
            "interaction_states": {},
            "files_downloaded": [],
        }

        async def download_file(target_url, filename):
            self._heartbeat_safe(f"Downloading {filename}...")
            try:
                async with httpx.AsyncClient(verify=False, timeout=60.0) as client:
                    resp = await client.get(target_url)
                    if resp.status_code == 200:
                        with open(files_dir / filename, "wb") as f:
                            f.write(resp.content)
                        return True
            except Exception as e:
                logger.error(f"Failed to download {target_url}: {e}")
            return False

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(ignore_https_errors=True)
            page = await context.new_page()
            page.on("popup", lambda popup: None)

            try:
                await page.goto(url, wait_until="networkidle", timeout=timeout_ms)
                extracted_data["interaction_states"]["baseline"] = await page.content()

                for selector in interaction_selectors:
                    self._heartbeat_safe(f"Clicking selector: {selector}")
                    try:
                        element = await page.wait_for_selector(selector, timeout=10000)
                        if element:
                            await element.click()
                            await page.wait_for_timeout(wait_settle_ms)
                            extracted_data["interaction_states"][
                                selector
                            ] = await page.content()
                    except Exception as e:
                        logger.warning(f"Failed to interact with {selector}: {e}")

                if download_patterns:
                    self._heartbeat_safe("Scanning DOM for file downloads...")
                    file_links = await page.query_selector_all("a")
                    for link in file_links:
                        href = await link.get_attribute("href")
                        if not href:
                            continue
                        matched = any(
                            pattern.lower() in href.lower()
                            for pattern in download_patterns
                        )
                        if matched:
                            full_url = urljoin(page.url, href)
                            safe_name = f"artifact_{len(extracted_data['files_downloaded'])}.download"
                            if "archivo=" in href.lower():
                                safe_name = href.split("=")[-1].split("&")[0][:50]
                            elif href.split("?")[0].endswith(".pdf"):
                                safe_name = f"artifact_{len(extracted_data['files_downloaded'])}.pdf"
                            extracted_data["files_downloaded"].append(
                                {"url": full_url, "filename": safe_name}
                            )
                            await download_file(full_url, safe_name)
                        elif "javascript" in href.lower() and "'" in href:
                            extracted_path = href.split("'")[1]
                            matched_js = any(
                                pattern.lower() in extracted_path.lower()
                                for pattern in download_patterns
                            )
                            if matched_js:
                                full_url = urljoin(page.url, extracted_path)
                                safe_name = f"js_artifact_{len(extracted_data['files_downloaded'])}.download"
                                if "archivo=" in extracted_path.lower():
                                    safe_name = extracted_path.split("=")[-1].split(
                                        "&"
                                    )[0][:50]
                                extracted_data["files_downloaded"].append(
                                    {"url": full_url, "filename": safe_name}
                                )
                                await download_file(full_url, safe_name)

            except Exception as e:
                logger.error(f"Deep archive failed during execution: {e}")
                extracted_data["error"] = str(e)
            finally:
                await browser.close()

            import json as _json

            json_path = out_dir / "deep_archive_manifest.json"
            with open(json_path, "w", encoding="utf-8") as f:
                _json.dump(extracted_data, f, indent=2, ensure_ascii=False)

            return extracted_data

    async def _fetch_httpx(self, url: str, timeout: int = 30) -> Dict[str, Any]:
        """Fetch a URL using httpx for fast static HTML retrieval."""
        import ssl

        import certifi
        import httpx

        if not settings.scraper_tls_verify:
            verify: bool | ssl.SSLContext = False
        elif settings.scraper_tls_trust_store == "certifi":
            verify = ssl.create_default_context(cafile=certifi.where())
        else:
            verify = ssl.create_default_context()

        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            verify=verify,
        ) as client:
            response = await client.get(
                url,
                headers={
                    "User-Agent": settings.scraper_http_user_agent,
                    "Accept-Language": settings.scraper_http_accept_language,
                },
            )
            return {
                "html": response.text,
                "url": str(response.url),
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "fetched_at": datetime.utcnow().isoformat(),
            }

    async def _fetch_scrapy(self, url: str, timeout: int = 30) -> Dict[str, Any]:
        """Fetch a URL using Scrapy patterns. Falls back to httpx pending full integration."""
        return await self._fetch_httpx(url, timeout)
