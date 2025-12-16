"""
KPI SQL Template Library

Standard KPI calculations that can be applied to any compatible dataset.
Reference: docs/CANONICAL_ROADMAP.md - P1 Extended Insights

Each template includes:
- SQL template with {placeholders}
- Required columns (must be provided)
- Optional columns (with defaults)
- Output columns (expected in result)
- Description for documentation
- Category for organization

Usage:
    from voyant.core.kpi_templates import get_template, render_template, list_templates
    
    # Get a template
    template = get_template("revenue_growth")
    
    # Render SQL with parameters
    sql = render_template("revenue_growth", {
        "table": "sales",
        "date_column": "sale_date",
        "amount_column": "amount"
    })
"""
from __future__ import annotations

import re
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class KPITemplate:
    """Definition of a KPI SQL template."""
    name: str
    category: str
    description: str
    sql: str
    required_columns: List[str]
    optional_columns: Dict[str, str]  # column_name -> default_value
    output_columns: List[str]


# =============================================================================
# Template Definitions (15+ Standard KPIs)
# =============================================================================

KPI_TEMPLATES: Dict[str, KPITemplate] = {}


def _register(
    name: str,
    category: str,
    description: str,
    sql: str,
    required_columns: List[str],
    optional_columns: Optional[Dict[str, str]] = None,
    output_columns: Optional[List[str]] = None,
):
    """Register a KPI template."""
    KPI_TEMPLATES[name] = KPITemplate(
        name=name,
        category=category,
        description=description,
        sql=sql.strip(),
        required_columns=required_columns,
        optional_columns=optional_columns or {},
        output_columns=output_columns or [],
    )


# =============================================================================
# Financial KPIs
# =============================================================================

_register(
    name="revenue_growth",
    category="financial",
    description="Calculate revenue and period-over-period growth percentage",
    sql="""
        SELECT 
            {date_column} as period,
            SUM({amount_column}) as revenue,
            LAG(SUM({amount_column})) OVER (ORDER BY {date_column}) as prev_revenue,
            ROUND(
                (SUM({amount_column}) - LAG(SUM({amount_column})) OVER (ORDER BY {date_column})) 
                / NULLIF(LAG(SUM({amount_column})) OVER (ORDER BY {date_column}), 0) * 100, 
                2
            ) as growth_pct
        FROM {table}
        GROUP BY {date_column}
        ORDER BY {date_column}
    """,
    required_columns=["table", "date_column", "amount_column"],
    output_columns=["period", "revenue", "prev_revenue", "growth_pct"],
)

_register(
    name="revenue_by_segment",
    category="financial",
    description="Revenue breakdown by segment with percentage of total",
    sql="""
        SELECT 
            {segment_column} as segment,
            SUM({amount_column}) as revenue,
            ROUND(
                SUM({amount_column}) * 100.0 / SUM(SUM({amount_column})) OVER (), 
                2
            ) as pct_of_total
        FROM {table}
        GROUP BY {segment_column}
        ORDER BY revenue DESC
    """,
    required_columns=["table", "segment_column", "amount_column"],
    output_columns=["segment", "revenue", "pct_of_total"],
)

_register(
    name="profit_margin",
    category="financial",
    description="Calculate profit margin by segment",
    sql="""
        SELECT 
            {segment_column} as segment,
            SUM({revenue_column}) as revenue,
            SUM({cost_column}) as cost,
            SUM({revenue_column}) - SUM({cost_column}) as profit,
            ROUND(
                (SUM({revenue_column}) - SUM({cost_column})) 
                / NULLIF(SUM({revenue_column}), 0) * 100,
                2
            ) as margin_pct
        FROM {table}
        GROUP BY {segment_column}
        ORDER BY margin_pct DESC
    """,
    required_columns=["table", "segment_column", "revenue_column", "cost_column"],
    output_columns=["segment", "revenue", "cost", "profit", "margin_pct"],
)

