"""Dashboard management commands for the Voyant CLI."""

from __future__ import annotations

import click

from cli.client import VoyantClient, format_output, handle_response


@click.group()
def dashboards():
    """Manage dashboards and widgets."""
    pass


@dashboards.command("list")
@click.option("--limit", "-l", default=50, help="Maximum number of dashboards to return")
@click.option("--output", "-o", type=click.Choice(["table", "json"]), default="table", help="Output format")
def list_dashboards(limit: int, output: str):
    """List all dashboards."""
    client = VoyantClient()
    response = client.get("/dashboards", params={"limit": limit})
    data = handle_response(response, output)
    click.echo(format_output(data, output))


@dashboards.command("get")
@click.argument("dashboard_id")
@click.option("--output", "-o", type=click.Choice(["table", "json"]), default="json", help="Output format")
def get_dashboard(dashboard_id: str, output: str):
    """Get details for a specific dashboard."""
    client = VoyantClient()
    response = client.get(f"/dashboards/{dashboard_id}")
    data = handle_response(response, output)
    click.echo(format_output(data, output))


@dashboards.command("widgets")
@click.argument("dashboard_id")
@click.option("--output", "-o", type=click.Choice(["table", "json"]), default="table", help="Output format")
def list_widgets(dashboard_id: str, output: str):
    """List widgets on a specific dashboard."""
    client = VoyantClient()
    response = client.get(f"/dashboards/{dashboard_id}/widgets")
    data = handle_response(response, output)
    click.echo(format_output(data, output))
