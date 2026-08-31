"""Tests for governance models: DataContract, Policy, LineageNode."""

from __future__ import annotations

import pytest
from django.test import TestCase

from apps.core.models import Tenant
from apps.governance.models import DataContract, LineageNode, Policy


@pytest.mark.django_db
class TestDataContract(TestCase):
    """Tests for DataContract model."""

    def setUp(self):
        """Set up test fixtures."""
        self.tenant = Tenant.objects.create(
            name="test-tenant",
            realm="test",
            external_tenant_id="ext-123",
        )

    def test_create_data_contract(self):
        """Test creating a basic data contract."""
        contract = DataContract.objects.create(
            tenant=self.tenant,
            name="user_data_contract",
            description="Contract for user data",
            dataset_urn="urn:datahub:dataset:user_profile",
            owner="data-team",
            status=DataContract.Status.ACTIVE,
            version="1.0.0",
        )
        assert contract.name == "user_data_contract"
        assert contract.status == DataContract.Status.ACTIVE
        assert str(contract) == "user_data_contract v1.0.0 (active)"

    def test_contract_with_schema_definition(self):
        """Test creating a contract with schema definition."""
        schema = {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "email": {"type": "string", "format": "email"},
                "created_at": {"type": "string", "format": "date-time"},
            },
            "required": ["user_id", "email"],
        }
        contract = DataContract.objects.create(
            tenant=self.tenant,
            name="user_schema",
            dataset_urn="urn:datahub:dataset:users",
            schema_definition=schema,
            owner="platform",
        )
        assert contract.schema_definition["properties"]["user_id"]["type"] == "string"
        assert "email" in contract.schema_definition["required"]

    def test_contract_with_quality_rules(self):
        """Test creating a contract with quality rules."""
        rules = [
            {"type": "not_null", "column": "user_id"},
            {"type": "unique", "column": "email"},
            {"type": "pattern", "column": "email", "pattern": r"^[\w\.-]+@[\w\.-]+\.\w+$"},
        ]
        contract = DataContract.objects.create(
            tenant=self.tenant,
            name="user_quality",
            dataset_urn="urn:datahub:dataset:users",
            quality_rules=rules,
            owner="qa-team",
        )
        assert len(contract.quality_rules) == 3
        assert contract.quality_rules[0]["type"] == "not_null"

    def test_contract_status_transitions(self):
        """Test contract status lifecycle."""
        contract = DataContract.objects.create(
            tenant=self.tenant,
            name="lifecycle_test",
            dataset_urn="urn:datahub:dataset:test",
            owner="owner",
            status=DataContract.Status.DRAFT,
        )
        assert contract.status == DataContract.Status.DRAFT

        contract.status = DataContract.Status.ACTIVE
        contract.save()
        contract.refresh_from_db()
        assert contract.status == DataContract.Status.ACTIVE

        contract.status = DataContract.Status.DEPRECATED
        contract.save()
        contract.refresh_from_db()
        assert contract.status == DataContract.Status.DEPRECATED

    def test_contract_versioning(self):
        """Test multiple versions of the same contract."""
        contract_v1 = DataContract.objects.create(
            tenant=self.tenant,
            name="versioned_contract",
            dataset_urn="urn:datahub:dataset:versioned",
            version="1.0.0",
            owner="owner",
        )
        contract_v2 = DataContract.objects.create(
            tenant=self.tenant,
            name="versioned_contract",
            dataset_urn="urn:datahub:dataset:versioned",
            version="2.0.0",
            owner="owner",
        )
        assert contract_v1.version == "1.0.0"
        assert contract_v2.version == "2.0.0"

        contracts = DataContract.objects.filter(
            tenant=self.tenant, name="versioned_contract"
        ).order_by("version")
        assert len(contracts) == 2


