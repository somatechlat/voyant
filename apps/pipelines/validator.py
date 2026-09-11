"""Pipeline DAG Validator — cycle detection, schema compatibility, topological sort.

Validates that a set of pipeline steps and edges form a valid DAG before
execution. Checks for cycles, missing connections, and (optionally) schema
compatibility between connected transforms.
"""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from typing import Any

logger = logging.getLogger(__name__)


class DAGValidationError:
    """A single validation error with severity and context."""

    def __init__(
        self,
        message: str,
        severity: str = "error",
        step_id: str | None = None,
        edge: tuple[str, str] | None = None,
    ) -> None:
        self.message = message
        self.severity = severity  # "error" | "warning"
        self.step_id = step_id
        self.edge = edge

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "message": self.message,
            "severity": self.severity,
        }
        if self.step_id:
            d["step_id"] = self.step_id
        if self.edge:
            d["edge"] = {"source": self.edge[0], "target": self.edge[1]}
        return d


class DAGValidationResult:
    """Aggregate result of DAG validation."""

    def __init__(self) -> None:
        self.errors: list[DAGValidationError] = []
        self.warnings: list[DAGValidationError] = []
        self.execution_order: list[str] = []

    @property
    def valid(self) -> bool:
        return len(self.errors) == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
            "execution_order": self.execution_order,
        }

    def add_error(self, message: str, **kwargs: Any) -> None:
        self.errors.append(DAGValidationError(message, severity="error", **kwargs))

    def add_warning(self, message: str, **kwargs: Any) -> None:
        self.warnings.append(DAGValidationError(message, severity="warning", **kwargs))


# ── Validation ───────────────────────────────────────────────────────────────


