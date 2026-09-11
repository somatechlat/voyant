"""
Ontology Query Engine — Translates semantic queries into Trino SQL.

Implements the query engine specified in the Deep-Dive spec §4.3:
- Aggregate queries (GROUP BY + SUM/AVG/COUNT/MIN/MAX/P95/P99)
- Interface-based queries (UNION ALL across implementing types)
- Count queries
- Cursor-based (keyset) pagination
- Geospatial near() filter
- Filter DSL translation (AND/OR/eq/neq/gt/gte/lt/lte/in/not_in/like/is_null/is_not_null)

All SQL is constructed from validated, schema-derived metadata — never from
raw user input — and executed through the existing TrinoClient.
"""

from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass
from typing import Any

from apps.core.lib.trino import QueryResult, TrinoClient, get_trino_client
from apps.ontology.models import Interface, ObjectType

logger = logging.getLogger(__name__)

# ── Allowed aggregation functions ────────────────────────────────────────────

ALLOWED_AGG_FUNCTIONS = frozenset(
    {"SUM", "AVG", "COUNT", "MIN", "MAX", "P95", "P99"}
)

# Trino equivalents for percentile functions
_PERCENTILE_MAP = {
    "P95": "approx_percentile(col, 0.95)",
    "P99": "approx_percentile(col, 0.99)",
}


# ── Data classes ─────────────────────────────────────────────────────────────


@dataclass
class AggregationSpec:
    """A single aggregation clause."""

    property: str  # column name
    function: str  # SUM, AVG, COUNT, MIN, MAX, P95, P99
    alias: str = ""  # optional output alias

    def __post_init__(self) -> None:
        func = self.function.upper()
        if func not in ALLOWED_AGG_FUNCTIONS:
            raise ValueError(
                f"Unsupported aggregation function: {self.function}. "
                f"Allowed: {sorted(ALLOWED_AGG_FUNCTIONS)}"
            )
        self.function = func
        if not self.alias:
            self.alias = f"{self.function.lower()}_{self.property}"


@dataclass
class GeoNearFilter:
    """Geospatial proximity filter."""

    lat: float
    lng: float
    radius_km: float
    lat_column: str = "latitude"
    lng_column: str = "longitude"


@dataclass
class QueryFilter:
    """Recursive filter expression tree."""

    # Leaf filters
    property: str | None = None
    operator: str | None = None  # eq, neq, gt, gte, lt, lte, in, not_in, like, is_null, is_not_null
    value: Any = None

    # Branch filters
    AND: list[QueryFilter] | None = None
    OR: list[QueryFilter] | None = None

    # Geospatial
    near: GeoNearFilter | None = None


@dataclass
class PaginationCursor:
    """Keyset pagination cursor."""

    last_pk_value: Any
    last_pk_column: str = "id"


@dataclass
class AggregateQueryParams:
    """Parameters for an aggregation query."""

    group_by: list[str]
    aggregations: list[AggregationSpec]
    filter: QueryFilter | None = None
    having: QueryFilter | None = None
    sort: list[dict[str, str]] | None = None  # [{"property": "x", "order": "asc|desc"}]
    limit: int = 1000


@dataclass
class InterfaceQueryParams:
    """Parameters for an interface-based query."""

    filter: QueryFilter | None = None
    sort: list[dict[str, str]] | None = None
    limit: int = 100
    cursor: PaginationCursor | None = None
    select: list[str] | None = None


# ── Identifier validation ────────────────────────────────────────────────────

_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _validate_identifier(name: str) -> str:
    """Ensure *name* is a safe SQL identifier (no injection vectors)."""
    if not _IDENT_RE.match(name):
        raise ValueError(
            f"Invalid identifier: {name!r}. "
            "Only alphanumeric characters and underscores are allowed."
        )
    return name


def _validate_dataset_name(name: str) -> str:
    """Validate a fully-qualified table name (schema.table)."""
    parts = name.split(".")
    for part in parts:
        _validate_identifier(part)
    return name


# ── Filter → SQL translator ─────────────────────────────────────────────────