@pytest.mark.django_db
class TestPolicy(TestCase):
    """Tests for Policy model."""

    def setUp(self):
        """Set up test fixtures."""
        self.tenant = Tenant.objects.create(
            name="test-tenant",
            realm="test",
            external_tenant_id="ext-123",
        )

    def test_create_access_control_policy(self):
        """Test creating an access control policy."""
        policy = Policy.objects.create(
            tenant=self.tenant,
            name="restrict_pii_access",
            policy_type=Policy.PolicyType.ACCESS_CONTROL,
            status=Policy.Status.ACTIVE,
            owner="security",
            enforcement_level="strict",
            rules={
                "conditions": [
                    {"attribute": "department", "value": "data-science", "operator": "equals"}
                ]
            },
            scope={
                "datasets": ["urn:datahub:dataset:users"],
                "operations": ["read"],
            },
        )
        assert policy.policy_type == Policy.PolicyType.ACCESS_CONTROL
        assert policy.enforcement_level == "strict"
        assert str(policy) == "restrict_pii_access (access_control)"

    def test_create_data_retention_policy(self):
        """Test creating a data retention policy."""
        policy = Policy.objects.create(
            tenant=self.tenant,
            name="user_data_retention",
            policy_type=Policy.PolicyType.DATA_RETENTION,
            status=Policy.Status.ACTIVE,
            owner="legal",
            rules={
                "retention_period_days": 365,
                "archive_after_days": 90,
                "deletion_method": "secure_wipe",
            },
            scope={"datasets": ["urn:datahub:dataset:user_sessions"]},
        )
        assert policy.rules["retention_period_days"] == 365
        assert policy.rules["deletion_method"] == "secure_wipe"

    def test_policy_status_transitions(self):
        """Test policy status lifecycle."""
        policy = Policy.objects.create(
            tenant=self.tenant,
            name="lifecycle_test",
            policy_type=Policy.PolicyType.COMPLIANCE,
            status=Policy.Status.DRAFT,
            owner="owner",
        )
        assert policy.status == Policy.Status.DRAFT

        policy.status = Policy.Status.ACTIVE
        policy.save()
        policy.refresh_from_db()
        assert policy.status == Policy.Status.ACTIVE

    def test_enforcement_levels(self):
        """Test different enforcement levels."""
        enforcement_levels = ["strict", "warn", "audit"]
        for level in enforcement_levels:
            policy = Policy.objects.create(
                tenant=self.tenant,
                name=f"policy_{level}",
                policy_type=Policy.PolicyType.USAGE,
                enforcement_level=level,
                owner="owner",
            )
            assert policy.enforcement_level == level

    def test_policy_with_complex_rules(self):
        """Test policy with complex conditional rules."""
        rules = {
            "conditions": [
                {
                    "condition_name": "business_hours_only",
                    "type": "time_based",
                    "start_hour": 9,
                    "end_hour": 17,
                }
            ],
            "actions": [
                {
                    "action": "deny",
                    "reason": "Outside business hours",
                }
            ],
        }
        policy = Policy.objects.create(
            tenant=self.tenant,
            name="business_hours_policy",
            policy_type=Policy.PolicyType.ACCESS_CONTROL,
            rules=rules,
            owner="owner",
        )
        assert policy.rules["conditions"][0]["type"] == "time_based"


