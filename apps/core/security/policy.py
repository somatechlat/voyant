import logging

from authzed.api.v1 import (  # type: ignore[reportMissingImports]
    CheckPermissionRequest,
    CheckPermissionResponse,
    Consistency,
    ObjectReference,
    SubjectReference,
)

from apps.core.config import get_settings

logger = logging.getLogger(__name__)


class SpiceDBClient:
    """
    Client for Authzed SpiceDB.

    Handles permission checks against the SpiceDB service.
    All credentials are loaded from get_settings(), which enforces
    Vault in non-local environments.
    """

    def __init__(self):
        settings = get_settings()
        self.endpoint = settings.spicedb_endpoint
        self.token = settings.spicedb_grpc_preshared_key
        self._tls_enabled = settings.spicedb_tls
        if not self.token:
            logger.warning("VOYANT_SPICEDB_GRPC_PRESHARED_KEY is not set")
        self._channel = None
        self._permissions_service = None
        self._schema_service = None

    @property
    def channel(self):
        if not self._channel:
            import grpc

            if self._tls_enabled:
                from grpc import ssl_channel_credentials

                self._channel = grpc.secure_channel(
                    self.endpoint, ssl_channel_credentials()
                )
            else:
                self._channel = grpc.insecure_channel(self.endpoint)
        return self._channel

    @property
    def permissions_service(self):
        if not self._permissions_service:
            from authzed.api.v1 import PermissionsServiceStub  # type: ignore[reportMissingImports]

            self._permissions_service = PermissionsServiceStub(self.channel)
        return self._permissions_service

    @property
    def schema_service(self):
        if not self._schema_service:
            from authzed.api.v1 import SchemaServiceStub  # type: ignore[reportMissingImports]

            self._schema_service = SchemaServiceStub(self.channel)
        return self._schema_service

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
        """
        # Preshared key is sent via gRPC metadata
        metadata = [("authorization", f"Bearer {self.token}")] if self.token else []
        try:
            resp = self.permissions_service.CheckPermission(
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
                ),
                metadata=metadata,
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
