"""
Voyant Scraper - Django ORM Models

ScrapeJob: Pure execution job record (no LLM)
ScrapeArtifact: Artifact produced by scraping
ScrapeTemplate: Pre-built scraping configurations (v4.0)
ScrapeWorkflow: Multi-step workflow definitions
ScrapeStep: Individual steps within a workflow
ScrapeSchedule: Cron scheduling for tasks
ScrapeExport: Export configuration for task results
ScrapeRun: Execution run record for a task
ScrapeProxy: Proxy pool configuration
ScrapeFingerprint: Browser fingerprint profiles
AgentSkill: Agent skill definitions for scraper automation
"""

import uuid

from django.db import models

from apps.core.models import TenantModel, UUIDModel


class ScrapeJob(models.Model):
    """
    Web scraping job record.

    Pure execution model - Agent provides all parameters.
    NO LLM integration.
    """

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"
        PARTIAL = "partial", "Partial Success"

    job_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.CharField(max_length=128, db_index=True)
    status = models.CharField(
        max_length=64, choices=Status.choices, default=Status.QUEUED, db_index=True
    )

    # Input (Agent-provided)
    urls = models.JSONField(help_text="List of URLs to scrape")
    selectors = models.JSONField(
        null=True, blank=True, help_text="Agent-provided CSS/XPath selectors"
    )
    options = models.JSONField(
        default=dict,
        help_text="Execution options: engine, timeout, scroll, ocr, transcribe",
    )

    # Progress
    pages_fetched = models.IntegerField(default=0)
    bytes_processed = models.BigIntegerField(default=0)
    artifact_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    # Error handling
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)

    class Meta:
        db_table = "voyant_scrape_job"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"ScrapeJob({self.job_id}) - {self.status}"


class ScrapeArtifact(models.Model):
    """
    Artifact produced by scraping job.

    Stores raw data extracted by pure execution tools.
    """

    class ArtifactType(models.TextChoices):
        HTML = "html", "HTML"
        JSON = "json", "JSON"
        CSV = "csv", "CSV"
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"
        PDF = "pdf", "PDF"
        TEXT = "text", "Text"
        AUDIO = "audio", "Audio"
        OCR = "ocr", "OCR Text"
        TRANSCRIPT = "transcript", "Transcript"

    artifact_id = models.CharField(max_length=512, primary_key=True)
    job = models.ForeignKey(
        ScrapeJob, on_delete=models.CASCADE, related_name="artifacts"
    )
    artifact_type = models.CharField(max_length=64, choices=ArtifactType.choices)
    format = models.CharField(max_length=32)
    storage_path = models.CharField(max_length=512, help_text="MinIO/S3 object key")
    content_hash = models.CharField(max_length=128, null=True, blank=True)
    size_bytes = models.BigIntegerField(null=True, blank=True)
    source_url = models.URLField(max_length=2048, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "voyant_scrape_artifact"
        ordering = ["-created_at"]

    def __str__(self):
        return f"ScrapeArtifact({self.artifact_id}) - {self.artifact_type}"


class ScrapeTemplate(models.Model):
    """Pre-built scraping template for a specific website or use case.

    Templates define reusable scraping configurations that can be executed
    with parameter substitution. Part of the Scraper Octopus v4.0 system.
    """

    CATEGORY_CHOICES = [
        ("ecommerce", "E-Commerce"),
        ("social", "Social Media"),
        ("maps", "Maps"),
        ("news", "News"),
        ("finance", "Finance"),
        ("jobs", "Jobs"),
        ("realestate", "Real Estate"),
        ("travel", "Travel"),
        ("education", "Education"),
        ("developer", "Developer"),
        ("leadgen", "Lead Generation"),
        ("directory", "Directory"),
        ("search", "Search Engine"),
        ("universal", "Universal"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.CharField(max_length=128, default="system", db_index=True)
    name = models.CharField(max_length=255)
    site_pattern = models.CharField(max_length=500, help_text="URL pattern or domain")
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, db_index=True)
    description = models.TextField(blank=True, default="")
    language = models.CharField(max_length=10, default="en")
    status = models.CharField(max_length=20, default="active", db_index=True)

    # Scraping config
    engine = models.CharField(max_length=20, default="playwright")
    selectors = models.JSONField(default=dict)
    workflow = models.JSONField(default=list)
    options = models.JSONField(default=dict)

    # Parameterization
    parameters = models.JSONField(default=list)

    # Output
    output_fields = models.JSONField(default=list)

    # Stats
    use_count = models.PositiveIntegerField(default=0)
    success_rate = models.FloatField(default=0.0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "scraper_template"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "category"]),
            models.Index(fields=["tenant_id", "status"]),
            models.Index(fields=["site_pattern"]),
        ]

    def __str__(self):
        return f"Template({self.name} [{self.category}])"


