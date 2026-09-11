"""Job management commands for the Voyant CLI."""

from __future__ import annotations

import click

from cli.client import VoyantClient, format_output, handle_response


@click.group()
def jobs():
    """Manage background jobs."""
    pass


@jobs.command("list")
@click.option("--status", "-s", help="Filter by status (queued, running, completed, failed)")
@click.option("--type", "-t", "job_type", help="Filter by job type")
@click.option("--limit", "-l", default=50, help="Maximum number of jobs to return")
@click.option("--output", "-o", type=click.Choice(["table", "json"]), default="table", help="Output format")
def list_jobs(status: str | None, job_type: str | None, limit: int, output: str):
    """List all jobs."""
    client = VoyantClient()
    params: dict = {"limit": limit}
    if status:
        params["status"] = status
    if job_type:
        params["job_type"] = job_type

    response = client.get("/jobs", params=params)
    data = handle_response(response, output)
    click.echo(format_output(data, output))


@jobs.command("get")
@click.argument("job_id")
@click.option("--output", "-o", type=click.Choice(["table", "json"]), default="json", help="Output format")
def get_job(job_id: str, output: str):
    """Get details for a specific job."""
    client = VoyantClient()
    response = client.get(f"/jobs/{job_id}")
    data = handle_response(response, output)
    click.echo(format_output(data, output))


@jobs.command("cancel")
@click.argument("job_id")
@click.confirmation_option(prompt="Are you sure you want to cancel this job?")
def cancel_job(job_id: str):
    """Cancel a running job."""
    client = VoyantClient()
    response = client.post(f"/jobs/{job_id}/cancel")
    data = handle_response(response)
    click.echo(f"Job {job_id} cancelled successfully." if data else "Cancel request sent.")
