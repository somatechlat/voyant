"""Dashboard Builder — Django ORM models.

Provides Dashboard and Widget models for building custom dashboards
with configurable widget layouts.
"""

from __future__ import annotations

from django.db import models

from apps.core.models import TenantModel, UUIDModel


class Dashboard(TenantModel, UUIDModel):
    """
    A user-created dashboard that contains a configurable layout of widgets.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    name = models.CharField(
        max_length=255,
        help_text="Dashboard name (unique per tenant)",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Human-readable description",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
        help_text="Publication status",
    )
    layout = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Dashboard layout configuration: "
            '{"columns": 12, "row_height": 80, "gap": 8, "responsive": true}'
        ),
    )
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text='Tags for categorization: ["monitoring", "sales"]',
    )
    is_public = models.BooleanField(
        default=False,
        help_text="Whether this dashboard is visible to all tenant users",
    )
    created_by = models.CharField(
        max_length=256,
        blank=True,
        default="",
        help_text="User who created the dashboard",
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Soft-deletion timestamp (null = active)",
    )

    class Meta(TenantModel.Meta, UUIDModel.Meta):  # type: ignore[reportIncompatibleVariableOverride]
        db_table = "voyant_dashboard"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                condition=models.Q(deleted_at__isnull=True),
                name="uq_dashboard_name_active",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant_id", "status"], name="idx_dash_tenant_status"),
            models.Index(
                fields=["tenant_id", "-created_at"], name="idx_dash_tenant_created"
            ),
        ]

    def __str__(self) -> str:
        return f"Dashboard({self.name} [{self.status}])"


class Widget(UUIDModel):
    """
    A single widget within a dashboard.

    Widgets represent visual elements (charts, tables, metrics, etc.)
    positioned on the dashboard grid.
    """

    class WidgetType(models.TextChoices):
        CHART_BAR = "chart_bar", "Bar Chart"
        CHART_LINE = "chart_line", "Line Chart"
        CHART_PIE = "chart_pie", "Pie Chart"
        CHART_AREA = "chart_area", "Area Chart"
        CHART_SCATTER = "chart_scatter", "Scatter Plot"
        TABLE = "table", "Data Table"
        METRIC = "metric", "Single Metric"
        KPI = "kpi", "KPI Card"
        TEXT = "text", "Text / Markdown"
        IFRAME = "iframe", "Embedded IFrame"
        MAP = "map", "Map"
        HEATMAP = "heatmap", "Heatmap"
        CUSTOM = "custom", "Custom"

    dashboard = models.ForeignKey(
        Dashboard,
        on_delete=models.CASCADE,
        related_name="widgets",
        help_text="Parent dashboard",
    )
    widget_type = models.CharField(
        max_length=32,
        choices=WidgetType.choices,
        help_text="Type of visual element",
    )
    title = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Widget title displayed in the header",
    )
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Widget-specific configuration: "
            '{"data_source": "sql", "query": "SELECT ...", "color": "#4f46e5", '
            '"refresh_interval": 60, "options": {}}'
        ),
    )
    # Grid position (using a simple 12-column grid system)
    position_x = models.PositiveIntegerField(
        default=0,
        help_text="Column position (0-based, 12-column grid)",
    )
    position_y = models.PositiveIntegerField(
        default=0,
        help_text="Row position (0-based)",
    )
    width = models.PositiveIntegerField(
        default=6,
        help_text="Number of columns spanned (1-12)",
    )
    height = models.PositiveIntegerField(
        default=4,
        help_text="Number of rows spanned",
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Z-index / render order",
    )
    visible = models.BooleanField(
        default=True,
        help_text="Whether the widget is visible",
    )

    class Meta(UUIDModel.Meta):  # type: ignore[reportIncompatibleVariableOverride]
        db_table = "voyant_widget"
        ordering = ["order", "position_y", "position_x"]
        indexes = [
            models.Index(
                fields=["dashboard_id", "order"], name="idx_widget_dash_order"
            ),
        ]

    def __str__(self) -> str:
        label = self.title or self.widget_type
        return f"Widget({label} on {self.dashboard_id})"  # type: ignore[attr-defined]
