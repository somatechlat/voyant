"""Scraping commands for the Voyant CLI."""

from __future__ import annotations

import click

from cli.client import VoyantClient, format_output, handle_response


@click.group()
def scrape():
    """Manage scraping jobs and templates."""
    pass


@scrape.group("templates")
def templates_group():
    """Manage scrape templates."""
    pass


@templates_group.command("list")
@click.option("--limit", "-l", default=50, help="Maximum number of templates to return")
@click.option("--output", "-o", type=click.Choice(["table", "json"]), default="table", help="Output format")
def list_templates(limit: int, output: str):
    """List available scrape templates."""
    client = VoyantClient()
    response = client.get("/scraper/workflows", params={"limit": limit})
    data = handle_response(response, output)
    click.echo(format_output(data, output))


@templates_group.command("get")
@click.argument("template_id")
@click.option("--output", "-o", type=click.Choice(["table", "json"]), default="json", help="Output format")
def get_template(template_id: str, output: str):
    """Get details for a specific scrape template."""
    client = VoyantClient()
    response = client.get(f"/scraper/workflows/{template_id}")
    data = handle_response(response, output)
    click.echo(format_output(data, output))


@scrape.command("start")
@click.option("--urls", "-u", multiple=True, required=True, help="URLs to scrape")
@click.option("--engine", "-e", default="playwright", help="Scraping engine (playwright, scrapy, httpx)")
@click.option("--scroll", is_flag=True, help="Scroll the page before capture")
@click.option("--timeout", "-t", default=30, help="Timeout in seconds")
@click.option("--output", "-o", type=click.Choice(["table", "json"]), default="json", help="Output format")
def start_scrape(urls: tuple[str, ...], engine: str, scroll: bool, timeout: int, output: str):
    """Start a new scraping job."""
    client = VoyantClient()
    response = client.post("/scrape/start", json_body={
        "urls": list(urls),
        "options": {
            "engine": engine,
            "scroll": scroll,
            "timeout": timeout,
        },
    })
    data = handle_response(response, output)
    click.echo(format_output(data, output))


@scrape.command("status")
@click.argument("job_id")
@click.option("--output", "-o", type=click.Choice(["table", "json"]), default="json", help="Output format")
def scrape_status(job_id: str, output: str):
    """Get the status of a scraping job."""
    client = VoyantClient()
    response = client.get(f"/scrape/status/{job_id}")
    data = handle_response(response, output)
    click.echo(format_output(data, output))
