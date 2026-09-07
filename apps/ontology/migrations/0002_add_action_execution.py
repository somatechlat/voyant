# Generated manually — adds ActionExecution model for action audit trail.

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ontology", "0001_add_v4_ontology_models"),
    ]

    operations = [
        migrations.CreateModel(
            name="ActionExecution",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="Timestamp when the record was created",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        help_text="Timestamp when the record was last updated",
                    ),
                ),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "realm",
                    models.CharField(
                        db_index=True,
                        default="default",
                        max_length=64,
                        help_text="Realm identifier for RBAC realm isolation",
                    ),
                ),
                (
                    "tenant_id",
                    models.CharField(
                        db_index=True,
                        max_length=128,
                        help_text="Tenant identifier for multi-tenancy isolation",
                    ),
                ),
                (
                    "actor",
                    models.CharField(
                        max_length=256,
                        blank=True,
                        default="",
                        help_text="Who executed this action",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("success", "Success"),
                            ("failed", "Failed"),
                            ("undone", "Undone"),
                        ],
                        db_index=True,
                        default="success",
                        max_length=20,
                    ),
                ),
                (
                    "previous_values",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Object properties before action execution",
                    ),
                ),
                (
                    "changes",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Changes applied by this action",
                    ),
                ),
                (
                    "params",
                    models.JSONField(
                        default=dict,
                        blank=True,
                        help_text="Parameters passed to the action",
                    ),
                ),
                (
                    "action_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="executions",
                        to="ontology.actiontype",
                    ),
                ),
                (
                    "target_object",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="action_executions",
                        to="ontology.object",
                    ),
                ),
            ],
            options={
                "db_table": "ontology_action_execution",
                "indexes": [
                    models.Index(
                        fields=["tenant_id", "action_type_id"],
                        name="idx_exec_tenant_action",
                    ),
                    models.Index(
                        fields=["tenant_id", "target_object_id"],
                        name="idx_exec_tenant_obj",
                    ),
                ],
            },
        ),
    ]
