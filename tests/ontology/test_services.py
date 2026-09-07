"""
Integration tests for apps.ontology.services — Service layer.

Tests CRUD, batch, upsert, soft-delete, versioning, traversal, and
referential integrity for Object Types, Objects, Link Types, and Links.
Uses real DB via @pytest.mark.django_db.

These tests require a running PostgreSQL instance. Mark as integration:
    pytest tests/ontology/test_services.py -m integration
"""

import pytest
from django.db import connection

# Skip entire module if DB is unreachable
_db_available = True
try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
except Exception:
    _db_available = False

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not _db_available, reason="PostgreSQL not available"),
]

from apps.ontology.models import (
    Cardinality,
    Link,
    LinkType,
    Object,
    ObjectType,
)
from apps.ontology.services import (
    LinkService,
    LinkTypeService,
    ObjectService,
    ObjectTypeService,
)
from apps.ontology.validators import ValidationError

TENANT = "test-tenant-001"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def object_type(db):
    """Create an ObjectType with two properties."""
    ot = ObjectTypeService.create(
        TENANT,
        name="Customer",
        description="A customer entity",
        properties=[
            {"name": "name", "property_type": "string", "required": True},
            {"name": "age", "property_type": "integer", "default_value": 0},
        ],
    )
    return ot


@pytest.fixture
def second_object_type(db):
    """Create a second ObjectType for link tests."""
    ot = ObjectTypeService.create(
        TENANT,
        name="Order",
        description="An order entity",
        properties=[
            {"name": "total", "property_type": "float", "required": True},
        ],
    )
    return ot


# =========================================================================
# ObjectTypeService
# =========================================================================


class TestObjectTypeService:
    @pytest.mark.django_db
    def test_create_object_type(self, object_type):
        assert object_type.name == "Customer"
        assert object_type.version == 1
        assert object_type.tenant_id == TENANT
        assert object_type.deleted_at is None
        props = list(object_type.properties.all())
        assert len(props) == 2
        names = {p.name for p in props}
        assert names == {"name", "age"}

    @pytest.mark.django_db
    def test_list_excludes_deleted(self, object_type):
        qs = ObjectTypeService.list(TENANT)
        assert qs.count() == 1
        ObjectTypeService.soft_delete(TENANT, str(object_type.id))
        assert ObjectTypeService.list(TENANT).count() == 0
        assert ObjectTypeService.list(TENANT, include_deleted=True).count() == 1

    @pytest.mark.django_db
    def test_get_by_id(self, object_type):
        fetched = ObjectTypeService.get(TENANT, str(object_type.id))
        assert fetched.id == object_type.id
        assert fetched.name == "Customer"

    @pytest.mark.django_db
    def test_get_nonexistent_raises(self, db):
        with pytest.raises(ObjectType.DoesNotExist):
            ObjectTypeService.get(TENANT, "nonexistent-id")

    @pytest.mark.django_db
    def test_update_name_and_description(self, object_type):
        updated = ObjectTypeService.update(
            TENANT,
            str(object_type.id),
            name="Client",
            description="Updated description",
        )
        assert updated.name == "Client"
        assert updated.description == "Updated description"
        assert updated.version == 2

    @pytest.mark.django_db
    def test_update_add_new_property(self, object_type):
        updated = ObjectTypeService.update(
            TENANT,
            str(object_type.id),
            properties=[
                {"name": "name", "property_type": "string", "required": True},
                {"name": "age", "property_type": "integer", "default_value": 0},
                {"name": "email", "property_type": "string"},
            ],
        )
        assert updated.version == 2
        props = list(updated.properties.all())
        assert len(props) == 3

    @pytest.mark.django_db
    def test_update_type_change_on_required_field_raises(self, object_type):
        with pytest.raises(ValidationError) as exc_info:
            ObjectTypeService.update(
                TENANT,
                str(object_type.id),
                properties=[
                    {"name": "name", "property_type": "integer", "required": True},
                    {"name": "age", "property_type": "integer"},
                ],
            )
        assert any(e["code"] == "incompatible_change" for e in exc_info.value.errors)

    @pytest.mark.django_db
    def test_soft_delete(self, object_type):
        ObjectTypeService.soft_delete(TENANT, str(object_type.id))
        ot = ObjectType.objects.get(id=object_type.id)
        assert ot.deleted_at is not None

    @pytest.mark.django_db
    def test_soft_delete_with_instances_raises(self, object_type):
        ObjectService.create(TENANT, str(object_type.id), {"name": "Alice"})
        with pytest.raises(ValidationError) as exc_info:
            ObjectTypeService.soft_delete(TENANT, str(object_type.id))
        assert any(e["code"] == "has_instances" for e in exc_info.value.errors)

    @pytest.mark.django_db
    def test_version_increments_on_update(self, object_type):
        assert object_type.version == 1
        ot2 = ObjectTypeService.update(TENANT, str(object_type.id), name="V2")
        assert ot2.version == 2
        ot3 = ObjectTypeService.update(TENANT, str(object_type.id), name="V3")
        assert ot3.version == 3


