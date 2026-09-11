"""Status and health commands for the Voyant CLI."""

from __future__ import annotations

import sys

import click

from cli.client import VoyantClient, format_output, handle_response


@click.command()
@click.option("--output", "-o", type=click.Choice(["table", "json"]), default="json", help="Output format")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed status")
def status(output: str, verbose: bool):
    """Show Voyant system status and health."""
    client = VoyantClient()

    # Get health
    health_response = client.get("/../../health", timeout=5.0)
    health_ok = health_response.status_code == 200

    # Get version
    version_response = client.get("/../../version", timeout=5.0)
    version_data = handle_response(version_response, output) if version_response.status_code == 200 else {}

    # Build status info
    info = {
        "api_url": client.base_url,
        "health": "healthy" if health_ok else "unreachable",
        "version": version_data.get("version", "unknown") if isinstance(version_data, dict) else "unknown",
        "tenant_id": client.tenant_id,
    }

    if verbose:
        # Get job counts by status
        try:
            jobs_response = client.get("/jobs", params={"limit": 100})
            if jobs_response.status_code == 200:
                jobs = jobs_response.json()
                if isinstance(jobs, list):
                    status_counts: dict[str, int] = {}
                    for job in jobs:
                        s = job.get("status", "unknown")
                        status_counts[s] = status_counts.get(s, 0) + 1
                    info["jobs"] = status_counts
                    info["total_jobs"] = len(jobs)
        except Exception:
            pass

        # Get ontology type count
        try:
            types_response = client.get("/ontology/object-types", params={"limit": 1})
            if types_response.status_code == 200:
                types_data = types_response.json()
                if isinstance(types_data, list):
                    info["object_types"] = len(types_data)
        except Exception:
            pass

    click.echo(format_output(info, output))

    if not health_ok:
        click.echo("\nWarning: API health check failed.", err=True)
        sys.exit(1)
