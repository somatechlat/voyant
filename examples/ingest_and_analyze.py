#!/usr/bin/env python
"""End-to-end example: upload sample data, run analysis, fetch artifacts & metrics.

Requires the local stack running (docker compose) and the API at http://localhost:8000.
"""
from __future__ import annotations

import json
import os
import pathlib

import requests

API = os.environ.get("UDB_API_URL", "http://localhost:8000")
ROLE_HEADERS = {"X-UDB-Role": "analyst"}
SAMPLE_PATH = pathlib.Path(__file__).parent / "data" / "sample_customers.csv"


def upload_csv(table: str = "customers"):
    with open(SAMPLE_PATH, "rb") as f:
        files = {"file": (SAMPLE_PATH.name, f, "text/csv")}
        data = {"table": table}
        r = requests.post(f"{API}/ingest/upload", headers=ROLE_HEADERS, files=files, data=data, timeout=60)
    r.raise_for_status()
    return r.json()


def run_analyze(kpi_sql: str = "select count(*) as cnt from customers"):
    payload = {"kpis": [{"name": "customer_count", "sql": kpi_sql}]}
    r = requests.post(
        f"{API}/analyze",
        headers={**ROLE_HEADERS, "Content-Type": "application/json"},
        json=payload,
        timeout=300,
    )
    r.raise_for_status()
    return r.json()


def fetch_manifest(job_id: str):
    r = requests.get(f"{API}/artifact_manifest/{job_id}", timeout=30)
    r.raise_for_status()
    return r.json()


def fetch_metrics_core():
    r = requests.get(f"{API}/metrics/select?mode=core", timeout=10)
    r.raise_for_status()
    return r.text


def main():
    print("[1] Uploading sample CSV ...")
    ingest = upload_csv()
    print(json.dumps(ingest, indent=2))

    print("[2] Running analyze job ... (this may take a few seconds)")
    analysis = run_analyze()
    print(json.dumps({k: analysis[k] for k in ["jobId", "summary"]}, indent=2))

    job_id = analysis["jobId"]
    print("[3] Fetching artifact manifest ...")
    manifest = fetch_manifest(job_id)
    print(f"Found {len(manifest['files'])} files")

    # Save sufficiency JSON locally if present
    suff = [f for f in manifest["files"] if f["path"].endswith("sufficiency.json")] \
        if isinstance(manifest.get("files"), list) else []
    if suff:
        target = suff[0]["path"].replace(f"/artifact/{job_id}/", "")
        r = requests.get(f"{API}{suff[0]['path']}", timeout=10)
        if r.ok:
            with open(target, "wb") as out:
                out.write(r.content)
            print(f"Wrote {target}")

    print("[4] Core metrics snapshot ...")
    metrics_text = fetch_metrics_core()
    interesting = [
        ln
        for ln in metrics_text.splitlines()
        if ln.startswith("udb_sufficiency_score")
        or ln.startswith("udb_job_duration_seconds_bucket")
    ]
    for ln in interesting[:10]:
        print(ln)

    print("Done.")


if __name__ == "__main__":
    main()
