"""
Unit tests for apps.core.lib.trino — SQL validation.

Real TrinoClient validation logic. No Trino server needed for validation.
"""

import pytest

from apps.core.lib.trino import QueryResult, TrinoClient


@pytest.fixture
def trino():
    client = TrinoClient.__new__(TrinoClient)
    return client


class TestSQLValidation:
    def test_select_allowed(self, trino):
        trino._validate_sql("SELECT 1 AS x")

    def test_with_cte_allowed(self, trino):
        trino._validate_sql("WITH t AS (SELECT 1) SELECT * FROM t")

    def test_show_allowed(self, trino):
        trino._validate_sql("SHOW TABLES")

    def test_describe_allowed(self, trino):
        trino._validate_sql("DESCRIBE orders")

    def test_explain_allowed(self, trino):
        trino._validate_sql("EXPLAIN SELECT 1")

    def test_lowercase_select_allowed(self, trino):
        trino._validate_sql("select id from users")

    def test_mixed_case_allowed(self, trino):
        trino._validate_sql("SeLeCt * FROM users")

    def test_insert_blocked(self, trino):
        with pytest.raises(ValueError, match="Invalid query type"):
            trino._validate_sql("INSERT INTO t VALUES (1)")

    def test_delete_blocked(self, trino):
        with pytest.raises(ValueError, match="Invalid query type"):
            trino._validate_sql("DELETE FROM t WHERE id = 1")

    def test_drop_blocked(self, trino):
        with pytest.raises(ValueError, match="Invalid query type"):
            trino._validate_sql("DROP TABLE t")

    def test_update_blocked(self, trino):
        with pytest.raises(ValueError, match="Invalid query type"):
            trino._validate_sql("UPDATE t SET a = 1")

    def test_truncate_blocked(self, trino):
        with pytest.raises(ValueError, match="Invalid query type"):
            trino._validate_sql("TRUNCATE TABLE t")

    def test_create_table_blocked(self, trino):
        with pytest.raises(ValueError, match="Invalid query type"):
            trino._validate_sql("CREATE TABLE t (id INT)")

    def test_grant_blocked(self, trino):
        with pytest.raises(ValueError, match="Invalid query type"):
            trino._validate_sql("GRANT ALL ON t TO user")

    def test_revoke_blocked(self, trino):
        with pytest.raises(ValueError, match="Invalid query type"):
            trino._validate_sql("REVOKE ALL ON t FROM user")

    def test_empty_query_blocked(self, trino):
        with pytest.raises(ValueError):
            trino._validate_sql("")

    def test_whitespace_only_blocked(self, trino):
        with pytest.raises(ValueError):
            trino._validate_sql("   ")


class TestQueryResult:
    def test_query_result_dataclass(self):
        result = QueryResult(
            columns=["id", "name"],
            rows=[[1, "a"], [2, "b"]],
            row_count=2,
            truncated=False,
            execution_time_ms=15,
            query_id="q-123",
        )
        assert result.row_count == 2
        assert result.columns == ["id", "name"]
        assert result.truncated is False
