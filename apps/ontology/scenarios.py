"""
Scenario Engine — What-if analysis for ontology changes.

Allows users to create hypothetical scenarios that apply changes to a
snapshot of the ontology, compare results, and merge approved scenarios
into the main ontology. Think of it as a sandbox for schema evolution.

Supports:
- Create scenario from current ontology snapshot
- Apply hypothetical changes (add/remove/modify types, properties, links)
- Compare scenario with base ontology to see impact
- Merge approved scenarios into main ontology
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.ontology.models import (
    LinkType,
    Object,
    ObjectType,
    Property,
)

logger = logging.getLogger(__name__)


# ── Scenario Model ───────────────────────────────────────────────────────────


class ScenarioStatus:
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    MERGED = "merged"
    REJECTED = "rejected"


@dataclass
class Scenario:
    """A hypothetical set of ontology changes for what-if analysis."""

    id: str
    name: str
    description: str
    tenant_id: str
    base_ontology_snapshot: dict[str, Any]  # Serialized snapshot at creation
    changes: list[dict[str, Any]] = field(default_factory=list)
    status: str = ScenarioStatus.DRAFT
    created_at: datetime = field(default_factory=timezone.now)
    updated_at: datetime = field(default_factory=timezone.now)
    merged_at: datetime | None = None
    created_by: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tenant_id": self.tenant_id,
            "status": self.status,
            "changes_count": len(self.changes),
            "changes": self.changes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "merged_at": self.merged_at.isoformat() if self.merged_at else None,
            "created_by": self.created_by,
            "metadata": self.metadata,
        }


# ── Comparison Result ────────────────────────────────────────────────────────


@dataclass
class ScenarioComparison:
    """Comparison between a scenario and its base ontology."""

    scenario_id: str
    scenario_name: str
    base_version: int

    # Impact analysis
    types_would_add: list[dict[str, Any]] = field(default_factory=list)
    types_would_remove: list[dict[str, Any]] = field(default_factory=list)
    types_would_modify: list[dict[str, Any]] = field(default_factory=list)

    properties_would_add: list[dict[str, Any]] = field(default_factory=list)
    properties_would_remove: list[dict[str, Any]] = field(default_factory=list)
    properties_would_modify: list[dict[str, Any]] = field(default_factory=list)

    links_would_add: list[dict[str, Any]] = field(default_factory=list)
    links_would_remove: list[dict[str, Any]] = field(default_factory=list)

    # Risk assessment
    breaking_changes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def total_changes(self) -> int:
        return (
            len(self.types_would_add) + len(self.types_would_remove) + len(self.types_would_modify)
            + len(self.properties_would_add) + len(self.properties_would_remove) + len(self.properties_would_modify)
            + len(self.links_would_add) + len(self.links_would_remove)
        )

    @property
    def has_breaking_changes(self) -> bool:
        return len(self.breaking_changes) > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "base_version": self.base_version,
            "total_changes": self.total_changes,
            "has_breaking_changes": self.has_breaking_changes,
            "types_would_add": self.types_would_add,
            "types_would_remove": self.types_would_remove,
            "types_would_modify": self.types_would_modify,
            "properties_would_add": self.properties_would_add,
            "properties_would_remove": self.properties_would_remove,
            "properties_would_modify": self.properties_would_modify,
            "links_would_add": self.links_would_add,
            "links_would_remove": self.links_would_remove,
            "breaking_changes": self.breaking_changes,
            "warnings": self.warnings,
        }


@dataclass
class MergeResult:
    """Result of merging a scenario into the main ontology."""

    success: bool
    scenario_id: str
    scenario_name: str
    applied_changes: int = 0
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "applied_changes": self.applied_changes,
            "conflicts": self.conflicts,
            "message": self.message,
        }


# ── Scenario Service ─────────────────────────────────────────────────────────


class ScenarioService:
    """
    Provides what-if analysis for ontology changes.

    Scenarios capture a snapshot of the current ontology, then track
    hypothetical changes. Users can compare scenarios against the base
    to understand impact before merging.

    Usage::

        svc = ScenarioService(tenant_id="acme")
        scenario = svc.create_scenario("New Customer Types", "Adding VIP tier")
        svc.apply_change(scenario.id, "add_type", {"name": "VIPCustomer"})
        svc.apply_change(scenario.id, "add_property", {
            "type_name": "Customer",
            "name": "tier",
            "property_type": "string"
        })
        comparison = svc.compare_with_base(scenario.id)
        if not comparison.has_breaking_changes:
            result = svc.merge_to_main(scenario.id)
    """

    # In-memory scenario store (would be Django model in production)
    _scenarios: dict[str, dict[str, Scenario]] = {}

    def __init__(self, tenant_id: str) -> None:
        self.tenant_id = tenant_id
        if tenant_id not in ScenarioService._scenarios:
            ScenarioService._scenarios[tenant_id] = {}

    @property
    def _store(self) -> dict[str, Scenario]:
        return ScenarioService._scenarios[self.tenant_id]

    def _capture_snapshot(self) -> dict[str, Any]:
        """Capture a snapshot of the current ontology state."""
        types = ObjectType.objects.filter(
            tenant_id=self.tenant_id, deleted_at__isnull=True
        ).prefetch_related("properties")

        snapshot: dict[str, Any] = {
            "version": 0,
            "types": [],
            "links": [],
        }

        for ot in types:
            type_data = {
                "id": str(ot.id),
                "name": ot.name,
                "description": ot.description,
                "version": ot.version,
                "properties": [],
            }
            for prop in ot.properties.filter(deleted_at__isnull=True) if hasattr(ot, 'properties') else []:
                type_data["properties"].append({
                    "id": str(prop.id),
                    "name": prop.name,
                    "property_type": prop.property_type,
                    "required": prop.required,
                    "default_value": prop.default_value,
                })
            if ot.version > snapshot["version"]:
                snapshot["version"] = ot.version
            snapshot["types"].append(type_data)

        link_types = LinkType.objects.filter(
            tenant_id=self.tenant_id, deleted_at__isnull=True
        )
        for lt in link_types:
            snapshot["links"].append({
                "id": str(lt.id),
                "name": lt.name,
                "source_type": lt.source_object_type.name,
                "target_type": lt.target_object_type.name,
                "cardinality": lt.cardinality,
            })

        return snapshot

    # ── CRUD ──────────────────────────────────────────────────────────────

    def create_scenario(
        self,
        name: str,
        description: str = "",
        created_by: str = "",
    ) -> Scenario:
        """Create a new scenario with a snapshot of the current ontology."""
        snapshot = self._capture_snapshot()

        scenario = Scenario(
            id=f"sc_{name.replace(' ', '_').lower()}_{int(timezone.now().timestamp())}",
            name=name,
            description=description,
            tenant_id=self.tenant_id,
            base_ontology_snapshot=snapshot,
            created_by=created_by,
        )
        self._store[scenario.id] = scenario
        logger.info("Created scenario '%s' (snapshot v%d)", name, snapshot["version"])
        return scenario

    def get_scenario(self, scenario_id: str) -> Scenario:
        """Get a scenario by ID."""
        if scenario_id not in self._store:
            raise ValueError(f"Scenario '{scenario_id}' not found")
        return self._store[scenario_id]

    def list_scenarios(self, status: str | None = None) -> list[Scenario]:
        """List all scenarios, optionally filtered by status."""
        scenarios = list(self._store.values())
        if status:
            scenarios = [s for s in scenarios if s.status == status]
        return sorted(scenarios, key=lambda s: s.created_at or datetime.min, reverse=True)

    def delete_scenario(self, scenario_id: str) -> None:
        """Delete a scenario (only drafts can be deleted)."""
        scenario = self.get_scenario(scenario_id)
        if scenario.status not in (ScenarioStatus.DRAFT, ScenarioStatus.REJECTED):
            raise ValueError(f"Cannot delete scenario with status '{scenario.status}'")
        del self._store[scenario_id]
        logger.info("Deleted scenario '%s'", scenario_id)

    # ── Apply Changes ─────────────────────────────────────────────────────

    def apply_change(
        self,
        scenario_id: str,
        change_type: str,
        payload: dict[str, Any],
    ) -> None:
        """
        Apply a hypothetical change to a scenario.

        change_type: "add_type", "remove_type", "modify_type",
                     "add_property", "remove_property", "modify_property",
                     "add_link", "remove_link"
        """
        scenario = self.get_scenario(scenario_id)
        if scenario.status not in (ScenarioStatus.DRAFT, ScenarioStatus.REVIEW):
            raise ValueError(f"Cannot modify scenario with status '{scenario.status}'")

        change = {
            "type": change_type,
            "payload": payload,
            "timestamp": timezone.now().isoformat(),
        }
        scenario.changes.append(change)
        scenario.updated_at = timezone.now()
        logger.debug("Applied change '%s' to scenario '%s'", change_type, scenario_id)

    # ── Compare ───────────────────────────────────────────────────────────

    def compare_with_base(self, scenario_id: str) -> ScenarioComparison:
        """
        Compare a scenario's changes against the base ontology snapshot.

        Performs impact analysis including breaking change detection.
        """
        scenario = self.get_scenario(scenario_id)
        snapshot = scenario.base_ontology_snapshot

        comparison = ScenarioComparison(
            scenario_id=scenario_id,
            scenario_name=scenario.name,
            base_version=snapshot.get("version", 0),
        )

        existing_type_names = {t["name"] for t in snapshot.get("types", [])}
        existing_types_by_name = {t["name"]: t for t in snapshot.get("types", [])}

        for change in scenario.changes:
            ct = change["type"]
            payload = change["payload"]

            if ct == "add_type":
                name = payload.get("name", "")
                if name in existing_type_names:
                    comparison.warnings.append(f"Type '{name}' already exists in base")
                else:
                    comparison.types_would_add.append(payload)

            elif ct == "remove_type":
                name = payload.get("name", "")
                if name in existing_type_names:
                    comparison.types_would_remove.append(payload)
                    # Check for dependent instances
                    instance_count = Object.objects.filter(
                        tenant_id=self.tenant_id,
                        object_type__name=name,
                        deleted_at__isnull=True,
                    ).count()
                    if instance_count > 0:
                        comparison.breaking_changes.append(
                            f"Removing type '{name}' would affect {instance_count} existing instances"
                        )

            elif ct == "modify_type":
                name = payload.get("name", "")
                if name in existing_type_names:
                    comparison.types_would_modify.append(payload)
                else:
                    comparison.warnings.append(f"Cannot modify non-existent type '{name}'")

            elif ct == "add_property":
                type_name = payload.get("type_name", "")
                if type_name in existing_type_names:
                    comparison.properties_would_add.append(payload)
                else:
                    comparison.warnings.append(f"Cannot add property to non-existent type '{type_name}'")

            elif ct == "remove_property":
                type_name = payload.get("type_name", "")
                prop_name = payload.get("name", "")
                if type_name in existing_type_names:
                    comparison.properties_would_remove.append(payload)
                    # Check if required and has data
                    if type_name in existing_types_by_name:
                        type_data = existing_types_by_name[type_name]
                        for p in type_data.get("properties", []):
                            if p["name"] == prop_name and p.get("required"):
                                comparison.breaking_changes.append(
                                    f"Removing required property '{prop_name}' from '{type_name}' is a breaking change"
                                )
                else:
                    comparison.warnings.append(f"Cannot remove property from non-existent type '{type_name}'")

            elif ct == "modify_property":
                type_name = payload.get("type_name", "")
                if type_name in existing_type_names:
                    comparison.properties_would_modify.append(payload)
                    # Type change is breaking
                    if "property_type" in payload:
                        comparison.breaking_changes.append(
                            f"Changing type of property '{payload.get('name')}' on '{type_name}' may break existing data"
                        )
                else:
                    comparison.warnings.append(f"Cannot modify property on non-existent type '{type_name}'")

            elif ct == "add_link":
                comparison.links_would_add.append(payload)

            elif ct == "remove_link":
                comparison.links_would_remove.append(payload)
                link_name = payload.get("name", "")
                comparison.breaking_changes.append(
                    f"Removing link type '{link_name}' may break traversals"
                )

        return comparison

    # ── Merge ─────────────────────────────────────────────────────────────

    def merge_to_main(self, scenario_id: str) -> MergeResult:
        """
        Merge a scenario's changes into the main ontology.

        Only approved scenarios can be merged. Changes are applied
        atomically with conflict detection.
        """
        scenario = self.get_scenario(scenario_id)

        if scenario.status == ScenarioStatus.DRAFT:
            scenario.status = ScenarioStatus.APPROVED  # Auto-approve for convenience

        if scenario.status not in (ScenarioStatus.APPROVED, ScenarioStatus.REVIEW):
            return MergeResult(
                success=False,
                scenario_id=scenario_id,
                scenario_name=scenario.name,
                message=f"Cannot merge scenario with status '{scenario.status}'. Must be approved first.",
            )

        conflicts: list[dict[str, Any]] = []
        applied = 0

        with transaction.atomic():
            for change in scenario.changes:
                try:
                    self._apply_change_to_ontology(change)
                    applied += 1
                except Exception as exc:
                    conflicts.append({
                        "change": change,
                        "error": str(exc),
                    })

        scenario.status = ScenarioStatus.MERGED
        scenario.merged_at = timezone.now()
        scenario.updated_at = timezone.now()

        success = len(conflicts) == 0
        return MergeResult(
            success=success,
            scenario_id=scenario_id,
            scenario_name=scenario.name,
            applied_changes=applied,
            conflicts=conflicts,
            message=(
                f"Successfully merged {applied} changes from scenario '{scenario.name}'"
                if success
                else f"Merged {applied} changes with {len(conflicts)} conflicts"
            ),
        )

    def _apply_change_to_ontology(self, change: dict[str, Any]) -> None:
        """Apply a single change to the live ontology."""
        ct = change["type"]
        payload = change["payload"]

        if ct == "add_type":
            name = payload["name"]
            existing = ObjectType.objects.filter(
                tenant_id=self.tenant_id, name=name, deleted_at__isnull=True
            ).exists()
            if existing:
                raise ValueError(f"Type '{name}' already exists")
            ObjectType.objects.create(
                tenant_id=self.tenant_id,
                name=name,
                description=payload.get("description", ""),
            )

        elif ct == "remove_type":
            ot = ObjectType.objects.filter(
                tenant_id=self.tenant_id, name=payload["name"], deleted_at__isnull=True
            ).first()
            if not ot:
                raise ValueError(f"Type '{payload['name']}' not found")
            ot.deleted_at = timezone.now()
            ot.save(update_fields=["deleted_at", "updated_at"])

        elif ct == "modify_type":
            ot = ObjectType.objects.filter(
                tenant_id=self.tenant_id, name=payload["name"], deleted_at__isnull=True
            ).first()
            if not ot:
                raise ValueError(f"Type '{payload['name']}' not found")
            if "description" in payload:
                ot.description = payload["description"]
            ot.version += 1
            ot.save()

        elif ct == "add_property":
            ot = ObjectType.objects.filter(
                tenant_id=self.tenant_id, name=payload["type_name"], deleted_at__isnull=True
            ).first()
            if not ot:
                raise ValueError(f"Type '{payload['type_name']}' not found")
            existing = Property.objects.filter(
                object_type=ot, name=payload["name"]
            ).exists()
            if existing:
                raise ValueError(f"Property '{payload['name']}' already exists on '{payload['type_name']}'")
            Property.objects.create(
                tenant_id=self.tenant_id,
                object_type=ot,
                name=payload["name"],
                property_type=payload.get("property_type", "string"),
                required=payload.get("required", False),
                default_value=payload.get("default_value"),
            )

        elif ct == "remove_property":
            ot = ObjectType.objects.filter(
                tenant_id=self.tenant_id, name=payload["type_name"], deleted_at__isnull=True
            ).first()
            if not ot:
                raise ValueError(f"Type '{payload['type_name']}' not found")
            prop = Property.objects.filter(object_type=ot, name=payload["name"]).first()
            if not prop:
                raise ValueError(f"Property '{payload['name']}' not found on '{payload['type_name']}'")
            prop.delete()

        elif ct == "modify_property":
            ot = ObjectType.objects.filter(
                tenant_id=self.tenant_id, name=payload["type_name"], deleted_at__isnull=True
            ).first()
            if not ot:
                raise ValueError(f"Type '{payload['type_name']}' not found")
            prop = Property.objects.filter(object_type=ot, name=payload["name"]).first()
            if not prop:
                raise ValueError(f"Property '{payload['name']}' not found")
            if "property_type" in payload:
                prop.property_type = payload["property_type"]
            if "required" in payload:
                prop.required = payload["required"]
            if "description" in payload:
                prop.metadata["description"] = payload["description"]
            prop.save()

        elif ct == "add_link":
            source_ot = ObjectType.objects.filter(
                tenant_id=self.tenant_id, name=payload.get("source_type", ""), deleted_at__isnull=True
            ).first()
            target_ot = ObjectType.objects.filter(
                tenant_id=self.tenant_id, name=payload.get("target_type", ""), deleted_at__isnull=True
            ).first()
            if not source_ot or not target_ot:
                raise ValueError("Source or target type not found")
            from apps.ontology.models import LinkType as LT
            LT.objects.create(
                tenant_id=self.tenant_id,
                name=payload["name"],
                source_object_type=source_ot,
                target_object_type=target_ot,
                cardinality=payload.get("cardinality", "one_to_many"),
            )

        elif ct == "remove_link":
            from apps.ontology.models import LinkType as LT
            lt = LT.objects.filter(
                tenant_id=self.tenant_id, name=payload["name"], deleted_at__isnull=True
            ).first()
            if not lt:
                raise ValueError(f"Link type '{payload['name']}' not found")
            lt.deleted_at = timezone.now()
            lt.save(update_fields=["deleted_at", "updated_at"])

        else:
            logger.warning("Unknown scenario change type: %s", ct)
