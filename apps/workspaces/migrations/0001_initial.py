"""Create workspace, member, asset, and comment models."""

import uuid

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Workspace",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier (UUID)",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
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
                        db_index=True,
                        help_text="Timestamp when the record was last updated",
                    ),
                ),
                (
                    "realm",
                    models.CharField(
                        db_index=True,
                        default="default",
                        help_text="Realm identifier for RBAC realm isolation",
                        max_length=64,
                    ),
                ),
                (
                    "tenant_id",
                    models.CharField(
                        db_index=True,
                        help_text="Tenant identifier for multi-tenancy isolation",
                        max_length=128,
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="Workspace name",
                        max_length=255,
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Workspace description",
                    ),
                ),
                (
                    "owner_id",
                    models.CharField(
                        db_index=True,
                        help_text="User identifier of the workspace owner",
                        max_length=256,
                    ),
                ),
                (
                    "is_public",
                    models.BooleanField(
                        default=False,
                        help_text="Whether this workspace is visible to all tenant users",
                    ),
                ),
                (
                    "tags",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text='Tags for categorization: ["analytics", "ml"]',
                    ),
                ),
            ],
            options={
                "verbose_name": "Workspace",
                "verbose_name_plural": "Workspaces",
                "db_table": "voyant_workspace",
                "abstract": False,
                "indexes": [
                    models.Index(
                        fields=["tenant_id", "-created_at"],
                        name="idx_ws_tenant_created",
                    ),
                    models.Index(
                        fields=["realm", "tenant_id", "created_at"],
                        name="idx_ws_realm_tenant",
                    ),
                    models.Index(
                        fields=["tenant_id", "owner_id"],
                        name="idx_ws_tenant_owner",
                    ),
                    models.Index(
                        fields=["tenant_id", "is_public"],
                        name="idx_ws_tenant_public",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="WorkspaceMember",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier (UUID)",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
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
                        db_index=True,
                        help_text="Timestamp when the record was last updated",
                    ),
                ),
                (
                    "realm",
                    models.CharField(
                        db_index=True,
                        default="default",
                        help_text="Realm identifier for RBAC realm isolation",
                        max_length=64,
                    ),
                ),
                (
                    "tenant_id",
                    models.CharField(
                        db_index=True,
                        help_text="Tenant identifier for multi-tenancy isolation",
                        max_length=128,
                    ),
                ),
                (
                    "workspace",
                    models.ForeignKey(
                        help_text="Workspace this membership belongs to",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="members",
                        to="workspaces.workspace",
                    ),
                ),
                (
                    "user_id",
                    models.CharField(
                        db_index=True,
                        help_text="User identifier",
                        max_length=256,
                    ),
                ),
                (
                    "role",
                    models.CharField(
                        choices=[
                            ("owner", "Owner"),
                            ("admin", "Admin"),
                            ("member", "Member"),
                            ("viewer", "Viewer"),
                        ],
                        db_index=True,
                        default="member",
                        help_text="Role of the user in the workspace",
                        max_length=20,
                    ),
                ),
                (
                    "joined_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now,
                        help_text="When the user joined the workspace",
                    ),
                ),
            ],
            options={
                "verbose_name": "Workspace Member",
                "verbose_name_plural": "Workspace Members",
                "db_table": "voyant_workspace_member",
                "abstract": False,
                "unique_together": {("workspace", "user_id")},
                "indexes": [
                    models.Index(
                        fields=["tenant_id", "-created_at"],
                        name="idx_wsm_tenant_created",
                    ),
                    models.Index(
                        fields=["realm", "tenant_id", "created_at"],
                        name="idx_wsm_realm_tenant",
                    ),
                    models.Index(
                        fields=["tenant_id", "user_id"],
                        name="idx_wsmember_tenant_user",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="WorkspaceAsset",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier (UUID)",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
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
                        db_index=True,
                        help_text="Timestamp when the record was last updated",
                    ),
                ),
                (
                    "realm",
                    models.CharField(
                        db_index=True,
                        default="default",
                        help_text="Realm identifier for RBAC realm isolation",
                        max_length=64,
                    ),
                ),
                (
                    "tenant_id",
                    models.CharField(
                        db_index=True,
                        help_text="Tenant identifier for multi-tenancy isolation",
                        max_length=128,
                    ),
                ),
                (
                    "workspace",
                    models.ForeignKey(
                        help_text="Workspace this asset is shared in",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assets",
                        to="workspaces.workspace",
                    ),
                ),
                (
                    "asset_type",
                    models.CharField(
                        choices=[
                            ("dashboard", "Dashboard"),
                            ("dataset", "Dataset"),
                            ("pipeline", "Pipeline"),
                            ("model", "Model"),
                            ("query", "Query"),
                        ],
                        db_index=True,
                        help_text="Type of shared asset",
                        max_length=30,
                    ),
                ),
                (
                    "asset_id",
                    models.CharField(
                        db_index=True,
                        help_text="Identifier of the shared asset",
                        max_length=256,
                    ),
                ),
                (
                    "shared_by",
                    models.CharField(
                        help_text="User who shared the asset",
                        max_length=256,
                    ),
                ),
                (
                    "shared_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now,
                        help_text="When the asset was shared",
                    ),
                ),
            ],
            options={
                "verbose_name": "Workspace Asset",
                "verbose_name_plural": "Workspace Assets",
                "db_table": "voyant_workspace_asset",
                "abstract": False,
                "unique_together": {("workspace", "asset_type", "asset_id")},
                "indexes": [
                    models.Index(
                        fields=["tenant_id", "-created_at"],
                        name="idx_wsa_tenant_created",
                    ),
                    models.Index(
                        fields=["realm", "tenant_id", "created_at"],
                        name="idx_wsa_realm_tenant",
                    ),
                    models.Index(
                        fields=["tenant_id", "workspace", "asset_type"],
                        name="idx_wsasset_tenant_ws_type",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="Comment",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier (UUID)",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
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
                        db_index=True,
                        help_text="Timestamp when the record was last updated",
                    ),
                ),
                (
                    "realm",
                    models.CharField(
                        db_index=True,
                        default="default",
                        help_text="Realm identifier for RBAC realm isolation",
                        max_length=64,
                    ),
                ),
                (
                    "tenant_id",
                    models.CharField(
                        db_index=True,
                        help_text="Tenant identifier for multi-tenancy isolation",
                        max_length=128,
                    ),
                ),
                (
                    "workspace",
                    models.ForeignKey(
                        blank=True,
                        help_text="Workspace context (nullable for standalone comments)",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="comments",
                        to="workspaces.workspace",
                    ),
                ),
                (
                    "asset_type",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        default="",
                        help_text="Type of asset being commented on (blank = workspace-level)",
                        max_length=30,
                    ),
                ),
                (
                    "asset_id",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        default="",
                        help_text="Identifier of the asset being commented on",
                        max_length=256,
                    ),
                ),
                (
                    "content",
                    models.TextField(
                        help_text="Comment text content",
                    ),
                ),
                (
                    "parent_comment",
                    models.ForeignKey(
                        blank=True,
                        help_text="Parent comment for threaded replies (null = top-level)",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="replies",
                        to="workspaces.comment",
                    ),
                ),
                (
                    "mentions",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text='List of mentioned user IDs: ["user1", "user2"]',
                    ),
                ),
                (
                    "created_by",
                    models.CharField(
                        db_index=True,
                        help_text="User who created the comment",
                        max_length=256,
                    ),
                ),
            ],
            options={
                "verbose_name": "Comment",
                "verbose_name_plural": "Comments",
                "db_table": "voyant_comment",
                "ordering": ["created_at"],
                "abstract": False,
                "indexes": [
                    models.Index(
                        fields=["tenant_id", "created_at"],
                        name="idx_comment_tenant_created",
                    ),
                    models.Index(
                        fields=["realm", "tenant_id", "created_at"],
                        name="idx_comment_realm_tenant",
                    ),
                    models.Index(
                        fields=["tenant_id", "workspace", "asset_type", "asset_id"],
                        name="idx_comment_tenant_ws_asset",
                    ),
                    models.Index(
                        fields=["tenant_id", "created_by"],
                        name="idx_comment_tenant_creator",
                    ),
                ],
            },
        ),
    ]