_register(
    name="average_order_value",
    category="financial",
    description="Calculate average order value over time",
    sql="""
        SELECT 
            {date_column} as period,
            COUNT(DISTINCT {order_id_column}) as order_count,
            SUM({amount_column}) as total_revenue,
            ROUND(SUM({amount_column}) / NULLIF(COUNT(DISTINCT {order_id_column}), 0), 2) as aov
        FROM {table}
        GROUP BY {date_column}
        ORDER BY {date_column}
    """,
    required_columns=["table", "date_column", "order_id_column", "amount_column"],
    output_columns=["period", "order_count", "total_revenue", "aov"],
)

# =============================================================================
# Customer KPIs
# =============================================================================

_register(
    name="customer_count_by_period",
    category="customer",
    description="Unique customer count over time periods",
    sql="""
        SELECT 
            {date_column} as period,
            COUNT(DISTINCT {customer_id_column}) as unique_customers,
            LAG(COUNT(DISTINCT {customer_id_column})) OVER (ORDER BY {date_column}) as prev_customers,
            COUNT(DISTINCT {customer_id_column}) - 
                COALESCE(LAG(COUNT(DISTINCT {customer_id_column})) OVER (ORDER BY {date_column}), 0) as net_new
        FROM {table}
        GROUP BY {date_column}
        ORDER BY {date_column}
    """,
    required_columns=["table", "date_column", "customer_id_column"],
    output_columns=["period", "unique_customers", "prev_customers", "net_new"],
)

_register(
    name="customer_revenue_distribution",
    category="customer",
    description="Revenue distribution across customers (top N contribution)",
    sql="""
        WITH customer_revenue AS (
            SELECT 
                {customer_id_column} as customer_id,
                SUM({amount_column}) as total_revenue
            FROM {table}
            GROUP BY {customer_id_column}
        ),
        ranked AS (
            SELECT 
                customer_id,
                total_revenue,
                ROW_NUMBER() OVER (ORDER BY total_revenue DESC) as rank,
                SUM(total_revenue) OVER () as grand_total
            FROM customer_revenue
        )
        SELECT 
            CASE 
                WHEN rank <= 10 THEN 'Top 10'
                WHEN rank <= 50 THEN 'Top 11-50'
                WHEN rank <= 100 THEN 'Top 51-100'
                ELSE 'Others'
            END as customer_tier,
            COUNT(*) as customer_count,
            SUM(total_revenue) as tier_revenue,
            ROUND(SUM(total_revenue) / MAX(grand_total) * 100, 2) as pct_of_total
        FROM ranked
        GROUP BY 
            CASE 
                WHEN rank <= 10 THEN 'Top 10'
                WHEN rank <= 50 THEN 'Top 11-50'
                WHEN rank <= 100 THEN 'Top 51-100'
                ELSE 'Others'
            END
        ORDER BY MIN(rank)
    """,
    required_columns=["table", "customer_id_column", "amount_column"],
    output_columns=["customer_tier", "customer_count", "tier_revenue", "pct_of_total"],
)

_register(
    name="rfm_segments",
    category="customer",
    description="RFM (Recency, Frequency, Monetary) customer segmentation",
    sql="""
        WITH customer_rfm AS (
            SELECT 
                {customer_id_column} as customer_id,
                DATEDIFF('day', MAX({date_column}), CURRENT_DATE) as recency_days,
                COUNT(DISTINCT {order_id_column}) as frequency,
                SUM({amount_column}) as monetary
            FROM {table}
            GROUP BY {customer_id_column}
        )
        SELECT 
            customer_id,
            recency_days,
            frequency,
            monetary,
            CASE 
                WHEN recency_days <= 30 AND frequency >= 5 AND monetary >= 1000 THEN 'Champions'
                WHEN recency_days <= 60 AND frequency >= 3 THEN 'Loyal'
                WHEN recency_days <= 30 THEN 'Recent'
                WHEN recency_days > 90 AND frequency >= 3 THEN 'At Risk'
                ELSE 'Other'
            END as segment
        FROM customer_rfm
        ORDER BY monetary DESC
    """,
    required_columns=["table", "customer_id_column", "order_id_column", "date_column", "amount_column"],
    output_columns=["customer_id", "recency_days", "frequency", "monetary", "segment"],
)

