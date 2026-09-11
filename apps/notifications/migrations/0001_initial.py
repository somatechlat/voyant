"""Create notification and notification preference models."""

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Notification",
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
                    "user_id",
                    models.CharField(
                        db_index=True,
                        help_text="Recipient user identifier",
                        max_length=256,
                    ),
                ),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("information", "Information"),
                            ("warning", "Warning"),
                            ("error", "Error"),
                            ("success", "Success"),
                        ],
                        db_index=True,
                        default="information",
                        help_text="Notification severity/type",
                        max_length=20,
                    ),
                ),
                (
                    "title",
                    models.CharField(
                        help_text="Short notification title",
                        max_length=255,
                    ),
                ),
                (
                    "message",
                    models.TextField(
                        help_text="Full notification body",
                    ),
                ),
                (
                    "resource_type",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        default="",
                        help_text="Type of related resource (e.g. 'job', 'pipeline')",
                        max_length=64,
                    ),
                ),
                (
                    "resource_id",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        default="",
                        help_text="Identifier of the related resource",
                        max_length=256,
                    ),
                ),
                (
                    "is_read",
                    models.BooleanField(
                        db_index=True,
                        default=False,
                        help_text="Whether the user has read this notification",
                    ),
                ),
                (
                    "read_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="Timestamp when the notification was marked as read",
                        null=True,
                    ),
                ),
            ],
            options={
                "verbose_name": "Notification",
                "verbose_name_plural": "Notifications",
                "db_table": "voyant_notification",
                "ordering": ["-created_at"],
                "abstract": False,
                "indexes": [
                    models.Index(
                        fields=["tenant_id", "-created_at"],
                        name="idx_notif_tenant_created",
                    ),
                    models.Index(
                        fields=["realm", "tenant_id", "created_at"],
                        name="idx_notif_realm_tenant",
                    ),
                    models.Index(
                        fields=["tenant_id", "user_id", "is_read"],
                        name="idx_notif_tenant_user_read",
                    ),
                    models.Index(
                        fields=["tenant_id", "user_id", "-created_at"],
                        name="idx_notif_tenant_user_time",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="NotificationPreference",
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
                    "user_id",
                    models.CharField(
                        db_index=True,
                        help_text="User identifier",
                        max_length=256,
                    ),
                ),
                (
                    "event_type",
                    models.CharField(
                        db_index=True,
                        help_text="Event type this preference applies to (e.g. 'job.completed')",
                        max_length=128,
                    ),
                ),
                (
                    "channel",
                    models.CharField(
                        choices=[
                            ("in_app", "In-App"),
                            ("email", "Email"),
                            ("slack", "Slack"),
                        ],
                        default="in_app",
                        help_text="Delivery channel",
                        max_length=20,
                    ),
                ),
                (
                    "enabled",
                    models.BooleanField(
                        default=True,
                        help_text="Whether notifications for this event+channel are enabled",
                    ),
                ),
            ],
            options={
                "verbose_name": "Notification Preference",
                "verbose_name_plural": "Notification Preferences",
                "db_table": "voyant_notification_preference",
                "abstract": False,
                "unique_together": {
                    ("tenant_id", "user_id", "event_type", "channel")
                },
            },
        ),
    ]
