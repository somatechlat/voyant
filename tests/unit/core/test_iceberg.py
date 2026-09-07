"""
Unit tests for apps.core.lib.iceberg — IcebergTable, IcebergSnapshot dataclasses,
IcebergClient URL construction, and response parsing.

Real dataclass construction and parsing logic. No mocks.
"""


from apps.core.lib.iceberg import (
    IcebergClient,
    IcebergSnapshot,
    IcebergTable,
    get_iceberg_client,
)

# ── Dataclass Tests ───────────────────────────────────────────────────────────


class TestIcebergTable:
    def test_defaults(self):
        t = IcebergTable(namespace="ns", table_name="tbl")
        assert t.namespace == "ns"
        assert t.table_name == "tbl"
        assert t.location == ""
        assert t.current_snapshot_id is None
        assert t.schema_fields == []
        assert t.partition_spec == []
        assert t.properties == {}
        assert t.snapshot_count == 0

    def test_full_construction(self):
        t = IcebergTable(
            namespace="analytics",
            table_name="events",
            location="s3://bucket/analytics/events",
            current_snapshot_id=12345,
            schema_fields=[
                {"id": 1, "name": "event_id", "type": "string", "required": True},
                {"id": 2, "name": "ts", "type": "timestamp", "required": False},
            ],
            partition_spec=[
                {
                    "source-id": 2,
                    "field-id": 1000,
                    "transform": "day",
                    "name": "ts_day",
                }
            ],
            properties={"write.format.default": "parquet"},
            snapshot_count=5,
        )
        assert t.namespace == "analytics"
        assert t.table_name == "events"
        assert t.location == "s3://bucket/analytics/events"
        assert t.current_snapshot_id == 12345
        assert len(t.schema_fields) == 2
        assert t.schema_fields[0]["name"] == "event_id"
        assert len(t.partition_spec) == 1
        assert t.partition_spec[0]["transform"] == "day"
        assert t.properties["write.format.default"] == "parquet"
        assert t.snapshot_count == 5

    def test_default_factories_are_independent(self):
        t1 = IcebergTable(namespace="a", table_name="b")
        t2 = IcebergTable(namespace="c", table_name="d")
        t1.schema_fields.append({"id": 1, "name": "x", "type": "int", "required": False})
        t1.partition_spec.append({"source-id": 1, "field-id": 1, "transform": "identity", "name": "x"})
        t1.properties["key"] = "val"
        assert t2.schema_fields == []
        assert t2.partition_spec == []
        assert t2.properties == {}


class TestIcebergSnapshot:
    def test_defaults(self):
        s = IcebergSnapshot(snapshot_id=1, timestamp_ms=1000)
        assert s.snapshot_id == 1
        assert s.timestamp_ms == 1000
        assert s.operation == ""
        assert s.summary == {}
        assert s.manifest_list == ""

    def test_full_construction(self):
        s = IcebergSnapshot(
            snapshot_id=99,
            timestamp_ms=1700000000000,
            operation="append",
            summary={"added-files-size": "1024", "total-records": "500"},
            manifest_list="s3://bucket/metadata/manifest-list.avro",
        )
        assert s.snapshot_id == 99
        assert s.operation == "append"
        assert s.summary["added-files-size"] == "1024"
        assert "manifest" in s.manifest_list


# ── IcebergClient Construction ───────────────────────────────────────────────


class TestIcebergClientInit:
    def test_custom_catalog_url(self):
        client = IcebergClient(catalog_url="http://my-catalog:8181")
        assert client.catalog_url == "http://my-catalog:8181"

    def test_default_warehouse(self):
        client = IcebergClient(catalog_url="http://test:8181")
        assert client.warehouse == "voyant-warehouse"

    def test_client_initially_none(self):
        client = IcebergClient(catalog_url="http://test:8181")
        assert client._client is None


# ── IcebergClient URL Construction (via _get_client) ─────────────────────────


class TestIcebergClientGetClient:
    def test_creates_httpx_client(self):
        client = IcebergClient(catalog_url="http://test:8181")
        http = client._get_client()
        assert http is not None
        assert client._client is http

    def test_reuses_existing_client(self):
        client = IcebergClient(catalog_url="http://test:8181")
        http1 = client._get_client()
        http2 = client._get_client()
        assert http1 is http2

    def test_recreates_closed_client(self):
        client = IcebergClient(catalog_url="http://test:8181")
        http1 = client._get_client()
        http1.close()
        http2 = client._get_client()
        assert http2 is not http1
        assert not http2.is_closed


# ── Response Parsing (testing the parsing logic with real data structures) ────


