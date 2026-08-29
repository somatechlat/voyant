"""
Capsule Core Service.

The 4 core operations:
1. verify_capsule  — Check integrity (SHA-256 content hash verification)
2. certify_capsule — Sign and activate
3. inject_capsule  — Load verified capsule for runtime
4. edit_capsule    — Clone-on-edit for active capsules
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Optional
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.capsules.models import Capsule, CapsuleInstance, Constitution

logger = logging.getLogger(__name__)


def verify_capsule(capsule: Capsule) -> bool:
    """
    Verify capsule integrity.

    Returns True if the capsule passes structural and signature validation.
    Verification checks SHA-256 content hash against the registry_signature.
    """
    if not capsule.name or not capsule.version:
        logger.warning("Capsule %s missing name or version", capsule.id)
        return False

    # Validate execution_graph is a list
    if not isinstance(capsule.execution_graph, list):
        logger.warning("Capsule %s has invalid execution_graph", capsule.id)
        return False

    # Validate parameters_schema is a dict
    if not isinstance(capsule.parameters_schema, dict):
        logger.warning("Capsule %s has invalid parameters_schema", capsule.id)
        return False

    # Verify registry signature against SHA-256 content hash
    if capsule.registry_signature:
        content = json.dumps(capsule.body, sort_keys=True, default=str)
        expected = f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"
        if capsule.registry_signature != expected:
            logger.warning(
                "Capsule %s signature mismatch: expected %s, got %s",
                capsule.id,
                expected,
                capsule.registry_signature,
            )
            return False

    logger.info("Capsule %s:%s verified", capsule.name, capsule.version)
    return True


def certify_capsule(capsule: Capsule, constitution: Optional[Constitution] = None) -> Capsule:
    """
    Sign capsule and bind to active Constitution.

    Precondition: capsule.status == 'draft'
    Postcondition: capsule.status == 'certified' and signature is set
    """
    if capsule.status != Capsule.STATUS_DRAFT:
        raise ValueError(f"Only drafts can be certified. Current status: {capsule.status}")

    with transaction.atomic():
        # Bind to constitution
        if constitution is None:
            constitution = Constitution.objects.filter(
                realm=capsule.realm, tenant_id=capsule.tenant_id, is_active=True
            ).first()

        if constitution:
            capsule.constitution = constitution
            capsule.constitution_ref = {
                "checksum": constitution.content_hash,
                "url": "local",
            }
        else:
            logger.warning("No active constitution found for capsule %s", capsule.id)
            capsule.constitution_ref = {}

        # Compute SHA-256 content hash as the signature
        content = json.dumps(capsule.body, sort_keys=True, default=str)
        capsule.registry_signature = f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"
        capsule.certified_at = timezone.now()
        capsule.status = Capsule.STATUS_CERTIFIED
        capsule.save()

    logger.info("Capsule %s:%s certified", capsule.name, capsule.version)
    return capsule


def activate_capsule(capsule: Capsule) -> Capsule:
    """Promote a certified capsule to active."""
    if capsule.status != Capsule.STATUS_CERTIFIED:
        raise ValueError(f"Only certified capsules can be activated. Status: {capsule.status}")

    capsule.status = Capsule.STATUS_ACTIVE
    capsule.is_active = True
    capsule.save()
    logger.info("Capsule %s:%s activated", capsule.name, capsule.version)
    return capsule


def inject_capsule(capsule_id: UUID) -> Capsule:
    """
    Load and verify an active capsule for runtime.

    Invariant: inject(c) implies verify(c) is True.
    """
    try:
        capsule = Capsule.objects.get(
            id=capsule_id, status=Capsule.STATUS_ACTIVE, is_active=True
        )
    except Capsule.DoesNotExist:
        raise ValueError(f"Active capsule {capsule_id} not found")

    if not verify_capsule(capsule):
        raise RuntimeError(f"Capsule {capsule.name} failed integrity verification")

    logger.info("Capsule %s:%s injected for runtime", capsule.name, capsule.version)
    return capsule


def edit_capsule(capsule: Capsule, updates: dict) -> Capsule:
    """
    Active capsules spawn a new version; drafts update in place.

    Invariant: edit(v1) -> spawn(v2, parent=v1) if v1.status == 'active'
    """
    with transaction.atomic():
        if capsule.status == Capsule.STATUS_DRAFT:
            _apply_updates(capsule, updates)
            capsule.save()
            logger.info("Updated draft capsule %s:%s", capsule.name, capsule.version)
            return capsule

        if capsule.status in (Capsule.STATUS_ACTIVE, Capsule.STATUS_CERTIFIED):
            new_version = _increment_version(capsule.version)
            new_capsule = Capsule.objects.create(
                name=capsule.name,
                version=new_version,
                tenant_id=capsule.tenant_id,
                realm=capsule.realm,
                description=updates.get("description", capsule.description),
                parent=capsule,
                status=Capsule.STATUS_DRAFT,
                system_prompt=updates.get("system_prompt", capsule.system_prompt),
                personality_traits=updates.get("personality_traits", capsule.personality_traits),
                neuromodulator_baseline=updates.get(
                    "neuromodulator_baseline", capsule.neuromodulator_baseline
                ),
                capsule_type=updates.get("capsule_type", capsule.capsule_type),
                execution_graph=updates.get("execution_graph", capsule.execution_graph),
                parameters_schema=updates.get("parameters_schema", capsule.parameters_schema),
                output_formats=updates.get("output_formats", capsule.output_formats),
                rbac_rules=updates.get("rbac_rules", capsule.rbac_rules),
                capabilities_whitelist=updates.get(
                    "capabilities_whitelist", capsule.capabilities_whitelist
                ),
                resource_limits=updates.get("resource_limits", capsule.resource_limits),
            )
            # Copy M2M capabilities
            new_capsule.capabilities.set(capsule.capabilities.all())
            logger.info(
                "Created new version %s:%s from %s",
                new_capsule.name,
                new_version,
                capsule.version,
            )
            return new_capsule

        raise ValueError(f"Cannot edit capsule with status: {capsule.status}")


def archive_capsule(capsule: Capsule) -> Capsule:
    """Archive a capsule (soft delete)."""
    if capsule.status == Capsule.STATUS_ARCHIVED:
        return capsule

    capsule.status = Capsule.STATUS_ARCHIVED
    capsule.is_active = False
    capsule.save()
    logger.info("Capsule %s:%s archived", capsule.name, capsule.version)
    return capsule


def suspend_capsule(capsule: Capsule, reason: str = "") -> Capsule:
    """Suspend a capsule for security or policy reasons."""
    if capsule.status == Capsule.STATUS_SUSPENDED:
        return capsule

    capsule.status = Capsule.STATUS_SUSPENDED
    capsule.is_active = False
    capsule.save()
    logger.info("Capsule %s:%s suspended. Reason: %s", capsule.name, capsule.version, reason)
    return capsule


def create_capsule_instance(
    capsule: Capsule,
    session_id: str,
    parameter_values: dict,
    triggered_by: str = "mcp",
) -> CapsuleInstance:
    """Create a new running instance of a Capsule."""
    if capsule.status != Capsule.STATUS_ACTIVE:
        raise ValueError(f"Cannot instantiate non-active capsule: {capsule.status}")

    instance = CapsuleInstance.objects.create(
        capsule=capsule,
        tenant_id=capsule.tenant_id,
        realm=capsule.realm,
        session_id=session_id,
        state={},
        status=CapsuleInstance.STATUS_RUNNING,
        triggered_by=triggered_by,
        parameter_values=parameter_values,
    )
    capsule.execution_count += 1
    capsule.save(update_fields=["execution_count"])

    # Structured audit log — never log actual parameter values (may contain PII)
    logger.info(
        "AUDIT capsule_executed tenant=%s realm=%s capsule=%s instance=%s "
        "triggered_by=%s param_keys=%s",
        capsule.tenant_id,
        capsule.realm,
        f"{capsule.name}:{capsule.version}",
        instance.id,
        triggered_by,
        list(parameter_values.keys()),
    )
    return instance


def _apply_updates(capsule: Capsule, updates: dict) -> None:
    """Apply dict updates to a capsule instance."""
    allowed_fields = {
        "description",
        "system_prompt",
        "personality_traits",
        "neuromodulator_baseline",
        "capsule_type",
        "execution_graph",
        "parameters_schema",
        "output_formats",
        "rbac_rules",
        "capabilities_whitelist",
        "resource_limits",
    }
    for key, value in updates.items():
        if key in allowed_fields and hasattr(capsule, key):
            setattr(capsule, key, value)


def _increment_version(version: str) -> str:
    """Increment patch version: 1.0.0 -> 1.0.1."""
    try:
        parts = version.split(".")
        if len(parts) == 3:
            major, minor, patch = parts
            return f"{major}.{minor}.{int(patch) + 1}"
    except (ValueError, TypeError) as exc:
        logger.warning("Failed to parse version '%s': %s", version, exc)
    return f"{version}.1"
