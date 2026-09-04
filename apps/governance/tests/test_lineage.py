"""Tests for data lineage module."""

from apps.governance.lib.lineage import (
    EdgeType,
    LineageEdge,
    LineageGraph,
    LineageNode,
    NodeType,
    get_lineage_graph,
    reset_lineage_graph,
)


class TestNodeType:
    """Test NodeType enum."""

    def test_source(self):
        assert NodeType.SOURCE.value == "source"

    def test_table(self):
        assert NodeType.TABLE.value == "table"

    def test_column(self):
        assert NodeType.COLUMN.value == "column"

    def test_job(self):
        assert NodeType.JOB.value == "job"

    def test_artifact(self):
        assert NodeType.ARTIFACT.value == "artifact"

    def test_baseline(self):
        assert NodeType.BASELINE.value == "baseline"

    def test_contract(self):
        assert NodeType.CONTRACT.value == "contract"


class TestEdgeType:
    """Test EdgeType enum."""

    def test_derives_from(self):
        assert EdgeType.DERIVES_FROM.value == "derives_from"

    def test_produces(self):
        assert EdgeType.PRODUCES.value == "produces"

    def test_validates(self):
        assert EdgeType.VALIDATES.value == "validates"

    def test_references(self):
        assert EdgeType.REFERENCES.value == "references"


class TestLineageNode:
    """Test LineageNode dataclass."""

    def test_creation(self):
        node = LineageNode(
            node_id="source:orders",
            node_type=NodeType.SOURCE,
            name="Orders Source",
            tenant_id="tenant_1",
        )
        assert node.node_id == "source:orders"
        assert node.node_type == NodeType.SOURCE
        assert node.name == "Orders Source"
        assert node.tenant_id == "tenant_1"
        assert node.created_at > 0

    def test_to_dict(self):
        node = LineageNode(
            node_id="artifact:abc",
            node_type=NodeType.ARTIFACT,
            name="Profile Artifact",
            tenant_id="tenant_1",
            properties={"format": "parquet"},
        )
        d = node.to_dict()
        assert d["node_id"] == "artifact:abc"
        assert d["node_type"] == "artifact"
        assert d["name"] == "Profile Artifact"
        assert d["properties"]["format"] == "parquet"

    def test_default_properties(self):
        node = LineageNode(
            node_id="test",
            node_type=NodeType.TABLE,
            name="Test",
            tenant_id="tenant_1",
        )
        assert node.properties == {}


class TestLineageEdge:
    """Test LineageEdge dataclass."""

    def test_creation(self):
        edge = LineageEdge(
            source_id="table:orders",
            target_id="job:transform",
            edge_type=EdgeType.DERIVES_FROM,
        )
        assert edge.source_id == "table:orders"
        assert edge.target_id == "job:transform"
        assert edge.edge_type == EdgeType.DERIVES_FROM
        assert edge.created_at > 0

    def test_to_dict(self):
        edge = LineageEdge(
            source_id="job:etl",
            target_id="artifact:report",
            edge_type=EdgeType.PRODUCES,
            job_id="job_123",
            properties={"runtime": "30s"},
        )
        d = edge.to_dict()
        assert d["source_id"] == "job:etl"
        assert d["target_id"] == "artifact:report"
        assert d["edge_type"] == "produces"
        assert d["job_id"] == "job_123"

    def test_optional_fields(self):
        edge = LineageEdge(
            source_id="a",
            target_id="b",
            edge_type=EdgeType.REFERENCES,
        )
        assert edge.job_id is None
        assert edge.properties == {}


