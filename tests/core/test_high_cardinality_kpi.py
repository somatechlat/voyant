"""
High Cardinality KPI Tests

Stress tests for KPI SQL templates using large synthetic datasets in DuckDB.
"""
import pytest
import duckdb
import time
import logging
from voyant.core.kpi_templates import render_template

logger = logging.getLogger(__name__)

@pytest.fixture
def large_db():
    """Create an in-memory DuckDB with large synthetic datasets."""
    conn = duckdb.connect(":memory:")
    
    # 1. High Cardinality Segments (10k segments, 1M rows)
    # segment_id: 0..9999
    # amount: random
    conn.execute("""
        CREATE TABLE sales_high_cardinality AS
        SELECT 
            (i % 10000)::VARCHAR as segment_id,
            (random() * 1000)::DOUBLE as amount,
            DATE '2024-01-01' + (i % 365) * INTERVAL '1' DAY as sale_date
        FROM range(1000000) t(i)
    """)
    
    # 2. Large Time Series (1M rows, single continuous series)
    conn.execute("""
        CREATE TABLE time_series_large AS
        SELECT 
            DATE '2020-01-01' + (i % 3650) * INTERVAL '1' DAY as log_date, -- 10 years
            (random() * 100)::DOUBLE as value
        FROM range(1000000) t(i)
    """)
    
    # 3. Many Customers (100k customers, 1M rows)
    conn.execute("""
        CREATE TABLE customer_transactions AS
        SELECT 
            (i % 100000)::VARCHAR as customer_id,
            (random() * 500)::DOUBLE as amount
        FROM range(1000000) t(i)
    """)
    
    yield conn
    conn.close()

def test_high_cardinality_segments(large_db):
    """Test aggregation with high cardinality grouping (10k groups)."""
    sql = render_template("revenue_by_segment", {
        "table": "sales_high_cardinality",
        "segment_column": "segment_id",
        "amount_column": "amount"
    })
    
    start_time = time.time()
    result = large_db.execute(sql).fetchall()
    duration = time.time() - start_time
    
    assert len(result) == 10000
    assert duration < 2.0, f"Query took too long: {duration:.2f}s"
    logger.info(f"High cardinality segments query took {duration:.4f}s")

def test_large_time_series_moving_avg(large_db):
    """Test window functions over large dataset (1M rows)."""
    sql = render_template("moving_average", {
        "table": "time_series_large",
        "date_column": "log_date",
        "value_column": "value",
        "window_size": "30"
    })
    
    start_time = time.time()
    result = large_db.execute(sql).fetchall()
    duration = time.time() - start_time
    
    # Result count might be less due to distinct dates if generated that way, 
    # but range generation with mod 3650 on 1M rows implies overlaps.
    # The distinct dates count:
    distinct_dates = large_db.execute("SELECT COUNT(DISTINCT log_date) FROM time_series_large").fetchone()[0]
    
    assert len(result) == 1000000
    assert duration < 3.0, f"Window function took too long: {duration:.2f}s"
    logger.info(f"Large time series moving avg query took {duration:.4f}s")

def test_customer_revenue_distribution(large_db):
    """Test CTEs and rankings with many customers (100k)."""
    sql = render_template("customer_revenue_distribution", {
        "table": "customer_transactions",
        "customer_id_column": "customer_id",
        "amount_column": "amount"
    })
    
    start_time = time.time()
    result = large_db.execute(sql).fetchall()
    duration = time.time() - start_time
    
    # Output should include 'Top 10', 'Top 11-50', 'Top 51-100', 'Others'
    categories = {row[0] for row in result}
    assert "Top 10" in categories
    assert "Others" in categories
    
    assert duration < 2.0, f"Customer distribution took too long: {duration:.2f}s"
    logger.info(f"Customer distribution query took {duration:.4f}s")
