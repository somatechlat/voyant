"""Shared source type detection logic."""

from __future__ import annotations

from typing import Any


def detect_source_type(hint: str) -> dict[str, Any]:
    """Detect source type and connector hints from user-provided input."""
    hint_lower = hint.lower()
    if hint_lower.startswith("postgresql://") or hint_lower.startswith("postgres://"):
        return {
            "source_type": "postgresql",
            "connector": "airbyte/source-postgres",
            "properties": {
                "host": hint.split("@")[-1].split("/")[0] if "@" in hint else "unknown"
            },
            "confidence": 0.95,
        }
    if hint_lower.startswith("mysql://"):
        return {
            "source_type": "mysql",
            "connector": "airbyte/source-mysql",
            "properties": {},
            "confidence": 0.95,
        }
    if hint_lower.startswith("mongodb://") or hint_lower.startswith("mongodb+srv://"):
        return {
            "source_type": "mongodb",
            "connector": "airbyte/source-mongodb-v2",
            "properties": {},
            "confidence": 0.95,
        }
    if "snowflake" in hint_lower:
        return {
            "source_type": "snowflake",
            "connector": "airbyte/source-snowflake",
            "properties": {},
            "confidence": 0.9,
        }
    if hint_lower.endswith(".csv"):
        return {
            "source_type": "csv",
            "connector": "file",
            "properties": {"format": "csv"},
            "confidence": 0.9,
        }
    if hint_lower.endswith(".parquet"):
        return {
            "source_type": "parquet",
            "connector": "file",
            "properties": {"format": "parquet"},
            "confidence": 0.9,
        }
    if hint_lower.endswith(".json") or hint_lower.endswith(".jsonl"):
        return {
            "source_type": "json",
            "connector": "file",
            "properties": {"format": "json"},
            "confidence": 0.9,
        }
    if "s3://" in hint_lower:
        return {
            "source_type": "s3",
            "connector": "airbyte/source-s3",
            "properties": {"bucket": hint.split("/")[2] if len(hint.split("/")) > 2 else ""},
            "confidence": 0.9,
        }
    if "sheets.google.com" in hint_lower or "docs.google.com/spreadsheets" in hint_lower:
        return {
            "source_type": "google_sheets",
            "connector": "airbyte/source-google-sheets",
            "properties": {},
            "confidence": 0.9,
        }
    if hint_lower.startswith("http://") or hint_lower.startswith("https://"):
        return {
            "source_type": "api",
            "connector": "airbyte/source-http",
            "properties": {"url": hint},
            "confidence": 0.5,
        }
    return {
        "source_type": "unknown",
        "connector": "unknown",
        "properties": {},
        "confidence": 0.1,
    }