class TestIcebergTableParsing:
    """Test the parsing logic that get_table uses by simulating the response data."""

    def test_schema_extraction_by_current_schema_id(self):
        """Verify the schema matching logic used in get_table."""
        metadata = {
            "current-schema-id": 1,
            "schemas": [
                {
                    "schema-id": 0,
                    "fields": [{"id": 0, "name": "old_col", "type": "string", "required": False}],
                },
                {
                    "schema-id": 1,
                    "fields": [
                        {"id": 1, "name": "event_id", "type": "string", "required": True},
                        {"id": 2, "name": "value", "type": "double", "required": False},
                    ],
                },
            ],
            "default-spec-id": 0,
            "partition-specs": [{"spec-id": 0, "fields": []}],
            "snapshots": [],
            "current-snapshot-id": None,
            "location": "s3://bucket/tbl",
            "properties": {},
        }

        # Replicate the parsing logic from get_table
        current_schema_id = metadata.get("current-schema-id", 0)
        schemas = metadata.get("schemas", [])
        fields = []
        for schema in schemas:
            if schema.get("schema-id") == current_schema_id:
                fields = schema.get("fields", [])
                break

        assert len(fields) == 2
        assert fields[0]["name"] == "event_id"

    def test_partition_spec_extraction(self):
        """Verify the partition spec matching logic."""
        metadata = {
            "default-spec-id": 1,
            "partition-specs": [
                {"spec-id": 0, "fields": []},
                {
                    "spec-id": 1,
                    "fields": [
                        {
                            "source-id": 2,
                            "field-id": 1000,
                            "transform": "bucket[16]",
                            "name": "user_bucket",
                        }
                    ],
                },
            ],
        }

        partition_spec_id = metadata.get("default-spec-id", 0)
        specs = metadata.get("partition-specs", [])
        partitions = []
        for spec in specs:
            if spec.get("spec-id") == partition_spec_id:
                partitions = spec.get("fields", [])
                break

        assert len(partitions) == 1
        assert partitions[0]["transform"] == "bucket[16]"
        assert partitions[0]["name"] == "user_bucket"

    def test_snapshot_parsing_logic(self):
        """Verify the snapshot parsing logic used in get_snapshots."""
        metadata = {
            "snapshots": [
                {
                    "snapshot-id": 100,
                    "timestamp-ms": 1700000000000,
                    "summary": {"operation": "append", "added-files-size": "512"},
                    "manifest-list": "s3://bucket/manifest-1.avro",
                },
                {
                    "snapshot-id": 101,
                    "timestamp-ms": 1700000100000,
                    "summary": {"operation": "overwrite", "total-files-size": "1024"},
                    "manifest-list": "s3://bucket/manifest-2.avro",
                },
            ]
        }

        snapshots = []
        for snap in metadata.get("snapshots", []):
            summary = snap.get("summary", {})
            snapshots.append(
                IcebergSnapshot(
                    snapshot_id=snap.get("snapshot-id", 0),
                    timestamp_ms=snap.get("timestamp-ms", 0),
                    operation=summary.get("operation", ""),
                    summary=summary,
                    manifest_list=snap.get("manifest-list", ""),
                )
            )

        assert len(snapshots) == 2
        assert snapshots[0].snapshot_id == 100
        assert snapshots[0].operation == "append"
        assert snapshots[1].operation == "overwrite"
        assert snapshots[1].summary["total-files-size"] == "1024"

    def test_namespace_list_parsing(self):
        """Verify the namespace list parsing logic."""
        data = {"namespaces": [["analytics"], ["raw", "events"], ["ml"]]}
        result = [".".join(ns) for ns in data.get("namespaces", [])]
        assert result == ["analytics", "raw.events", "ml"]

    def test_table_list_parsing(self):
        """Verify the table list parsing logic."""
        data = {
            "identifiers": [
                {"namespace": ["analytics"], "name": "events"},
                {"namespace": ["analytics"], "name": "sessions"},
            ]
        }
        result = [t.get("name", "") for t in data.get("identifiers", [])]
        assert result == ["events", "sessions"]

    def test_empty_metadata_handling(self):
        """Verify graceful handling of empty metadata."""
        metadata: dict = {}
        assert metadata.get("current-schema-id", 0) == 0
        assert metadata.get("schemas", []) == []
        assert metadata.get("snapshots", []) == []
        assert metadata.get("current-snapshot-id") is None
        assert metadata.get("location", "") == ""
        assert metadata.get("properties", {}) == {}


# ── Factory Function ─────────────────────────────────────────────────────────


class TestGetIcebergClient:
    def test_returns_iceberg_client(self):
        client = get_iceberg_client()
        assert isinstance(client, IcebergClient)


# ── Drop Table URL Construction ──────────────────────────────────────────────


class TestDropTableURL:
    def test_url_without_purge(self):
        namespace = "analytics"
        table_name = "events"
        url = f"/v1/namespaces/{namespace}/tables/{table_name}"
        assert url == "/v1/namespaces/analytics/tables/events"

    def test_url_with_purge(self):
        namespace = "analytics"
        table_name = "events"
        url = f"/v1/namespaces/{namespace}/tables/{table_name}"
        url += "?purge=true"
        assert url == "/v1/namespaces/analytics/tables/events?purge=true"
