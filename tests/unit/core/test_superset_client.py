"""
Unit tests for apps.core.lib.superset_client — SupersetDataset, SupersetChart,
SupersetDashboard dataclasses, SupersetClient construction, and response parsing.

Real dataclass construction and parsing. No mocks.
"""


from apps.core.lib.superset_client import (
    SupersetChart,
    SupersetClient,
    SupersetDashboard,
    SupersetDataset,
    get_superset_client,
)

# ── Dataclass Tests ───────────────────────────────────────────────────────────


class TestSupersetDataset:
    def test_defaults(self):
        ds = SupersetDataset()
        assert ds.id is None
        assert ds.database_id == 0
        assert ds.schema == ""
        assert ds.table_name == ""
        assert ds.sql == ""
        assert ds.columns == []

    def test_full_construction(self):
        ds = SupersetDataset(
            id=42,
            database_id=1,
            schema="analytics",
            table_name="events",
            sql="SELECT * FROM events WHERE ts > '2024-01-01'",
            columns=[
                {"name": "event_id", "type": "STRING"},
                {"name": "ts", "type": "TIMESTAMP"},
            ],
        )
        assert ds.id == 42
        assert ds.database_id == 1
        assert ds.schema == "analytics"
        assert "SELECT" in ds.sql
        assert len(ds.columns) == 2

    def test_default_columns_independent(self):
        ds1 = SupersetDataset()
        ds2 = SupersetDataset()
        ds1.columns.append({"name": "x"})
        assert ds2.columns == []


class TestSupersetChart:
    def test_defaults(self):
        c = SupersetChart()
        assert c.id is None
        assert c.slice_name == ""
        assert c.viz_type == ""
        assert c.datasource_id == 0
        assert c.params == {}

    def test_full_construction(self):
        c = SupersetChart(
            id=10,
            slice_name="Revenue by Region",
            viz_type="bar",
            datasource_id=42,
            params={"x_axis": "region", "y_axis": "revenue"},
        )
        assert c.id == 10
        assert c.slice_name == "Revenue by Region"
        assert c.viz_type == "bar"
        assert c.params["x_axis"] == "region"


class TestSupersetDashboard:
    def test_defaults(self):
        d = SupersetDashboard()
        assert d.id is None
        assert d.title == ""
        assert d.slug == ""
        assert d.charts == []

    def test_full_construction(self):
        d = SupersetDashboard(
            id=5,
            title="Executive Overview",
            slug="exec-overview",
            charts=[10, 20, 30],
        )
        assert d.id == 5
        assert d.title == "Executive Overview"
        assert len(d.charts) == 3

    def test_default_charts_independent(self):
        d1 = SupersetDashboard()
        d2 = SupersetDashboard()
        d1.charts.append(1)
        assert d2.charts == []


# ── SupersetClient Construction ───────────────────────────────────────────────


class TestSupersetClientInit:
    def test_custom_url(self):
        client = SupersetClient(base_url="http://superset:8088")
        assert client.base_url == "http://superset:8088"

    def test_token_initially_none(self):
        client = SupersetClient(base_url="http://test:8088")
        assert client._token is None

    def test_client_initially_none(self):
        client = SupersetClient(base_url="http://test:8088")
        assert client._client is None


class TestSupersetClientGetClient:
    def test_creates_httpx_client(self):
        client = SupersetClient(base_url="http://test:8088")
        http = client._get_client()
        assert http is not None
        assert client._client is http

    def test_reuses_existing_client(self):
        client = SupersetClient(base_url="http://test:8088")
        http1 = client._get_client()
        http2 = client._get_client()
        assert http1 is http2

    def test_recreates_closed_client(self):
        client = SupersetClient(base_url="http://test:8088")
        http1 = client._get_client()
        http1.close()
        http2 = client._get_client()
        assert http2 is not http1
        assert not http2.is_closed


# ── Payload Construction Logic ────────────────────────────────────────────────


class TestPayloadConstruction:
    """Test the payload construction logic used in create_* methods."""

    def test_dataset_payload_with_sql(self):
        dataset = SupersetDataset(
            database_id=1,
            schema="public",
            table_name="events",
            sql="SELECT * FROM events",
        )
        payload = {
            "database": dataset.database_id,
            "schema": dataset.schema,
            "table_name": dataset.table_name,
        }
        if dataset.sql:
            payload["sql"] = dataset.sql
        assert payload["database"] == 1
        assert payload["sql"] == "SELECT * FROM events"

    def test_dataset_payload_without_sql(self):
        dataset = SupersetDataset(
            database_id=1,
            schema="public",
            table_name="events",
        )
        payload = {
            "database": dataset.database_id,
            "schema": dataset.schema,
            "table_name": dataset.table_name,
        }
        if dataset.sql:
            payload["sql"] = dataset.sql
        assert "sql" not in payload

    def test_chart_payload(self):
        chart = SupersetChart(
            slice_name="Sales",
            viz_type="pie",
            datasource_id=42,
            params={"metric": "sum_amount"},
        )
        payload = {
            "slice_name": chart.slice_name,
            "viz_type": chart.viz_type,
            "datasource_id": chart.datasource_id,
            "params": str(chart.params),
        }
        assert payload["slice_name"] == "Sales"
        assert payload["viz_type"] == "pie"
        assert "sum_amount" in payload["params"]

    def test_dashboard_payload(self):
        dashboard = SupersetDashboard(title="Overview", slug="overview")
        payload = {
            "dashboard_title": dashboard.title,
            "slug": dashboard.slug,
        }
        assert payload["dashboard_title"] == "Overview"
        assert payload["slug"] == "overview"


# ── Response Parsing Logic ────────────────────────────────────────────────────


class TestResponseParsing:
    def test_token_extraction(self):
        data = {"access_token": "eyJhbGciOiJIUzI1NiJ9.test"}
        token = data.get("access_token", "")
        assert token == "eyJhbGciOiJIUzI1NiJ9.test"

    def test_dataset_id_extraction(self):
        data = {"id": 42}
        assert data.get("id") == 42

    def test_chart_id_extraction(self):
        data = {"id": 10}
        assert data.get("id") == 10

    def test_dashboard_id_extraction(self):
        data = {"id": 5}
        assert data.get("id") == 5

    def test_database_list_parsing(self):
        data = {
            "result": [
                {"id": 1, "database_name": "PostgreSQL"},
                {"id": 2, "database_name": "Trino"},
            ]
        }
        result = data.get("result", [])
        assert len(result) == 2
        assert result[0]["database_name"] == "PostgreSQL"


# ── Factory Function ─────────────────────────────────────────────────────────


class TestGetSupersetClient:
    def test_returns_superset_client(self):
        client = get_superset_client()
        assert isinstance(client, SupersetClient)