# ============================================================================
# v4.0 Scraper Octopus — New Models
# ============================================================================


class ScrapeWorkflow(UUIDModel, TenantModel):
    """Multi-step workflow definition for complex scraping tasks.

    Defines a reusable sequence of steps with input/output schemas.
    Part of the Scraper Octopus v4.0 visual builder system.
    """

    name = models.CharField(max_length=255, help_text="Workflow name")
    description = models.TextField(blank=True, default="")
    steps = models.JSONField(
        default=list,
        help_text="Ordered list of step definitions (JSON array)",
    )
    input_schema = models.JSONField(
        default=dict,
        help_text="JSON Schema defining expected input parameters",
    )
    output_schema = models.JSONField(
        default=dict,
        help_text="JSON Schema defining output structure",
    )

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
        db_table = "voyant_scrape_workflow"
        ordering = ["-created_at"]

    def __str__(self):
        return f"ScrapeWorkflow({self.id}) - {self.name}"


class ScrapeStep(UUIDModel):
    """Individual step within a ScrapeWorkflow.

    Each step defines a single action (navigate, click, extract, etc.)
    with its configuration and optional wait conditions.
    """

    class StepType(models.TextChoices):
        NAVIGATE = "navigate", "Navigate"
        CLICK = "click", "Click"
        SCROLL = "scroll", "Scroll"
        WAIT = "wait", "Wait"
        EXTRACT = "extract", "Extract"
        ENTER_TEXT = "enter_text", "Enter Text"
        HOVER = "hover", "Hover"
        SCREENSHOT = "screenshot", "Screenshot"
        LOOP = "loop", "Loop"
        CONDITION = "condition", "Condition"
        CLOSE_POPUP = "close_popup", "Close Popup"
        BACK = "back", "Back"
        NEW_TAB = "new_tab", "New Tab"
        DOWNLOAD = "download", "Download"

    workflow = models.ForeignKey(
        ScrapeWorkflow,
        on_delete=models.CASCADE,
        related_name="step_records",
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Execution order within the workflow",
    )
    step_type = models.CharField(
        max_length=32,
        choices=StepType.choices,
        help_text="Type of action this step performs",
    )
    selector = models.CharField(
        max_length=1024,
        blank=True,
        default="",
        help_text="CSS selector or XPath for the target element",
    )
    action = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Action identifier or label for this step",
    )
    wait_condition = models.CharField(
        max_length=512,
        blank=True,
        default="",
        help_text="Condition to wait for before executing (CSS selector or timeout)",
    )
    options = models.JSONField(
        default=dict,
        help_text="Step-specific configuration (e.g., wait_ms, times, text)",
    )

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
        db_table = "voyant_scrape_step"
        ordering = ["workflow", "order"]

    def __str__(self):
        return f"ScrapeStep({self.id}) [{self.step_type}] order={self.order}"


class ScrapeSchedule(UUIDModel, TenantModel):
    """Cron-based scheduling configuration for a scrape task.

    Enables recurring execution of ScrapeJobs on a defined schedule.
    """

    task = models.ForeignKey(
        "scraper.ScrapeJob",
        on_delete=models.CASCADE,
        related_name="schedules",
    )
    cron_expr = models.CharField(
        max_length=128,
        help_text="Cron expression (e.g., '0 8 * * *' for daily at 8am)",
    )
    timezone = models.CharField(
        max_length=64,
        default="UTC",
        help_text="Timezone for cron schedule (e.g., 'America/New_York')",
    )
    enabled = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this schedule is active",
    )

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
        db_table = "voyant_scrape_schedule"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["enabled", "-created_at"]),
        ]

    def __str__(self):
        return f"ScrapeSchedule({self.id}) cron={self.cron_expr} enabled={self.enabled}"


class ScrapeExport(UUIDModel, TenantModel):
    """Export configuration for scrape task results.

    Defines how and where extracted data should be delivered.
    """

    class ExportFormat(models.TextChoices):
        JSON = "json", "JSON"
        CSV = "csv", "CSV"
        XLSX = "xlsx", "XLSX"
        XML = "xml", "XML"
        JSONL = "jsonl", "JSONL"
        PARQUET = "parquet", "Parquet"

    task = models.ForeignKey(
        "scraper.ScrapeJob",
        on_delete=models.CASCADE,
        related_name="exports",
    )
    format = models.CharField(
        max_length=16,
        choices=ExportFormat.choices,
        default=ExportFormat.JSON,
        help_text="Export file format",
    )
    destination = models.CharField(
        max_length=1024,
        help_text="Export destination (S3 path, webhook URL, file path)",
    )
    auto_export = models.BooleanField(
        default=False,
        help_text="Automatically export after each task run",
    )

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
        db_table = "voyant_scrape_export"
        ordering = ["-created_at"]

    def __str__(self):
        return f"ScrapeExport({self.id}) format={self.format} dest={self.destination}"