class TestLineageGraph:
    """Test LineageGraph class."""

    def setup_method(self):
        self.graph = LineageGraph()

    def test_add_node(self):
        node = self.graph.add_node(
            "source:orders",
            NodeType.SOURCE,
            "Orders",
            "tenant_1",
        )
        assert node.node_id == "source:orders"
        assert len(self.graph._nodes) == 1

    def test_add_node_updates_existing(self):
        self.graph.add_node(
            "source:orders",
            NodeType.SOURCE,
            "Orders",
            "tenant_1",
            properties={"version": 1},
        )
        node = self.graph.add_node(
            "source:orders",
            NodeType.SOURCE,
            "Orders",
            "tenant_1",
            properties={"version": 2},
        )
        assert node.properties["version"] == 2
        assert len(self.graph._nodes) == 1

    def test_add_edge(self):
        self.graph.add_node("table:orders", NodeType.TABLE, "Orders", "tenant_1")
        self.graph.add_node("job:transform", NodeType.JOB, "Transform", "tenant_1")

        edge = self.graph.add_edge("table:orders", "job:transform")
        assert edge.source_id == "table:orders"
        assert edge.target_id == "job:transform"
        assert len(self.graph._edges) == 1

    def test_get_node(self):
        self.graph.add_node("test", NodeType.TABLE, "Test", "tenant_1")
        node = self.graph.get_node("test")
        assert node is not None
        assert node.name == "Test"

    def test_get_node_not_found(self):
        node = self.graph.get_node("nonexistent")
        assert node is None

    def test_get_upstream_direct(self):
        self.graph.add_node("table:a", NodeType.TABLE, "A", "tenant_1")
        self.graph.add_node("table:b", NodeType.TABLE, "B", "tenant_1")
        self.graph.add_edge("table:a", "table:b")

        upstream = self.graph.get_upstream("table:b", depth=1)
        assert "table:a" in upstream

    def test_get_upstream_no_nodes(self):
        upstream = self.graph.get_upstream("nonexistent", depth=1)
        assert upstream == []

    def test_get_upstream_depth_zero(self):
        self.graph.add_node("table:a", NodeType.TABLE, "A", "tenant_1")
        self.graph.add_node("table:b", NodeType.TABLE, "B", "tenant_1")
        self.graph.add_edge("table:a", "table:b")

        upstream = self.graph.get_upstream("table:b", depth=0)
        assert upstream == []

    def test_get_upstream_recursive(self):
        self.graph.add_node("source:raw", NodeType.SOURCE, "Raw", "tenant_1")
        self.graph.add_node("table:staging", NodeType.TABLE, "Staging", "tenant_1")
        self.graph.add_node("table:final", NodeType.TABLE, "Final", "tenant_1")

        self.graph.add_edge("source:raw", "table:staging")
        self.graph.add_edge("table:staging", "table:final")

        upstream = self.graph.get_upstream("table:final", depth=-1)
        assert "source:raw" in upstream
        assert "table:staging" in upstream

    def test_get_downstream_direct(self):
        self.graph.add_node("table:a", NodeType.TABLE, "A", "tenant_1")
        self.graph.add_node("table:b", NodeType.TABLE, "B", "tenant_1")
        self.graph.add_edge("table:a", "table:b")

        downstream = self.graph.get_downstream("table:a", depth=1)
        assert "table:b" in downstream

    def test_get_downstream_recursive(self):
        self.graph.add_node("source:raw", NodeType.SOURCE, "Raw", "tenant_1")
        self.graph.add_node("table:staging", NodeType.TABLE, "Staging", "tenant_1")
        self.graph.add_node("table:final", NodeType.TABLE, "Final", "tenant_1")

        self.graph.add_edge("source:raw", "table:staging")
        self.graph.add_edge("table:staging", "table:final")

        downstream = self.graph.get_downstream("source:raw", depth=-1)
        assert "table:staging" in downstream
        assert "table:final" in downstream

    def test_get_edges_for_node(self):
        self.graph.add_node("a", NodeType.TABLE, "A", "tenant_1")
        self.graph.add_node("b", NodeType.TABLE, "B", "tenant_1")
        self.graph.add_node("c", NodeType.TABLE, "C", "tenant_1")

        self.graph.add_edge("a", "b")
        self.graph.add_edge("b", "c")

        edges = self.graph.get_edges_for_node("b")
        assert len(edges) == 2

    def test_get_impact_analysis(self):
        self.graph.add_node("source:raw", NodeType.SOURCE, "Raw", "tenant_1")
        self.graph.add_node("table:staging", NodeType.TABLE, "Staging", "tenant_1")
        self.graph.add_node("table:final", NodeType.TABLE, "Final", "tenant_1")
        self.graph.add_node("artifact:report", NodeType.ARTIFACT, "Report", "tenant_1")

        self.graph.add_edge("source:raw", "table:staging")
        self.graph.add_edge("table:staging", "table:final")
        self.graph.add_edge("table:final", "artifact:report")

        impact = self.graph.get_impact_analysis("source:raw")
        assert impact["total_impacted"] == 3
        assert "table" in impact["by_type"]
        assert "artifact" in impact["by_type"]

    def test_to_json(self):
        self.graph.add_node("a", NodeType.TABLE, "A", "tenant_1")
        self.graph.add_node("b", NodeType.TABLE, "B", "tenant_2")
        self.graph.add_edge("a", "b")

        json_data = self.graph.to_json()
        assert len(json_data["nodes"]) == 2
        assert len(json_data["edges"]) == 1
        assert json_data["stats"]["node_count"] == 2

    def test_to_json_with_tenant_filter(self):
        self.graph.add_node("a", NodeType.TABLE, "A", "tenant_1")
        self.graph.add_node("b", NodeType.TABLE, "B", "tenant_2")

        json_data = self.graph.to_json(tenant_id="tenant_1")
        assert len(json_data["nodes"]) == 1
        assert json_data["nodes"][0]["name"] == "A"

    def test_record_job_lineage(self):
        self.graph.record_job_lineage(
            job_id="job_123",
            tenant_id="tenant_1",
            source_tables=["orders", "customers"],
            output_artifacts=["report_123"],
        )

        job_node = self.graph.get_node("job:job_123")
        assert job_node is not None
        assert job_node.node_type == NodeType.JOB

        upstream = self.graph.get_upstream("job:job_123")
        assert "table:orders" in upstream
        assert "table:customers" in upstream

        downstream = self.graph.get_downstream("job:job_123")
        assert "artifact:report_123" in downstream

    def test_clear_tenant(self):
        self.graph.add_node("a", NodeType.TABLE, "A", "tenant_1")
        self.graph.add_node("b", NodeType.TABLE, "B", "tenant_2")
        self.graph.add_edge("a", "b")

        cleared = self.graph.clear_tenant("tenant_1")
        assert cleared == 1
        assert self.graph.get_node("a") is None
        assert self.graph.get_node("b") is not None


class TestLineageGraphSingleton:
    """Test global lineage graph singleton."""

    def setup_method(self):
        reset_lineage_graph()

    def teardown_method(self):
        reset_lineage_graph()

    def test_get_lineage_graph_creates_instance(self):
        graph = get_lineage_graph()
        assert isinstance(graph, LineageGraph)

    def test_get_lineage_graph_returns_same_instance(self):
        graph1 = get_lineage_graph()
        graph2 = get_lineage_graph()
        assert graph1 is graph2

    def test_reset_lineage_graph(self):
        graph1 = get_lineage_graph()
        reset_lineage_graph()
        graph2 = get_lineage_graph()
        assert graph1 is not graph2
