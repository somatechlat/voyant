import pytest
from authzed.api.v1 import (
    ObjectReference,
    Relationship,
    RelationshipUpdate,
    SubjectReference,
    WriteRelationshipsRequest,
    WriteSchemaRequest,
)

from apps.core.security.policy import SpiceDBClient


@pytest.fixture(scope="module")
def spicedb_setup():
    # settings are already overridden in conftest.py
    v_client = SpiceDBClient()

    # Write test schema
    schema = """
    definition user {}
    definition document {
        relation viewer: user
        permission view = viewer
    }
    """
    # Use the internal stub which is already configured
    metadata = [("authorization", f"Bearer {v_client.token}")] if v_client.token else []
    v_client.schema_service.WriteSchema(
        WriteSchemaRequest(schema=schema), metadata=metadata
    )
    return v_client


class TestSpiceDBPolicyIntegration:
    def test_real_permission_check(self, spicedb_setup):
        voyant_client = spicedb_setup

        # Write relationship: user1 is viewer of doc1
        metadata = (
            [("authorization", f"Bearer {voyant_client.token}")]
            if voyant_client.token
            else []
        )
        voyant_client.permissions_service.WriteRelationships(
            WriteRelationshipsRequest(
                updates=[
                    RelationshipUpdate(
                        operation=RelationshipUpdate.Operation.OPERATION_TOUCH,
                        relationship=Relationship(
                            resource=ObjectReference(
                                object_type="document", object_id="doc1"
                            ),
                            relation="viewer",
                            subject=SubjectReference(
                                object=ObjectReference(
                                    object_type="user", object_id="user1"
                                )
                            ),
                        ),
                    )
                ]
            ),
            metadata=metadata,
        )

        # Check permission for user1 -> Should be True
        assert (
            voyant_client.check_permission(
                resource_type="document",
                resource_id="doc1",
                permission="view",
                subject_type="user",
                subject_id="user1",
            )
            is True
        )

        # Check permission for user2 -> Should be False
        assert (
            voyant_client.check_permission(
                resource_type="document",
                resource_id="doc1",
                permission="view",
                subject_type="user",
                subject_id="user2",
            )
            is False
        )
