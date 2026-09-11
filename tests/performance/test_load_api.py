"""
Concurrent load tests for the Voyant API.

Uses pytest + asyncio + httpx.AsyncClient to fire concurrent requests and
assert that the backend handles them without errors.  These tests are
designed to run against a live dev/staging server (default: http://localhost:8000).

Set the VOYANT_BASE_URL env-var to point at a different target.
Set the VOYANT_API_TOKEN env-var to provide a Bearer token (or omit for
unauthenticated health-check tests).

Usage:
    pytest tests/performance/test_load_api.py -v
"""

from __future__ import annotations

import asyncio
import os
import uuid

import httpx
import pytest

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = os.environ.get("VOYANT_BASE_URL", "http://localhost:8000")
API_TOKEN = os.environ.get("VOYANT_API_TOKEN", "")

TIMEOUT = httpx.Timeout(30.0, connect=10.0)


def _headers() -> dict[str, str]:
    """Build request headers with optional auth token."""
    h: dict[str, str] = {"Content-Type": "application/json"}
    if API_TOKEN:
        h["Authorization"] = f"Bearer {API_TOKEN}"
    return h


# ---------------------------------------------------------------------------
# Test 1: Concurrent health-check requests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_concurrent_api_requests() -> None:
    """Fire 100 concurrent requests to /v1/health and assert all return 200."""
    concurrency = 100

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT) as client:
        tasks = [client.get("/v1/health") for _ in range(concurrency)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    successes = 0
    failures: list[str] = []
    for i, res in enumerate(results):
        if isinstance(res, httpx.Response) and res.status_code == 200:
            successes += 1
        elif isinstance(res, httpx.Response):
            failures.append(f"[{i}] status={res.status_code}")
        elif isinstance(res, BaseException):
            failures.append(f"[{i}] error={res}")

    assert successes == concurrency, (
        f"Expected {concurrency} 200s, got {successes}. "
        f"Failures: {failures[:10]}"
    )


# ---------------------------------------------------------------------------
# Test 2: Concurrent ontology CRUD
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_concurrent_ontology_crud() -> None:
    """
    50 concurrent create → read → update cycles on ontology object types.

    Each goroutine creates a unique type, reads it back, updates its
    description, and then deletes it.
    """
    concurrency = 50

    async with httpx.AsyncClient(
        base_url=BASE_URL, timeout=TIMEOUT, headers=_headers()
    ) as client:

        async def crud_cycle(idx: int) -> str | None:
            """Create → read → update → delete. Returns error string or None."""
            name = f"load_test_type_{uuid.uuid4().hex[:12]}"
            try:
                # Create
                create_resp = await client.post(
                    "/v1/ontology/types",
                    json={
                        "name": name,
                        "description": f"Load test type {idx}",
                        "properties": [
                            {
                                "name": "label",
                                "property_type": "string",
                                "required": False,
                            }
                        ],
                    },
                )
                if create_resp.status_code not in (200, 201):
                    return f"create failed: {create_resp.status_code}"

                type_id = create_resp.json().get("id")
                if not type_id:
                    return "create returned no id"

                # Read
                read_resp = await client.get(f"/v1/ontology/types/{type_id}")
                if read_resp.status_code != 200:
                    return f"read failed: {read_resp.status_code}"

                # Update
                update_resp = await client.put(
                    f"/v1/ontology/types/{type_id}",
                    json={"description": f"Updated load test type {idx}"},
                )
                if update_resp.status_code not in (200, 204):
                    return f"update failed: {update_resp.status_code}"

                # Delete
                del_resp = await client.delete(f"/v1/ontology/types/{type_id}")
                if del_resp.status_code not in (200, 204):
                    return f"delete failed: {del_resp.status_code}"

                return None  # success
            except Exception as exc:
                return f"exception: {exc}"

        results = await asyncio.gather(
            *[crud_cycle(i) for i in range(concurrency)]
        )

    errors = [r for r in results if r is not None]
    assert len(errors) == 0, (
        f"{len(errors)}/{concurrency} CRUD cycles failed: {errors[:10]}"
    )


# ---------------------------------------------------------------------------
# Test 3: Concurrent SQL queries
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_concurrent_sql_queries() -> None:
    """
    20 concurrent SQL queries via /v1/sql/query.

    Uses simple SELECT statements that should succeed on any warehouse.
    """
    concurrency = 20
    queries = [
        "SELECT 1 AS test",
        "SELECT 1 AS num, 'hello' AS msg",
        "SELECT 42 AS answer",
        "SELECT CURRENT_TIMESTAMP AS now",
        "SELECT TRUE AS flag",
    ]

    async with httpx.AsyncClient(
        base_url=BASE_URL, timeout=TIMEOUT, headers=_headers()
    ) as client:

        async def run_query(idx: int) -> str | None:
            sql = queries[idx % len(queries)]
            try:
                resp = await client.post(
                    "/v1/sql/query",
                    json={"sql": sql, "limit": 10},
                )
                if resp.status_code != 200:
                    return f"query[{idx}] failed: {resp.status_code}"
                return None
            except Exception as exc:
                return f"query[{idx}] exception: {exc}"

        results = await asyncio.gather(
            *[run_query(i) for i in range(concurrency)]
        )

    errors = [r for r in results if r is not None]
    assert len(errors) == 0, (
        f"{len(errors)}/{concurrency} SQL queries failed: {errors[:10]}"
    )


# ---------------------------------------------------------------------------
# Test 4: Concurrent scraper job submissions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_concurrent_scraper_jobs() -> None:
    """
    10 concurrent scrape job submissions via /v1/scrape/start.

    Submits lightweight jobs that target example.com to avoid heavy load.
    """
    concurrency = 10

    async with httpx.AsyncClient(
        base_url=BASE_URL, timeout=TIMEOUT, headers=_headers()
    ) as client:

        async def submit_job(idx: int) -> str | None:
            try:
                resp = await client.post(
                    "/v1/scrape/start",
                    json={
                        "urls": [f"https://example.com/?q={idx}"],
                        "max_pages": 1,
                        "render_js": False,
                    },
                )
                # Accept 200, 201, or 202 (accepted for async processing)
                if resp.status_code not in (200, 201, 202):
                    return f"submit[{idx}] failed: {resp.status_code}"
                return None
            except Exception as exc:
                return f"submit[{idx}] exception: {exc}"

        results = await asyncio.gather(
            *[submit_job(i) for i in range(concurrency)]
        )

    errors = [r for r in results if r is not None]
    assert len(errors) == 0, (
        f"{len(errors)}/{concurrency} scraper job submissions failed: {errors[:10]}"
    )