# =============================================================================
# Quality KPIs
# =============================================================================

_register(
    name="null_rate_by_column",
    category="quality",
    description="Calculate null/missing rate for each column",
    sql="""
        SELECT 
            '{column}' as column_name,
            COUNT(*) as total_rows,
            SUM(CASE WHEN {column} IS NULL THEN 1 ELSE 0 END) as null_count,
            ROUND(
                SUM(CASE WHEN {column} IS NULL THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
                2
            ) as null_pct
        FROM {table}
    """,
    required_columns=["table", "column"],
    output_columns=["column_name", "total_rows", "null_count", "null_pct"],
)

_register(
    name="duplicate_rate",
    category="quality",
    description="Detect duplicate rows based on key columns",
    sql="""
        WITH duplicates AS (
            SELECT 
                {key_columns},
                COUNT(*) as occurrence_count
            FROM {table}
            GROUP BY {key_columns}
            HAVING COUNT(*) > 1
        )
        SELECT 
            COUNT(*) as duplicate_groups,
            SUM(occurrence_count) as total_duplicate_rows,
            SUM(occurrence_count - 1) as excess_rows
        FROM duplicates
    """,
    required_columns=["table", "key_columns"],
    output_columns=["duplicate_groups", "total_duplicate_rows", "excess_rows"],
)

_register(
    name="value_distribution",
    category="quality",
    description="Distribution of values for a categorical column",
    sql="""
        SELECT 
            COALESCE(CAST({column} AS VARCHAR), 'NULL') as value,
            COUNT(*) as count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as pct
        FROM {table}
        GROUP BY {column}
        ORDER BY count DESC
        LIMIT {limit}
    """,
    required_columns=["table", "column"],
    optional_columns={"limit": "20"},
    output_columns=["value", "count", "pct"],
)

# =============================================================================
# Operations KPIs
# =============================================================================

_register(
    name="inventory_turnover",
    category="operations",
    description="Calculate inventory turnover rate",
    sql="""
        SELECT 
            {product_id_column} as product_id,
            SUM({sold_quantity_column}) as units_sold,
            AVG({stock_quantity_column}) as avg_stock,
            ROUND(
                SUM({sold_quantity_column}) / NULLIF(AVG({stock_quantity_column}), 0),
                2
            ) as turnover_rate
        FROM {table}
        GROUP BY {product_id_column}
        ORDER BY turnover_rate DESC
    """,
    required_columns=["table", "product_id_column", "sold_quantity_column", "stock_quantity_column"],
    output_columns=["product_id", "units_sold", "avg_stock", "turnover_rate"],
)

_register(
    name="lead_time_analysis",
    category="operations",
    description="Analyze order-to-delivery lead times",
    sql="""
        SELECT 
            {segment_column} as segment,
            COUNT(*) as order_count,
            AVG(DATEDIFF('day', {order_date_column}, {delivery_date_column})) as avg_lead_days,
            MIN(DATEDIFF('day', {order_date_column}, {delivery_date_column})) as min_lead_days,
            MAX(DATEDIFF('day', {order_date_column}, {delivery_date_column})) as max_lead_days
        FROM {table}
        WHERE {delivery_date_column} IS NOT NULL
        GROUP BY {segment_column}
        ORDER BY avg_lead_days
    """,
    required_columns=["table", "segment_column", "order_date_column", "delivery_date_column"],
    output_columns=["segment", "order_count", "avg_lead_days", "min_lead_days", "max_lead_days"],
)

# =============================================================================
# Time Series KPIs
# =============================================================================

