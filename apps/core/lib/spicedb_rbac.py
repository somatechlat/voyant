"""SpiceDB RBAC client with realm-aware operations."""

from __future__ import annotations

import logging

from authzed.api.v1 import (  # type: ignore[reportMissingImports]
    CheckPermissionRequest,
    CheckPermissionResponse,
    Consistency,
    DeleteRelationshipsRequest,
    ObjectReference,
    Relationship,
    RelationshipFilter,
    RelationshipUpdate,
    SubjectFilter,
    SubjectReference,
    WriteRelationshipsRequest,
)

from apps.core.config import get_settings
from apps.core.security.policy import spicedb

logger = logging.getLogger(__name__)


class SpiceRBAC:
    """
    High-level RBAC interface over SpiceDB (Authzed).

    Provides realm-aware permission checks, tenant membership verification,
    and relationship mutation operations. All SpiceDB calls use the
    preshared key configured in ``voyant.core.config``.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self.endpoint = settings.spicedb_endpoint
        self.token = settings.spicedb_grpc_preshared_key
        if not self.token:
            logger.warning("VOYANT_SPICEDB_GRPC_PRESHARED_KEY is not set")

    def _metadata(self) -> list[tuple[str, str]]:
        """Return gRPC metadata bearing the Bearer token."""
        return [("authorization", f"Bearer {self.token}")] if self.token else []

    def check_permission(
        self,
        resource_type: str,
        resource_id: str,
        permission: str,
        subject_type: str,
        subject_id: str,
        subject_relation: str | None = None,
    ) -> bool:
        """
        Check whether *subject* has *permission* on *resource*.

        Args:
            resource_type: SpiceDB object type for the resource.
            resource_id: SpiceDB object ID for the resource.
            permission: The permission to check (e.g., ``"view"``).
            subject_type: SpiceDB object type for the subject (usually ``"user"``).
            subject_id: SpiceDB object ID for the subject.
            subject_relation: Optional relation on the subject reference.

        Returns:
            True if the permission is granted, False otherwise.
        """
        subject_ref = SubjectReference(
            object=ObjectReference(
                object_type=subject_type,
                object_id=subject_id,
            ),
            optional_relation=subject_relation or "",
        )
        try:
            resp = spicedb.permissions_service.CheckPermission(
                CheckPermissionRequest(
                    resource=ObjectReference(
                        object_type=resource_type,
                        object_id=resource_id,
                    ),
                    permission=permission,
                    subject=subject_ref,
                    consistency=Consistency(fully_consistent=True),
                ),
                metadata=self._metadata(),
            )
            return (
                resp.permissionship
                == CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION
            )
        except Exception as exc:
            logger.error("SpiceDB check_permission failed: %s", exc)
            return False

    def ensure_tenant_access(
        self,
        user_id: str,
        tenant_id: str,
        required_permission: str = "view",
    ) -> bool:
        """
        Verify that *user_id* has *required_permission* on the tenant.

        This is the canonical gate used by API endpoints before returning
        tenant-scoped data.

        Args:
            user_id: The user's unique identifier.
            tenant_id: The tenant to check access against.
            required_permission: The tenant permission required (default ``"view"``).

        Returns:
            True if access is granted, False otherwise.
        """
        return self.check_permission(
            resource_type="tenant",
            resource_id=tenant_id,
            permission=required_permission,
            subject_type="user",
            subject_id=user_id,
        )

    def add_relationship(
        self,
        resource_type: str,
        resource_id: str,
        relation: str,
        subject_type: str,
        subject_id: str,
        subject_relation: str | None = None,
    ) -> bool:
        """
        Idempotently write a relationship tuple to SpiceDB.

        Args:
            resource_type: SpiceDB object type for the resource.
            resource_id: SpiceDB object ID for the resource.
            relation: The relation name (e.g., ``"viewer"``).
            subject_type: SpiceDB object type for the subject.
            subject_id: SpiceDB object ID for the subject.
            subject_relation: Optional relation on the subject reference.

        Returns:
            True if the write succeeded, False otherwise.
        """
        rel = Relationship(
            resource=ObjectReference(
                object_type=resource_type,
                object_id=resource_id,
            ),
            relation=relation,
            subject=SubjectReference(
                object=ObjectReference(
                    object_type=subject_type,
                    object_id=subject_id,
                ),
                optional_relation=subject_relation or "",
            ),
        )
        try:
            spicedb.permissions_service.WriteRelationships(
                WriteRelationshipsRequest(
                    updates=[
                        RelationshipUpdate(
                            operation=RelationshipUpdate.Operation.OPERATION_TOUCH,
                            relationship=rel,
                        )
                    ]
                ),
                metadata=self._metadata(),
            )
            return True
        except Exception as exc:
            logger.error("SpiceDB add_relationship failed: %s", exc)
            return False

    def remove_relationship(
        self,
        resource_type: str,
        resource_id: str,
        relation: str,
        subject_type: str,
        subject_id: str,
        subject_relation: str | None = None,
    ) -> bool:
        """
        Delete a relationship tuple from SpiceDB.

        Args:
            resource_type: SpiceDB object type for the resource.
            resource_id: SpiceDB object ID for the resource.
            relation: The relation name.
            subject_type: SpiceDB object type for the subject.
            subject_id: SpiceDB object ID for the subject.
            subject_relation: Optional relation on the subject reference.

        Returns:
            True if the delete succeeded, False otherwise.
        """
        try:
            spicedb.permissions_service.DeleteRelationships(
                DeleteRelationshipsRequest(
                    relationship_filter=RelationshipFilter(
                        resource_type=resource_type,
                        optional_resource_id=resource_id,
                        optional_relation=relation,
                        optional_subject_filter=SubjectFilter(
                            subject_type=subject_type,
                            optional_subject_id=subject_id,
                            optional_relation=(
                                SubjectFilter.RelationFilter(relation=subject_relation)
                                if subject_relation
                                else None
                            ),
                        ),
                    )
                ),
                metadata=self._metadata(),
            )
            return True
        except Exception as exc:
            logger.error("SpiceDB remove_relationship failed: %s", exc)
            return False
