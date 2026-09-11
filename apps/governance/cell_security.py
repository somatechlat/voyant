"""Cell-Level Security — models, engine, and Trino integration.

Provides row+column intersection access control where individual cells
can be allowed, masked, or denied based on viewer identity and row data.
This goes beyond column masking (which is role→column) by adding
row-condition awareness to cell-level decisions.

GOV-F-011
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

from django.db import models

from apps.core.models import TenantModel, UUIDModel

logger = logging.getLogger("voyant.governance")

__all__ = [
    "CellSecurityPolicy",
    "CellAccessDecision",
    "CellSecurityEngine",
]


# ---------------------------------------------------------------------------
# Decision enum
# ---------------------------------------------------------------------------


class CellAccessDecision(str, Enum):
    """Outcome of a cell-level security evaluation."""

    ALLOW = "allow"
    MASK = "mask"
    DENY = "deny"


# ---------------------------------------------------------------------------
# Django Model
# ---------------------------------------------------------------------------


class CellSecurityPolicy(TenantModel, UUIDModel):
    """Cell-level security policy controlling access at the table×column×row
    intersection.

    Each policy targets a specific table and column, with optional row and
    viewer conditions expressed as JSONPath-like filter expressions.

    Example: allow analysts to see salary column only for employees in
    their own department.

    .. code-block:: python

        CellSecurityPolicy(
            table="employees",
            column="salary",
            row_condition='{"department": "$viewer.department"}',
            viewer_condition='{"roles": ["analyst"]}',
            mask_value="***",
            decision="mask",
        )
    """

    class Decision(models.TextChoices):
        ALLOW = "allow", "Allow"
        MASK = "mask", "Mask"
        DENY = "deny", "Deny"

    STATUS_ACTIVE = "active"
    STATUS_INACTIVE = "inactive"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_INACTIVE, "Inactive"),
    ]

    name = models.CharField(max_length=255, help_text="Policy name")
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        db_index=True,
    )

    # Target
    table_name = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Fully-qualified table name",
    )
    column_name = models.CharField(
        max_length=255,
        help_text="Column this policy applies to",
    )

    # Conditions
    row_condition = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            'Row condition as key/value pairs. Values starting with "$viewer." '
            "are resolved from viewer attributes. Empty = all rows."
        ),
    )
    viewer_condition = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            'Viewer attributes that must match: {"roles": ["analyst"], '
            '"department": "finance"}. Empty = all viewers.'
        ),
    )

    # Action
    decision = models.CharField(
        max_length=10,
        choices=Decision.choices,
        default=Decision.MASK,
        help_text="Access decision when conditions match: allow / mask / deny",
    )
    mask_value = models.CharField(
        max_length=255,
        default="***",
        blank=True,
        help_text="Replacement value when decision is MASK",
    )

    # Ordering
    priority = models.IntegerField(
        default=100,
        help_text="Lower number = higher priority. First matching policy wins.",
    )

    class Meta(TenantModel.Meta, UUIDModel.Meta):
        db_table = "governance_cell_security_policy"
        verbose_name = "Cell Security Policy"
        verbose_name_plural = "Cell Security Policies"
        indexes = [
            models.Index(fields=["tenant_id", "table_name", "column_name"]),
            models.Index(fields=["tenant_id", "status"]),
        ]
        ordering = ["priority", "-created_at"]

    def __str__(self) -> str:
        return f"CellPolicy({self.name} → {self.table_name}.{self.column_name} [{self.decision}])"


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class CellSecurityEngine:
    """Evaluates cell-level security policies for a given user, table, column,
    and row data.

    Usage::

        engine = CellSecurityEngine()
        decision = engine.evaluate_cell_access(
            user={"id": "u1", "roles": ["analyst"], "department": "finance"},
            table="employees",
            column="salary",
            row_data={"department": "engineering", "salary": 150000},
        )
        # decision == CellAccessDecision.MASK
    """

    def __init__(self, tenant_id: str | None = None) -> None:
        self._tenant_id = tenant_id

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate_cell_access(
        self,
        user: dict[str, Any],
        table: str,
        column: str,
        row_data: dict[str, Any],
    ) -> CellAccessDecision:
        """Evaluate access for a single cell.

        Parameters
        ----------
        user:
            Viewer attributes dict — must contain at least ``id`` and ``roles``.
        table:
            Fully-qualified table name.
        column:
            Column name.
        row_data:
            Complete row values for condition evaluation.

        Returns
        -------
        CellAccessDecision
            ``ALLOW``, ``MASK``, or ``DENY``.
        """
        policies = self._get_policies(table, column)
        if not policies:
            return CellAccessDecision.ALLOW

        for policy in policies:
            if self._matches_viewer(policy, user) and self._matches_row(
                policy, user, row_data
            ):
                decision = CellAccessDecision(policy.decision)
                logger.debug(
                    "CellSecurity hit: policy=%s → %s (table=%s col=%s)",
                    policy.name,
                    decision.value,
                    table,
                    column,
                )
                return decision

        # No policy matched — default allow.
        return CellAccessDecision.ALLOW

    def apply_cell_masks(
        self,
        user: dict[str, Any],
        table: str,
        columns: list[str],
        rows: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Apply cell-level masks to an entire result set.

        Parameters
        ----------
        user:
            Viewer attributes dict.
        table:
            Fully-qualified table name.
        columns:
            Column names present in each row.
        rows:
            List of row dicts.

        Returns
        -------
        list[dict[str, Any]]
            Rows with masked/denied cells replaced.
        """
        result: list[dict[str, Any]] = []
        for row in rows:
            masked_row: dict[str, Any] = {}
            for col in columns:
                if col not in row:
                    continue
                decision = self.evaluate_cell_access(user, table, col, row)
                if decision == CellAccessDecision.DENY:
                    masked_row[col] = None
                elif decision == CellAccessDecision.MASK:
                    policy = self._get_first_matching_policy(user, table, col, row)
                    mask_val = policy.mask_value if policy else "***"
                    masked_row[col] = self._apply_mask(row[col], mask_val)
                else:
                    masked_row[col] = row[col]
            result.append(masked_row)
        return result

    def get_policies_for_table(
        self, table: str
    ) -> list[CellSecurityPolicy]:
        """Return all active policies for a given table."""
        return list(self._get_policies(table, column=None))

    # ------------------------------------------------------------------
    # Trino integration helper
    # ------------------------------------------------------------------

    def build_cell_mask_sql(
        self,
        table: str,
        columns: list[str],
        user: dict[str, Any],
    ) -> dict[str, str]:
        """Build a mapping of column → SQL CASE expression for cell masking.

        This is used by the Trino client to rewrite SELECT clauses for
        tables that have cell-level policies.

        Returns
        -------
        dict[str, str]
            Mapping of column name → SQL CASE expression. Only columns
            with active policies are included.
        """
        column_masks: dict[str, str] = {}
        for col in columns:
            policies = self._get_policies(table, col)
            if not policies:
                continue

            # Build CASE WHEN ... THEN mask_value ELSE col END
            for policy in policies:
                if not self._matches_viewer(policy, user):
                    continue
                if policy.decision == CellAccessDecision.DENY.value:
                    column_masks[col] = f"NULL AS {col}"
                elif policy.decision == CellAccessDecision.MASK.value:
                    safe_mask = self._sql_escape(policy.mask_value)
                    # Build a simple CASE based on row_condition columns
                    when_clauses = self._build_when_clauses(policy, user)
                    if when_clauses:
                        column_masks[col] = (
                            f"CASE WHEN {when_clauses} "
                            f"THEN '{safe_mask}' ELSE {col} END AS {col}"
                        )
                    else:
                        column_masks[col] = f"'{safe_mask}' AS {col}"
                break  # First matching policy wins

        return column_masks

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_policies(
        self, table: str, column: str | None
    ) -> list[CellSecurityPolicy]:
        """Fetch active policies from DB for the given table (and optionally column)."""
        try:
            qs = CellSecurityPolicy.objects.filter(
                table_name=table,
                status=CellSecurityPolicy.STATUS_ACTIVE,
            )
            if self._tenant_id:
                qs = qs.filter(tenant_id=self._tenant_id)
            if column:
                qs = qs.filter(column_name=column)
            return list(qs)
        except Exception:
            logger.debug("CellSecurityPolicy query failed", exc_info=True)
            return []

    def _get_first_matching_policy(
        self,
        user: dict[str, Any],
        table: str,
        column: str,
        row_data: dict[str, Any],
    ) -> CellSecurityPolicy | None:
        """Return the first matching policy for mask_value extraction."""
        for policy in self._get_policies(table, column):
            if self._matches_viewer(policy, user) and self._matches_row(
                policy, user, row_data
            ):
                return policy
        return None

    @staticmethod
    def _matches_viewer(
        policy: CellSecurityPolicy, user: dict[str, Any]
    ) -> bool:
        """Check if the viewer satisfies the policy's viewer_condition."""
        vc = policy.viewer_condition
        if not vc:
            return True  # No viewer constraint → matches everyone.

        for attr, expected in vc.items():
            actual = user.get(attr)
            if isinstance(expected, list):
                if attr == "roles":
                    # User must have at least one matching role.
                    user_roles = user.get("roles", [])
                    if not set(expected) & set(user_roles):
                        return False
                elif actual not in expected:
                    return False
            elif actual != expected:
                return False
        return True

    @staticmethod
    def _matches_row(
        policy: CellSecurityPolicy,
        user: dict[str, Any],
        row_data: dict[str, Any],
    ) -> bool:
        """Check if the row satisfies the policy's row_condition.

        Supports ``$viewer.<attr>`` references in condition values to
        dynamically resolve viewer attributes.
        """
        rc = policy.row_condition
        if not rc:
            return True  # No row constraint → matches all rows.

        for col_name, expected_val in rc.items():
            actual = row_data.get(col_name)
            if isinstance(expected_val, str) and expected_val.startswith("$viewer."):
                viewer_attr = expected_val[len("$viewer."):]
                expected_val = user.get(viewer_attr)
            if actual != expected_val:
                return False
        return True

    @staticmethod
    def _apply_mask(value: Any, mask_value: str) -> Any:
        """Apply a mask to a cell value."""
        if value is None:
            return None
        return mask_value

    @staticmethod
    def _sql_escape(value: str) -> str:
        """Escape a string value for safe SQL embedding."""
        return value.replace("'", "''")

    def _build_when_clauses(
        self, policy: CellSecurityPolicy, user: dict[str, Any]
    ) -> str:
        """Build SQL WHERE fragment from row_condition."""
        rc = policy.row_condition
        if not rc:
            return ""  # No condition → unconditional mask.

        parts: list[str] = []
        for col, val in rc.items():
            if isinstance(val, str) and val.startswith("$viewer."):
                viewer_attr = val[len("$viewer."):]
                resolved = user.get(viewer_attr)
                if resolved is None:
                    continue
                if isinstance(resolved, str):
                    parts.append(f"{col} = '{self._sql_escape(resolved)}'")
                else:
                    parts.append(f"{col} = {resolved}")
            elif isinstance(val, str):
                parts.append(f"{col} = '{self._sql_escape(val)}'")
            elif isinstance(val, (int, float)):
                parts.append(f"{col} = {val}")
            elif val is None:
                parts.append(f"{col} IS NULL")

        return " AND ".join(parts) if parts else ""
