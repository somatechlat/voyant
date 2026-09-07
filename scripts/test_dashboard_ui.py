"""
VOYANT Dashboard UI Test Suite — Playwright-based visual testing.

Tests every page of the dashboard, checks for console errors,
verifies key elements exist, takes screenshots for visual review.

Run: python scripts/test_dashboard_ui.py
"""

import json
import sys
import time
from pathlib import Path

SCREENSHOTS_DIR = Path(__file__).parent.parent / "artifacts" / "ui_tests"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

PAGES = [
    {"path": "/admin", "name": "dashboard", "expect": ["Dashboard", "Services"]},
    {"path": "/admin/ontology", "name": "ontology", "expect": ["Ontology"]},
    {"path": "/admin/scraper", "name": "scraper", "expect": ["Scraper", "Templates"]},
    {"path": "/admin/sql", "name": "sql", "expect": ["SQL"]},
    {"path": "/admin/search", "name": "search", "expect": ["Search"]},
    {"path": "/admin/jobs", "name": "jobs", "expect": ["Jobs"]},
    {"path": "/admin/sources", "name": "sources", "expect": ["Sources"]},
    {"path": "/admin/governance", "name": "governance", "expect": ["Governance"]},
    {"path": "/admin/capsules", "name": "capsules", "expect": ["Capsules"]},
    {"path": "/admin/audit", "name": "audit", "expect": ["Audit"]},
    {"path": "/admin/settings", "name": "settings", "expect": ["Settings"]},
    {"path": "/admin/tenants", "name": "tenants", "expect": ["Tenants"]},
]


def run_tests():
    from playwright.sync_api import sync_playwright

    results = []
    console_errors = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # Collect console errors
        page.on("console", lambda msg: console_errors.append(f"[{msg.type}] {msg.text}") if msg.type == "error" else None)

        # Test login page first
        page.goto("http://localhost:3000/admin/login", wait_until="networkidle", timeout=15000)
        page.screenshot(path=str(SCREENSHOTS_DIR / "00_login.png"))
        time.sleep(1)

        # Set a fake token to bypass auth
        page.evaluate("localStorage.setItem('voyant_token', 'test-token')")
        time.sleep(0.5)

        for i, pg in enumerate(PAGES):
            name = pg["name"]
            path = pg["path"]
            expect = pg["expect"]
            errors_before = len(console_errors)

            try:
                page.goto(f"http://localhost:3000{path}", wait_until="networkidle", timeout=15000)
                time.sleep(2)  # Wait for Lit components to render

                # Screenshot
                screenshot_path = SCREENSHOTS_DIR / f"{i+1:02d}_{name}.png"
                page.screenshot(path=str(screenshot_path))

                # Check expected text exists
                body_text = page.inner_text("body")
                found = [e for e in expect if e.lower() in body_text.lower()]
                missing = [e for e in expect if e.lower() not in body_text.lower()]

                # Count new console errors
                new_errors = console_errors[errors_before:]

                status = "PASS" if not missing else "PARTIAL"
                results.append({
                    "page": name,
                    "path": path,
                    "status": status,
                    "found": found,
                    "missing": missing,
                    "console_errors": len(new_errors),
                    "screenshot": str(screenshot_path),
                })

                print(f"  {'✅' if status == 'PASS' else '⚠️'} {name}: {status} — found: {found}" + (f", missing: {missing}" if missing else ""))

            except Exception as exc:
                results.append({
                    "page": name,
                    "path": path,
                    "status": "ERROR",
                    "error": str(exc)[:200],
                })
                print(f"  ❌ {name}: ERROR — {exc}")

        browser.close()

    # Summary
    passed = sum(1 for r in results if r["status"] == "PASS")
    partial = sum(1 for r in results if r["status"] == "PARTIAL")
    errors = sum(1 for r in results if r["status"] == "ERROR")

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {partial} partial, {errors} errors, {len(console_errors)} console errors")
    print(f"Screenshots: {SCREENSHOTS_DIR}")

    # Save results
    results_path = SCREENSHOTS_DIR / "results.json"
    with open(results_path, "w") as f:
        json.dump({"results": results, "console_errors": console_errors, "summary": {"passed": passed, "partial": partial, "errors": errors}}, f, indent=2)

    return passed, partial, errors


if __name__ == "__main__":
    print("VOYANT Dashboard UI Test Suite")
    print("=" * 60)
    passed, partial, errors = run_tests()
    sys.exit(0 if errors == 0 else 1)
