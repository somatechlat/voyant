"""Workspaces — Django ORM models.

Provides Workspace, WorkspaceMember, WorkspaceAsset, and Comment models
for collaborative workspaces with asset sharing and threaded discussions.
"""

from __future__ import annotations

from django.db import models
from django.utils import timezone as tz

from apps.core.models import TenantModel, UUIDModel


class Workspace(TenantModel, UUIDModel):
    """
    A collaborative workspace that groups members, shared assets, and discussions.
    """

    name = models.CharField(
        max_length=255,
        help_text="Workspace name",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Workspace description",
    )
    owner_id = models.CharField(
        max_length=256,
        db_index=True,
        help_text="User identifier of the workspace owner",
    )
    is_public = models.BooleanField(
        default=False,
        help_text="Whether this workspace is visible to all tenant users",
    )
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text='Tags for categorization: ["analytics", "ml"]',
    )

    class Meta(TenantModel.Meta, UUIDModel.Meta):  # type: ignore[reportIncompatibleVariableOverride]
        db_table = "voyant_workspace"
        verbose_name = "Workspace"
        verbose_name_plural = "Workspaces"
        indexes = [
            models.Index(
                fields=["tenant_id", "owner_id"],
                name="idx_ws_tenant_owner",
            ),
            models.Index(
                fields=["tenant_id", "is_public"],
                name="idx_ws_tenant_public",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} (owner={self.owner_id})"


class WorkspaceMember(TenantModel, UUIDModel):
    """
    Membership record linking a user to a workspace with a specific role.
    """

    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        MEMBER = "member", "Member"
        VIEWER = "viewer", "Viewer"

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="members",
        help_text="Workspace this membership belongs to",
    )
    user_id = models.CharField(
        max_length=256,
        db_index=True,
        help_text="User identifier",
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
        db_index=True,
        help_text="Role of the user in the workspace",
    )
    joined_at = models.DateTimeField(
        default=tz.now,
        help_text="When the user joined the workspace",
    )

    class Meta(TenantModel.Meta, UUIDModel.Meta):  # type: ignore[reportIncompatibleVariableOverride]
        db_table = "voyant_workspace_member"
        verbose_name = "Workspace Member"
        verbose_name_plural = "Workspace Members"
        unique_together = [("workspace", "user_id")]
        indexes = [
            models.Index(
                fields=["tenant_id", "user_id"],
                name="idx_wsmember_tenant_user",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} ({self.role}) in {self.workspace_id}"


class WorkspaceAsset(TenantModel, UUIDModel):
    """
    An asset (dashboard, dataset, pipeline, etc.) shared into a workspace.
    """

    class AssetType(models.TextChoices):
        DASHBOARD = "dashboard", "Dashboard"
        DATASET = "dataset", "Dataset"
        PIPELINE = "pipeline", "Pipeline"
        MODEL = "model", "Model"
        QUERY = "query", "Query"

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="assets",
        help_text="Workspace this asset is shared in",
    )
    asset_type = models.CharField(
        max_length=30,
        choices=AssetType.choices,
        db_index=True,
        help_text="Type of shared asset",
    )
    asset_id = models.CharField(
        max_length=256,
        db_index=True,
        help_text="Identifier of the shared asset",
    )
    shared_by = models.CharField(
        max_length=256,
        help_text="User who shared the asset",
    )
    shared_at = models.DateTimeField(
        default=tz.now,
        help_text="When the asset was shared",
    )

    class Meta(TenantModel.Meta, UUIDModel.Meta):  # type: ignore[reportIncompatibleVariableOverride]
        db_table = "voyant_workspace_asset"
        verbose_name = "Workspace Asset"
        verbose_name_plural = "Workspace Assets"
        unique_together = [("workspace", "asset_type", "asset_id")]
        indexes = [
            models.Index(
                fields=["tenant_id", "workspace", "asset_type"],
                name="idx_wsasset_tenant_ws_type",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.asset_type}:{self.asset_id} in {self.workspace_id}"


class Comment(TenantModel, UUIDModel):
    """
    A comment on a workspace or on a specific asset, with optional threading
    and @mention support.
    """

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="comments",
        help_text="Workspace context (nullable for standalone comments)",
    )
    asset_type = models.CharField(
        max_length=30,
        blank=True,
        default="",
        db_index=True,
        help_text="Type of asset being commented on (blank = workspace-level)",
    )
    asset_id = models.CharField(
        max_length=256,
        blank=True,
        default="",
        db_index=True,
        help_text="Identifier of the asset being commented on",
    )
    content = models.TextField(
        help_text="Comment text content",
    )
    parent_comment = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies",
        help_text="Parent comment for threaded replies (null = top-level)",
    )
    mentions = models.JSONField(
        default=list,
        blank=True,
        help_text='List of mentioned user IDs: ["user1", "user2"]',
    )
    created_by = models.CharField(
        max_length=256,
        db_index=True,
        help_text="User who created the comment",
    )

    class Meta(TenantModel.Meta, UUIDModel.Meta):  # type: ignore[reportIncompatibleVariableOverride]
        db_table = "voyant_comment"
        verbose_name = "Comment"
        verbose_name_plural = "Comments"
        ordering = ["created_at"]
        indexes = [
            models.Index(
                fields=["tenant_id", "workspace", "asset_type", "asset_id"],
                name="idx_comment_tenant_ws_asset",
            ),
            models.Index(
                fields=["tenant_id", "created_by"],
                name="idx_comment_tenant_creator",
            ),
        ]

    def __str__(self) -> str:
        ctx = f"ws={self.workspace_id}" if self.workspace_id else "standalone"
        return f"Comment by {self.created_by} ({ctx})"
