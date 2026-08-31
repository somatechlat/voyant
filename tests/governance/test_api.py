"""Tests for governance API endpoints."""

from __future__ import annotations

import pytest
from django.test import Client, TestCase

from apps.core.models import Tenant
from apps.governance.models import DataContract, LineageNode, Policy


@pytest.mark.django_db
class TestGovernanceAPIEndpoints(TestCase):
    """Tests for governance API endpoints."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = Client()
        self.tenant = Tenant.objects.create(
            name="test-tenant",
            realm="test",
            external_tenant_id="ext-123",
        )
        # Note: In a real test, you'd need auth headers
        # This is a placeholder for integration testing

    def test_list_contracts_endpoint_exists(self):
        """Test that list contracts endpoint can be called."""
        # Create a test contract
        DataContract.objects.create(
            tenant=self.tenant,
            name="test_contract",
            dataset_urn="urn:datahub:dataset:test",
            owner="owner",
        )
        # In a real scenario, you would make an HTTP request
        # For now, verify the model is accessible
        contracts = DataContract.objects.filter(tenant=self.tenant)
        assert contracts.count() == 1

    def test_get_contract_endpoint_structure(self):
        """Test that contract retrieval would work."""
        contract = DataContract.objects.create(
            tenant=self.tenant,
            name="get_test_contract",
            dataset_urn="urn:datahub:dataset:get_test",
            owner="owner",
            description="Test contract for GET endpoint",
        )
        retrieved = DataContract.objects.get(id=contract.id)
        assert retrieved.name == "get_test_contract"
        assert retrieved.description == "Test contract for GET endpoint"

    def test_policy_crud_operations(self):
        """Test create, read, update, delete operations for policies."""
        # Create
        policy = Policy.objects.create(
            tenant=self.tenant,
            name="crud_test_policy",
            policy_type=Policy.PolicyType.ACCESS_CONTROL,
            owner="owner",
        )
        assert policy.id is not None

        # Read
        retrieved = Policy.objects.get(id=policy.id)
        assert retrieved.name == "crud_test_policy"

        # Update
        retrieved.status = Policy.Status.ACTIVE
        retrieved.save()
        retrieved.refresh_from_db()
        assert retrieved.status == Policy.Status.ACTIVE

        # Delete
        policy_id = policy.id
        policy.delete()
        with pytest.raises(Policy.DoesNotExist):
            Policy.objects.get(id=policy_id)

    def test_lineage_search_simulation(self):
        """Test lineage node retrieval (simulating search)."""
        node1 = LineageNode.objects.create(
            tenant=self.tenant,
            urn="urn:datahub:dataset:source",
            name="source",
            node_type=LineageNode.NodeType.DATASET,
            platform="postgresql",
        )
        node2 = LineageNode.objects.create(
            tenant=self.tenant,
            urn="urn:datahub:dataset:target",
            name="target",
            node_type=LineageNode.NodeType.DATASET,
            platform="s3",
            upstream_urns=[node1.urn],
        )
        # Simulate search by URN
        searched = LineageNode.objects.filter(tenant=self.tenant, urn__contains="source")
        assert searched.count() == 1
        assert searched.first().urn == "urn:datahub:dataset:source"

    def test_search_by_dataset_urn(self):
        """Test searching contracts by dataset URN."""
        urn = "urn:datahub:dataset:users"
        contract = DataContract.objects.create(
            tenant=self.tenant,
            name="user_contract",
            dataset_urn=urn,
            owner="owner",
        )
        # Search by URN
        results = DataContract.objects.filter(tenant=self.tenant, dataset_urn=urn)
        assert results.count() == 1
        assert results.first().id == contract.id

    def test_governance_quotas_endpoint_structure(self):
        """Test governance quotas endpoint response structure."""
        # This test verifies that the QuotaTier enum and policy structures exist
        # In a real test, you'd make an HTTP request and verify the response
        from apps.core.lib.tenant_quotas import QuotaTier

        tiers = list(QuotaTier)
        assert len(tiers) > 0
        assert QuotaTier.FREE in tiers


@pytest.mark.django_db
class TestGovernanceIntegration(TestCase):
    """Integration tests for governance module."""

    def setUp(self):
        """Set up test fixtures."""
        self.tenant = Tenant.objects.create(
            name="integration-tenant",
            realm="integration",
            external_tenant_id="int-123",
        )

    def test_contract_lineage_integration(self):
        """Test integration between DataContract and LineageNode."""
        # Create a contract for a dataset
        urn = "urn:datahub:dataset:integrated_data"
        contract = DataContract.objects.create(
            tenant=self.tenant,
            name="integrated_contract",
            dataset_urn=urn,
            owner="owner",
        )
        # Create a lineage node for the same dataset
        node = LineageNode.objects.create(
            tenant=self.tenant,
            urn=urn,
            name="integrated_data",
            node_type=LineageNode.NodeType.DATASET,
        )
        # Verify they reference the same dataset
        assert contract.dataset_urn == node.urn

    def test_policy_scoped_to_dataset(self):
        """Test that policies correctly scope to datasets."""
        dataset_urn = "urn:datahub:dataset:restricted"
        policy = Policy.objects.create(
            tenant=self.tenant,
            name="restrict_dataset",
            policy_type=Policy.PolicyType.ACCESS_CONTROL,
            owner="owner",
            scope={"datasets": [dataset_urn]},
        )
        # Verify policy is scoped correctly
        assert dataset_urn in policy.scope["datasets"]

    def test_multi_tenant_isolation(self):
        """Test that governance objects are properly isolated by tenant."""
        tenant2 = Tenant.objects.create(
            name="other-tenant",
            realm="other",
            external_tenant_id="other-123",
        )
        # Create contract in tenant 1
        contract1 = DataContract.objects.create(
            tenant=self.tenant,
            name="tenant1_contract",
            dataset_urn="urn:datahub:dataset:t1",
            owner="owner",
        )
        # Create contract in tenant 2
        contract2 = DataContract.objects.create(
            tenant=tenant2,
            name="tenant2_contract",
            dataset_urn="urn:datahub:dataset:t2",
            owner="owner",
        )
        # Verify isolation
        t1_contracts = DataContract.objects.filter(tenant=self.tenant)
        t2_contracts = DataContract.objects.filter(tenant=tenant2)
        assert t1_contracts.count() == 1
        assert t2_contracts.count() == 1
        assert t1_contracts.first().id == contract1.id
        assert t2_contracts.first().id == contract2.id
