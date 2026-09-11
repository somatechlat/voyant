"""Pipeline Transform Engine — composable data transforms.

Provides a registry of transform operations (Filter, Map, Join, Aggregate,
Sort, Dedup, Flatten) that can be composed into pipeline DAGs. Each transform
implements a common ``execute(input_data) → output_data`` interface.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

# Type alias for tabular data: list of row dicts
Rows = list[dict[str, Any]]


# ── Base ─────────────────────────────────────────────────────────────────────


class TransformBase(ABC):
    """Abstract base class for all pipeline transforms.

    Subclasses must implement ``execute(input_data, config)`` which receives
    the upstream output and the step's config dict.
    """

    # Human-readable type key used in PipelineStep.config["transform_type"]
    transform_type: str = ""

    # Declares what this transform can accept / produce for schema validation
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None

    @abstractmethod
    def execute(
        self,
        input_data: Any,
        config: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> Any:
        """Run the transform.

        Parameters
        ----------
        input_data:
            Output from the upstream step (usually ``Rows``).
        config:
            Step-level configuration dict (from ``PipelineStep.config``).
        context:
            Optional shared context across the pipeline run (parameters,
            intermediate results from other steps, etc.).

        Returns
        -------
        Transformed data, typically ``Rows``.
        """

    def validate_config(self, config: dict[str, Any]) -> list[str]:
        """Return a list of config error strings (empty = valid)."""
        return []

    def describe(self) -> dict[str, Any]:
        """Return a description dict for UI palette rendering."""
        return {
            "type": self.transform_type,
            "label": self.transform_type.replace("_", " ").title(),
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
        }


# ── Concrete Transforms ─────────────────────────────────────────────────────


class FilterTransform(TransformBase):
    """Filter rows by a condition expression.

    Config::

        {
            "field": "status",
            "operator": "==",       # ==, !=, >, <, >=, <=, in, not_in, contains, starts_with, ends_with
            "value": "active"
        }
    """

    transform_type = "filter"

    _OPS: dict[str, Callable[[Any, Any], bool]] = {
        "==": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
        ">": lambda a, b: a > b,
        "<": lambda a, b: a < b,
        ">=": lambda a, b: a >= b,
        "<=": lambda a, b: a <= b,
        "in": lambda a, b: a in b,
        "not_in": lambda a, b: a not in b,
        "contains": lambda a, b: str(b) in str(a),
        "starts_with": lambda a, b: str(a).startswith(str(b)),
        "ends_with": lambda a, b: str(a).endswith(str(b)),
    }

    def execute(
        self,
        input_data: Any,
        config: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> Rows:
        if not isinstance(input_data, list):
            return input_data

        field = config.get("field", "")
        operator = config.get("operator", "==")
        value = config.get("value")

        op_func = self._OPS.get(operator)
        if not op_func:
            logger.warning("Unknown filter operator: %s", operator)
            return input_data

        result: Rows = []
        for row in input_data:
            try:
                cell = row.get(field)
                if op_func(cell, value):
                    result.append(row)
            except (TypeError, KeyError):
                continue
        return result

    def validate_config(self, config: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        if not config.get("field"):
            errors.append("Filter requires 'field'")
        if config.get("operator") and config["operator"] not in self._OPS:
            errors.append(f"Unknown operator '{config['operator']}'")
        return errors


class MapTransform(TransformBase):
    """Apply a function/expression to each row.

    Config::

        {
            "expression": "row['price'] * 1.1",    # Python expression
            "output_field": "price_with_tax"
        }

    Or for direct field mapping::

        {
            "field_mapping": {
                "old_name": "new_name",
                "source_col": "dest_col"
            }
        }
    """

    transform_type = "map"

    def execute(
        self,
        input_data: Any,
        config: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> Rows:
        if not isinstance(input_data, list):
            return input_data

        # Field rename mode
        field_mapping = config.get("field_mapping")
        if field_mapping:
            return [
                {field_mapping.get(k, k): v for k, v in row.items()}
                for row in input_data
            ]

        # Expression mode
        expression = config.get("expression", "")
        output_field = config.get("output_field", "mapped_value")
        if not expression:
            return input_data

        result: Rows = []
        for row in input_data:
            new_row = dict(row)
            try:
                # Evaluate expression with row as local namespace
                new_row[output_field] = eval(  # noqa: S307 – intentional
                    expression, {"__builtins__": {}}, {"row": row, **row}
                )
            except Exception as exc:
                logger.debug("Map expression error: %s", exc)
                new_row[output_field] = None
            result.append(new_row)
        return result

    def validate_config(self, config: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        if not config.get("expression") and not config.get("field_mapping"):
            errors.append("Map requires 'expression' or 'field_mapping'")
        return errors


class JoinTransform(TransformBase):
    """Join two datasets on a key.

    Config::

        {
            "left_key": "user_id",
            "right_key": "id",
            "join_type": "inner",       # inner, left, right, full
            "right_data_field": "users"  # where to find right dataset in context
        }
    """

    transform_type = "join"

    def execute(
        self,
        input_data: Any,
        config: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> Rows:
        if not isinstance(input_data, list):
            return input_data

        left_key = config.get("left_key", "")
        right_key = config.get("right_key", left_key)
        join_type = config.get("join_type", "inner")
        right_data_field = config.get("right_data_field", "right")

        # Right dataset from context
        right_data: Rows = []
        if context:
            right_data = context.get(right_data_field, [])
        right_config_data = config.get("right_data")
        if isinstance(right_config_data, list):
            right_data = right_config_data

        if not right_data or not left_key:
            return input_data

        # Index right dataset
        right_index: dict[Any, list[dict[str, Any]]] = defaultdict(list)
        for rrow in right_data:
            right_index[rrow.get(right_key)].append(rrow)

        result: Rows = []
        matched_left: set[int] = set()

        for i, lrow in enumerate(input_data):
            lval = lrow.get(left_key)
            matches = right_index.get(lval, [])
            if matches:
                matched_left.add(i)
                for rmatch in matches:
                    result.append({**lrow, **rmatch})
            elif join_type in ("left", "full"):
                result.append(dict(lrow))

        # Right / full join: add unmatched right rows
        if join_type in ("right", "full"):
            matched_right: set[int] = set()
            for lrow in input_data:
                lval = lrow.get(left_key)
                for j, rrow in enumerate(right_data):
                    if rrow.get(right_key) == lval:
                        matched_right.add(j)
            for j, rrow in enumerate(right_data):
                if j not in matched_right:
                    result.append(dict(rrow))

        return result

    def validate_config(self, config: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        if not config.get("left_key"):
            errors.append("Join requires 'left_key'")
        jt = config.get("join_type", "inner")
        if jt not in ("inner", "left", "right", "full"):
            errors.append(f"Unknown join type '{jt}'")
        return errors


class AggregateTransform(TransformBase):
    """Group by + aggregate.

    Config::

        {
            "group_by": ["category"],
            "aggregations": [
                {"field": "amount", "function": "sum", "output": "total_amount"},
                {"field": "id", "function": "count", "output": "item_count"},
                {"field": "price", "function": "avg", "output": "avg_price"}
            ]
        }

    Supported functions: sum, avg, count, min, max, first, last, concat.
    """

    transform_type = "aggregate"

    _FUNCS: dict[str, Callable[[list[Any]], Any]] = {
        "sum": lambda vals: sum(v for v in vals if v is not None),
        "avg": lambda vals: (
            sum(v for v in vals if v is not None)
            / max(len([v for v in vals if v is not None]), 1)
        ),
        "count": lambda vals: len(vals),
        "min": lambda vals: min((v for v in vals if v is not None), default=None),
        "max": lambda vals: max((v for v in vals if v is not None), default=None),
        "first": lambda vals: vals[0] if vals else None,
        "last": lambda vals: vals[-1] if vals else None,
        "concat": lambda vals: ", ".join(str(v) for v in vals if v is not None),
    }

    def execute(
        self,
        input_data: Any,
        config: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> Rows:
        if not isinstance(input_data, list):
            return input_data

        group_by = config.get("group_by", [])
        if isinstance(group_by, str):
            group_by = [group_by]
        aggregations = config.get("aggregations", [])

        if not group_by and not aggregations:
            return input_data

        # Build groups
        groups: dict[tuple, Rows] = defaultdict(list)
        for row in input_data:
            key = tuple(row.get(g) for g in group_by) if group_by else ("__all__",)
            groups[key].append(row)

        result: Rows = []
        for key, rows in groups.items():
            out_row: dict[str, Any] = {}
            if group_by:
                for i, g in enumerate(group_by):
                    out_row[g] = key[i]

            for agg in aggregations:
                field = agg.get("field", "")
                func_name = agg.get("function", "count")
                output_name = agg.get("output", f"{func_name}_{field}")
                func = self._FUNCS.get(func_name)
                if not func:
                    out_row[output_name] = None
                    continue
                values = [r.get(field) for r in rows]
                out_row[output_name] = func(values)

            result.append(out_row)

        return result

    def validate_config(self, config: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        for agg in config.get("aggregations", []):
            fn = agg.get("function", "")
            if fn and fn not in self._FUNCS:
                errors.append(f"Unknown aggregate function '{fn}'")
        return errors


class SortTransform(TransformBase):
    """Sort rows by one or more columns.

    Config::

        {
            "sort_by": [
                {"field": "date", "direction": "desc"},
                {"field": "name", "direction": "asc"}
            ]
        }
    """

    transform_type = "sort"

    def execute(
        self,
        input_data: Any,
        config: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> Rows:
        if not isinstance(input_data, list):
            return input_data

        sort_by = config.get("sort_by", [])
        if isinstance(sort_by, str):
            sort_by = [{"field": sort_by, "direction": "asc"}]
        if not sort_by:
            return input_data

        result = list(input_data)
        for sort_spec in reversed(sort_by):
            field = sort_spec.get("field", "")
            reverse = sort_spec.get("direction", "asc") == "desc"
            result.sort(key=lambda r, f=field: (r.get(f) is None, r.get(f)), reverse=reverse)

        return result

    def validate_config(self, config: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        if not config.get("sort_by"):
            errors.append("Sort requires 'sort_by'")
        return errors


class DedupTransform(TransformBase):
    """Remove duplicate rows.

    Config::

        {
            "fields": ["email"],         # columns to check (empty = all)
            "keep": "first"              # first or last
        }
    """

    transform_type = "dedup"

    def execute(
        self,
        input_data: Any,
        config: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> Rows:
        if not isinstance(input_data, list):
            return input_data

        fields = config.get("fields", [])
        keep = config.get("keep", "first")

        seen: dict[tuple, int] = {}
        result: Rows = []

        iterable = input_data if keep == "first" else reversed(input_data)

        for row in iterable:
            if fields:
                key = tuple(row.get(f) for f in fields)
            else:
                key = tuple(sorted(row.items()))
            if key not in seen:
                seen[key] = 1
                result.append(row)

        if keep == "last":
            result.reverse()

        return result

    def validate_config(self, config: dict[str, Any]) -> list[str]:
        return []


class FlattenTransform(TransformBase):
    """Flatten nested structures (lists, nested dicts).

    Config::

        {
            "field": "tags",              # field containing nested list
            "flatten_type": "list",       # list | nested_dict
            "separator": "."              # key separator for nested_dict
        }
    """

    transform_type = "flatten"

    def execute(
        self,
        input_data: Any,
        config: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> Rows:
        if not isinstance(input_data, list):
            return input_data

        field = config.get("field", "")
        flatten_type = config.get("flatten_type", "list")
        separator = config.get("separator", ".")

        result: Rows = []

        if flatten_type == "list" and field:
            # Explode list field into one row per element
            for row in input_data:
                value = row.get(field)
                if isinstance(value, (list, tuple)):
                    if not value:
                        result.append(dict(row))
                    for item in value:
                        new_row = dict(row)
                        new_row[field] = item
                        result.append(new_row)
                else:
                    result.append(dict(row))

        elif flatten_type == "nested_dict":
            # Flatten nested dict keys with separator
            for row in input_data:
                flat_row = self._flatten_dict(row, separator)
                result.append(flat_row)
        else:
            return input_data

        return result

    @staticmethod
    def _flatten_dict(d: dict, sep: str = ".", prefix: str = "") -> dict[str, Any]:
        items: dict[str, Any] = {}
        for k, v in d.items():
            new_key = f"{prefix}{sep}{k}" if prefix else k
            if isinstance(v, dict):
                items.update(FlattenTransform._flatten_dict(v, sep, new_key))
            else:
                items[new_key] = v
        return items


# ── Registry ─────────────────────────────────────────────────────────────────


class TransformRegistry:
    """Registry for transform types. Supports register/lookup/list."""

    _transforms: dict[str, type[TransformBase]] = {}

    @classmethod
    def register(cls, transform_cls: type[TransformBase]) -> type[TransformBase]:
        """Register a transform class (usable as decorator)."""
        cls._transforms[transform_cls.transform_type] = transform_cls
        return transform_cls

    @classmethod
    def get(cls, transform_type: str) -> TransformBase | None:
        """Instantiate and return a transform by type key."""
        klass = cls._transforms.get(transform_type)
        if klass:
            return klass()
        return None

    @classmethod
    def list_types(cls) -> list[dict[str, Any]]:
        """Return descriptions of all registered transforms."""
        return [klass().describe() for klass in cls._transforms.values()]

    @classmethod
    def execute_transform(
        cls,
        transform_type: str,
        input_data: Any,
        config: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> Any:
        """Look up and execute a transform in one call."""
        transform = cls.get(transform_type)
        if not transform:
            logger.error("Unknown transform type: %s", transform_type)
            return input_data
        return transform.execute(input_data, config, context)


# ── Auto-register built-in transforms ───────────────────────────────────────

TransformRegistry.register(FilterTransform)
TransformRegistry.register(MapTransform)
TransformRegistry.register(JoinTransform)
TransformRegistry.register(AggregateTransform)
TransformRegistry.register(SortTransform)
TransformRegistry.register(DedupTransform)
TransformRegistry.register(FlattenTransform)