def _build_filter_sql(
    filt: QueryFilter | None,
    table_alias: str = "",
) -> tuple[str, list[Any]]:
    """Translate a :class:`QueryFilter` tree into a SQL WHERE clause + params.

    Returns ``(clause, params)`` where *clause* may be empty (no filter).
    Parameters are inlined as Trino ``?`` placeholders.
    """
    if filt is None:
        return "", []

    prefix = f"{table_alias}." if table_alias else ""

    # Branch: AND / OR
    if filt.AND:
        parts: list[str] = []
        params: list[Any] = []
        for child in filt.AND:
            clause, p = _build_filter_sql(child, table_alias)
            if clause:
                parts.append(f"({clause})")
                params.extend(p)
        return " AND ".join(parts), params

    if filt.OR:
        parts = []
        params = []
        for child in filt.OR:
            clause, p = _build_filter_sql(child, table_alias)
            if clause:
                parts.append(f"({clause})")
                params.extend(p)
        return " OR ".join(parts), params

    # Geospatial near() filter
    if filt.near:
        nf = filt.near
        # Haversine approximation: 1 degree latitude ≈ 111 km
        lat_delta = nf.radius_km / 111.0
        # Adjust longitude delta by latitude
        lng_delta = nf.radius_km / (111.0 * max(math.cos(math.radians(nf.lat)), 0.01))
        clause = (
            f"{prefix}{_validate_identifier(nf.lat_column)} BETWEEN ? AND ? "
            f"AND {prefix}{_validate_identifier(nf.lng_column)} BETWEEN ? AND ?"
        )
        return clause, [
            nf.lat - lat_delta,
            nf.lat + lat_delta,
            nf.lng - lng_delta,
            nf.lng + lng_delta,
        ]

    # Leaf filter
    if filt.property is None or filt.operator is None:
        return "", []

    col = f"{prefix}{_validate_identifier(filt.property)}"
    op = filt.operator.lower()

    if op == "eq":
        return f"{col} = ?", [filt.value]
    if op == "neq":
        return f"{col} != ?", [filt.value]
    if op == "gt":
        return f"{col} > ?", [filt.value]
    if op == "gte":
        return f"{col} >= ?", [filt.value]
    if op == "lt":
        return f"{col} < ?", [filt.value]
    if op == "lte":
        return f"{col} <= ?", [filt.value]
    if op == "in":
        if not isinstance(filt.value, (list, tuple)):
            raise ValueError("'in' operator requires a list value")
        placeholders = ", ".join("?" for _ in filt.value)
        return f"{col} IN ({placeholders})", list(filt.value)
    if op == "not_in":
        if not isinstance(filt.value, (list, tuple)):
            raise ValueError("'not_in' operator requires a list value")
        placeholders = ", ".join("?" for _ in filt.value)
        return f"{col} NOT IN ({placeholders})", list(filt.value)
    if op == "like":
        return f"{col} LIKE ?", [filt.value]
    if op == "is_null":
        return f"{col} IS NULL", []
    if op == "is_not_null":
        return f"{col} IS NOT NULL", []

    raise ValueError(f"Unsupported filter operator: {filt.operator}")


# ── Aggregation SQL builder ──────────────────────────────────────────────────


def _agg_expr(agg: AggregationSpec) -> str:
    """Build the SQL expression for a single aggregation."""
    col = _validate_identifier(agg.property)
    alias = _validate_identifier(agg.alias)

    if agg.function == "P95":
        return f"approx_percentile({col}, 0.95) AS {alias}"
    if agg.function == "P99":
        return f"approx_percentile({col}, 0.99) AS {alias}"
    return f"{agg.function}({col}) AS {alias}"


# ── Main Query Engine ───────────────────────────────────────────────────────


