"""
Ontology Branching — Git-like branching for ontology schemas.

Allows users to create isolated branches of the ontology for experimentation,
then diff and merge changes back to main. Each branch tracks the ontology
version it was created from and accumulates changes independently.

Supports:
- Create branch from main or another branch
- Merge branch with conflict detection
- Diff branches to see schema differences
- Branch lifecycle management (active, merged, abandoned)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.ontology.models import (
    Function,
    Interface,
    LinkType,
    ObjectType,
    Property,
)

logger = logging.getLogger(__name__)


# ── Branch Model ─────────────────────────────────────────────────────────────


class BranchStatus:
    ACTIVE = "active"
    MERGED = "merged"
    ABANDONED = "abandoned"


@dataclass
class OntologyBranch:
    """Represents a named branch of the ontology schema."""

    id: str
    name: str
    description: str
    tenant_id: str
    parent_branch: str  # "main" or another branch name
    created_from_version: int  # ontology version at branch creation
    status: str = BranchStatus.ACTIVE
    created_at: datetime = field(default_factory=timezone.now)
    merged_at: datetime | None = None
    created_by: str = ""

    # In-memory change tracking (serialized to JSON in storage)
    changes: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tenant_id": self.tenant_id,
            "parent_branch": self.parent_branch,
            "created_from_version": self.created_from_version,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "merged_at": self.merged_at.isoformat() if self.merged_at else None,
            "created_by": self.created_by,
            "changes_count": len(self.changes),
        }


# ── Diff Data Structures ─────────────────────────────────────────────────────


@dataclass
class SchemaDiff:
    """Represents the difference between two branches."""

    branch_from: str
    branch_to: str

    # Object type changes
    types_added: list[dict[str, Any]] = field(default_factory=list)
    types_removed: list[dict[str, Any]] = field(default_factory=list)
    types_modified: list[dict[str, Any]] = field(default_factory=list)

    # Property changes
    properties_added: list[dict[str, Any]] = field(default_factory=list)
    properties_removed: list[dict[str, Any]] = field(default_factory=list)
    properties_modified: list[dict[str, Any]] = field(default_factory=list)

    # Link type changes
    link_types_added: list[dict[str, Any]] = field(default_factory=list)
    link_types_removed: list[dict[str, Any]] = field(default_factory=list)
    link_types_modified: list[dict[str, Any]] = field(default_factory=list)

    # Interface changes
    interfaces_added: list[dict[str, Any]] = field(default_factory=list)
    interfaces_removed: list[dict[str, Any]] = field(default_factory=list)
    interfaces_modified: list[dict[str, Any]] = field(default_factory=list)

    # Function changes
    functions_added: list[dict[str, Any]] = field(default_factory=list)
    functions_removed: list[dict[str, Any]] = field(default_factory=list)
    functions_modified: list[dict[str, Any]] = field(default_factory=list)

    @property
    def total_changes(self) -> int:
        return (
            len(self.types_added) + len(self.types_removed) + len(self.types_modified)
            + len(self.properties_added) + len(self.properties_removed) + len(self.properties_modified)
            + len(self.link_types_added) + len(self.link_types_removed) + len(self.link_types_modified)
            + len(self.interfaces_added) + len(self.interfaces_removed) + len(self.interfaces_modified)
            + len(self.functions_added) + len(self.functions_removed) + len(self.functions_modified)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "branch_from": self.branch_from,
            "branch_to": self.branch_to,
            "total_changes": self.total_changes,
            "types_added": self.types_added,
            "types_removed": self.types_removed,
            "types_modified": self.types_modified,
            "properties_added": self.properties_added,
            "properties_removed": self.properties_removed,
            "properties_modified": self.properties_modified,
            "link_types_added": self.link_types_added,
            "link_types_removed": self.link_types_removed,
            "link_types_modified": self.link_types_modified,
            "interfaces_added": self.interfaces_added,
            "interfaces_removed": self.interfaces_removed,
            "interfaces_modified": self.interfaces_modified,
            "functions_added": self.functions_added,
            "functions_removed": self.functions_removed,
            "functions_modified": self.functions_modified,
        }


@dataclass
class MergeResult:
    """Result of merging a branch."""

    success: bool
    branch_name: str
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    merged_changes: int = 0
    skipped_conflicts: int = 0
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "branch_name": self.branch_name,
            "conflicts": self.conflicts,
            "merged_changes": self.merged_changes,
            "skipped_conflicts": self.skipped_conflicts,
            "message": self.message,
        }


# ── Branching Service ────────────────────────────────────────────────────────


class BranchingService:
    """
    Provides Git-like branching for ontology schemas.

    Branches are stored as in-memory change logs. In a production deployment,
    these would be persisted to a Django model. For now, we use a simple
    in-memory store that aligns with the existing service patterns.

    Usage::

        svc = BranchingService(tenant_id="acme")
        branch = svc.create_branch("feature/new-customer-types", parent="main")
        svc.apply_change(branch.id, "add_type", {"name": "VIPCustomer"})
        diff = svc.diff_branches("main", "feature/new-customer-types")
        result = svc.merge_branch("feature/new-customer-types")
    """

    # In-memory branch store (would be Django model in production)
    _branches: dict[str, dict[str, OntologyBranch]] = {}

    def __init__(self, tenant_id: str) -> None:
        self.tenant_id = tenant_id
        if tenant_id not in BranchingService._branches:
            BranchingService._branches[tenant_id] = {}

    @property
    def _store(self) -> dict[str, OntologyBranch]:
        return BranchingService._branches[self.tenant_id]

    def _current_version(self) -> int:
        """Get the current max version across all object types."""
        from django.db.models import Max
        result = ObjectType.objects.filter(
            tenant_id=self.tenant_id, deleted_at__isnull=True
        ).aggregate(max_ver=Max("version"))
        return result["max_ver"] or 1

    # ── CRUD ──────────────────────────────────────────────────────────────

    def create_branch(
        self,
        name: str,
        parent_branch: str = "main",
        description: str = "",
        created_by: str = "",
    ) -> OntologyBranch:
        """Create a new ontology branch."""
        if name in self._store:
            raise ValueError(f"Branch '{name}' already exists")
        if name == "main":
            raise ValueError("Cannot create a branch named 'main'")

        branch = OntologyBranch(
            id=f"br_{name.replace('/', '_')}_{int(timezone.now().timestamp())}",
            name=name,
            description=description,
            tenant_id=self.tenant_id,
            parent_branch=parent_branch,
            created_from_version=self._current_version(),
            created_by=created_by,
        )
        self._store[name] = branch
        logger.info("Created branch '%s' from '%s' (v%d)", name, parent_branch, branch.created_from_version)
        return branch

    def get_branch(self, name: str) -> OntologyBranch:
        """Get a branch by name."""
        if name not in self._store:
            raise ValueError(f"Branch '{name}' not found")
        return self._store[name]

    def list_branches(self, status: str | None = None) -> list[OntologyBranch]:
        """List all branches, optionally filtered by status."""
        branches = list(self._store.values())
        if status:
            branches = [b for b in branches if b.status == status]
        return sorted(branches, key=lambda b: b.created_at or datetime.min, reverse=True)

    def delete_branch(self, name: str) -> None:
        """Delete/abandon a branch."""
        if name == "main":
            raise ValueError("Cannot delete the main branch")
        branch = self.get_branch(name)
        if branch.status == BranchStatus.MERGED:
            raise ValueError("Cannot delete a merged branch")
        branch.status = BranchStatus.ABANDONED
        logger.info("Abandoned branch '%s'", name)

    # ── Change Tracking ───────────────────────────────────────────────────

    def apply_change(
        self,
        branch_name: str,
        change_type: str,
        payload: dict[str, Any],
    ) -> None:
        """
        Record a change on a branch.

        change_type: "add_type", "remove_type", "modify_type",
                     "add_property", "remove_property", "modify_property",
                     "add_link_type", "remove_link_type", etc.
        """
        branch = self.get_branch(branch_name)
        if branch.status != BranchStatus.ACTIVE:
            raise ValueError(f"Branch '{branch_name}' is not active (status: {branch.status})")

        change = {
            "type": change_type,
            "payload": payload,
            "timestamp": timezone.now().isoformat(),
        }
        branch.changes.append(change)
        logger.debug("Applied change '%s' to branch '%s'", change_type, branch_name)

    # ── Diff ──────────────────────────────────────────────────────────────

    def diff_branches(self, branch_from: str, branch_to: str) -> SchemaDiff:
        """
        Compute the schema difference between two branches.

        Currently compares branch change logs. In production, this would
        compare actual schema snapshots stored per branch.
        """
        diff = SchemaDiff(branch_from=branch_from, branch_to=branch_to)

        # Get changes from the target branch
        try:
            target = self.get_branch(branch_to)
        except ValueError:
            return diff

        # Classify changes by type
        for change in target.changes:
            ct = change["type"]
            payload = change["payload"]

            if ct == "add_type":
                diff.types_added.append(payload)
            elif ct == "remove_type":
                diff.types_removed.append(payload)
            elif ct == "modify_type":
                diff.types_modified.append(payload)
            elif ct == "add_property":
                diff.properties_added.append(payload)
            elif ct == "remove_property":
                diff.properties_removed.append(payload)
            elif ct == "modify_property":
                diff.properties_modified.append(payload)
            elif ct == "add_link_type":
                diff.link_types_added.append(payload)
            elif ct == "remove_link_type":
                diff.link_types_removed.append(payload)
            elif ct == "modify_link_type":
                diff.link_types_modified.append(payload)
            elif ct == "add_interface":
                diff.interfaces_added.append(payload)
            elif ct == "remove_interface":
                diff.interfaces_removed.append(payload)
            elif ct == "modify_interface":
                diff.interfaces_modified.append(payload)
            elif ct == "add_function":
                diff.functions_added.append(payload)
            elif ct == "remove_function":
                diff.functions_removed.append(payload)
            elif ct == "modify_function":
                diff.functions_modified.append(payload)

        return diff

    # ── Merge ─────────────────────────────────────────────────────────────

    def merge_branch(self, branch_name: str) -> MergeResult:
        """
        Merge a branch's changes into the main schema.

        Applies each change in order. Conflicts (e.g. type already exists)
        are collected but do not stop the merge. Non-conflicting changes
        are applied atomically.
        """
        branch = self.get_branch(branch_name)
        if branch.status != BranchStatus.ACTIVE:
            return MergeResult(
                success=False,
                branch_name=branch_name,
                message=f"Branch is not active (status: {branch.status})",
            )

        conflicts: list[dict[str, Any]] = []
        merged_count = 0

        with transaction.atomic():
            for change in branch.changes:
                try:
                    self._apply_change_to_main(change)
                    merged_count += 1
                except Exception as exc:
                    conflicts.append({
                        "change": change,
                        "error": str(exc),
                    })

        branch.status = BranchStatus.MERGED
        branch.merged_at = timezone.now()

        success = len(conflicts) == 0
        return MergeResult(
            success=success,
            branch_name=branch_name,
            conflicts=conflicts,
            merged_changes=merged_count,
            skipped_conflicts=len(conflicts),
            message=(
                f"Successfully merged {merged_count} changes"
                if success
                else f"Merged {merged_count} changes with {len(conflicts)} conflicts"
            ),
        )

    def _apply_change_to_main(self, change: dict[str, Any]) -> None:
        """Apply a single change to the main ontology."""
        ct = change["type"]
        payload = change["payload"]

        if ct == "add_type":
            ObjectType.objects.create(
                tenant_id=self.tenant_id,
                name=payload["name"],
                description=payload.get("description", ""),
            )
        elif ct == "remove_type":
            ot = ObjectType.objects.filter(
                tenant_id=self.tenant_id, name=payload["name"], deleted_at__isnull=True
            ).first()
            if ot:
                ot.deleted_at = timezone.now()
                ot.save(update_fields=["deleted_at", "updated_at"])
        elif ct == "modify_type":
            ot = ObjectType.objects.filter(
                tenant_id=self.tenant_id, name=payload["name"], deleted_at__isnull=True
            ).first()
            if ot:
                if "description" in payload:
                    ot.description = payload["description"]
                ot.version += 1
                ot.save()
        elif ct == "add_property":
            ot = ObjectType.objects.filter(
                tenant_id=self.tenant_id, name=payload.get("object_type_name", ""),
                deleted_at__isnull=True
            ).first()
            if ot:
                Property.objects.create(
                    tenant_id=self.tenant_id,
                    object_type=ot,
                    name=payload["name"],
                    property_type=payload.get("property_type", "string"),
                    required=payload.get("required", False),
                )
        elif ct == "add_interface":
            Interface.objects.create(
                tenant_id=self.tenant_id,
                name=payload["name"],
                description=payload.get("description", ""),
            )
        elif ct == "add_function":
            Function.objects.create(
                tenant_id=self.tenant_id,
                name=payload["name"],
                description=payload.get("description", ""),
                language=payload.get("language", "python"),
                source_code=payload.get("source_code", ""),
                entry_point=payload.get("entry_point", "handler"),
            )
        elif ct == "add_link_type":
            source_ot = ObjectType.objects.filter(
                tenant_id=self.tenant_id, name=payload.get("source_type", ""),
                deleted_at__isnull=True
            ).first()
            target_ot = ObjectType.objects.filter(
                tenant_id=self.tenant_id, name=payload.get("target_type", ""),
                deleted_at__isnull=True
            ).first()
            if source_ot and target_ot:
                LinkType.objects.create(
                    tenant_id=self.tenant_id,
                    name=payload["name"],
                    source_object_type=source_ot,
                    target_object_type=target_ot,
                    cardinality=payload.get("cardinality", "one_to_many"),
                )
        else:
            logger.warning("Unknown change type: %s", ct)
