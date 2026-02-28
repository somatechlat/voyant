import logging

from authzed.api.v1 import (
    CheckPermissionRequest,
    CheckPermissionResponse,
    Client,
    Consistency,
    ObjectReference,
    SubjectReference,
)
from grpc import insecure_channel

from apps.core.config import get_settings

logger = logging.getLogger(__name__)


class SpiceDBClient:
    """
    Client for Authzed SpiceDB.

    Handles permission checks against the SpiceDB service.
    """

    def __init__(self):
        get_settings()
        # Defaults for local dev if not in settings yet
        self.endpoint = "voyant_spicedb:50051"
        self.token = "somerandomkey"
        self._client = None

    @property
    def client(self) -> Client:
        if not self._client:
            self._client = Client(
                self.endpoint,
                insecure_channel(self.endpoint),  # Use secure_channel in prod
                self.token,
            )
        return self._client

    def check_permission(
        self,
        resource_type: str,
        resource_id: str,
        permission: str,
        subject_type: str,
        subject_id: str,
    ) -> bool:
        """
        Check if subject has permission on resource.

        Args:
            resource_type: e.g., "resource"
            resource_id: e.g., "doc:123"
            permission: e.g., "view"
            subject_type: e.g., "user"
            subject_id: e.g., "user:456"
        """
        try:
            resp = self.client.permissions_service.CheckPermission(
                CheckPermissionRequest(
                    resource=ObjectReference(
                        object_type=resource_type,
                        object_id=resource_id,
                    ),
                    permission=permission,
                    subject=SubjectReference(
                        object=ObjectReference(
                            object_type=subject_type,
                            object_id=subject_id,
                        )
                    ),
                    consistency=Consistency(fully_consistent=True),
                )
            )
            return (
                resp.permissionship
                == CheckPermissionResponse.PERMISSIONSHIP_HAS_PERMISSION
            )
        except Exception as e:
            logger.error(f"SpiceDB check failed: {e}")
            return False


# Singleton
spicedb = SpiceDBClient()
