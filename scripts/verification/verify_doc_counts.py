"""
verify_doc_counts — CI lint for documentation numerical truth.

Measures actual counts from the codebase and compares them against an
authoritative config file (scripts/verification/doc_counts.json).  Fails
(exit 1) when any count drifts, preventing stale documentation from merging.

Measured quantities:
  - REST API endpoints (Ninja route decorators across apps/)
  - MCP tools (@mcp_app.tool registrations in apps/mcp/)
  - Django apps (apps.* in INSTALLED_APPS)
  - OpenAPI paths (paths in docs/api/openapi.json)

Usage:
    python scripts/verification/verify_doc_counts.py          # normal check
    python scripts/verification/verify_doc_counts.py --update  # refresh config
    python scripts/verification/verify_doc_counts.py --dry-run # print only

Exit codes:
    0  All counts match (or --update wrote new values)
    1  One or more counts disagree
    2  Config file missing (run with --update first)
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = Path(__file__).resolve().parent / "doc_counts.json"

# \w* (not \w+) so bare `@router.get(...)` is also captured.
ROUTE_RE = re.compile(r"@(\w*router)\.(get|post|put|delete|patch)\(")
MCP_TOOL_RE = re.compile(r"@mcp_app\.tool\b")
APP_RE = re.compile(r'"(apps\.\w+)"')


# ── Measurement ─────────────────────────────────────────────────────────────


def count_endpoints() -> int:
    """Count Ninja route decorators across all apps/ Python files."""
    total = 0
    for path in sorted((ROOT / "apps").rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        total += len(ROUTE_RE.findall(path.read_text(encoding="utf-8")))
    return total


def count_mcp_tools() -> int:
    """Count @mcp_app.tool registrations in apps/mcp/."""
    total = 0
    for path in sorted((ROOT / "apps" / "mcp").glob("*.py")):
        total += len(MCP_TOOL_RE.findall(path.read_text(encoding="utf-8")))
    return total


def count_django_apps() -> int:
    """Count installed Voyant apps (apps.*) in settings INSTALLED_APPS."""
    text = (ROOT / "voyant_project" / "settings.py").read_text(encoding="utf-8")
    return len(set(APP_RE.findall(text)))


def count_openapi_paths() -> int | None:
    """Count paths in docs/api/openapi.json (None if file missing)."""
    path = ROOT / "docs" / "api" / "openapi.json"
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as fh:
        return len(json.load(fh).get("paths", {}))


# ── Config I/O ──────────────────────────────────────────────────────────────


def load_config() -> dict | None:
    """Load doc_counts.json or return None."""
    if not CONFIG_PATH.exists():
        return None
    with CONFIG_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def write_config(measured: dict) -> None:
    """Write measured counts to doc_counts.json."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG_PATH.open("w", encoding="utf-8") as fh:
        json.dump(measured, fh, indent=2, sort_keys=True)
        fh.write("\n")


# ── Main ────────────────────────────────────────────────────────────────────


def main() -> int:
    dry_run = "--dry-run" in sys.argv
    update = "--update" in sys.argv

    measured = {
        "rest_endpoints": count_endpoints(),
        "mcp_tools": count_mcp_tools(),
        "django_apps": count_django_apps(),
        "openapi_paths": count_openapi_paths(),
    }

    print("Ground truth (measured from code)")
    print("─" * 50)
    for key, value in measured.items():
        print(f"  {key:20s} {value}")

    if update:
        write_config(measured)
        print(f"\n✅ Wrote {CONFIG_PATH}")
        return 0

    if dry_run:
        print("\n(dry-run — no comparison)")
        return 0

    config = load_config()
    if config is None:
        print(f"\n❌ Config file not found: {CONFIG_PATH}")
        print("   Run with --update to create it from current code.")
        return 2

    print("\nComparison (measured vs expected)")
    print("─" * 50)
    failures = 0
    for key, expected in sorted(config.items()):
        actual = measured.get(key)
        if actual is None:
            print(f"  {key:20s} {'N/A':>8s} vs {expected:>8d}  [SKIP — file missing]")
            continue
        ok = actual == expected
        status = "OK " if ok else "FAIL"
        if not ok:
            failures += 1
        print(f"  {key:20s} {actual:>8d} vs {expected:>8d}  [{status}]")

    if failures:
        print(f"\n❌ {failures} count(s) disagree — run with --update to accept new values")
        return 1

    print(f"\n✅ All {len(config)} counts match ground truth")
    return 0


if __name__ == "__main__":
    sys.exit(main())
