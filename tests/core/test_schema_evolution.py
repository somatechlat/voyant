"""
Test Schema Evolution Persistence

Verifies DuckDB-backed schema versioning.
"""

import os
import shutil
import tempfile

import pytest

from apps.core.config import Settings
from apps.core.lib.schema_evolution import (
    ColumnSchema,
    TableSchema,
    get_latest_schema,
    get_registry,
    get_schema_history,
    reset_registry,
    track_schema,
)


@pytest.fixture
def mock_settings(monkeypatch):
    """Override DuckDB path for testing."""
    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "test_voyant.duckdb")

    # Mock get_settings to return a settings object with our test db path
    def mock_get():
        s = Settings()
        s.duckdb_path = db_path
        return s

    monkeypatch.setattr("apps.core.config.get_settings", mock_get)
    monkeypatch.setattr(
        "apps.core.lib.schema_evolution.get_settings", mock_get
    )  # In case it's used there directly

    yield

    shutil.rmtree(tmp_dir)


@pytest.fixture
def clean_registry(mock_settings):
    """Reset registry and clear DB."""
    reset_registry()
    get_registry().clear()
    yield


def test_track_schema_persistence(clean_registry):
    t1 = TableSchema(
        name="users",
        columns=[ColumnSchema("id", "int"), ColumnSchema("name", "string")],
    )

    # 1. Track version 1
    v1 = track_schema("users", t1, "1.0.0", "Initial schema")
    assert v1.version == "1.0.0"

    # 2. Reset registry to simulate restart (force DB reload)
    reset_registry()

    # 3. Retrieve history
    history = get_schema_history("users")
    assert len(history) == 1
    assert history[0]["version"] == "1.0.0"
    assert history[0]["description"] == "Initial schema"


def test_schema_evolution_logic(clean_registry):
    t1 = TableSchema(
        name="orders",
        columns=[ColumnSchema("id", "int"), ColumnSchema("amount", "float")],
    )
    track_schema("orders", t1, "1.0.0")

    # Evolve: Add column
    t2 = TableSchema(
        name="orders",
        columns=[
            ColumnSchema("id", "int"),
            ColumnSchema("amount", "float"),
            ColumnSchema("status", "string", default="pending"),
        ],
    )
    track_schema("orders", t2, "1.1.0", "Added status")

    history = get_schema_history("orders")
    assert len(history) == 2
    assert history[1]["changes_count"] == 1
    assert history[1]["description"] == "Added status"


def test_get_version(clean_registry):
    t1 = TableSchema(name="test", columns=[ColumnSchema("a", "int")])
    track_schema("test", t1, "1.0.0")

    reset_registry()

    schema = get_latest_schema("test")
    assert schema.name == "test"
    assert len(schema.columns) == 1
