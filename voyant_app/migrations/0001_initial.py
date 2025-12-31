from django.db import migrations, models
import uuid


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Source",
            fields=[
                (
                    "source_id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("tenant_id", models.CharField(db_index=True, max_length=128)),
                ("name", models.CharField(max_length=255)),
                ("source_type", models.CharField(max_length=128)),
                ("status", models.CharField(default="pending", max_length=64)),
                ("connection_config", models.JSONField()),
                ("credentials", models.JSONField(blank=True, null=True)),
                ("sync_schedule", models.CharField(blank=True, max_length=128, null=True)),
                ("datahub_urn", models.CharField(blank=True, max_length=512, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="Job",
            fields=[
                (
                    "job_id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("tenant_id", models.CharField(db_index=True, max_length=128)),
                ("job_type", models.CharField(db_index=True, max_length=64)),
                ("source_id", models.CharField(blank=True, max_length=36, null=True)),
                ("soma_session_id", models.CharField(blank=True, max_length=128, null=True)),
                ("soma_task_id", models.CharField(blank=True, max_length=64, null=True)),
                ("status", models.CharField(default="queued", max_length=64)),
                ("progress", models.IntegerField(default=0)),
                ("parameters", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("result_summary", models.JSONField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name="PresetJob",
            fields=[
                (
                    "job_id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("tenant_id", models.CharField(db_index=True, max_length=128)),
                ("preset_name", models.CharField(db_index=True, max_length=255)),
                ("source_id", models.CharField(max_length=36)),
                ("parameters", models.JSONField(default=dict)),
                ("status", models.CharField(default="queued", max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="Artifact",
            fields=[
                ("artifact_id", models.CharField(max_length=512, primary_key=True, serialize=False)),
                ("job_id", models.CharField(db_index=True, max_length=36)),
                ("tenant_id", models.CharField(db_index=True, max_length=128)),
                ("artifact_type", models.CharField(max_length=128)),
                ("format", models.CharField(max_length=32)),
                ("storage_path", models.CharField(max_length=512)),
                ("size_bytes", models.IntegerField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
