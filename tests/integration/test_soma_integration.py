import os
import uuid

import httpx
import pytest


def _require_env(*names: str) -> dict[str, str]:
    values: dict[str, str] = {}
    missing = []
    for name in names:
        value = os.environ.get(name, "").strip()
        if not value:
            missing.append(name)
        else:
            values[name] = value
    if missing:
        pytest.skip(f"Missing env vars for Soma integration: {', '.join(missing)}")
    return values


@pytest.mark.asyncio
async def test_soma_policy_evaluate():
    env = _require_env("SOMA_POLICY_URL", "SOMA_TEST_TENANT", "SOMA_TEST_USER")
    base_url = env["SOMA_POLICY_URL"].rstrip("/")
    payload = {
        "session_id": f"voyant-test-{uuid.uuid4()}",
        "tenant": env["SOMA_TEST_TENANT"],
        "user": env["SOMA_TEST_USER"],
        "prompt": "voyant integration test policy check",
        "role": "agent",
        "metadata": {"test": True},
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(f"{base_url}/v1/evaluate", json=payload)
        resp.raise_for_status()
        data = resp.json()

    assert isinstance(data, dict)
    assert "allowed" in data
    assert isinstance(data["allowed"], bool)


@pytest.mark.asyncio
async def test_soma_memory_remember_and_recall():
    env = _require_env("SOMA_MEMORY_URL")
    base_url = env["SOMA_MEMORY_URL"].rstrip("/")
    key = f"voyant-test:{uuid.uuid4()}"
    payload = {"key": key, "value": {"test": True, "source": "voyant"}}

    async with httpx.AsyncClient(timeout=10.0) as client:
        remember = await client.post(f"{base_url}/v1/remember", json=payload)
        remember.raise_for_status()
        recall = await client.get(f"{base_url}/v1/recall/{key}")
        recall.raise_for_status()
        data = recall.json()

    assert data["key"] == key
    assert data["value"]["source"] == "voyant"


@pytest.mark.asyncio
async def test_soma_orchestrator_task_lifecycle():
    env = _require_env("SOMA_ORCHESTRATOR_URL", "SOMA_TEST_TENANT_ID", "SOMA_TEST_USER_ID")
    base_url = env["SOMA_ORCHESTRATOR_URL"].rstrip("/")
    tenant_id = env["SOMA_TEST_TENANT_ID"]
    user_id = env["SOMA_TEST_USER_ID"]

    payload = {
        "tenant_id": tenant_id,
        "user_principal_id": user_id,
        "source_application": "VOYANT",
        "original_request_text": "voyant integration test task",
        "task_type": "VOYANT_TEST",
        "labels": {"test": True},
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        created = await client.post(
            f"{base_url}/v1/tasks/",
            json=payload,
            headers={"X-Tenant-ID": tenant_id},
        )
        created.raise_for_status()
        task = created.json()

        task_id = task["id"]
        updated = await client.patch(
            f"{base_url}/v1/tasks/{task_id}/status",
            params={"status": "RUNNING", "reason": "voyant test"},
            headers={"X-Tenant-ID": tenant_id},
        )
        updated.raise_for_status()

        completed = await client.patch(
            f"{base_url}/v1/tasks/{task_id}/status",
            params={"status": "COMPLETED", "reason": "voyant test complete"},
            headers={"X-Tenant-ID": tenant_id},
        )
        completed.raise_for_status()

    assert task_id