class ScrapeRun(UUIDModel, TenantModel):
    """Execution run record for a scrape task.

    Tracks individual execution runs with status, metrics, and distributed tracing.
    """

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"
        TIMEOUT = "timeout", "Timeout"

    task = models.ForeignKey(
        "scraper.ScrapeJob",
        on_delete=models.CASCADE,
        related_name="runs",
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.QUEUED,
        db_index=True,
    )
    rows_extracted = models.PositiveIntegerField(
        default=0,
        help_text="Number of data rows extracted in this run",
    )
    duration_ms = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Total execution duration in milliseconds",
    )
    trace_id = models.CharField(
        max_length=128,
        blank=True,
        default="",
        db_index=True,
        help_text="Distributed tracing ID (e.g., OpenTelemetry trace ID)",
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this run actually started executing",
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this run completed (success, failure, or cancellation)",
    )

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
        db_table = "voyant_scrape_run"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["task", "-created_at"]),
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["trace_id"]),
        ]

    def __str__(self):
        return f"ScrapeRun({self.id}) task={self.task_id} status={self.status}"  # type: ignore[attr-defined]


class ScrapeProxy(UUIDModel, TenantModel):
    """Proxy pool configuration for anti-bot evasion.

    Manages proxy endpoints, providers, and rotation strategies.
    """

    class ProxyType(models.TextChoices):
        RESIDENTIAL = "residential", "Residential"
        DATACENTER = "datacenter", "Datacenter"
        MOBILE = "mobile", "Mobile"
        ISP = "isp", "ISP"

    class RotationStrategy(models.TextChoices):
        PER_REQUEST = "per_request", "Per Request"
        SESSION = "session", "Session-Based"
        STICKY = "sticky", "Sticky"

    proxy_type = models.CharField(
        max_length=32,
        choices=ProxyType.choices,
        default=ProxyType.RESIDENTIAL,
        db_index=True,
    )
    provider = models.CharField(
        max_length=128,
        help_text="Proxy provider (e.g., brightdata, oxylabs, smartproxy)",
    )
    endpoints = models.JSONField(
        default=list,
        help_text="List of proxy gateway URLs",
    )
    rotation_strategy = models.CharField(
        max_length=32,
        choices=RotationStrategy.choices,
        default=RotationStrategy.PER_REQUEST,
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this proxy configuration is currently active",
    )

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
        db_table = "voyant_scrape_proxy"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["proxy_type", "is_active"]),
            models.Index(fields=["provider", "is_active"]),
        ]

    def __str__(self):
        return f"ScrapeProxy({self.id}) provider={self.provider} type={self.proxy_type}"


class ScrapeFingerprint(UUIDModel, TenantModel):
    """Browser fingerprint profile for anti-detection.

    Stores a specific browser fingerprint configuration that can be applied
    to Playwright contexts to avoid bot detection.
    """

    user_agent = models.TextField(
        help_text="User-Agent string for the browser context",
    )
    viewport_width = models.PositiveIntegerField(
        default=1920,
        help_text="Browser viewport width in pixels",
    )
    viewport_height = models.PositiveIntegerField(
        default=1080,
        help_text="Browser viewport height in pixels",
    )
    webgl_vendor = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="WebGL vendor string (e.g., 'Google Inc. (NVIDIA)')",
    )
    webgl_renderer = models.TextField(
        blank=True,
        default="",
        help_text="WebGL renderer string (e.g., 'ANGLE (NVIDIA GeForce GTX 1080 ...)')",
    )

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
        db_table = "voyant_scrape_fingerprint"
        ordering = ["-created_at"]

    def __str__(self):
        return f"ScrapeFingerprint({self.id}) viewport={self.viewport_width}x{self.viewport_height}"


class AgentSkill(UUIDModel, TenantModel):
    """Agent skill definition for scraper automation.

    Defines reusable, agent-callable skill configurations that combine
    workflow steps with tool definitions and parameters.
    """

    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Unique skill name identifier",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Human-readable description of what this skill does",
    )
    steps = models.JSONField(
        default=list,
        help_text="Ordered list of step definitions for this skill",
    )
    tools = models.JSONField(
        default=list,
        help_text="List of MCP tool names this skill can invoke",
    )
    parameters = models.JSONField(
        default=dict,
        help_text="JSON Schema defining parameters this skill accepts",
    )

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
        db_table = "voyant_agent_skill"
        ordering = ["-created_at"]

    def __str__(self):
        return f"AgentSkill({self.id}) - {self.name}"
