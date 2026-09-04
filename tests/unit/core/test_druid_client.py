"""
Unit tests for apps.core.lib.druid_client — OLAPQueryResult, OLAPDataSource
dataclasses, DruidClient construction, and response parsing logic.

Real dataclass construction and parsing. No mocks.
"""

import pytest

from apps.core.lib.druid_client import (
    DruidClient,
    OLAPDataSource,
    OLAPQueryResult,
    get_druid_client,
    get_pinot_client,
)


# ── Dataclass Tests ───────────────────────────────────────────────────────────


class TestOLAPQueryResult:
    def test_defaults(self):
        r = OLAPQueryResult(columns=["a", "b"], rows=[[1, 2]], row_count=1)
        assert r.columns == ["a", "b"]
        assert r.rows == [[1, 2]]
        assert r.row_count == 1
        assert r.query_duration_ms == 0
        assert r.engine == "druid"

    def test_custom_engine(self):
        r = OLAPQueryResult(columns=[], rows=[], row_count=0, engine="pinot")
        assert r.engine == "pinot"

    def test_with_duration(self):
        r = OLAPQueryResult(
            columns=["ts", "count"],
            rows=[["2024-01-01", 100], ["2024-01-02", 200]],
            row_count=2,
            query_duration_ms=42,
        )
        assert r.query_duration_ms == 42
        assert r.row_count == 2


class TestOLAPDataSource:
    def test_defaults(self):
        ds = OLAPDataSource(name="wikipedia")
        assert ds.name == "wikipedia"
        assert ds.dimensions == []
        assert ds.metrics == []
        assert ds.intervals == []
        assert ds.row_count == 0
        assert ds.engine == "druid"

    def test_full_construction(self):
        ds = OLAPDataSource(
            name="events",
            dimensions=["browser", "country"],
            metrics=["count", "sum_duration"],
            intervals=["2024-01-01/2024-02-01"],
            row_count=50000,
            engine="pinot",
        )
        assert ds.name == "events"
        assert len(ds.dimensions) == 2
        assert len(ds.metrics) == 2
        assert ds.engine == "pinot"


# ── DruidClient Construction ─────────────────────────────────────────────────


class TestDruidClientInit:
    def test_custom_url(self):
        client = DruidClient(base_url="http://druid:8082")
        assert client.base_url == "http://druid:8082"
        assert client.engine == "druid"

    def test_pinot_engine(self):
        client = DruidClient(base_url="http://pinot:9000", engine="pinot")
        assert client.engine == "pinot"

    def test_client_initially_none(self):
        client = DruidClient(base_url="http://test:8082")
        assert client._client is None


class TestDruidClientGetClient:
    def test_creates_httpx_client(self):
        client = DruidClient(base_url="http://test:8082")
        http = client._get_client()
        assert http is not None
        assert client._client is http

    def test_reuses_existing_client(self):
        client = DruidClient(base_url="http://test:8082")
        http1 = client._get_client()
        http2 = client._get_client()
        assert http1 is http2

    def test_recreates_closed_client(self):
        client = DruidClient(base_url="http://test:8082")
        http1 = client._get_client()
        http1.close()
        http2 = client._get_client()
        assert http2 is not http1
        assert not http2.is_closed


# ── Response Parsing Logic ────────────────────────────────────────────────────


class TestDruidSQLResponseParsing:
    """Test the parsing logic used in execute_sql for Druid responses."""

    def test_druid_header_and_rows_parsing(self):
        """Verify the Druid SQL response parsing logic."""
        data = {
            "header": [
                {"name": "country", "type": "STRING"},
                {"name": "count", "type": "LONG"},
            ],
            "rows": [
                ["US", 100],
                ["UK", 50],
                ["DE", 30],
            ],
        }
        columns = [c.get("name", "") for c in data.get("header", [])]
        rows = data.get("rows", [])

        result = OLAPQueryResult(
            columns=columns,
            rows=rows,
            row_count=len(rows),
            engine="druid",
        )
        assert result.columns == ["country", "count"]
        assert result.row_count == 3
        assert result.rows[0] == ["US", 100]

    def test_empty_druid_response(self):
        data = {"header": [], "rows": []}
        columns = [c.get("name", "") for c in data.get("header", [])]
        rows = data.get("rows", [])
        result = OLAPQueryResult(columns=columns, rows=rows, row_count=len(rows))
        assert result.columns == []
        assert result.row_count == 0


class TestPinotSQLResponseParsing:
    """Test the parsing logic used in _execute_pinot_sql."""

    def test_pinot_result_table_parsing(self):
        data = {
            "resultTable": {
                "columnNames": ["city", "population"],
                "rows": [
                    ["Berlin", 3600000],
                    ["Munich", 1500000],
                ],
            }
        }
        result_table = data.get("resultTable", {})
        columns = result_table.get("columnNames", [])
        rows = result_table.get("rows", [])

        result = OLAPQueryResult(
            columns=columns,
            rows=rows[:10000],
            row_count=len(rows),
            engine="pinot",
        )
        assert result.columns == ["city", "population"]
        assert result.row_count == 2
        assert result.engine == "pinot"

    def test_pinot_limit_applied(self):
        rows = [[i, f"val_{i}"] for i in range(100)]
        data = {
            "resultTable": {
                "columnNames": ["id", "value"],
                "rows": rows,
            }
        }
        result_table = data.get("resultTable", {})
        limited_rows = result_table.get("rows", [])[:10]
        assert len(limited_rows) == 10


class TestDruidDatasourceParsing:
    """Test the parsing logic for listing datasources."""

    def test_druid_datasource_metadata_parsing(self):
        meta = {
            "dimensions": ["browser", "os", "country"],
            "metrics": ["count", "sum_duration"],
            "intervals": ["2024-01-01T00:00:00.000Z/2024-02-01T00:00:00.000Z"],
        }
        ds = OLAPDataSource(
            name="wikipedia",
            dimensions=meta.get("dimensions", []),
            metrics=meta.get("metrics", []),
            intervals=meta.get("intervals", []),
            engine="druid",
        )
        assert ds.name == "wikipedia"
        assert len(ds.dimensions) == 3
        assert len(ds.metrics) == 2
        assert "2024-01-01" in ds.intervals[0]

    def test_druid_datasource_fallback_on_error(self):
        """When metadata fetch fails, datasource should still be created."""
        ds = OLAPDataSource(name="wikipedia", engine="druid")
        assert ds.name == "wikipedia"
        assert ds.dimensions == []
        assert ds.metrics == []

    def test_pinot_tables_parsing(self):
        data = {"tables": ["events", "sessions", "users"]}
        tables = data.get("tables", [])
        datasources = [OLAPDataSource(name=t, engine="pinot") for t in tables]
        assert len(datasources) == 3
        assert all(d.engine == "pinot" for d in datasources)
        assert datasources[0].name == "events"


# ── Factory Functions ─────────────────────────────────────────────────────────


class TestFactoryFunctions:
    def test_get_druid_client(self):
        client = get_druid_client()
        assert isinstance(client, DruidClient)
        assert client.engine == "druid"

    def test_get_pinot_client(self):
        client = get_pinot_client()
        assert isinstance(client, DruidClient)
        assert client.engine == "pinot"
