"""
Unit tests for SpiceRBAC wrapper.

These tests exercise real code paths against the real SpiceDB client singleton.
When SpiceDB is unavailable (as in CI/local test runs without containers),
the production-grade error handling returns False. No mocks.
"""


from apps.core.lib.spicedb_rbac import SpiceRBAC


class TestSpiceRBAC:
    """Tests for the high-level RBAC interface — real client, real failure paths."""

    def test_reads_settings(self):
        rbac = SpiceRBAC()
        assert rbac.endpoint is not None
        assert rbac.token is not None

    def test_metadata_returns_bearer_tuple_when_token_set(self):
        rbac = SpiceRBAC()
        meta = rbac._metadata()
        assert len(meta) == 1
        assert meta[0][0] == "authorization"
        assert meta[0][1].startswith("Bearer ")

    def test_metadata_returns_empty_list_when_token_missing(self):
        # Temporarily blank the token so we can test the empty-metadata path.
        rbac = SpiceRBAC()
        original_token = rbac.token
        try:
            rbac.token = ""
            meta = rbac._metadata()
            assert meta == []
        finally:
            rbac.token = original_token

    def test_check_permission_returns_false_when_spicedb_unreachable(self):
        """Real SpiceDB is down → graceful degradation returns False."""
        rbac = SpiceRBAC()
        result = rbac.check_permission(
            resource_type="source",
            resource_id="src-1",
            permission="view",
            subject_type="user",
            subject_id="u-1",
        )
        assert result is False

    def test_ensure_tenant_access_returns_false_when_spicedb_unreachable(self):
        """Real SpiceDB is down → graceful degradation returns False."""
        rbac = SpiceRBAC()
        result = rbac.ensure_tenant_access("u-1", "t-1")
        assert result is False

    def test_add_relationship_returns_false_when_spicedb_unreachable(self):
        """Real SpiceDB is down → graceful degradation returns False."""
        rbac = SpiceRBAC()
        result = rbac.add_relationship(
            resource_type="source",
            resource_id="src-1",
            relation="viewer",
            subject_type="user",
            subject_id="u-1",
        )
        assert result is False

    def test_remove_relationship_returns_false_when_spicedb_unreachable(self):
        """Real SpiceDB is down → graceful degradation returns False."""
        rbac = SpiceRBAC()
        result = rbac.remove_relationship(
            resource_type="source",
            resource_id="src-1",
            relation="viewer",
            subject_type="user",
            subject_id="u-1",
        )
        assert result is False