def validate_dag(
    steps: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> DAGValidationResult:
    """Validate a pipeline DAG.

    Parameters
    ----------
    steps:
        List of step dicts. Each must have at least ``id`` and ``step_type``.
        Optional: ``name``, ``config``, ``transform_type``.
    edges:
        List of edge dicts: ``{"source": "<step_id>", "target": "<step_id>"}``

    Returns
    -------
    DAGValidationResult with errors, warnings, and (if valid) execution_order.
    """
    result = DAGValidationResult()

    if not steps:
        result.add_warning("Pipeline has no steps")
        return result

    step_ids = {s["id"] for s in steps}
    step_map = {s["id"]: s for s in steps}

    # ── Validate edges reference existing steps ──
    adj: dict[str, set[str]] = defaultdict(set)
    in_degree: dict[str, int] = {sid: 0 for sid in step_ids}

    for edge in edges:
        src = edge.get("source", "")
        tgt = edge.get("target", "")
        if src not in step_ids:
            result.add_error(f"Edge source '{src}' not found in steps", edge=(src, tgt))
            continue
        if tgt not in step_ids:
            result.add_error(f"Edge target '{tgt}' not found in steps", edge=(src, tgt))
            continue
        if src == tgt:
            result.add_error(f"Self-loop on step '{src}'", step_id=src)
            continue
        adj[src].add(tgt)
        in_degree[tgt] = in_degree.get(tgt, 0) + 1

    # ── Cycle detection (Kahn's algorithm) ──
    topo_order = _topological_sort(step_ids, adj, in_degree.copy())
    if topo_order is None:
        result.add_error("DAG contains a cycle")
        # Try to identify the cycle for a useful error message
        cycle = _find_cycle(step_ids, adj)
        if cycle:
            result.add_error(f"Cycle path: {' → '.join(cycle)}")
        return result

    result.execution_order = topo_order

    # ── Check for disconnected components ──
    all_connected: set[str] = set()
    for edge in edges:
        all_connected.add(edge.get("source", ""))
        all_connected.add(edge.get("target", ""))
    orphans = step_ids - all_connected
    if orphans and len(step_ids) > 1:
        for orphan in orphans:
            result.add_warning(
                f"Step '{orphan}' has no connections",
                step_id=orphan,
            )

    # ── Check for source nodes (no incoming edges) ──
    sources = [sid for sid in step_ids if in_degree.get(sid, 0) == 0]
    if not sources and len(step_ids) > 0:
        result.add_error("No source node found (every node has an incoming edge)")

    # ── Check for sink nodes (no outgoing edges) ──
    sinks = [sid for sid in step_ids if len(adj.get(sid, set())) == 0]
    if not sinks and len(step_ids) > 0:
        result.add_warning("No sink node found (every node has an outgoing edge)")

    # ── Schema compatibility checks ──
    _check_schema_compatibility(step_map, edges, adj, result)

    # ── Validate transform configs ──
    _validate_transform_configs(steps, result)

    return result


# ── Topological Sort ─────────────────────────────────────────────────────────


def topological_sort(
    steps: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> list[str] | None:
    """Return execution order as list of step IDs, or None if cyclic.

    This is a convenience wrapper around the internal Kahn's implementation.
    """
    step_ids = {s["id"] for s in steps}
    adj: dict[str, set[str]] = defaultdict(set)
    in_degree: dict[str, int] = {sid: 0 for sid in step_ids}

    for edge in edges:
        src = edge.get("source", "")
        tgt = edge.get("target", "")
        if src in step_ids and tgt in step_ids and src != tgt:
            adj[src].add(tgt)
            in_degree[tgt] = in_degree.get(tgt, 0) + 1

    return _topological_sort(step_ids, adj, in_degree)


def _topological_sort(
    node_ids: set[str],
    adj: dict[str, set[str]],
    in_degree: dict[str, int],
) -> list[str] | None:
    """Kahn's algorithm. Returns ordered list or None if cycle detected."""
    queue: deque[str] = deque()
    for nid in node_ids:
        if in_degree.get(nid, 0) == 0:
            queue.append(nid)

    order: list[str] = []
    while queue:
        node = queue.popleft()
        order.append(node)
        for neighbor in sorted(adj.get(node, set())):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(order) != len(node_ids):
        return None  # Cycle
    return order


def _find_cycle(
    node_ids: set[str],
    adj: dict[str, set[str]],
) -> list[str] | None:
    """DFS-based cycle finder. Returns the cycle path or None."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {nid: WHITE for nid in node_ids}
    parent: dict[str, str | None] = {nid: None for nid in node_ids}

    for start in node_ids:
        if color[start] != WHITE:
            continue
        stack = [start]
        while stack:
            node = stack[-1]
            if color[node] == WHITE:
                color[node] = GRAY
                for neighbor in adj.get(node, set()):
                    if color[neighbor] == GRAY:
                        # Found cycle — reconstruct path
                        cycle = [neighbor, node]
                        current = node
                        while parent[current] is not None and parent[current] != neighbor:
                            current = parent[current]  # type: ignore[assignment]
                            cycle.append(current)
                        cycle.reverse()
                        return cycle
                    if color[neighbor] == WHITE:
                        parent[neighbor] = node
                        stack.append(neighbor)
            else:
                color[node] = BLACK
                stack.pop()

    return None


# ── Schema Compatibility ─────────────────────────────────────────────────────


def _check_schema_compatibility(
    step_map: dict[str, dict[str, Any]],
    edges: list[dict[str, Any]],
    adj: dict[str, set[str]],
    result: DAGValidationResult,
) -> None:
    """Check that connected transforms have compatible schemas."""
    from apps.pipelines.transforms import TransformRegistry

    for edge in edges:
        src_id = edge.get("source", "")
        tgt_id = edge.get("target", "")
        src_step = step_map.get(src_id)
        tgt_step = step_map.get(tgt_id)
        if not src_step or not tgt_step:
            continue

        src_type = src_step.get("config", {}).get("transform_type", src_step.get("step_type", ""))
        tgt_type = tgt_step.get("config", {}).get("transform_type", tgt_step.get("step_type", ""))

        src_transform = TransformRegistry.get(src_type)
        tgt_transform = TransformRegistry.get(tgt_type)

        if src_transform and tgt_transform:
            src_out = src_transform.output_schema
            tgt_in = tgt_transform.input_schema
            if src_out and tgt_in and src_out.get("type") != tgt_in.get("type"):
                result.add_warning(
                    f"Potential schema mismatch: '{src_type}' output "
                    f"({src_out.get('type')}) → '{tgt_type}' input ({tgt_in.get('type')})",
                    edge=(src_id, tgt_id),
                )


# ── Config Validation ────────────────────────────────────────────────────────


def _validate_transform_configs(
    steps: list[dict[str, Any]],
    result: DAGValidationResult,
) -> None:
    """Validate each step's transform config."""
    from apps.pipelines.transforms import TransformRegistry

    for step in steps:
        config = step.get("config", {})
        transform_type = config.get("transform_type", step.get("step_type", ""))
        transform = TransformRegistry.get(transform_type)
        if transform:
            config_errors = transform.validate_config(config)
            for err in config_errors:
                result.add_error(
                    f"Step '{step.get('name', step['id'])}': {err}",
                    step_id=step["id"],
                )
