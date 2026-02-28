"""
Diagnostic Script for Core Schema Evolution Imports.

Purpose:
    This script is a standalone diagnostic tool designed to test the importability
    of the `voyant.core.schema_evolution` module and its key components. It helps
    in quickly identifying and isolating circular dependency issues or environment-
    related problems without running the full application.

Usage:
    Run this script directly from the command line from the project root:
    $ python scripts/debug_imports.py

Expected Output:
    - "Imports successful!" if all components are imported correctly.
    - An "ImportError" message if a specific component fails to import.
    - A generic "Error" message for any other exceptions during import.
"""

# This try-except block attempts to import critical modules and reports
# on success or failure, providing a quick check on the application's
# foundational components.
try:
    from apps.core.lib.schema_evolution import (
        ColumnSchema,
        TableSchema,
        get_latest_schema,
        get_registry,
        get_schema_history,
        reset_registry,
        track_schema,
    )  # noqa: F401

    print("Imports successful!")
except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Error: {e}")
