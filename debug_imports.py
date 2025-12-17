try:
    from voyant.core.schema_evolution import (
        track_schema, get_schema_history, get_latest_schema,
        TableSchema, ColumnSchema, reset_registry, get_registry
    )
    print("Imports successful!")
except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Error: {e}")