# =========================================================================
# ObjectService
# =========================================================================


class TestObjectService:
    @pytest.mark.django_db
    def test_create_object(self, object_type):
        obj = ObjectService.create(TENANT, str(object_type.id), {"name": "Alice", "age": 30})
        assert obj.version == 1
        assert obj.properties["name"] == "Alice"
        assert obj.properties["age"] == 30

    @pytest.mark.django_db
    def test_create_with_validation_error(self, object_type):
        with pytest.raises(ValidationError):
            ObjectService.create(TENANT, str(object_type.id), {"age": 30})  # missing required 'name'

    @pytest.mark.django_db
    def test_list_objects(self, object_type):
        ObjectService.create(TENANT, str(object_type.id), {"name": "A"})
        ObjectService.create(TENANT, str(object_type.id), {"name": "B"})
        qs = ObjectService.list(TENANT, str(object_type.id))
        assert qs.count() == 2

    @pytest.mark.django_db
    def test_list_excludes_deleted(self, object_type):
        obj = ObjectService.create(TENANT, str(object_type.id), {"name": "A"})
        ObjectService.soft_delete(TENANT, str(obj.id))
        assert ObjectService.list(TENANT).count() == 0

    @pytest.mark.django_db
    def test_get_object(self, object_type):
        obj = ObjectService.create(TENANT, str(object_type.id), {"name": "A"})
        fetched = ObjectService.get(TENANT, str(obj.id))
        assert fetched.id == obj.id

    @pytest.mark.django_db
    def test_update_object(self, object_type):
        obj = ObjectService.create(TENANT, str(object_type.id), {"name": "Alice", "age": 25})
        updated = ObjectService.update(TENANT, str(obj.id), {"age": 26})
        assert updated.properties["age"] == 26
        assert updated.properties["name"] == "Alice"  # preserved
        assert updated.version == 2

    @pytest.mark.django_db
    def test_optimistic_concurrency(self, object_type):
        obj = ObjectService.create(TENANT, str(object_type.id), {"name": "Alice", "age": 25})
        # Correct version
        ObjectService.update(TENANT, str(obj.id), {"age": 26}, version=1)
        # Stale version
        with pytest.raises(ValidationError) as exc_info:
            ObjectService.update(TENANT, str(obj.id), {"age": 27}, version=1)
        assert any(e["code"] == "conflict" for e in exc_info.value.errors)

    @pytest.mark.django_db
    def test_soft_delete_object(self, object_type):
        obj = ObjectService.create(TENANT, str(object_type.id), {"name": "A"})
        ObjectService.soft_delete(TENANT, str(obj.id))
        assert Object.objects.get(id=obj.id).deleted_at is not None

    @pytest.mark.django_db
    def test_soft_delete_with_links_raises(self, object_type, second_object_type):
        obj = ObjectService.create(TENANT, str(object_type.id), {"name": "A"})
        tgt = ObjectService.create(TENANT, str(second_object_type.id), {"total": 99.9})
        lt = LinkTypeService.create(
            TENANT,
            name="relates",
            source_object_type_id=str(object_type.id),
            target_object_type_id=str(second_object_type.id),
        )
        LinkService.create(TENANT, str(lt.id), str(obj.id), str(tgt.id))
        with pytest.raises(ValidationError) as exc_info:
            ObjectService.soft_delete(TENANT, str(obj.id))
        assert any(e["code"] == "has_links" for e in exc_info.value.errors)

    @pytest.mark.django_db
    def test_batch_create(self, object_type):
        items = [
            {"name": "A", "age": 10},
            {"name": "B", "age": 20},
            {"name": "C", "age": 30},
        ]
        created = ObjectService.batch_create(TENANT, str(object_type.id), items)
        assert len(created) == 3
        assert Object.objects.filter(tenant_id=TENANT, deleted_at__isnull=True).count() == 3

    @pytest.mark.django_db
    def test_batch_create_validation_error_rolls_back(self, object_type):
        items = [
            {"name": "A", "age": 10},
            {"age": 20},  # missing required 'name'
        ]
        with pytest.raises(ValidationError):
            ObjectService.batch_create(TENANT, str(object_type.id), items)
        # Transaction should roll back — nothing created
        assert Object.objects.filter(tenant_id=TENANT, deleted_at__isnull=True).count() == 0

    @pytest.mark.django_db
    def test_upsert_creates_new(self, object_type):
        results = ObjectService.upsert(
            TENANT, str(object_type.id), "name", [{"name": "Alice", "age": 30}]
        )
        assert len(results) == 1
        assert results[0].properties["name"] == "Alice"

    @pytest.mark.django_db
    def test_upsert_updates_existing(self, object_type):
        ObjectService.create(TENANT, str(object_type.id), {"name": "Alice", "age": 30})
        results = ObjectService.upsert(
            TENANT, str(object_type.id), "name", [{"name": "Alice", "age": 31}]
        )
        assert len(results) == 1
        assert results[0].properties["age"] == 31

    @pytest.mark.django_db
    def test_upsert_missing_key_raises(self, object_type):
        with pytest.raises(ValidationError) as exc_info:
            ObjectService.upsert(
                TENANT, str(object_type.id), "name", [{"age": 30}]
            )
        assert any(e["code"] == "required" for e in exc_info.value.errors)