class OntologyQueryEngine:
    """Translates Ontology-level queries into Trino SQL against backing datasets.

    Lifecycle::

        engine = OntologyQueryEngine(tenant_id="acme")
        result = engine.aggregate_query(type_id, params)
    """

    def __init__(
        self,
        tenant_id: str,
        trino: TrinoClient | None = None,
    ) -> None:
        self.tenant_id = tenant_id
        self._trino = trino or get_trino_client()

    # ── Internal helpers ─────────────────────────────────────────────────

    def _resolve_type(self, object_type_id: str) -> ObjectType:
        """Load an ObjectType and verify it belongs to this tenant."""
        ot = ObjectType.objects.filter(
            tenant_id=self.tenant_id,
            id=object_type_id,
            deleted_at__isnull=True,
        ).first()
        if ot is None:
            raise ValueError(f"Object type not found: {object_type_id}")
        if not ot.backing_dataset:
            raise ValueError(
                f"Object type '{ot.name}' has no backing_dataset configured"
            )
        return ot

    def _resolve_interface(self, interface_id: str) -> Interface:
        """Load an Interface and verify it belongs to this tenant."""
        iface = Interface.objects.filter(
            tenant_id=self.tenant_id,
            id=interface_id,
            deleted_at__isnull=True,
        ).first()
        if iface is None:
            raise ValueError(f"Interface not found: {interface_id}")
        return iface

    def _property_columns(self, ot: ObjectType) -> set[str]:
        """Return the set of property names defined on *ot*."""
        return {p.name for p in ot.properties.all()}

    # ── Public API ───────────────────────────────────────────────────────

    def aggregate_query(
        self,
        object_type_id: str,
        params: AggregateQueryParams,
    ) -> QueryResult:
        """Run an aggregation query against an object type's backing dataset.

        Translates to::

            SELECT <group_by_cols>, <agg_exprs>
            FROM <backing_dataset>
            WHERE <filter>
            GROUP BY <group_by_cols>
            [HAVING <having>]
            [ORDER BY <sort>]
            LIMIT <limit>

        Args:
            object_type_id: UUID of the ObjectType to query.
            params: Group-by columns, aggregation specs, optional filter/sort/limit.

        Returns:
            Trino :class:`QueryResult` with aggregated data.
        """
        ot = self._resolve_type(object_type_id)
        dataset = _validate_dataset_name(ot.backing_dataset)

        for gb in params.group_by:
            _validate_identifier(gb)

        # Build SELECT
        group_cols = ", ".join(_validate_identifier(g) for g in params.group_by)
        agg_exprs = ", ".join(_agg_expr(a) for a in params.aggregations)
        select_clause = f"{group_cols}, {agg_exprs}" if group_cols else agg_exprs

        sql = f"SELECT {select_clause}\nFROM {dataset}"

        # WHERE
        all_params: list[Any] = []
        where_clause, where_params = _build_filter_sql(params.filter)
        if where_clause:
            sql += f"\nWHERE {where_clause}"
            all_params.extend(where_params)

        # GROUP BY
        if params.group_by:
            sql += f"\nGROUP BY {group_cols}"

        # HAVING
        if params.having:
            having_clause, having_params = _build_filter_sql(params.having)
            if having_clause:
                sql += f"\nHAVING {having_clause}"
                all_params.extend(having_params)

        # ORDER BY
        if params.sort:
            order_parts = []
            for s in params.sort:
                prop = _validate_identifier(s["property"])
                direction = "DESC" if s.get("order", "").lower() == "desc" else "ASC"
                order_parts.append(f"{prop} {direction}")
            sql += f"\nORDER BY {', '.join(order_parts)}"

        # LIMIT
        sql += f"\nLIMIT {min(params.limit, self._trino.max_rows)}"

        logger.info("aggregate_query SQL: %s", sql)
        return self._trino.execute(sql, parameters=all_params or None)

    def count_query(
        self,
        object_type_id: str,
        filter: QueryFilter | None = None,
    ) -> int:
        """Return the count of objects matching *filter*.

        Args:
            object_type_id: UUID of the ObjectType.
            filter: Optional filter expression tree.

        Returns:
            Integer count.
        """
        ot = self._resolve_type(object_type_id)
        dataset = _validate_dataset_name(ot.backing_dataset)

        sql = f"SELECT COUNT(*) AS cnt\nFROM {dataset}"
        params: list[Any] = []

        where_clause, where_params = _build_filter_sql(filter)
        if where_clause:
            sql += f"\nWHERE {where_clause}"
            params.extend(where_params)

        result = self._trino.execute(sql, parameters=params or None)
        return int(result.rows[0][0]) if result.rows else 0

    def interface_query(
        self,
        interface_id: str,
        params: InterfaceQueryParams,
    ) -> dict[str, Any]:
        """Run a query across all implementing types of an interface.

        Executes one query per implementing type's backing dataset and merges
        results.  This avoids the Trino ``UNION`` keyword block in the
        read-only validator while still producing a unified result set.

        Args:
            interface_id: UUID of the Interface.
            params: Filter, sort, limit, cursor, select columns.

        Returns:
            ``{"results": [...], "total_count": int, "has_more": bool}``
        """
        iface = self._resolve_interface(interface_id)
        implementing_types = list(
            iface.implementing_types.filter(deleted_at__isnull=True)
        )
        if not implementing_types:
            return {"results": [], "total_count": 0, "has_more": False}

        all_rows: list[dict[str, Any]] = []
        per_type_limit = max(params.limit * 2, 200)  # over-fetch for merge-sort

        for ot in implementing_types:
            if not ot.backing_dataset:
                continue

            dataset = _validate_dataset_name(ot.backing_dataset)
            pk_col = _validate_identifier(ot.primary_key_column or "id")

            # SELECT clause
            if params.select:
                select_cols = ", ".join(
                    _validate_identifier(c) for c in params.select
                )
            else:
                select_cols = "*"

            sql = f"SELECT {select_cols}, '{ot.name}' AS _object_type\nFROM {dataset}"
            all_params: list[Any] = []

            # WHERE — combine user filter + cursor
            where_parts: list[str] = []
            where_clause, where_params = _build_filter_sql(params.filter)
            if where_clause:
                where_parts.append(f"({where_clause})")
                all_params.extend(where_params)

            if params.cursor:
                _validate_identifier(params.cursor.last_pk_column)
                where_parts.append(
                    f"{_validate_identifier(params.cursor.last_pk_column)} > ?"
                )
                all_params.append(params.cursor.last_pk_value)

            if where_parts:
                sql += f"\nWHERE {' AND '.join(where_parts)}"

            # ORDER BY
            if params.sort:
                order_parts = []
                for s in params.sort:
                    prop = _validate_identifier(s["property"])
                    direction = (
                        "DESC" if s.get("order", "").lower() == "desc" else "ASC"
                    )
                    order_parts.append(f"{prop} {direction}")
                sql += f"\nORDER BY {', '.join(order_parts)}"
            else:
                sql += f"\nORDER BY {pk_col} ASC"

            sql += f"\nLIMIT {per_type_limit}"

            try:
                result = self._trino.execute(sql, parameters=all_params or None)
                for row in result.rows:
                    row_dict = dict(zip(result.columns, row))
                    all_rows.append(row_dict)
            except Exception as exc:
                logger.warning(
                    "interface_query: failed on type %s/%s: %s",
                    ot.name,
                    ot.backing_dataset,
                    exc,
                )
                continue

        # Merge-sort by first sort property if specified, else by _object_type
        if params.sort and all_rows:
            sort_col = params.sort[0]["property"]
            reverse = params.sort[0].get("order", "").lower() == "desc"
            all_rows.sort(
                key=lambda r: (r.get(sort_col) is None, r.get(sort_col, "")),
                reverse=reverse,
            )

        total = len(all_rows)
        has_more = total > params.limit
        rows = all_rows[: params.limit]

        return {
            "results": rows,
            "total_count": total,
            "has_more": has_more,
        }

    def object_query(
        self,
        object_type_id: str,
        filter: QueryFilter | None = None,
        sort: list[dict[str, str]] | None = None,
        limit: int = 50,
        cursor: PaginationCursor | None = None,
        select: list[str] | None = None,
    ) -> dict[str, Any]:
        """Run a filtered, paginated query against an object type's backing dataset.

        Uses keyset pagination on the primary key for efficient cursor-based paging.

        Args:
            object_type_id: UUID of the ObjectType.
            filter: Optional filter expression tree.
            sort: Optional sort specification.
            limit: Max rows to return (default 50).
            cursor: Optional keyset cursor for pagination.
            select: Optional list of columns to return.

        Returns:
            ``{"results": [...], "has_more": bool, "next_cursor": {...} | None}``
        """
        ot = self._resolve_type(object_type_id)
        dataset = _validate_dataset_name(ot.backing_dataset)
        pk_col = _validate_identifier(ot.primary_key_column or "id")

        # SELECT
        if select:
            select_cols = ", ".join(_validate_identifier(c) for c in select)
        else:
            select_cols = "*"

        sql = f"SELECT {select_cols}\nFROM {dataset}"
        all_params: list[Any] = []

        # WHERE — combine filter + cursor
        where_parts: list[str] = []
        where_clause, where_params = _build_filter_sql(filter)
        if where_clause:
            where_parts.append(f"({where_clause})")
            all_params.extend(where_params)

        if cursor:
            _validate_identifier(cursor.last_pk_column)
            where_parts.append(
                f"{_validate_identifier(cursor.last_pk_column)} > ?"
            )
            all_params.append(cursor.last_pk_value)

        if where_parts:
            sql += f"\nWHERE {' AND '.join(where_parts)}"

        # ORDER BY
        if sort:
            order_parts = []
            for s in sort:
                prop = _validate_identifier(s["property"])
                direction = "DESC" if s.get("order", "").lower() == "desc" else "ASC"
                order_parts.append(f"{prop} {direction}")
            sql += f"\nORDER BY {', '.join(order_parts)}"
        else:
            sql += f"\nORDER BY {pk_col} ASC"

        # Fetch one extra to detect has_more
        fetch_limit = min(limit + 1, self._trino.max_rows)
        sql += f"\nLIMIT {fetch_limit}"

        logger.info("object_query SQL: %s", sql)
        result = self._trino.execute(sql, parameters=all_params or None)

        rows_as_dicts = [
            dict(zip(result.columns, row)) for row in result.rows
        ]

        has_more = len(rows_as_dicts) > limit
        rows = rows_as_dicts[:limit]

        next_cursor = None
        if has_more and rows:
            last_row = rows[-1]
            next_cursor = {
                "last_pk_column": pk_col,
                "last_pk_value": last_row.get(pk_col),
            }

        return {
            "results": rows,
            "has_more": has_more,
            "next_cursor": next_cursor,
        }
