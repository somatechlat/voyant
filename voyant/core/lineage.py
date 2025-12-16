"""
Data Lineage Module

Tracks data flow from sources to artifacts.
Reference: docs/CANONICAL_ROADMAP.md - P5 Governance & Contracts

Features:
- Source-to-artifact lineage graph
- Column-level lineage
- Impact analysis (downstream dependencies)
- Lineage JSON export

Usage:
    from voyant.core.lineage import (
        LineageGraph, get_lineage_graph,
        add_lineage_edge, get_upstream, get_downstream
    )
    
    graph = get_lineage_graph()
    
    # Record lineage
    graph.add_edge("source:orders", "artifact:profile_123")
    
    # Query lineage
    upstream = graph.get_upstream("artifact:profile_123")
    downstream = graph.get_downstream("source:orders")
"""
from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


class NodeType(str, Enum):
    """Types of nodes in the lineage graph."""
    SOURCE = "source"            # External data source
    TABLE = "table"              # Ingested table
    COLUMN = "column"            # Column within a table
    JOB = "job"                  # Processing job
    ARTIFACT = "artifact"        # Generated artifact
    BASELINE = "baseline"        # Baseline version
    CONTRACT = "contract"        # Data contract


class EdgeType(str, Enum):
    """Types of edges in the lineage graph."""
    DERIVES_FROM = "derives_from"    # Downstream derives from upstream
    PRODUCES = "produces"            # Job produces artifact
    VALIDATES = "validates"          # Contract validates data
    REFERENCES = "references"        # References another entity


@dataclass
class LineageNode:
    """A node in the lineage graph."""
    node_id: str           # Unique ID (e.g., "source:orders", "artifact:abc123")
    node_type: NodeType
    name: str
    tenant_id: str
    
    # Metadata
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: float = 0
    
    def __post_init__(self):
        if self.created_at == 0:
            self.created_at = datetime.utcnow().timestamp()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "name": self.name,
            "tenant_id": self.tenant_id,
            "properties": self.properties,
        }


@dataclass
class LineageEdge:
    """An edge in the lineage graph."""
    source_id: str         # Upstream node
    target_id: str         # Downstream node
    edge_type: EdgeType
    
    # Metadata
    job_id: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: float = 0
    
    def __post_init__(self):
        if self.created_at == 0:
            self.created_at = datetime.utcnow().timestamp()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "edge_type": self.edge_type.value,
            "job_id": self.job_id,
            "properties": self.properties,
        }