_register(
    name="moving_average",
    category="timeseries",
    description="Calculate N-period moving average",
    sql="""
        SELECT 
            {date_column} as period,
            {value_column} as value,
            AVG({value_column}) OVER (
                ORDER BY {date_column} 
                ROWS BETWEEN {window_size} PRECEDING AND CURRENT ROW
            ) as moving_avg
        FROM {table}
        ORDER BY {date_column}
    """,
    required_columns=["table", "date_column", "value_column"],
    optional_columns={"window_size": "7"},
    output_columns=["period", "value", "moving_avg"],
)

_register(
    name="year_over_year",
    category="timeseries",
    description="Year-over-year comparison",
    sql="""
        WITH current_period AS (
            SELECT 
                EXTRACT(MONTH FROM {date_column}) as month,
                SUM({value_column}) as current_value
            FROM {table}
            WHERE EXTRACT(YEAR FROM {date_column}) = EXTRACT(YEAR FROM CURRENT_DATE)
            GROUP BY EXTRACT(MONTH FROM {date_column})
        ),
        previous_period AS (
            SELECT 
                EXTRACT(MONTH FROM {date_column}) as month,
                SUM({value_column}) as previous_value
            FROM {table}
            WHERE EXTRACT(YEAR FROM {date_column}) = EXTRACT(YEAR FROM CURRENT_DATE) - 1
            GROUP BY EXTRACT(MONTH FROM {date_column})
        )
        SELECT 
            c.month,
            c.current_value,
            p.previous_value,
            ROUND(
                (c.current_value - COALESCE(p.previous_value, 0)) 
                / NULLIF(p.previous_value, 0) * 100,
                2
            ) as yoy_change_pct
        FROM current_period c
        LEFT JOIN previous_period p ON c.month = p.month
        ORDER BY c.month
    """,
    required_columns=["table", "date_column", "value_column"],
    output_columns=["month", "current_value", "previous_value", "yoy_change_pct"],
)

_register(
    name="cumulative_sum",
    category="timeseries",
    description="Running cumulative sum over time",
    sql="""
        SELECT 
            {date_column} as period,
            {value_column} as value,
            SUM({value_column}) OVER (ORDER BY {date_column}) as cumulative_sum
        FROM {table}
        ORDER BY {date_column}
    """,
    required_columns=["table", "date_column", "value_column"],
    output_columns=["period", "value", "cumulative_sum"],
)


# =============================================================================
# Public API
# =============================================================================

def list_templates(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List all available KPI templates.
    
    Args:
        category: Optional filter by category (financial, customer, quality, etc.)
    
    Returns:
        List of template info dicts
    """
    templates = []
    for name, template in KPI_TEMPLATES.items():
        if category and template.category != category:
            continue
        templates.append({
            "name": name,
            "category": template.category,
            "description": template.description,
            "required_columns": template.required_columns,
            "optional_columns": template.optional_columns,
            "output_columns": template.output_columns,
        })
    return templates


def get_template(name: str) -> Optional[KPITemplate]:
    """Get a specific template by name."""
    return KPI_TEMPLATES.get(name)


def render_template(name: str, params: Dict[str, str]) -> str:
    """
    Render a KPI template with provided parameters.
    
    Args:
        name: Template name
        params: Dictionary of column/table names to substitute
    
    Returns:
        Rendered SQL query
    
    Raises:
        ValueError: If template not found or required params missing
    """
    template = get_template(name)
    if not template:
        raise ValueError(f"Template not found: {name}")
    
    # Check required columns
    missing = [col for col in template.required_columns if col not in params]
    if missing:
        raise ValueError(f"Missing required columns for {name}: {missing}")
    
    # Merge with optional defaults
    full_params = {**template.optional_columns, **params}
    
    # Simple placeholder substitution
    sql = template.sql
    for key, value in full_params.items():
        sql = sql.replace(f"{{{key}}}", value)
    
    # Check for any remaining placeholders
    remaining = re.findall(r'\{(\w+)\}', sql)
    if remaining:
        logger.warning(f"Template {name} has unsubstituted placeholders: {remaining}")
    
    return sql.strip()


def get_categories() -> List[str]:
    """Get list of unique template categories."""
    return sorted(set(t.category for t in KPI_TEMPLATES.values()))
