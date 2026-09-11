"""Voyant CLI — Main entry point.

A command-line interface for the Voyant Data Intelligence platform.
Provides access to jobs, ontology, SQL queries, scraping, pipelines,
dashboards, and system status.

Usage:
    voyant auth login              # Authenticate via Keycloak
    voyant jobs list               # List background jobs
    voyant jobs get <id>           # Get job details
    voyant ontology types list     # List object types
    voyant ontology objects list <type>  # List objects by type
    voyant sql query <sql>         # Execute SQL query
    voyant scrape templates list   # List scrape templates
    voyant pipelines list          # List pipelines
    voyant dashboards list         # List dashboards
    voyant status                  # Show system status
"""

from __future__ import annotations

import click

from cli import __version__
from cli.auth import auth
from cli.dashboards import dashboards
from cli.jobs import jobs
from cli.ontology import ontology
from cli.pipelines import pipelines
from cli.scrape import scrape
from cli.sql import sql
from cli.status import status


@click.group()
@click.version_option(version=__version__, prog_name="voyant")
def cli():
    """Voyant — Data Intelligence CLI.

    A command-line interface for the Voyant Data Intelligence platform.
    Configure your API endpoint with:

        voyant config set api-url https://your-voyant-instance.com/v1

    Then authenticate:

        voyant auth login
    """
    pass


# Register command groups
cli.add_command(auth)
cli.add_command(jobs)
cli.add_command(ontology)
cli.add_command(sql)
cli.add_command(scrape)
cli.add_command(pipelines)
cli.add_command(dashboards)
cli.add_command(status)


@cli.group()
def config():
    """Manage CLI configuration."""
    pass


@config.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str):
    """Set a configuration value.

    Available keys: api-url, tenant-id, keycloak-url
    """
    from cli.config import load_config, save_config

    valid_keys = {"api-url", "tenant-id", "keycloak-url"}
    config_key = key.replace("-", "_")

    if key not in valid_keys:
        click.echo(f"Error: Unknown config key '{key}'. Valid keys: {', '.join(sorted(valid_keys))}", err=True)
        raise SystemExit(1)

    config_data = load_config()
    config_data[config_key] = value
    save_config(config_data)
    click.echo(f"Set {key} = {value}")


@config.command("show")
def config_show():
    """Show current configuration."""
    from cli.config import get_api_url, get_tenant_id, load_config

    config_data = load_config()
    click.echo(f"API URL:    {get_api_url()}")
    click.echo(f"Tenant ID:  {get_tenant_id()}")
    if config_data.get("keycloak_url"):
        click.echo(f"Keycloak:   {config_data['keycloak_url']}")


def main():
    """Entry point for the voyant CLI."""
    cli()


if __name__ == "__main__":
    main()