class LineageGraph:
    """
    In-memory lineage graph implementation.
    
    For production, use a graph database (Neo4j, Neptune) or
    DataHub's lineage capabilities.
    """
    
    def __init__(self):
        self._nodes: Dict[str, LineageNode] = {}
        self._edges: List[LineageEdge] = []
        self._upstream: Dict[str, Set[str]] = defaultdict(set)  # node -> upstream nodes
        self._downstream: Dict[str, Set[str]] = defaultdict(set)  # node -> downstream nodes
    
    def add_node(
        self,
        node_id: str,
        node_type: NodeType,
        name: str,
        tenant_id: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> LineageNode:
        """Add a node to the graph."""
        if node_id in self._nodes:
            # Update existing node
            node = self._nodes[node_id]
            node.properties.update(properties or {})
            return node
        
        node = LineageNode(
            node_id=node_id,
            node_type=node_type,
            name=name,
            tenant_id=tenant_id,
            properties=properties or {},
        )
        self._nodes[node_id] = node
        return node
    
    def add_edge(
        self,
        source_id: str,
        target_id: str,
        edge_type: EdgeType = EdgeType.DERIVES_FROM,
        job_id: Optional[str] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> LineageEdge:
        """
        Add an edge between two nodes.
        
        The edge means: target DERIVES_FROM source (source -> target)
        """
        edge = LineageEdge(
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            job_id=job_id,
            properties=properties or {},
        )
        
        self._edges.append(edge)
        self._upstream[target_id].add(source_id)
        self._downstream[source_id].add(target_id)
        
        return edge
    
    def get_node(self, node_id: str) -> Optional[LineageNode]:
        """Get a node by ID."""
        return self._nodes.get(node_id)
    
    def get_upstream(
        self,
        node_id: str,
        depth: int = 1,
    ) -> List[str]:
        """
        Get upstream nodes (dependencies).
        
        Args:
            node_id: Target node
            depth: How many levels to traverse (1 = direct, -1 = all)
        """
        if depth == 0:
            return []
        
        direct = list(self._upstream.get(node_id, set()))
        
        if depth == 1:
            return direct
        
        # Recursive traversal
        result = set(direct)
        for upstream_id in direct:
            next_depth = -1 if depth < 0 else depth - 1
            result.update(self.get_upstream(upstream_id, next_depth))
        
        return list(result)
    
    def get_downstream(
        self,
        node_id: str,
        depth: int = 1,
    ) -> List[str]:
        """
        Get downstream nodes (dependents).
        
        Args:
            node_id: Source node
            depth: How many levels to traverse (1 = direct, -1 = all)
        """
        if depth == 0:
            return []
        
        direct = list(self._downstream.get(node_id, set()))
        
        if depth == 1:
            return direct
        
        # Recursive traversal
        result = set(direct)
        for downstream_id in direct:
            next_depth = -1 if depth < 0 else depth - 1
            result.update(self.get_downstream(downstream_id, next_depth))
        
        return list(result)
    
    def get_edges_for_node(self, node_id: str) -> List[LineageEdge]:
        """Get all edges involving a node."""
        return [
            e for e in self._edges
            if e.source_id == node_id or e.target_id == node_id
        ]
    
    def get_impact_analysis(
        self,
        node_id: str,
    ) -> Dict[str, Any]:
        """
        Analyze impact of changes to a node.
        
        Returns downstream dependencies that would be affected.
        """
        downstream = self.get_downstream(node_id, depth=-1)
        
        # Group by type
        by_type: Dict[str, List[str]] = defaultdict(list)
        for node_id in downstream:
            node = self._nodes.get(node_id)
            if node:
                by_type[node.node_type.value].append(node_id)
        
        return {
            "node_id": node_id,
            "total_impacted": len(downstream),
            "by_type": dict(by_type),
            "downstream_ids": downstream,
        }
    
    def to_json(
        self,
        tenant_id: Optional[str] = None,
        include_properties: bool = False,
    ) -> Dict[str, Any]:
        """
        Export graph as JSON.
        
        Args:
            tenant_id: Filter to specific tenant
            include_properties: Include node/edge properties
        """
        nodes = list(self._nodes.values())
        if tenant_id:
            nodes = [n for n in nodes if n.tenant_id == tenant_id]
        
        node_ids = {n.node_id for n in nodes}
        edges = [
            e for e in self._edges
            if e.source_id in node_ids and e.target_id in node_ids
        ]
        
        return {
            "nodes": [
                {
                    "id": n.node_id,
                    "type": n.node_type.value,
                    "name": n.name,
                    **({"properties": n.properties} if include_properties else {}),
                }
                for n in nodes
            ],
            "edges": [
                {
                    "source": e.source_id,
                    "target": e.target_id,
                    "type": e.edge_type.value,
                    **({"properties": e.properties} if include_properties else {}),
                }
                for e in edges
            ],
            "stats": {
                "node_count": len(nodes),
                "edge_count": len(edges),
            },
        }
    
    def record_job_lineage(
        self,
        job_id: str,
        tenant_id: str,
        source_tables: List[str],
        output_artifacts: List[str],
    ) -> None:
        """
        Record lineage for a job execution.
        
        Creates nodes and edges for: tables -> job -> artifacts
        """
        # Add job node
        job_node_id = f"job:{job_id}"
        self.add_node(job_node_id, NodeType.JOB, job_id, tenant_id)
        
        # Link source tables to job
        for table in source_tables:
            table_node_id = f"table:{table}"
            self.add_node(table_node_id, NodeType.TABLE, table, tenant_id)
            self.add_edge(table_node_id, job_node_id, EdgeType.DERIVES_FROM)
        
        # Link job to artifacts
        for artifact in output_artifacts:
            artifact_node_id = f"artifact:{artifact}"
            self.add_node(artifact_node_id, NodeType.ARTIFACT, artifact, tenant_id)
            self.add_edge(job_node_id, artifact_node_id, EdgeType.PRODUCES)
    
    def clear_tenant(self, tenant_id: str) -> int:
        """Clear all lineage for a tenant (testing)."""
        node_ids = [n.node_id for n in self._nodes.values() if n.tenant_id == tenant_id]
        
        for node_id in node_ids:
            del self._nodes[node_id]
            self._upstream.pop(node_id, None)
            self._downstream.pop(node_id, None)
        
        self._edges = [
            e for e in self._edges
            if e.source_id not in node_ids and e.target_id not in node_ids
        ]
        
        return len(node_ids)


# =============================================================================
# Singleton
# =============================================================================

_lineage_graph: Optional[LineageGraph] = None


def get_lineage_graph() -> LineageGraph:
    """Get or create the global lineage graph instance."""
    global _lineage_graph
    if _lineage_graph is None:
        _lineage_graph = LineageGraph()
        logger.info("Initialized lineage graph")
    return _lineage_graph


def reset_lineage_graph():
    """Reset the global lineage graph (testing)."""
    global _lineage_graph
    _lineage_graph = None
