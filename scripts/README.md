# Scripts Directory

This directory is organized by script intent to keep operations predictable and maintainable.

## Structure

- `dev/`: local developer runtime helpers.
- `examples/`: executable examples and reference crawlers.
- `ops/`: operational and diagnostics scripts used for platform maintenance.
- `sql/`: SQL bootstrap files for local/integration environments.
- `verification/`: workflow and platform verification scripts (`verify_*`).

## Usage Conventions

- Run scripts from repository root to preserve import and path assumptions.
- Prefer explicit paths, for example:
  - `python scripts/verification/verify_benchmark.py`
  - `python scripts/ops/deploy_spicedb_schema.py`
  - `bash scripts/dev/dev.sh`
