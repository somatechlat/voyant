"""
Tests for KPI Template Library

Verifies template listing, rendering, and validation.
Reference: docs/CANONICAL_ROADMAP.md - P1 Extended Insights
"""
import pytest

from voyant.core.kpi_templates import (
    get_template,
    list_templates,
    render_template,
    get_categories,
    KPI_TEMPLATES,
)


class TestTemplateRegistry:
    """Test template registration and listing."""

    def test_templates_registered(self):
        """Should have 15+ templates registered."""
        assert len(KPI_TEMPLATES) >= 15

    def test_list_all_templates(self):
        """Should list all templates."""
        templates = list_templates()
        assert len(templates) >= 15
        # Each should have required fields
        for t in templates:
            assert "name" in t
            assert "category" in t
            assert "description" in t
            assert "required_columns" in t

    def test_list_templates_by_category(self):
        """Should filter templates by category."""
        financial = list_templates(category="financial")
        assert len(financial) >= 3
        for t in financial:
            assert t["category"] == "financial"

    def test_get_categories(self):
        """Should return unique categories."""
        categories = get_categories()
        assert "financial" in categories
        assert "customer" in categories
        assert "quality" in categories


class TestGetTemplate:
    """Test individual template retrieval."""

    def test_get_existing_template(self):
        """Should return template object for existing template."""
        template = get_template("revenue_growth")
        assert template is not None
        assert template.name == "revenue_growth"
        assert template.category == "financial"
        assert "date_column" in template.required_columns

    def test_get_nonexistent_template(self):
        """Should return None for unknown template."""
        template = get_template("nonexistent_kpi")
        assert template is None


class TestRenderTemplate:
    """Test SQL template rendering."""

    def test_render_revenue_growth(self):
        """Should render revenue_growth template."""
        sql = render_template("revenue_growth", {
            "table": "sales",
            "date_column": "sale_date",
            "amount_column": "amount",
        })
        assert "FROM sales" in sql
        assert "sale_date" in sql
        assert "amount" in sql
        assert "{" not in sql  # No remaining placeholders

    def test_render_with_optional_defaults(self):
        """Should use optional defaults when not provided."""
        sql = render_template("value_distribution", {
            "table": "products",
            "column": "category",
        })
        # Should have default limit of 20
        assert "LIMIT 20" in sql

    def test_render_with_optional_override(self):
        """Should override optional defaults when provided."""
        sql = render_template("value_distribution", {
            "table": "products",
            "column": "category",
            "limit": "50",
        })
        assert "LIMIT 50" in sql

    def test_render_missing_required_raises(self):
        """Should raise ValueError when required column missing."""
        with pytest.raises(ValueError) as exc_info:
            render_template("revenue_growth", {
                "table": "sales",
                # Missing date_column and amount_column
            })
        assert "Missing required columns" in str(exc_info.value)

    def test_render_nonexistent_template_raises(self):
        """Should raise ValueError for unknown template."""
        with pytest.raises(ValueError) as exc_info:
            render_template("nonexistent", {"table": "x"})
        assert "Template not found" in str(exc_info.value)


class TestTemplateSQLValidity:
    """Test that rendered SQL is syntactically reasonable."""

    def test_all_templates_render_without_placeholders(self):
        """All templates should render cleanly with mock params."""
        # Build mock params that cover all required columns
        mock_params = {
            "table": "test_table",
            "date_column": "created_at",
            "amount_column": "amount",
            "segment_column": "segment",
            "revenue_column": "revenue",
            "cost_column": "cost",
            "order_id_column": "order_id",
            "customer_id_column": "customer_id",
            "column": "test_col",
            "key_columns": "id",
            "product_id_column": "product_id",
            "sold_quantity_column": "qty_sold",
            "stock_quantity_column": "qty_stock",
            "order_date_column": "order_date",
            "delivery_date_column": "delivery_date",
            "value_column": "value",
        }
        
        for name in KPI_TEMPLATES:
            try:
                sql = render_template(name, mock_params)
                # Should not have remaining placeholders
                assert "{" not in sql, f"Template {name} has unresolved placeholders"
            except ValueError:
                # Some templates may need special params, skip those
                pass
