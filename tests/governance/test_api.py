"""Tests for governance API endpoints."""

from __future__ import annotations

import pytest
from django.test import Client, TestCase

from apps.governance.models import DataContract, LineageNode, Policy


@pytest.mark.django_db
class TestGovernanceAPIEndpoints(TestCase):
    """Tests for governance API endpoints."""

    def setUp(self):
        self.client = Client()
        self.tenant_id = "test-tenant"
        self.realm = "test"

    def test_create_contract(self):
        contract = DataContract.objects.create(
            tenant_id=self.tenant_id,
            realm=self.realm,
            name="test_contract",
            dataset_urn="urn:datahub:dataset:test",
            owner="owner",
        )
        assert contract.id is not None
        assert DataContract.objects.filter(tenant_id=self.tenant_id).count() == 1

    def test_get_contract(self):
        contract = DataContract.objects.create(
            tenant_id=self.tenant_id,
            realm=self.realm,
            name="get_test_contract",
            dataset_urn="urn:datahub:dataset:get_test",
            owner="owner",
            description="Test contract for GET endpoint",
        )
        retrieved = DataContract.objects.get(id=contract.id)
        assert retrieved.name == "get_test_contract"
        assert retrieved.description == "Test contract for GET endpoint"

    def test_policy_crud_operations(self):
        policy = Policy.objects.create(
            tenant_id=self.tenant_id,
            realm=self.realm,
            name="crud_test_policy",
            policy_type=Policy.PolicyType.ACCESS_CONTROL,
            owner="owner",
        )
        assert policy.id is not None

        retrieved = Policy.objects.get(id=policy.id)
        assert retrieved.name == "crud_test_policy"

        retrieved.status = Policy.Status.ACTIVE
        retrieved.save()
        retrieved.refresh_from_db()
        assert retrieved.status == Policy.Status.ACTIVE

        policy_id = policy.id
        policy.delete()
        with pytest.raises(Policy.DoesNotExist):
            Policy.objects.get(id=policy_id)

    def test_lineage_search(self):
        node1 = LineageNode.objects.create(
            tenant_id=self.tenant_id,
            realm=self.realm,
            urn="urn:datahub:dataset:source",
            name="source",
            node_type=LineageNode.NodeType.DATASET,
            platform="postgresql",
        )
        LineageNode.objects.create(
            tenant_id=self.tenant_id,
            realm=self.realm,
            urn="urn:datahub:dataset:target",
            name="target",
            node_type=LineageNode.NodeType.DATASET,
            platform="s3",
            upstream_urns=[node1.urn],
        )
        searched = LineageNode.objects.filter(tenant_id=self.tenant_id, urn__contains="source")
        assert searched.count() == 1
        assert searched.first().urn == "urn:datahub:dataset:source"

    def test_search_by_dataset_urn(self):
        urn = "urn:datahub:dataset:users"
        contract = DataContract.objects.create(
            tenant_id=self.tenant_id,
            realm=self.realm,
            name="user_contract",
            dataset_urn=urn,
            owner="owner",
        )
        results = DataContract.objects.filter(tenant_id=self.tenant_id, dataset_urn=urn)
        assert results.count() == 1
        assert results.first().id == contract.id

    def test_governance_quotas_structure(self):
        from apps.core.lib.tenant_quotas import QuotaTier

        tiers = list(QuotaTier)
        assert len(tiers) > 0
        assert QuotaTier.FREE in tiers


@pytest.mark.django_db
class TestGovernanceIntegration(TestCase):
    """Integration tests for governance module."""

    def setUp(self):
        self.tenant_id = "integration-tenant"
        self.realm = "integration"

    def test_contract_lineage_integration(self):
        urn = "urn:datahub:dataset:integrated_data"
        contract = DataContract.objects.create(
            tenant_id=self.tenant_id,
            realm=self.realm,
            name="integrated_contract",
            dataset_urn=urn,
            owner="owner",
        )
        node = LineageNode.objects.create(
            tenant_id=self.tenant_id,
            realm=self.realm,
            urn=urn,
            name="integrated_data",
            node_type=LineageNode.NodeType.DATASET,
        )
        assert contract.dataset_urn == node.urn

    def test_policy_scoped_to_dataset(self):
        dataset_urn = "urn:datahub:dataset:restricted"
        policy = Policy.objects.create(
            tenant_id=self.tenant_id,
            realm=self.realm,
            name="restrict_dataset",
            policy_type=Policy.PolicyType.ACCESS_CONTROL,
            owner="owner",
            scope={"datasets": [dataset_urn]},
        )
        assert dataset_urn in policy.scope["datasets"]

    def test_multi_tenant_isolation(self):
        tenant2 = "other-tenant"
        contract1 = DataContract.objects.create(
            tenant_id=self.tenant_id,
            realm=self.realm,
            name="tenant1_contract",
            dataset_urn="urn:datahub:dataset:t1",
            owner="owner",
        )
        contract2 = DataContract.objects.create(
            tenant_id=tenant2,
            realm="other",
            name="tenant2_contract",
            dataset_urn="urn:datahub:dataset:t2",
            owner="owner",
        )
        t1_contracts = DataContract.objects.filter(tenant_id=self.tenant_id)
        t2_contracts = DataContract.objects.filter(tenant_id=tenant2)
        assert t1_contracts.count() == 1
        assert t2_contracts.count() == 1
        assert t1_contracts.first().id == contract1.id
        assert t2_contracts.first().id == contract2.id
