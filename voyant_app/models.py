import uuid

from django.db import models


class Source(models.Model):
    source_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.CharField(max_length=128, db_index=True)
    name = models.CharField(max_length=255)
    source_type = models.CharField(max_length=128)
    status = models.CharField(max_length=64, default="pending")
    connection_config = models.JSONField()
    credentials = models.JSONField(null=True, blank=True)
    sync_schedule = models.CharField(max_length=128, null=True, blank=True)
    datahub_urn = models.CharField(max_length=512, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Job(models.Model):
    job_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.CharField(max_length=128, db_index=True)
    job_type = models.CharField(max_length=64, db_index=True)
    source_id = models.CharField(max_length=36, null=True, blank=True)
    soma_session_id = models.CharField(max_length=128, null=True, blank=True)
    soma_task_id = models.CharField(max_length=64, null=True, blank=True)
    status = models.CharField(max_length=64, default="queued")
    progress = models.IntegerField(default=0)
    parameters = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    result_summary = models.JSONField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)


class PresetJob(models.Model):
    job_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.CharField(max_length=128, db_index=True)
    preset_name = models.CharField(max_length=255, db_index=True)
    source_id = models.CharField(max_length=36)
    parameters = models.JSONField(default=dict)
    status = models.CharField(max_length=64, default="queued")
    created_at = models.DateTimeField(auto_now_add=True)


class Artifact(models.Model):
    artifact_id = models.CharField(max_length=512, primary_key=True)
    job_id = models.CharField(max_length=36, db_index=True)
    tenant_id = models.CharField(max_length=128, db_index=True)
    artifact_type = models.CharField(max_length=128)
    format = models.CharField(max_length=32)
    storage_path = models.CharField(max_length=512)
    size_bytes = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