# =========================================================================
# LinkTypeService
# =========================================================================


class TestLinkTypeService:
    @pytest.mark.django_db
    def test_create_link_type(self, object_type, second_object_type):
        lt = LinkTypeService.create(
            TENANT,
            name="places",
            source_object_type_id=str(object_type.id),
            target_object_type_id=str(second_object_type.id),
            cardinality=Cardinality.ONE_TO_MANY,
        )
        assert lt.name == "places"
        assert lt.cardinality == Cardinality.ONE_TO_MANY

    @pytest.mark.django_db
    def test_create_with_invalid_source_raises(self, second_object_type):
        with pytest.raises(ObjectType.DoesNotExist):
            LinkTypeService.create(
                TENANT,
                name="bad",
                source_object_type_id="nonexistent",
                target_object_type_id=str(second_object_type.id),
            )

    @pytest.mark.django_db
    def test_list_link_types(self, object_type, second_object_type):
        LinkTypeService.create(
            TENANT,
            name="lt1",
            source_object_type_id=str(object_type.id),
            target_object_type_id=str(second_object_type.id),
        )
        assert LinkTypeService.list(TENANT).count() == 1

    @pytest.mark.django_db
    def test_soft_delete_link_type(self, object_type, second_object_type):
        lt = LinkTypeService.create(
            TENANT,
            name="lt1",
            source_object_type_id=str(object_type.id),
            target_object_type_id=str(second_object_type.id),
        )
        LinkTypeService.soft_delete(TENANT, str(lt.id))
        assert LinkType.objects.get(id=lt.id).deleted_at is not None

    @pytest.mark.django_db
    def test_soft_delete_with_instances_raises(self, object_type, second_object_type):
        lt = LinkTypeService.create(
            TENANT,
            name="lt1",
            source_object_type_id=str(object_type.id),
            target_object_type_id=str(second_object_type.id),
        )
        src = ObjectService.create(TENANT, str(object_type.id), {"name": "A"})
        tgt = ObjectService.create(TENANT, str(second_object_type.id), {"total": 10.0})
        LinkService.create(TENANT, str(lt.id), str(src.id), str(tgt.id))
        with pytest.raises(ValidationError) as exc_info:
            LinkTypeService.soft_delete(TENANT, str(lt.id))
        assert any(e["code"] == "has_instances" for e in exc_info.value.errors)


# =========================================================================
# LinkService
# =========================================================================


