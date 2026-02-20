"""
Schema Visualization Generator: Creates Timelines of Schema Changes.

This module provides a generator plugin that transforms historical schema
change data into a structured format suitable for visualization as a timeline.
It integrates with the `plugin_registry` and `schema_evolution` modules
to retrieve and interpret schema version history for a given table.

Reference: docs/CANONICAL_ROADMAP.md - Future Investigation Backlog
"""

from typing import Any, Dict

from apps.core.lib.plugin_registry import GeneratorPlugin, PluginCategory, register_plugin
from apps.core.lib.schema_evolution import (
    get_schema_history,
)


@register_plugin(
    name="schema_timeline",
    category=PluginCategory.VISUALIZATION,
    version="1.0.0",
    description="Generates schema evolution timeline artifact",
)
class SchemaTimelineGenerator(GeneratorPlugin):
    """
    A generator plugin that creates a structured timeline of schema changes for a table.

    This generator processes the historical schema versions retrieved from the
    `schema_evolution` module and formats them into events that can be used
    to render a visual timeline.
    """

    def get_name(self) -> str:
        """
        Returns the unique name of this generator plugin.

        Returns:
            str: The name "schema_timeline".
        """
        return "schema_timeline"

    def generate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates a timeline artifact based on the schema evolution history of a table.

        Args:
            context (Dict[str, Any]): A dictionary containing the necessary context for generation.
                                       Expected keys include:
                                       - `table_name` (str): The name of the table to generate the timeline for.
                                       - `tables` (List[str], optional): A list of tables, if `table_name` is not directly provided.

        Returns:
            Dict[str, Any]: A dictionary representing the generated timeline artifact,
                            including events and summary statistics.

        Raises:
            ValueError: If `table_name` is not provided in the context.
        """
        table_name = context.get("table_name")
        if not table_name:
            # Fallback for multi-table context if 'table_name' is not explicitly set.
            tables = context.get("tables", [])
            if tables:
                table_name = tables[0]

        if not table_name:
            raise ValueError(
                "table_name required in context for schema timeline generation."
            )

        history = get_schema_history(table_name)

        # Transform the historical schema entries into a visualization-ready format.
        timeline_events = []
        for entry in history:
            version = entry["version"]
            created_at = entry["created_at"]
            changes_count = entry["changes_count"]
            breaking_changes_count = entry["breaking_changes"]

            # Determine badge and color based on the presence of breaking changes.
            badge_text = "Breaking" if breaking_changes_count > 0 else "Compatible"
            badge_color = "red" if breaking_changes_count > 0 else "green"

            event = {
                "date": created_at,
                "title": f"Version {version}",
                "description": entry["description"],
                "badge": badge_text,
                "badge_color": badge_color,
                "details": f"{changes_count} changes ({breaking_changes_count} breaking)",
            }
            timeline_events.append(event)

        # Return a structured JSON representation of the timeline artifact.
        return {
            "type": "timeline",
            "title": f"Schema History: {table_name}",
            "events": timeline_events,
            "stats": {
                "total_versions": len(history),
                "total_changes": sum(h["changes_count"] for h in history),
                "total_breaking": sum(h["breaking_changes"] for h in history),
            },
        }
