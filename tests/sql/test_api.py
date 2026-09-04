"""
Unit tests for apps.sql.api — SQL query API schemas and endpoint logic.

Tests SqlRequest/SqlResponse schema validation and the endpoint
function signatures.
Pure schema logic — no DB, no Trino.
"""

import pytest
from ninja import Schema
from pydantic import ValidationError as PydanticValidationError


# =========================================================================
# SqlRequest schema
# =========================================================================


class TestSqlRequest:
    def test_valid_request(self):
        from apps.sql.api import SqlRequest

        req = SqlRequest(sql="SELECT * FROM users")
        assert req.sql == "SELECT * FROM users"
        assert req.limit == 1000
        assert req.parameters is None

    def test_custom_limit(self):
        from apps.sql.api import SqlRequest

        req = SqlRequest(sql="SELECT 1", limit=500)
        assert req.limit == 500

    def test_with_parameters(self):
        from apps.sql.api import SqlRequest

        req = SqlRequest(sql="SELECT * FROM t WHERE id = :id", parameters={"id": 42})
        assert req.parameters == {"id": 42}

    def test_missing_sql_raises(self):
        from apps.sql.api import SqlRequest

        with pytest.raises(PydanticValidationError):
            SqlRequest()

    def test_limit_too_low_raises(self):
        from apps.sql.api import SqlRequest

        with pytest.raises(PydanticValidationError):
            SqlRequest(sql="SELECT 1", limit=0)

    def test_limit_too_high_raises(self):
        from apps.sql.api import SqlRequest

        with pytest.raises(PydanticValidationError):
            SqlRequest(sql="SELECT 1", limit=10001)

    def test_limit_boundary_min(self):
        from apps.sql.api import SqlRequest

        req = SqlRequest(sql="SELECT 1", limit=1)
        assert req.limit == 1

    def test_limit_boundary_max(self):
        from apps.sql.api import SqlRequest

        req = SqlRequest(sql="SELECT 1", limit=10000)
        assert req.limit == 10000


# =========================================================================
# SqlResponse schema
# =========================================================================


class TestSqlResponse:
    def test_valid_response(self):
        from apps.sql.api import SqlResponse

        resp = SqlResponse(
            columns=["id", "name"],
            rows=[[1, "Alice"], [2, "Bob"]],
            row_count=2,
            truncated=False,
            execution_time_ms=42,
            query_id="q-123",
        )
        assert resp.columns == ["id", "name"]
        assert resp.row_count == 2
        assert resp.truncated is False
        assert resp.execution_time_ms == 42
        assert resp.query_id == "q-123"

    def test_response_without_query_id(self):
        from apps.sql.api import SqlResponse

        resp = SqlResponse(
            columns=["count"],
            rows=[[100]],
            row_count=1,
            truncated=False,
            execution_time_ms=10,
        )
        assert resp.query_id is None

    def test_empty_result(self):
        from apps.sql.api import SqlResponse

        resp = SqlResponse(
            columns=["id"],
            rows=[],
            row_count=0,
            truncated=False,
            execution_time_ms=5,
        )
        assert resp.rows == []
        assert resp.row_count == 0

    def test_truncated_result(self):
        from apps.sql.api import SqlResponse

        resp = SqlResponse(
            columns=["x"],
            rows=[[i] for i in range(1000)],
            row_count=1000,
            truncated=True,
            execution_time_ms=200,
        )
        assert resp.truncated is True

    def test_missing_required_field_raises(self):
        from apps.sql.api import SqlResponse

        with pytest.raises(PydanticValidationError):
            SqlResponse(
                columns=["id"],
                # missing rows
                row_count=0,
                truncated=False,
                execution_time_ms=5,
            )


# =========================================================================
# Endpoint function signatures
# =========================================================================


class TestEndpointSignatures:
    def test_execute_sql_signature(self):
        from apps.sql.api import execute_sql

        import inspect

        sig = inspect.signature(execute_sql)
        assert "request" in sig.parameters
        assert "payload" in sig.parameters

    def test_list_tables_signature(self):
        from apps.sql.api import list_tables

        import inspect

        sig = inspect.signature(list_tables)
        assert "request" in sig.parameters
        assert sig.parameters["schema"].default is None

    def test_get_columns_signature(self):
        from apps.sql.api import get_columns

        import inspect

        sig = inspect.signature(get_columns)
        assert "table" in sig.parameters
        assert sig.parameters["schema"].default is None