class TestLinkService:
    @pytest.mark.django_db
    def test_create_link(self, object_type, second_object_type):
        lt = LinkTypeService.create(
            TENANT,
            name="places",
            source_object_type_id=str(object_type.id),
            target_object_type_id=str(second_object_type.id),
        )
        src = ObjectService.create(TENANT, str(object_type.id), {"name": "A"})
        tgt = ObjectService.create(TENANT, str(second_object_type.id), {"total": 10.0})
        link = LinkService.create(TENANT, str(lt.id), str(src.id), str(tgt.id))
        assert link.link_type_id == lt.id
        assert link.source_object_id == src.id
        assert link.target_object_id == tgt.id

    @pytest.mark.django_db
    def test_create_link_with_properties(self, object_type, second_object_type):
        lt = LinkTypeService.create(
            TENANT,
            name="places",
            source_object_type_id=str(object_type.id),
            target_object_type_id=str(second_object_type.id),
        )
        src = ObjectService.create(TENANT, str(object_type.id), {"name": "A"})
        tgt = ObjectService.create(TENANT, str(second_object_type.id), {"total": 10.0})
        link = LinkService.create(
            TENANT, str(lt.id), str(src.id), str(tgt.id), {"quantity": 5}
        )
        assert link.properties == {"quantity": 5}

    @pytest.mark.django_db
    def test_type_mismatch_source_raises(self, object_type, second_object_type):
        lt = LinkTypeService.create(
            TENANT,
            name="places",
            source_object_type_id=str(object_type.id),
            target_object_type_id=str(second_object_type.id),
        )
        # Swap: use second_object_type as source (wrong type)
        wrong_src = ObjectService.create(TENANT, str(second_object_type.id), {"total": 5.0})
        tgt = ObjectService.create(TENANT, str(second_object_type.id), {"total": 10.0})
        with pytest.raises(ValidationError) as exc_info:
            LinkService.create(TENANT, str(lt.id), str(wrong_src.id), str(tgt.id))
        assert any(e["field"] == "source_object" for e in exc_info.value.errors)

    @pytest.mark.django_db
    def test_type_mismatch_target_raises(self, object_type, second_object_type):
        lt = LinkTypeService.create(
            TENANT,
            name="places",
            source_object_type_id=str(object_type.id),
            target_object_type_id=str(second_object_type.id),
        )
        src = ObjectService.create(TENANT, str(object_type.id), {"name": "A"})
        wrong_tgt = ObjectService.create(TENANT, str(object_type.id), {"name": "B"})
        with pytest.raises(ValidationError) as exc_info:
            LinkService.create(TENANT, str(lt.id), str(src.id), str(wrong_tgt.id))
        assert any(e["field"] == "target_object" for e in exc_info.value.errors)

    @pytest.mark.django_db
    def test_one_to_one_uniqueness(self, object_type, second_object_type):
        lt = LinkTypeService.create(
            TENANT,
            name="exclusive",
            source_object_type_id=str(object_type.id),
            target_object_type_id=str(second_object_type.id),
            cardinality=Cardinality.ONE_TO_ONE,
        )
        src = ObjectService.create(TENANT, str(object_type.id), {"name": "A"})
        tgt1 = ObjectService.create(TENANT, str(second_object_type.id), {"total": 1.0})
        tgt2 = ObjectService.create(TENANT, str(second_object_type.id), {"total": 2.0})
        LinkService.create(TENANT, str(lt.id), str(src.id), str(tgt1.id))
        with pytest.raises(ValidationError) as exc_info:
            LinkService.create(TENANT, str(lt.id), str(src.id), str(tgt2.id))
        assert any(e["code"] == "duplicate" for e in exc_info.value.errors)

    @pytest.mark.django_db
    def test_delete_link(self, object_type, second_object_type):
        lt = LinkTypeService.create(
            TENANT,
            name="places",
            source_object_type_id=str(object_type.id),
            target_object_type_id=str(second_object_type.id),
        )
        src = ObjectService.create(TENANT, str(object_type.id), {"name": "A"})
        tgt = ObjectService.create(TENANT, str(second_object_type.id), {"total": 10.0})
        link = LinkService.create(TENANT, str(lt.id), str(src.id), str(tgt.id))
        LinkService.delete(TENANT, str(link.id))
        assert Link.objects.get(id=link.id).deleted_at is not None

    @pytest.mark.django_db
    def test_traverse_outgoing(self, object_type, second_object_type):
        lt = LinkTypeService.create(
            TENANT,
            name="places",
            source_object_type_id=str(object_type.id),
            target_object_type_id=str(second_object_type.id),
        )
        src = ObjectService.create(TENANT, str(object_type.id), {"name": "Alice"})
        tgt = ObjectService.create(TENANT, str(second_object_type.id), {"total": 100.0})
        LinkService.create(TENANT, str(lt.id), str(src.id), str(tgt.id))
        results = LinkService.traverse(TENANT, str(src.id), direction="outgoing")
        assert len(results) == 1
        assert results[0]["object_id"] == str(tgt.id)
        assert results[0]["direction"] == "outgoing"
        assert results[0]["link_type"] == "places"

    @pytest.mark.django_db
    def test_traverse_incoming(self, object_type, second_object_type):
        lt = LinkTypeService.create(
            TENANT,
            name="places",
            source_object_type_id=str(object_type.id),
            target_object_type_id=str(second_object_type.id),
        )
        src = ObjectService.create(TENANT, str(object_type.id), {"name": "Alice"})
        tgt = ObjectService.create(TENANT, str(second_object_type.id), {"total": 100.0})
        LinkService.create(TENANT, str(lt.id), str(src.id), str(tgt.id))
        results = LinkService.traverse(TENANT, str(tgt.id), direction="incoming")
        assert len(results) == 1
        assert results[0]["object_id"] == str(src.id)
        assert results[0]["direction"] == "incoming"

    @pytest.mark.django_db
    def test_traverse_both(self, object_type, second_object_type):
        lt = LinkTypeService.create(
            TENANT,
            name="places",
            source_object_type_id=str(object_type.id),
            target_object_type_id=str(second_object_type.id),
        )
        src = ObjectService.create(TENANT, str(object_type.id), {"name": "Alice"})
        tgt = ObjectService.create(TENANT, str(second_object_type.id), {"total": 100.0})
        LinkService.create(TENANT, str(lt.id), str(src.id), str(tgt.id))
        results = LinkService.traverse(TENANT, str(src.id), direction="both")
        assert len(results) >= 1

    @pytest.mark.django_db
    def test_traverse_filter_by_link_type(self, object_type, second_object_type):
        lt1 = LinkTypeService.create(
            TENANT, name="places",
            source_object_type_id=str(object_type.id),
            target_object_type_id=str(second_object_type.id),
        )
        lt2 = LinkTypeService.create(
            TENANT, name="cancels",
            source_object_type_id=str(object_type.id),
            target_object_type_id=str(second_object_type.id),
        )
        src = ObjectService.create(TENANT, str(object_type.id), {"name": "A"})
        tgt1 = ObjectService.create(TENANT, str(second_object_type.id), {"total": 1.0})
        tgt2 = ObjectService.create(TENANT, str(second_object_type.id), {"total": 2.0})
        LinkService.create(TENANT, str(lt1.id), str(src.id), str(tgt1.id))
        LinkService.create(TENANT, str(lt2.id), str(src.id), str(tgt2.id))
        results = LinkService.traverse(
            TENANT, str(src.id), link_type_name="places", direction="outgoing"
        )
        assert len(results) == 1
        assert results[0]["link_type"] == "places"

    @pytest.mark.django_db
    def test_traverse_empty(self, object_type):
        obj = ObjectService.create(TENANT, str(object_type.id), {"name": "Isolated"})
        results = LinkService.traverse(TENANT, str(obj.id))
        assert results == []

    @pytest.mark.django_db
    def test_traverse_multi_hop(self, object_type, second_object_type):
        """Two-hop traversal: A -> B -> C."""
        lt = LinkTypeService.create(
            TENANT, name="next",
            source_object_type_id=str(object_type.id),
            target_object_type_id=str(object_type.id),
        )
        a = ObjectService.create(TENANT, str(object_type.id), {"name": "A"})
        b = ObjectService.create(TENANT, str(object_type.id), {"name": "B"})
        c = ObjectService.create(TENANT, str(object_type.id), {"name": "C"})
        LinkService.create(TENANT, str(lt.id), str(a.id), str(b.id))
        LinkService.create(TENANT, str(lt.id), str(b.id), str(c.id))
        results = LinkService.traverse(TENANT, str(a.id), max_depth=2, direction="outgoing")
        object_ids = {r["object_id"] for r in results}
        assert str(b.id) in object_ids
        assert str(c.id) in object_ids

    @pytest.mark.django_db
    def test_traverse_cycle_no_infinite_loop(self, object_type):
        """Traversal should not loop on cycles."""
        lt = LinkTypeService.create(
            TENANT, name="cycle",
            source_object_type_id=str(object_type.id),
            target_object_type_id=str(object_type.id),
        )
        a = ObjectService.create(TENANT, str(object_type.id), {"name": "A"})
        b = ObjectService.create(TENANT, str(object_type.id), {"name": "B"})
        LinkService.create(TENANT, str(lt.id), str(a.id), str(b.id))
        LinkService.create(TENANT, str(lt.id), str(b.id), str(a.id))
        results = LinkService.traverse(TENANT, str(a.id), max_depth=5, direction="outgoing")
        # Should terminate without error; each node visited once
        assert len(results) == 2
