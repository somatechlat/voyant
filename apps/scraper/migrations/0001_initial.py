# Generated Django migration for Voyant Scraper

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ScrapeJob",
            fields=[
                (
                    "job_id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("tenant_id", models.CharField(db_index=True, max_length=128)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("queued", "Queued"),
                            ("running", "Running"),
                            ("succeeded", "Succeeded"),
                            ("failed", "Failed"),
                            ("cancelled", "Cancelled"),
                            ("partial", "Partial Success"),
                        ],
                        db_index=True,
                        default="queued",
                        max_length=64,
                    ),
                ),
                ("urls", models.JSONField(help_text="List of URLs to scrape")),
                (
                    "selectors",
                    models.JSONField(
                        blank=True,
                        help_text="Agent-provided CSS/XPath selectors",
                        null=True,
                    ),
                ),
                (
                    "options",
                    models.JSONField(
                        default=dict,
                        help_text="Execution options: engine, timeout, scroll, ocr, transcribe",
                    ),
                ),
                ("pages_fetched", models.IntegerField(default=0)),
                ("bytes_processed", models.BigIntegerField(default=0)),
                ("artifact_count", models.IntegerField(default=0)),
                ("error_count", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True)),
                ("retry_count", models.IntegerField(default=0)),
            ],
            options={
                "db_table": "voyant_scrape_job",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="ScrapeArtifact",
            fields=[
                (
                    "artifact_id",
                    models.CharField(max_length=512, primary_key=True, serialize=False),
                ),
                (
                    "artifact_type",
                    models.CharField(
                        choices=[
                            ("html", "HTML"),
                            ("json", "JSON"),
                            ("csv", "CSV"),
                            ("image", "Image"),
                            ("video", "Video"),
                            ("pdf", "PDF"),
                            ("text", "Text"),
                            ("audio", "Audio"),
                            ("ocr", "OCR Text"),
                            ("transcript", "Transcript"),
                        ],
                        max_length=64,
                    ),
                ),
                ("format", models.CharField(max_length=32)),
                (
                    "storage_path",
                    models.CharField(help_text="MinIO/S3 object key", max_length=512),
                ),
                (
                    "content_hash",
                    models.CharField(blank=True, max_length=128, null=True),
                ),
                ("size_bytes", models.BigIntegerField(blank=True, null=True)),
                ("source_url", models.URLField(blank=True, max_length=2048, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "job",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="artifacts",
                        to="scraper.scrapejob",
                    ),
                ),
            ],
            options={
                "db_table": "voyant_scrape_artifact",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="scrapejob",
            index=models.Index(
                fields=["tenant_id", "status"], name="voyant_scra_tenant__e7c5e0_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="scrapejob",
            index=models.Index(
                fields=["created_at"], name="voyant_scra_created_7c2346_idx"
            ),
        ),
    ]
