"""Tests for governance API endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.governance.api import (
    GovernanceSearchResult,
    LineageEdge,
    LineageNode,
    LineageResponse,
    QuotaTierInfo,
    QuotaUsageStatus,
    SchemaField,
    SchemaResponse,
    SearchResponse,
    SetTierRequest,
    _policy_limit,
    _quota_usage_for_tenant,
)


class TestSchemaClasses:
    """Test API schema classes."""

    def test_governance_search_result(self):
        result = GovernanceSearchResult(
            urn="urn:li:dataset:orders",
            name="orders",
            type="DATASET",
            description="Orders dataset",
            platform="postgres",
            tags=["production", "finance"],
        )
        assert result.urn == "urn:li:dataset:orders"
        assert result.name == "orders"
        assert result.tags == ["production", "finance"]

    def test_governance_search_result_defaults(self):
        result = GovernanceSearchResult(
            urn="test",
            name="test",
            type="DATASET",
        )
        assert result.description is None
        assert result.platform is None
        assert result.tags == []

    def test_search_response(self):
        response = SearchResponse(
            results=[
                GovernanceSearchResult(
                    urn="urn:1",
                    name="dataset1",
                    type="DATASET",
                )
            ],
            total=1,
        )
        assert len(response.results) == 1
        assert response.total == 1

    def test_lineage_node(self):
        node = LineageNode(
            urn="urn:li:dataset:orders",
            name="orders",
            type="dataset",
            platform="postgres",
        )
        assert node.urn == "urn:li:dataset:orders"
        assert node.platform == "postgres"

    def test_lineage_node_defaults(self):
        node = LineageNode(urn="test", name="test", type="dataset")
        assert node.platform is None

    def test_lineage_edge(self):
        edge = LineageEdge(
            source="urn:source",
            target="urn:target",
            type="PRODUCES",
        )
        assert edge.source == "urn:source"
        assert edge.target == "urn:target"

    def test_lineage_response(self):
        response = LineageResponse(
            nodes=[
                LineageNode(urn="a", name="a", type="dataset"),
                LineageNode(urn="b", name="b", type="dataset"),
            ],
            edges=[
                LineageEdge(source="a", target="b", type="DERIVES_FROM"),
            ],
        )
        assert len(response.nodes) == 2
        assert len(response.edges) == 1

    def test_schema_field(self):
        field = SchemaField(
            name="id",
            type="INTEGER",
            nullable=False,
            description="Primary key",
        )
        assert field.name == "id"
        assert field.nullable is False

    def test_schema_field_defaults(self):
        field = SchemaField(name="col", type="VARCHAR")
        assert field.nullable is True
        assert field.description is None

    def test_schema_response(self):
        response = SchemaResponse(
            urn="urn:li:dataset:orders",
            fields=[
                SchemaField(name="id", type="INTEGER"),
                SchemaField(name="name", type="VARCHAR"),
            ],
        )
        assert len(response.fields) == 2

    def test_quota_tier_info(self):
        tier = QuotaTierInfo(
            tier_id="free",
            name="Free Tier",
            max_jobs_per_day=10,
            max_artifacts_gb=1.0,
            max_sources=5,
            max_concurrent_jobs=2,
        )
        assert tier.tier_id == "free"
        assert tier.max_jobs_per_day == 10

    def test_quota_usage_status(self):
        status = QuotaUsageStatus(
            tenant_id="tenant_1",
            tier="free",
            jobs_today=5,
            jobs_limit=10,
            jobs_remaining=5,
            artifacts_gb=0.5,
            artifacts_limit_gb=1.0,
            sources_count=2,
            sources_limit=5,
            concurrent_jobs=1,
            concurrent_limit=2,
        )
        assert status.tenant_id == "tenant_1"
        assert status.jobs_remaining == 5

    def test_set_tier_request(self):
        request = SetTierRequest(tier="enterprise")
        assert request.tier == "enterprise"


class TestPolicyLimit:
    """Test _policy_limit helper function."""

    def test_policy_limit_with_limit(self):
        policy = MagicMock()
        policy.get_limit.return_value = MagicMock(limit=100)
        result = _policy_limit(policy, MagicMock())
        assert result == 100.0

    def test_policy_limit_without_limit(self):
        policy = MagicMock()
        policy.get_limit.return_value = None
        result = _policy_limit(policy, MagicMock())
        assert result == 0.0


class TestQuotaUsageForTenant:
    """Test _quota_usage_for_tenant helper function."""

    @patch("apps.governance.api.get_usage_stats")
    @patch("apps.governance.api.get_quota_manager")
    def test_quota_usage_basic(self, mock_get_manager, mock_get_usage):

        mock_manager = MagicMock()
        mock_manager.get_tenant_tier.return_value = MagicMock(value="free")
        mock_policy = MagicMock()

        def get_limit_side_effect(resource):
            return None

        mock_policy.get_limit = get_limit_side_effect
        mock_manager.get_policy.return_value = mock_policy
        mock_get_manager.return_value = mock_manager

        mock_get_usage.return_value = []

        result = _quota_usage_for_tenant("tenant_1")
        assert result.tenant_id == "tenant_1"
        assert result.tier == "free"
        assert result.jobs_today == 0
        assert result.jobs_limit == 0

    @patch("apps.governance.api.get_usage_stats")
    @patch("apps.governance.api.get_quota_manager")
    def test_quota_usage_with_usage(self, mock_get_manager, mock_get_usage):
        from apps.core.lib.tenant_quotas import ResourceType

        mock_manager = MagicMock()
        mock_manager.get_tenant_tier.return_value = MagicMock(value="pro")
        mock_policy = MagicMock()

        def get_limit_side_effect(resource):
            limits = {
                ResourceType.JOBS_PER_DAY: MagicMock(limit=100),
                ResourceType.TOTAL_STORAGE_MB: MagicMock(limit=10240),
                ResourceType.WORKFLOWS_PER_DAY: MagicMock(limit=50),
                ResourceType.JOBS_CONCURRENT: MagicMock(limit=10),
            }
            return limits.get(resource)

        mock_policy.get_limit = get_limit_side_effect
        mock_manager.get_policy.return_value = mock_policy
        mock_get_manager.return_value = mock_manager

        mock_usage = MagicMock()
        mock_usage.resource = ResourceType.JOBS_PER_DAY
        mock_usage.current_usage = 25
        mock_get_usage.return_value = [mock_usage]

        result = _quota_usage_for_tenant("tenant_1")
        assert result.jobs_today == 25
        assert result.jobs_limit == 100
        assert result.jobs_remaining == 75


class TestSearchMetadataEndpoint:
    """Test search_metadata endpoint (mocked)."""

    @pytest.mark.asyncio
    @patch("apps.governance.api._datahub_graphql")
    async def test_search_metadata_success(self, mock_graphql):
        from apps.governance.api import search_metadata

        mock_graphql.return_value = {
            "search": {
                "total": 1,
                "searchResults": [
                    {
                        "entity": {
                            "urn": "urn:li:dataset:orders",
                            "name": "orders",
                            "type": "DATASET",
                            "description": "Orders dataset",
                            "platform": {"name": "postgres"},
                            "tags": {"tags": [{"tag": {"name": "production"}}]},
                        }
                    }
                ],
            }
        }

        request = MagicMock()
        response = await search_metadata(request, query="orders")

        assert response.total == 1
        assert len(response.results) == 1
        assert response.results[0].urn == "urn:li:dataset:orders"
        assert response.results[0].tags == ["production"]

    @pytest.mark.asyncio
    @patch("apps.governance.api._datahub_graphql")
    async def test_search_metadata_empty_results(self, mock_graphql):
        from apps.governance.api import search_metadata

        mock_graphql.return_value = {"search": {"total": 0, "searchResults": []}}

        request = MagicMock()
        response = await search_metadata(request, query="nonexistent")

        assert response.total == 0
        assert len(response.results) == 0


class TestLineageEndpoint:
    """Test get_lineage endpoint (mocked)."""

    @pytest.mark.asyncio
    @patch("apps.governance.api._datahub_graphql")
    async def test_get_lineage_basic(self, mock_graphql):
        from apps.governance.api import get_lineage

        mock_graphql.return_value = {"lineage": {"relationships": []}}

        request = MagicMock()
        response = await get_lineage(request, urn="urn:li:dataset:orders")

        assert len(response.nodes) == 1
        assert response.nodes[0].urn == "urn:li:dataset:orders"
        assert len(response.edges) == 0

    @pytest.mark.asyncio
    @patch("apps.governance.api._datahub_graphql")
    async def test_get_lineage_with_relationships(self, mock_graphql):
        from apps.governance.api import get_lineage

        def side_effect(query, variables):
            direction = variables["direction"]
            if direction == "UPSTREAM":
                return {
                    "lineage": {
                        "relationships": [
                            {
                                "entity": {
                                    "urn": "urn:li:dataset:customers",
                                    "name": "customers",
                                    "type": "DATASET",
                                    "platform": {"name": "postgres"},
                                },
                                "type": "DERIVES_FROM",
                            }
                        ]
                    }
                }
            return {"lineage": {"relationships": []}}

        mock_graphql.side_effect = side_effect

        request = MagicMock()
        response = await get_lineage(
            request, urn="urn:li:dataset:orders", direction="both"
        )

        assert len(response.nodes) == 2
        assert len(response.edges) == 1
        assert response.edges[0].source == "urn:li:dataset:customers"
        assert response.edges[0].target == "urn:li:dataset:orders"


class TestSchemaEndpoint:
    """Test get_schema endpoint (mocked)."""

    @pytest.mark.asyncio
    @patch("apps.governance.api.httpx.AsyncClient")
    async def test_get_schema_success(self, mock_client_class):
        from apps.governance.api import get_schema

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "value": {
                "schemaMetadata": {
                    "fields": [
                        {
                            "fieldPath": "id",
                            "nativeDataType": "INTEGER",
                            "nullable": False,
                            "description": "Primary key",
                        },
                        {
                            "fieldPath": "name",
                            "nativeDataType": "VARCHAR",
                            "nullable": True,
                        },
                    ]
                }
            }
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        request = MagicMock()
        response = await get_schema(request, urn="urn:li:dataset:orders")

        assert response.urn == "urn:li:dataset:orders"
        assert len(response.fields) == 2
        assert response.fields[0].name == "id"
        assert response.fields[0].nullable is False

    @pytest.mark.asyncio
    @patch("apps.governance.api.httpx.AsyncClient")
    async def test_get_schema_not_found(self, mock_client_class):
        from ninja.errors import HttpError

        from apps.governance.api import get_schema

        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        request = MagicMock()
        with pytest.raises(HttpError):
            await get_schema(request, urn="urn:li:dataset:nonexistent")


class TestQuotaEndpoints:
    """Test quota-related endpoints."""

    @patch("apps.governance.api.get_usage_stats")
    @patch("apps.governance.api.get_quota_manager")
    def test_list_quota_tiers(self, mock_get_manager, mock_get_usage):
        from apps.core.lib.tenant_quotas import QuotaTier
        from apps.governance.api import list_quota_tiers

        mock_manager = MagicMock()
        mock_policy = MagicMock()

        def get_limit_side_effect(resource):
            from apps.core.lib.tenant_quotas import ResourceType

            limits = {
                ResourceType.JOBS_PER_DAY: MagicMock(limit=100),
                ResourceType.TOTAL_STORAGE_MB: MagicMock(limit=10240),
                ResourceType.WORKFLOWS_PER_DAY: MagicMock(limit=50),
                ResourceType.JOBS_CONCURRENT: MagicMock(limit=10),
            }
            return limits.get(resource)

        mock_policy.get_limit = get_limit_side_effect
        mock_manager.policies = {QuotaTier.FREE: mock_policy}
        mock_get_manager.return_value = mock_manager

        request = MagicMock()
        tiers = list_quota_tiers(request)

        assert len(tiers) >= 1
        assert tiers[0].tier_id == "free"

    @patch("apps.governance.api.get_tenant_id")
    @patch("apps.governance.api.get_usage_stats")
    @patch("apps.governance.api.get_quota_manager")
    def test_get_quota_usage(
        self, mock_get_manager, mock_get_usage, mock_get_tenant_id
    ):
        from apps.governance.api import get_quota_usage

        mock_get_tenant_id.return_value = "tenant_1"
        mock_manager = MagicMock()
        mock_manager.get_tenant_tier.return_value = MagicMock(value="free")
        mock_manager.get_policy.return_value = MagicMock()
        mock_get_manager.return_value = mock_manager
        mock_get_usage.return_value = []

        request = MagicMock()
        result = get_quota_usage(request)

        assert result.tenant_id == "tenant_1"
        assert result.tier == "free"

    @patch("apps.governance.api.get_tenant_id")
    @patch("apps.governance.api.set_tenant_tier")
    def test_update_quota_tier_success(self, mock_set_tier, mock_get_tenant_id):
        from apps.core.lib.tenant_quotas import QuotaTier
        from apps.governance.api import update_quota_tier

        mock_get_tenant_id.return_value = "tenant_1"

        request = MagicMock()
        payload = SetTierRequest(tier="free")
        result = update_quota_tier(request, payload)

        assert result["tenant_id"] == "tenant_1"
        assert result["tier"] == "free"
        assert result["status"] == "updated"
        mock_set_tier.assert_called_once_with("tenant_1", QuotaTier.FREE)

    @patch("apps.governance.api.get_tenant_id")
    def test_update_quota_tier_invalid(self, mock_get_tenant_id):
        from ninja.errors import HttpError

        from apps.governance.api import update_quota_tier

        mock_get_tenant_id.return_value = "tenant_1"

        request = MagicMock()
        payload = SetTierRequest(tier="nonexistent_tier")

        with pytest.raises(HttpError):
            update_quota_tier(request, payload)
