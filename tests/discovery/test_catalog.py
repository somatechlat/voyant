"""
Unit tests for apps.discovery.lib.catalog — DiscoveryRepo and ServiceDef.

Tests registration, retrieval, listing, searching, clearing, and the
ServiceDef dataclass including its to_dict method.
Pure in-memory logic — no DB, no external services.
"""

import time

import pytest

from apps.discovery.lib.catalog import DiscoveryRepo, ServiceDef, get_discovery_repo
from apps.discovery.lib.models import ApiEndpoint


# =========================================================================
# ServiceDef
# =========================================================================


class TestServiceDef:
    def test_defaults(self):
        svc = ServiceDef(name="Test", base_url="https://example.com")
        assert svc.name == "Test"
        assert svc.base_url == "https://example.com"
        assert svc.version == "1.0.0"
        assert svc.description == ""
        assert svc.auth_type == "none"
        assert svc.spec_url is None
        assert svc.owner == "unknown"
        assert svc.tags == []
        assert svc.endpoints == []
        assert svc.metadata == {}
        assert isinstance(svc.first_seen, float)
        assert isinstance(svc.last_seen, float)

    def test_to_dict_basic(self):
        svc = ServiceDef(name="Svc", base_url="https://svc.io")
        d = svc.to_dict()
        assert d["name"] == "Svc"
        assert d["base_url"] == "https://svc.io"
        assert d["version"] == "1.0.0"
        assert d["description"] == ""
        assert d["auth_type"] == "none"
        assert d["endpoints"] == []
        assert d["metadata"] == {}
        assert "first_seen" in d
        assert "last_seen" in d
        # Timestamps should be ISO strings
        assert "T" in d["first_seen"]

    def test_to_dict_with_endpoints(self):
        ep = ApiEndpoint(path="/users", method="GET", summary="List users")
        svc = ServiceDef(
            name="API",
            base_url="https://api.io",
            endpoints=[ep],
        )
        d = svc.to_dict()
        assert len(d["endpoints"]) == 1
        assert d["endpoints"][0]["path"] == "/users"
        assert d["endpoints"][0]["method"] == "GET"

    def test_to_dict_with_metadata(self):
        svc = ServiceDef(
            name="X",
            base_url="https://x.io",
            metadata={"region": "us-east-1", "tier": "premium"},
        )
        d = svc.to_dict()
        assert d["metadata"]["region"] == "us-east-1"

    def test_custom_fields(self):
        svc = ServiceDef(
            name="Auth",
            base_url="https://auth.io",
            version="2.0.0",
            description="Auth service",
            auth_type="OAuth2",
            spec_url="https://auth.io/spec.json",
            owner="team-security",
            tags=["auth", "oauth"],
        )
        assert svc.version == "2.0.0"
        assert svc.auth_type == "OAuth2"
        assert svc.owner == "team-security"
        assert svc.tags == ["auth", "oauth"]


# =========================================================================
# DiscoveryRepo
# =========================================================================


class TestDiscoveryRepo:
    @pytest.fixture
    def repo(self):
        return DiscoveryRepo()

    def test_register_and_get(self, repo):
        svc = ServiceDef(name="Payments", base_url="https://pay.io")
        repo.register(svc)
        found = repo.get("Payments")
        assert found is not None
        assert found.name == "Payments"
        assert found.base_url == "https://pay.io"

    def test_get_nonexistent(self, repo):
        assert repo.get("NoSuch") is None

    def test_register_update_existing(self, repo):
        svc1 = ServiceDef(name="X", base_url="https://v1.io", metadata={"a": "1"})
        repo.register(svc1)
        old_first_seen = svc1.first_seen

        svc2 = ServiceDef(name="X", base_url="https://v2.io", metadata={"b": "2"})
        repo.register(svc2)

        found = repo.get("X")
        assert found.base_url == "https://v2.io"
        assert found.metadata == {"a": "1", "b": "2"}  # merged
        assert found.last_seen >= old_first_seen

    def test_register_empty_name_raises(self, repo):
        svc = ServiceDef(name="", base_url="https://x.io")
        with pytest.raises(ValueError, match="Service name is required"):
            repo.register(svc)

    def test_list_services(self, repo):
        repo.register(ServiceDef(name="A", base_url="https://a.io"))
        repo.register(ServiceDef(name="B", base_url="https://b.io"))
        services = repo.list_services()
        assert len(services) == 2
        names = {s.name for s in services}
        assert names == {"A", "B"}

    def test_list_empty(self, repo):
        assert repo.list_services() == []

    def test_search_by_name(self, repo):
        repo.register(ServiceDef(name="Payments API", base_url="https://pay.io"))
        repo.register(ServiceDef(name="Inventory", base_url="https://inv.io"))
        results = repo.search("payment")
        assert len(results) == 1
        assert results[0].name == "Payments API"

    def test_search_by_description(self, repo):
        repo.register(ServiceDef(
            name="Auth", base_url="https://auth.io", description="OAuth2 provider"
        ))
        repo.register(ServiceDef(name="Other", base_url="https://other.io"))
        results = repo.search("oauth2")
        assert len(results) == 1
        assert results[0].name == "Auth"

    def test_search_case_insensitive(self, repo):
        repo.register(ServiceDef(name="MyService", base_url="https://m.io"))
        results = repo.search("myservice")
        assert len(results) == 1

    def test_search_no_match(self, repo):
        repo.register(ServiceDef(name="A", base_url="https://a.io"))
        results = repo.search("nonexistent")
        assert results == []

    def test_clear(self, repo):
        repo.register(ServiceDef(name="A", base_url="https://a.io"))
        repo.register(ServiceDef(name="B", base_url="https://b.io"))
        assert len(repo.list_services()) == 2
        repo.clear()
        assert repo.list_services() == []

    def test_register_with_endpoints(self, repo):
        ep1 = ApiEndpoint(path="/users", method="GET", summary="List")
        ep2 = ApiEndpoint(path="/users", method="POST", summary="Create")
        svc = ServiceDef(
            name="Users",
            base_url="https://users.io",
            endpoints=[ep1, ep2],
        )
        repo.register(svc)
        found = repo.get("Users")
        assert len(found.endpoints) == 2

    def test_update_preserves_first_seen(self, repo):
        svc1 = ServiceDef(name="X", base_url="https://v1.io")
        repo.register(svc1)
        first = svc1.first_seen

        time.sleep(0.01)
        svc2 = ServiceDef(name="X", base_url="https://v2.io")
        repo.register(svc2)

        found = repo.get("X")
        assert found.first_seen == first
        assert found.last_seen > first


# =========================================================================
# get_discovery_repo singleton
# =========================================================================


class TestGetDiscoveryRepo:
    def test_returns_same_instance(self):
        # Reset global singleton for test isolation
        import apps.discovery.lib.catalog as mod
        original = mod._repo
        mod._repo = None
        try:
            r1 = get_discovery_repo()
            r2 = get_discovery_repo()
            assert r1 is r2
            assert isinstance(r1, DiscoveryRepo)
        finally:
            mod._repo = original

    def test_returns_discovery_repo_type(self):
        import apps.discovery.lib.catalog as mod
        original = mod._repo
        mod._repo = None
        try:
            r = get_discovery_repo()
            assert isinstance(r, DiscoveryRepo)
        finally:
            mod._repo = original
