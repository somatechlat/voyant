#!/usr/bin/env bash
set -euo pipefail

python -m uvicorn voyant_project.asgi:application --reload --host 0.0.0.0 --port 8000
