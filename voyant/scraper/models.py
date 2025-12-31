"""
Voyant Scraper - Django ORM Models

ScrapeJob: Web scraping job record
ScrapeArtifact: Artifact produced by scraping job
"""
import uuid
from django.db import models


class ScrapeJob(models.Model):
    """Web scraping job record."""
    
    class Status(models.TextChoices):
        QUEUED = 'queued', 'Queued'
        RUNNING = 'running', 'Running'
        SUCCEEDED = 'succeeded', 'Succeeded'
        FAILED = 'failed', 'Failed'
        CANCELLED = 'cancelled', 'Cancelled'
    
    job_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.CharField(max_length=128, db_index=True)
    status = models.CharField(
        max_length=64, 
        choices=Status.choices, 
        default=Status.QUEUED,
        db_index=True
    )
    
    # Input
    urls = models.JSONField(help_text="List of URLs to scrape")
    llm_prompt = models.TextField(blank=True, help_text="Optional LLM extraction hints")
    options = models.JSONField(default=dict, help_text="Scraping options: ocr, media, engine")
    
    # Progress
    pages_fetched = models.IntegerField(default=0)
    bytes_processed = models.BigIntegerField(default=0)
    ocr_success_rate = models.FloatField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    
    # Error handling
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'voyant_scrape_job'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant_id', 'status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"ScrapeJob({self.job_id}) - {self.status}"


class ScrapeArtifact(models.Model):
    """Artifact produced by scraping job."""
    
    class ArtifactType(models.TextChoices):
        HTML = 'html', 'HTML'
        JSON = 'json', 'JSON'
        CSV = 'csv', 'CSV'
        IMAGE = 'image', 'Image'
        VIDEO = 'video', 'Video'
        PDF = 'pdf', 'PDF'
        TEXT = 'text', 'Text'
        AUDIO = 'audio', 'Audio'
    
    artifact_id = models.CharField(max_length=512, primary_key=True)
    job = models.ForeignKey(
        ScrapeJob, 
        on_delete=models.CASCADE, 
        related_name='artifacts'
    )
    artifact_type = models.CharField(max_length=64, choices=ArtifactType.choices)
    format = models.CharField(max_length=32)
    storage_path = models.CharField(max_length=512, help_text="MinIO/S3 object key")
    size_bytes = models.BigIntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'voyant_scrape_artifact'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"ScrapeArtifact({self.artifact_id}) - {self.artifact_type}"
