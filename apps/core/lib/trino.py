"""
Trino client with read-only query enforcement.

All SQL is validated against a denylist of destructive keywords before execution.
Includes Row-Level Security (RLS) enforcement and column masking support.
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
from dataclasses import dataclass
from typing import Any

from apps.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """Trino SQL query result."""

    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    truncated: bool
    execution_time_ms: int
    query_id: str | None = None


class TrinoClient:
    """Validated, read-only Trino SQL client."""

    def __init__(self):
        settings = get_settings()
        self.host = settings.trino_host
        self.port = settings.trino_port
        self.user = settings.trino_user
        self.catalog = settings.trino_catalog
        self.schema = settings.trino_schema
        self.max_rows = settings.max_query_rows
        self._connection = None

    def _get_connection(self):
        if self._connection is None:
            try:
                import trino

                self._connection = trino.dbapi.connect(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    catalog=self.catalog,
                    schema=self.schema,
                )
                logger.info("Trino connection established: %s:%s", self.host, self.port)
            except ImportError:
                raise RuntimeError(
                    "Trino client is not installed. Run: pip install 'trino[dbapi]'"
                )
            except Exception as e:
                logger.error("Failed to establish connection to Trino: %s", e)
                raise
        return self._connection

    def execute(
        self,
        sql: str,
        limit: int | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> QueryResult:
        start_time = time.time()
        # Enforce the maximum allowed row limit.
        limit = min(limit or self.max_rows, self.max_rows)

        self._validate_sql(sql)
        sql_with_limit = self._apply_limit(sql, limit)

        conn = self._get_connection()
        cursor = conn.cursor()
        if parameters:
            cursor.execute(sql_with_limit, parameters)
        else:
            cursor.execute(sql_with_limit)

        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchall()

        return QueryResult(
            columns=columns,
            rows=[list(row) for row in rows],
            row_count=len(rows),
            truncated=len(rows) >= limit,
            execution_time_ms=int((time.time() - start_time) * 1000),
            query_id=getattr(cursor, "query_id", None),
        )

    @staticmethod
    def _validate_identifier(name: str) -> str:
        """Reject identifiers that contain injection-viable characters."""
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
            raise ValueError(
                f"Invalid identifier: {name!r}. "
                "Only alphanumeric characters and underscores are allowed."
            )
        return name

    def get_tables(self, schema: str | None = None) -> list[str]:
        target_schema = self._validate_identifier(schema or self.schema)
        result = self.execute(f"SHOW TABLES FROM {target_schema}")
        return [row[0] for row in result.rows]

    def get_columns(
        self, table: str, schema: str | None = None
    ) -> list[dict[str, Any]]:
        target_schema = self._validate_identifier(schema or self.schema)
        safe_table = self._validate_identifier(table)
        result = self.execute(f"DESCRIBE {target_schema}.{safe_table}")
        columns = []
        for row in result.rows:
            if not row:
                continue
            columns.append({"name": row[0], "type": row[1] if len(row) > 1 else ""})
        return columns

    def _validate_sql(self, sql: str) -> None:
        """
        Perform security validation on a SQL string to prevent destructive queries.

        Enforces read-only query policy using prefix allowlist and keyword denylist.
        Strips SQL comments before validation to prevent bypass.
        Blocks multi-statement injection via semicolons.

        Args:
            sql: The SQL string to validate.

        Raises:
            ValueError: If the query is not a read-only query or contains forbidden keywords.
        """
        # Block multi-statement injection — semicolons only allowed at the very end
        # (Trailing semicolon is harmless and commonly added by tools)
        semicolon_body = sql.rstrip().rstrip(";")
        if ";" in semicolon_body:
            raise ValueError(
                "Multi-statement queries are not allowed (semicolon detected)."
            )

        # Strip single-line comments (-- ...) and multi-line comments before validating
        stripped = re.sub(r"--[^\n]*", "", sql)
        stripped = re.sub(r"/\*.*?\*/", "", stripped, flags=re.DOTALL)
        sql_upper = stripped.strip().upper()

        allowed_prefixes = ("SELECT", "WITH", "SHOW", "DESCRIBE", "EXPLAIN")
        if not sql_upper.startswith(allowed_prefixes):
            raise ValueError(
                "Invalid query type. Only SELECT, WITH, SHOW, DESCRIBE, and EXPLAIN are allowed."
            )

        forbidden_keywords = [
            # DDL — schema mutation
            "DROP ",
            "CREATE ",
            "ALTER ",
            "TRUNCATE ",
            "RENAME ",
            # DML — data mutation
            "DELETE ",
            "INSERT ",
            "UPDATE ",
            "MERGE ",
            "UPSERT ",
            # Privilege escalation
            "GRANT ",
            "REVOKE ",
            # Session / procedural manipulation
            "SET ",
            "RESET ",
            "CALL ",
            "EXECUTE ",
            "PREPARE ",
            "DEALLOCATE ",
            # UNION-based exfiltration (covers UNION SELECT and UNION ALL SELECT)
            "UNION ",
            # Exfiltration / injection vectors
            "INTO OUTFILE",
            "INTO DUMPFILE",
            "LOAD_FILE(",
            "BENCHMARK(",
            "SLEEP(",
            "WAITFOR DELAY",
            "PG_SLEEP(",
            "DBMS_PIPE.RECEIVE_MESSAGE(",
        ]
        for kw in forbidden_keywords:
            if kw in sql_upper:
                raise ValueError(f"Forbidden SQL keyword detected: '{kw.strip()}'")

    def _apply_limit(self, sql: str, limit: int) -> str:
        # Do not modify the query if a LIMIT clause already exists.
        if " LIMIT " in sql.upper():
            return sql
        # Wrap the original query and apply the system limit.
        return f"SELECT * FROM ({sql}) AS _q LIMIT {limit}"

    # ------------------------------------------------------------------
    # Row-Level Security (RLS) enforcement  — GOV-F-003
    # ------------------------------------------------------------------

    def execute_with_governance(
        self,
        sql: str,
        tenant_id: str,
        user_id: str | None = None,
        user_roles: list[str] | None = None,
        limit: int | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> QueryResult:
        """Execute SQL with RLS filter injection and column masking.

        Steps:
        1. Look up active ``RowSecurityPolicy`` and ``SecurityPolicy``
           entries for *tenant_id* and any tables referenced in the query.
        2. Inject ``WHERE`` clauses based on policy configurations.
        3. Execute the (possibly modified) query.
        4. Apply column masking rules (``ColumnMaskPolicy`` + ``ColumnMask``)
           to the result set before returning.
        """
        from apps.governance.models import (
            ColumnMask,
            ColumnMaskPolicy,
            RowSecurityPolicy,
        )

        user_roles = user_roles or []

        # Apply RowSecurityPolicy RLS filters
        effective_sql = self._inject_rls_filters(
            sql,
            tenant_id,
            user_id,
            user_roles,
            RowSecurityPolicy,
        )

        # Apply SecurityPolicy RLS filters
        effective_sql = self._inject_security_policy_filters(
            effective_sql,
            tenant_id,
            user_roles,
        )

        result = self.execute(effective_sql, limit=limit, parameters=parameters)

        # Apply column masking
        result = self._apply_column_masks(
            result,
            tenant_id,
            user_roles,
            ColumnMaskPolicy,
        )
        result = self._apply_column_mask_defs(
            result,
            tenant_id,
            user_roles,
            ColumnMask,
        )
        return result

    def _inject_rls_filters(
        self,
        sql: str,
        tenant_id: str,
        user_id: str | None,
        user_roles: list[str],
        model_class: Any,
    ) -> str:
        """Inject RLS WHERE clauses into *sql* based on active policies."""
        policies = list(
            model_class.objects.filter(tenant_id=tenant_id, status="active")
        )
        if not policies:
            return sql

        # Group policies by table name
        table_policies: dict[str, list[Any]] = {}
        for p in policies:
            table_policies.setdefault(p.table_name, []).append(p)

        # Extract table references from the SQL (best-effort)
        referenced_tables = self._extract_table_references(sql)
        if not referenced_tables:
            return sql

        clauses: list[str] = []
        for table in referenced_tables:
            for policy in table_policies.get(table, []):
                if not self._policy_applies(policy, user_id, user_roles):
                    continue
                clause = self._build_filter_clause(
                    policy, tenant_id, user_id, user_roles
                )
                if clause:
                    clauses.append(clause)

        if not clauses:
            return sql

        combined_filter = " AND ".join(f"({c})" for c in clauses)

        # Inject into the outermost SELECT/WITH by wrapping
        return f"SELECT * FROM ({sql}) AS _rls_base WHERE {combined_filter}"

    @staticmethod
    def _policy_applies(
        policy: Any,
        user_id: str | None,
        user_roles: list[str],
    ) -> bool:
        """Return True if *policy* applies to the current user/roles."""
        applies_to_roles: list[str] = getattr(policy, "applies_to_roles", []) or []
        applies_to_users: list[str] = getattr(policy, "applies_to_users", []) or []

        if not applies_to_roles and not applies_to_users:
            return True  # applies to everyone

        if applies_to_users and user_id and user_id in applies_to_users:
            return True

        if applies_to_roles and any(r in applies_to_roles for r in user_roles):
            return True

        return False

    @staticmethod
    def _build_filter_clause(
        policy: Any,
        tenant_id: str,
        user_id: str | None,
        user_roles: list[str],
    ) -> str:
        """Build a SQL WHERE clause from a single RLS policy."""
        filter_type: str = getattr(policy, "filter_type", "")
        config: dict[str, Any] = getattr(policy, "filter_config", {}) or {}

        if filter_type == "user_match":
            column = config.get("column", policy.column_name or "tenant_id")
            safe_column = re.sub(r"[^A-Za-z0-9_.]", "", column)
            safe_user = (user_id or "").replace("'", "''")
            return f"{safe_column} = '{safe_user}'"

        if filter_type == "role_based":
            column = config.get("column", policy.column_name or "role")
            safe_column = re.sub(r"[^A-Za-z0-9_.]", "", column)
            role_map: dict[str, list[str]] = config.get("role_map", {})
            allowed_values: set[str] = set()
            for role in user_roles:
                vals = role_map.get(role, [])
                if "*" in vals:
                    return ""  # unrestricted
                allowed_values.update(vals)
            if not allowed_values:
                return "1 = 0"  # no matching role → deny all
            escaped = ", ".join(
                f"'{v.replace(chr(39), chr(39) * 2)}'" for v in allowed_values
            )
            return f"{safe_column} IN ({escaped})"

        if filter_type == "custom_sql":
            raw_sql: str = getattr(policy, "custom_sql", "")
            if raw_sql:
                return raw_sql

        return ""

    @staticmethod
    def _extract_table_references(sql: str) -> list[str]:
        """Best-effort extraction of table names from a SQL query."""
        # Match FROM and JOIN clauses
        stripped = re.sub(r"--[^\n]*", "", sql)
        stripped = re.sub(r"/\*.*?\*/", "", stripped, flags=re.DOTALL)
        tables: list[str] = []
        for m in re.finditer(
            r"(?:FROM|JOIN)\s+([A-Za-z_][A-Za-z0-9_.]*)",
            stripped,
            re.IGNORECASE,
        ):
            name = m.group(1)
            # Skip subquery aliases and Trino system tables
            if name.upper() in ("AS", "SELECT", "VALUES", "DUAL"):
                continue
            # Extract just the table name (last part after dot)
            parts = name.split(".")
            tables.append(parts[-1])
        return list(set(tables))

    # ------------------------------------------------------------------
    # Column masking — GOV-F-004
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_column_masks(
        result: QueryResult,
        tenant_id: str,
        user_roles: list[str],
        model_class: Any,
    ) -> QueryResult:
        """Apply column masking rules to the result set."""
        masks = list(model_class.objects.filter(tenant_id=tenant_id, status="active"))
        if not masks or not result.columns:
            return result

        # Build column→mask mapping
        col_mask_map: dict[str, list[Any]] = {}
        for m in masks:
            col_mask_map.setdefault(m.column_name, []).append(m)

        # Determine which masks apply based on roles
        active_masks: dict[str, Any] = {}
        for col_name, col_masks in col_mask_map.items():
            for mask in col_masks:
                exempt_roles: list[str] = mask.exempt_roles or []
                if any(r in exempt_roles for r in user_roles):
                    continue
                applies_to: list[str] = mask.applies_to_roles or []
                if applies_to and not any(r in applies_to for r in user_roles):
                    continue
                active_masks[col_name] = mask
                break  # first matching mask wins

        if not active_masks:
            return result

        # Build column index
        col_index = {name: i for i, name in enumerate(result.columns)}

        new_rows = []
        for row in result.rows:
            new_row = list(row)
            for col_name, mask in active_masks.items():
                idx = col_index.get(col_name)
                if idx is None or idx >= len(new_row):
                    continue
                new_row[idx] = TrinoClient._mask_value(
                    new_row[idx],
                    mask.mask_type,
                    mask.mask_config or {},
                )
            new_rows.append(new_row)

        return QueryResult(
            columns=result.columns,
            rows=new_rows,
            row_count=result.row_count,
            truncated=result.truncated,
            execution_time_ms=result.execution_time_ms,
            query_id=result.query_id,
        )

    @staticmethod
    def _mask_value(
        value: Any,
        mask_type: str,
        config: dict[str, Any],
    ) -> Any:
        """Apply a single masking transformation to a cell value."""
        if value is None:
            return None

        str_val = str(value)

        if mask_type == "null":
            return None

        if mask_type == "redact":
            return "[REDACTED]"

        if mask_type == "hash":
            return hashlib.sha256(str_val.encode()).hexdigest()[:16]

        if mask_type == "full":
            mask_char = config.get("mask_char", "*")
            return mask_char * min(len(str_val), 8)

        if mask_type == "partial":
            show_first = config.get("show_first", 2)
            show_last = config.get("show_last", 4)
            mask_char = config.get("mask_char", "*")
            if len(str_val) <= show_first + show_last:
                return mask_char * len(str_val)
            prefix = str_val[:show_first]
            suffix = str_val[-show_last:] if show_last > 0 else ""
            masked_len = max(0, len(str_val) - show_first - show_last)
            return f"{prefix}{mask_char * masked_len}{suffix}"

        if mask_type == "custom":
            # Custom mask config can specify a replacement template
            template = config.get("template", "***")
            return template

        return str_val

    # ------------------------------------------------------------------
    # SecurityPolicy RLS enforcement — GOV-F-006
    # ------------------------------------------------------------------

    def _inject_security_policy_filters(
        self,
        sql: str,
        tenant_id: str,
        user_roles: list[str],
    ) -> str:
        """Inject WHERE clauses from active SecurityPolicy entries.

        SecurityPolicy uses a simpler model than RowSecurityPolicy:
        ``filter_expression`` is a raw SQL fragment, ``roles`` is a JSON
        list of roles the policy applies to.
        """
        from apps.governance.models import SecurityPolicy

        policies = list(
            SecurityPolicy.objects.filter(tenant_id=tenant_id, status="active")
        )
        if not policies:
            return sql

        referenced_tables = self._extract_table_references(sql)
        if not referenced_tables:
            return sql

        clauses: list[str] = []
        for policy in policies:
            # Check table match (support wildcard "*")
            if policy.table_name != "*" and policy.table_name not in referenced_tables:
                continue
            # Check role match (empty roles = applies to everyone)
            policy_roles: list[str] = policy.roles or []
            if policy_roles and not any(r in policy_roles for r in user_roles):
                continue
            expr = (policy.filter_expression or "").strip()
            if expr:
                clauses.append(expr)

        if not clauses:
            return sql

        combined_filter = " AND ".join(f"({c})" for c in clauses)
        return f"SELECT * FROM ({sql}) AS _rls_sp WHERE {combined_filter}"

    # ------------------------------------------------------------------
    # ColumnMask enforcement — GOV-F-007
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_column_mask_defs(
        result: QueryResult,
        tenant_id: str,
        user_roles: list[str],
        model_class: Any,
    ) -> QueryResult:
        """Apply ColumnMask policies to the result set.

        Similar to ``_apply_column_masks`` but uses the ColumnMask model
        with ``mask_type`` in (null, hash, partial, redact).
        """
        masks = list(model_class.objects.filter(tenant_id=tenant_id, status="active"))
        if not masks or not result.columns:
            return result

        col_mask_map: dict[str, list[Any]] = {}
        for m in masks:
            col_mask_map.setdefault(m.column_name, []).append(m)

        active_masks: dict[str, Any] = {}
        for col_name, col_masks in col_mask_map.items():
            for mask in col_masks:
                exempt: list[str] = mask.exempt_roles or []
                if any(r in exempt for r in user_roles):
                    continue
                applies: list[str] = mask.roles or []
                if applies and not any(r in applies for r in user_roles):
                    continue
                active_masks[col_name] = mask
                break

        if not active_masks:
            return result

        col_index = {name: i for i, name in enumerate(result.columns)}

        new_rows = []
        for row in result.rows:
            new_row = list(row)
            for col_name, mask in active_masks.items():
                idx = col_index.get(col_name)
                if idx is None or idx >= len(new_row):
                    continue
                new_row[idx] = TrinoClient._mask_value(
                    new_row[idx],
                    mask.mask_type,
                    mask.mask_config or {},
                )
            new_rows.append(new_row)

        return QueryResult(
            columns=result.columns,
            rows=new_rows,
            row_count=result.row_count,
            truncated=result.truncated,
            execution_time_ms=result.execution_time_ms,
            query_id=result.query_id,
        )

    def close(self):
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("Trino connection closed.")


# Singleton client instance for application-wide use.
_client: TrinoClient | None = None


def get_trino_client() -> TrinoClient:
    global _client
    if _client is None:
        _client = TrinoClient()
    return _client
