"""
Verification Script for Observability

Tests that:
1. Prometheus server starts.
2. MetricsRegistry records data.
3. /metrics endpoint returns the data.
"""
import logging
import sys
import os
import time
import threading
import requests
from prometheus_client.parser import text_string_to_metric_families

# Add project root to path
sys.path.append(os.getcwd())

from voyant.core.monitoring import MetricsRegistry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_obs")

def test_metrics_server():
    logger.info("Testing Metrics Server...")
    
    registry = MetricsRegistry()
    port = 9091 # Use different port than worker to avoid collision if running
    
    # Start server in thread
    t = threading.Thread(target=registry.start_server, args=(port,), daemon=True)
    t.start()
    
    # Give it a second to bind
    time.sleep(2)
    
    # Record some dummy metrics
    logger.info("Recording metrics...")
    registry.activity_executions.labels(activity_type="test_activity", status="success").inc()
    registry.activity_duration.labels(activity_type="test_activity").observe(0.5)
    
    # Fetch metrics
    url = f"http://localhost:{port}/metrics"
    logger.info(f"Scraping {url}...")
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        # Parse response
        found_count = False
        found_bucket = False
        
        for family in text_string_to_metric_families(response.text):
            if family.name == 'voyant_activity_executions_total':
                for sample in family.samples:
                    if sample.labels['activity_type'] == 'test_activity':
                        logger.info(f"Found Counter: {sample.value}")
                        assert sample.value >= 1.0
                        found_count = True
            
            if family.name == 'voyant_activity_duration_seconds':
                # Histograms produce _bucket, _sum, _count
                logger.info(f"Found Histogram Family: {family.name}")
                found_bucket = True
                
        if found_count and found_bucket:
            logger.info("✅ Verification SUCCESS: Metrics exposed and scraped.")
        else:
            logger.error("❌ Verification FAILED: Metrics not found in output.")
            logger.debug(response.text)
            
    except Exception as e:
        logger.error(f"Verification Failed: {e}")

if __name__ == "__main__":
    test_metrics_server()
