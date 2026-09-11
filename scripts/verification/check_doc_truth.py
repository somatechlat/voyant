"""
check_doc_truth — Verify documentation numbers against code ground truth.

Measures quantitative facts from the codebase and fails (exit 1) when
numeric claims in README.md / docs/operations/DEPLOYMENT.md disagree.

Measured quantities:
  - Ninja route decorators (@<router>.get/post/put/delete/patch) across apps/
  - @mcp_app.tool registrations in apps/mcp/
  - Voyant apps ("apps.*") in voyant_project/settings.py INSTALLED_APPS
  - Paths in docs/api/openapi.json

Run: python scripts/verification/check_doc_truth.py
"""

import json
import logging
import re
import sys
from collections import Counter
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="{message}", style="{")
logger = logging.getLogger("check_doc_truth")

ROOT = Path(__file__).resolve().parents[2]

ROUTE_RE = re.compile(r"@(\w*router)\.(get|post|put|delete|patch)\(")
MCP_TOOL_RE = re.compile(r"@mcp_app\.tool\b")
APP_RE = re.compile(r'"(apps\.\w+)"')

# (file, regex, metric key) — regex group 1 must capture the claimed number.
CLAIM_PATTERNS = [
    ("README.md", r"(\d+) tools for agent orchestration", "mcp_tools"),
    ("README.md", r"MCP Tools Available \((\d+) Total\)", "mcp_tools"),
    ("README.md", r"MCP Tools:\*\*\s*(\d+) registered tools", "mcp_tools"),
    ("README.md", r"REST API:\*\*\s*(\d+) endpoints", "endpoints"),
    ("README.md", r"\((\d+) Django apps\)", "django_apps"),
    ("docs/operations/DEPLOYMENT.md", r"\((\d+) endpoints under", "endpoints"),
    ("docs/operations/DEPLOYMENT.md", r"\((\d+) tools at", "mcp_tools"),
]


def measure_routes():
    """Count Ninja route decorators per (module, router) across apps/."""
    per_router = Counter()
    for path in sorted((ROOT / "apps").rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        for name, _method in ROUTE_RE.findall(path.read_text(encoding="utf-8")):
            per_router[f"{path.relative_to(ROOT)} ({name})"] += 1
    return per_router


def measure_mcp_tools():
    """Count @mcp_app.tool registrations in apps/mcp/."""
    total = 0
    for path in sorted((ROOT / "apps" / "mcp").glob("*.py")):
        total += len(MCP_TOOL_RE.findall(path.read_text(encoding="utf-8")))
    return total


def measure_apps():
    """Count installed Voyant apps ('apps.*') in settings INSTALLED_APPS."""
    text = (ROOT / "voyant_project" / "settings.py").read_text(encoding="utf-8")
    return len(set(APP_RE.findall(text)))


def measure_openapi_paths():
    path = ROOT / "docs" / "api" / "openapi.json"
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as fh:
        return len(json.load(fh).get("paths", {}))


def extract_claims():
    """Extract numeric claims from docs using CLAIM_PATTERNS."""
    claims = []
    for rel_path, pattern, metric in CLAIM_PATTERNS:
        full = ROOT / rel_path
        if not full.exists():
            logger.warning("⚠️  %s not found — skipping claims", rel_path)
            continue
        lines = full.read_text(encoding="utf-8").splitlines()
        matched = False
        for lineno, line in enumerate(lines, start=1):
            for value in re.findall(pattern, line):
                matched = True
                claims.append(
                    {"file": rel_path, "line": lineno, "metric": metric, "claimed": int(value)}
                )
        if not matched:
            logger.warning("⚠️  No '%s' claim matched in %s", metric, rel_path)
    return claims


def main():
    per_router = measure_routes()
    measured = {
        "endpoints": sum(per_router.values()),
        "mcp_tools": measure_mcp_tools(),
        "django_apps": measure_apps(),
        "openapi_paths": measure_openapi_paths(),
    }

    logger.info("Ground truth (measured from code)")
    logger.info("─" * 60)
    logger.info("  endpoints (Ninja route decorators): %d", measured["endpoints"])
    for router, count in sorted(per_router.items()):
        logger.info("    %-48s %3d", router, count)
    logger.info("  MCP tools (@mcp_app.tool):            %d", measured["mcp_tools"])
    logger.info("  Django apps (apps.* installed):       %d", measured["django_apps"])
    logger.info("  openapi.json paths:                   %s", measured["openapi_paths"])
    logger.info("")

    claims = extract_claims()
    logger.info("Documentation claims")
    logger.info("─" * 60)
    logger.info("  %-16s %-8s %-8s %s", "metric", "measured", "claimed", "location")
    failures = 0
    for claim in claims:
        expected = measured[claim["metric"]]
        ok = claim["claimed"] == expected
        status = "OK " if ok else "FAIL"
        if not ok:
            failures += 1
        logger.info(
            "  %-16s %-8s %-8s %s:%s  [%s]",
            claim["metric"],
            expected,
            claim["claimed"],
            claim["file"],
            claim["line"],
            status,
        )

    if not claims:
        logger.error("❌ No claims extracted — check CLAIM_PATTERNS against doc phrasing")
        return 1
    if measured["openapi_paths"] is None:
        logger.error("❌ docs/api/openapi.json missing — run 'python manage.py export_openapi'")
        failures += 1

    if failures:
        logger.error("❌ %d doc claim(s) disagree with measured ground truth", failures)
        return 1
    logger.info("✅ All %d doc claims match measured ground truth", len(claims))
    return 0


if __name__ == "__main__":
    sys.exit(main())