@pytest.mark.django_db
class TestLineageNode(TestCase):
    """Tests for LineageNode model."""

    def setUp(self):
        """Set up test fixtures."""
        self.tenant = Tenant.objects.create(
            name="test-tenant",
            realm="test",
            external_tenant_id="ext-123",
        )

    def test_create_dataset_node(self):
        """Test creating a dataset lineage node."""
        node = LineageNode.objects.create(
            tenant=self.tenant,
            urn="urn:datahub:dataset:raw_customers",
            name="raw_customers",
            node_type=LineageNode.NodeType.DATASET,
            platform="postgresql",
            description="Raw customer data from production database",
        )
        assert node.node_type == LineageNode.NodeType.DATASET
        assert node.platform == "postgresql"

    def test_create_transformation_node(self):
        """Test creating a transformation lineage node."""
        node = LineageNode.objects.create(
            tenant=self.tenant,
            urn="urn:datahub:transformation:customer_aggregation",
            name="customer_aggregation",
            node_type=LineageNode.NodeType.TRANSFORMATION,
            description="Aggregates customer data by region",
        )
        assert node.node_type == LineageNode.NodeType.TRANSFORMATION

    def test_lineage_upstream_downstream(self):
        """Test tracking upstream and downstream dependencies."""
        upstream_urn = "urn:datahub:dataset:raw_data"
        downstream_urn = "urn:datahub:dataset:processed_data"

        node = LineageNode.objects.create(
            tenant=self.tenant,
            urn="urn:datahub:transformation:process",
            name="process",
            node_type=LineageNode.NodeType.TRANSFORMATION,
            upstream_urns=[upstream_urn],
            downstream_urns=[downstream_urn],
        )
        assert upstream_urn in node.upstream_urns
        assert downstream_urn in node.downstream_urns

    def test_lineage_with_metadata(self):
        """Test lineage node with custom metadata."""
        metadata = {
            "owner": "data-team",
            "sla": "99.9%",
            "refresh_frequency": "daily",
            "tags": ["production", "critical"],
        }
        node = LineageNode.objects.create(
            tenant=self.tenant,
            urn="urn:datahub:dataset:critical_data",
            name="critical_data",
            node_type=LineageNode.NodeType.DATASET,
            metadata=metadata,
        )
        assert node.metadata["sla"] == "99.9%"
        assert "production" in node.metadata["tags"]

    def test_unique_urn_constraint(self):
        """Test that URN uniqueness is enforced."""
        urn = "urn:datahub:dataset:unique_test"
        LineageNode.objects.create(
            tenant=self.tenant,
            urn=urn,
            name="node1",
            node_type=LineageNode.NodeType.DATASET,
        )
        # Attempting to create another node with the same URN should fail
        with pytest.raises(Exception):  # IntegrityError
            LineageNode.objects.create(
                tenant=self.tenant,
                urn=urn,
                name="node2",
                node_type=LineageNode.NodeType.DATASET,
            )


@pytest.mark.django_db
class TestGovernanceQuerysets(TestCase):
    """Tests for governance model querysets and filtering."""

    def setUp(self):
        """Set up test fixtures."""
        self.tenant = Tenant.objects.create(
            name="test-tenant",
            realm="test",
            external_tenant_id="ext-123",
        )

    def test_filter_contracts_by_status(self):
        """Test filtering contracts by status."""
        DataContract.objects.create(
            tenant=self.tenant,
            name="active_contract",
            dataset_urn="urn:datahub:dataset:active",
            owner="owner",
            status=DataContract.Status.ACTIVE,
        )
        DataContract.objects.create(
            tenant=self.tenant,
            name="draft_contract",
            dataset_urn="urn:datahub:dataset:draft",
            owner="owner",
            status=DataContract.Status.DRAFT,
        )
        active = DataContract.objects.filter(
            tenant=self.tenant, status=DataContract.Status.ACTIVE
        )
        draft = DataContract.objects.filter(
            tenant=self.tenant, status=DataContract.Status.DRAFT
        )
        assert active.count() == 1
        assert draft.count() == 1

    def test_filter_policies_by_type(self):
        """Test filtering policies by type."""
        Policy.objects.create(
            tenant=self.tenant,
            name="access_policy",
            policy_type=Policy.PolicyType.ACCESS_CONTROL,
            owner="owner",
        )
        Policy.objects.create(
            tenant=self.tenant,
            name="retention_policy",
            policy_type=Policy.PolicyType.DATA_RETENTION,
            owner="owner",
        )
        access = Policy.objects.filter(
            tenant=self.tenant, policy_type=Policy.PolicyType.ACCESS_CONTROL
        )
        retention = Policy.objects.filter(
            tenant=self.tenant, policy_type=Policy.PolicyType.DATA_RETENTION
        )
        assert access.count() == 1
        assert retention.count() == 1

    def test_filter_lineage_by_platform(self):
        """Test filtering lineage nodes by platform."""
        LineageNode.objects.create(
            tenant=self.tenant,
            urn="urn:datahub:dataset:postgres_data",
            name="postgres_data",
            node_type=LineageNode.NodeType.DATASET,
            platform="postgresql",
        )
        LineageNode.objects.create(
            tenant=self.tenant,
            urn="urn:datahub:dataset:s3_data",
            name="s3_data",
            node_type=LineageNode.NodeType.DATASET,
            platform="s3",
        )
        postgres_nodes = LineageNode.objects.filter(
            tenant=self.tenant, platform="postgresql"
        )
        s3_nodes = LineageNode.objects.filter(tenant=self.tenant, platform="s3")
        assert postgres_nodes.count() == 1
        assert s3_nodes.count() == 1
