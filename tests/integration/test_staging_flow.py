"""
Staging Integration Flow

Simulates a full end-to-end run of the Voyant pipeline in a staging-like environment.
Verifies cohesion between:
- Persistence (DuckDB)
- Event Emission (Kafka/Schema Registry)
- Generation Activities (Plugin Registry)
- Schema Evolution
"""
import pytest
import os
import duckdb
import time
from unittest.mock import MagicMock
import sys

# Mock temporalio before importing anything that uses it
mock_temporalio = MagicMock()
mock_activity = MagicMock()
mock_activity.defn = lambda x: x
mock_temporalio.activity = mock_activity
sys.modules["temporalio"] = mock_temporalio
sys.modules["temporalio.activity"] = mock_activity

from voyant.core.config import get_settings
from voyant.core.schema_evolution import (
    SchemaEvolutionRegistry, 
    reset_registry as reset_schema_registry,
    TableSchema
)
from voyant.core.plugin_registry import reset_registry as reset_plugin_registry, register_plugin, GeneratorPlugin, PluginCategory, get_plugin
from voyant.core.events import VoyantEvent, KafkaProducer
from voyant.core.event_schema import validate_event, _register_canonical_schemas
from voyant.activities.generation_activities import GenerationActivities

# Ensure canonical schemas are registered
_register_canonical_schemas()

@pytest.fixture
def staging_env(tmp_path):
    """Setup a staging environment with a fresh DuckDB and registry."""
    # 1. Setup persistence
    db_path = tmp_path / "staging_voyant.duckdb"
    settings = get_settings()
    settings.duckdb_path = str(db_path)
    
    # Reset singleton
    reset_schema_registry()
    
    registry = SchemaEvolutionRegistry()
    # Hack: Inject this new instance as the global singleton if needed
    import voyant.core.schema_evolution
    voyant.core.schema_evolution._registry = registry
    
    # 2. Reset Plugin Registry
    reset_plugin_registry()
    
    # 3. Register a real plugin for the test (Schema Timeline)
    from voyant.generators import schema_vis
    
    yield registry
    
    registry.close()
    reset_schema_registry()

def test_end_to_end_pipeline(staging_env):
    """
    Simulate a full data pipeline run:
    1. Update Schema (Evolution)
    2. Emit Event (Ingestion)
    3. Run Generators (Artifact Creation)
    """
    registry = staging_env
    tenant_id = "staging_tenant_001"
    source_id = "crm_raw_leads"
    
    # ---------------------------------------------------------
    # Step 1: Schema Evolution (Simulate schema detection)
    # ---------------------------------------------------------
    schema_v1 = {
        "name": "leads",
        "columns": [
            {"name": "id", "data_type": "VARCHAR"},
            {"name": "email", "data_type": "VARCHAR"},
            {"name": "created_at", "data_type": "TIMESTAMP"}
        ]
    }
    
    # Register V1
    table_schema = TableSchema.from_dict(schema_v1)
    
    registry.register(
        table_name=source_id, 
        schema=table_schema, 
        version="1.0.0", 
        description="Initial schema"
    )
    
    # Verify persistence
    history = registry.get_history(source_id)
    assert len(history) == 1
    assert history[0]["version"] == "1.0.0"
    
    # ---------------------------------------------------------
    # Step 2: Event Emission (Simulate Ingestion Complete)
    # ---------------------------------------------------------
    # We mock the producer's internal confluent instance but keep the validation logic true
    producer = KafkaProducer()
    producer._get_producer = MagicMock(return_value=MagicMock())
    
    event_payload = {
        "source_id": source_id,
        "tenant_id": tenant_id,
        "table_name": "leads",
        "row_count": 5000,
        "ingested_at": "2024-01-01T12:00:00Z"
    }
    
    event = VoyantEvent(
        event_type="data.ingested",
        event_id="evt_001",
        timestamp="2024-01-01T12:00:00Z",
        tenant_id=tenant_id,
        payload=event_payload
    )
    
    # Emit (this validates the schema internally)
    success = producer.emit("lineage", event)
    assert success is True, "Event emission failed validation"
    
    # ---------------------------------------------------------
    # Step 3: Generation Activity (Triggered by workflow usually)
    # ---------------------------------------------------------
    # Manually trigger the activity as the worker would
    activity = GenerationActivities()
    
    # Context passed from workflow
    context = {
        "source_id": source_id,
        "tenant_id": tenant_id,
        "job_id": "job_staging_123",
        "table_name": source_id # Plugin expects table_name in context
    }
    
    # Run generators (plugins)
    results = activity.run_generators(context)
    
    # ---------------------------------------------------------
    # Step 4: Verification
    # ---------------------------------------------------------
    assert results is not None
    # Check for specific artifacts
    # The SchemaTimelineGenerator plugin name is 'schema_timeline'
    assert "schema_timeline" in results
    
    timeline = results["schema_timeline"]
    assert source_id in timeline["title"]
    assert len(timeline["events"]) == 1
    assert timeline["events"][0]["title"] == "Version 1.0.0"
