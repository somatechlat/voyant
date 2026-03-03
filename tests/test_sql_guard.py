"""
Tests for SQL Guard (TrinoClient read-only enforcement).

The guard is implemented in TrinoClient._validate_query() — a pure Python
method that enforces read-only query policy before any network call.
No mocking required: the validation logic runs entirely in-process.
"""

import pytest

from apps.core.lib.trino import TrinoClient


@pytest.fixture
def trino():
    """
    Instantiate a TrinoClient without connecting.
    _validate_query() is pure Python — no Trino server required.
    """
    client = TrinoClient.__new__(TrinoClient)
    return client


def test_select_query_allowed(trino):
    """SELECT query must pass validation without raising."""
    trino._validate_sql("SELECT 1 AS x")  # must not raise


def test_with_query_allowed(trino):
    """CTE (WITH) queries must pass validation."""
    trino._validate_sql("WITH t AS (SELECT 1) SELECT * FROM t")


def test_show_query_allowed(trino):
    """SHOW queries must pass validation."""
    trino._validate_sql("SHOW TABLES")


def test_describe_query_allowed(trino):
    """DESCRIBE queries must pass validation."""
    trino._validate_sql("DESCRIBE orders")


def test_insert_blocked(trino):
    """INSERT must be rejected with ValueError."""
    with pytest.raises(ValueError, match="Invalid query type"):
        trino._validate_sql("INSERT INTO t VALUES (1)")


def test_delete_blocked(trino):
    """DELETE must be rejected with ValueError."""
    with pytest.raises(ValueError, match="Invalid query type"):
        trino._validate_sql("DELETE FROM t WHERE id = 1")


def test_drop_blocked(trino):
    """DROP must be rejected with ValueError."""
    with pytest.raises(ValueError, match="Invalid query type"):
        trino._validate_sql("DROP TABLE t")


def test_update_blocked(trino):
    """UPDATE must be rejected with ValueError."""
    with pytest.raises(ValueError, match="Invalid query type"):
        trino._validate_sql("UPDATE t SET a = 1")


def test_empty_query_blocked(trino):
    """Empty query string must be rejected."""
    with pytest.raises(ValueError):
        trino._validate_sql("")


def test_case_insensitive_select_allowed(trino):
    """select (lowercase) must also pass — guard must be case-insensitive."""
    trino._validate_sql("select id from users")
