#!/usr/bin/env bash
set -euo pipefail

python -m uvicorn udb_api.app:app --reload --host 0.0.0.0 --port 8000
