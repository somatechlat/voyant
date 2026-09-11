"""Pipeline management commands for the Voyant CLI."""

from __future__ import annotations

import click

from cli.client import VoyantClient, format_output, handle_response


@click.group()
def pipelines():
    """Manage data pipelines."""
    pass


@pipelines.command("list")
@click.option("--limit", "-l", default=50, help="Maximum number of pipelines to return")
@click.option("--output", "-o", type=click.Choice(["table", "json"]), default="table", help="Output format")
def list_pipelines(limit: int, output: str):
    """List all pipelines."""
    client = VoyantClient()
    response = client.get("/pipelines", params={"limit": limit})
    data = handle_response(response, output)
    click.echo(format_output(data, output))


@pipelines.command("get")
@click.argument("pipeline_id")
@click.option("--output", "-o", type=click.Choice(["table", "json"]), default="json", help="Output format")
def get_pipeline(pipeline_id: str, output: str):
    """Get details for a specific pipeline."""
    client = VoyantClient()
    response = client.get(f"/pipelines/{pipeline_id}")
    data = handle_response(response, output)
    click.echo(format_output(data, output))


@pipelines.command("run")
@click.argument("pipeline_id")
@click.option("--output", "-o", type=click.Choice(["table", "json"]), default="json", help="Output format")
def run_pipeline(pipeline_id: str, output: str):
    """Trigger a pipeline run."""
    client = VoyantClient()
    response = client.post(f"/pipelines/{pipeline_id}/run")
    data = handle_response(response, output)
    click.echo(format_output(data, output))


@pipelines.command("runs")
@click.argument("pipeline_id")
@click.option("--limit", "-l", default=20, help="Maximum number of runs to return")
@click.option("--output", "-o", type=click.Choice(["table", "json"]), default="table", help="Output format")
def list_runs(pipeline_id: str, limit: int, output: str):
    """List runs for a specific pipeline."""
    client = VoyantClient()
    response = client.get(f"/pipelines/{pipeline_id}/runs", params={"limit": limit})
    data = handle_response(response, output)
    click.echo(format_output(data, output))
