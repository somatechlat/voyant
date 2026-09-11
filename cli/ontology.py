"""Ontology commands for the Voyant CLI."""

from __future__ import annotations

import click

from cli.client import VoyantClient, format_output, handle_response


@click.group()
def ontology():
    """Query and manage the ontology engine."""
    pass


@ontology.group("types")
def types_group():
    """Manage object types."""
    pass


@types_group.command("list")
@click.option("--limit", "-l", default=50, help="Maximum number of types to return")
@click.option("--output", "-o", type=click.Choice(["table", "json"]), default="table", help="Output format")
def list_types(limit: int, output: str):
    """List all object types."""
    client = VoyantClient()
    response = client.get("/ontology/object-types", params={"limit": limit})
    data = handle_response(response, output)
    click.echo(format_output(data, output))


@types_group.command("get")
@click.argument("type_id")
@click.option("--output", "-o", type=click.Choice(["table", "json"]), default="json", help="Output format")
def get_type(type_id: str, output: str):
    """Get details for a specific object type."""
    client = VoyantClient()
    response = client.get(f"/ontology/object-types/{type_id}")
    data = handle_response(response, output)
    click.echo(format_output(data, output))


@ontology.group("objects")
def objects_group():
    """Manage object instances."""
    pass


@objects_group.command("list")
@click.argument("type_name")
@click.option("--limit", "-l", default=50, help="Maximum number of objects to return")
@click.option("--output", "-o", type=click.Choice(["table", "json"]), default="table", help="Output format")
def list_objects(type_name: str, limit: int, output: str):
    """List objects of a specific type."""
    client = VoyantClient()
    response = client.get(
        "/ontology/objects",
        params={"object_type": type_name, "limit": limit},
    )
    data = handle_response(response, output)
    click.echo(format_output(data, output))


@objects_group.command("get")
@click.argument("object_id")
@click.option("--output", "-o", type=click.Choice(["table", "json"]), default="json", help="Output format")
def get_object(object_id: str, output: str):
    """Get details for a specific object."""
    client = VoyantClient()
    response = client.get(f"/ontology/objects/{object_id}")
    data = handle_response(response, output)
    click.echo(format_output(data, output))


@ontology.group("links")
def links_group():
    """Manage link types and instances."""
    pass


@links_group.command("list-types")
@click.option("--limit", "-l", default=50, help="Maximum number of link types to return")
@click.option("--output", "-o", type=click.Choice(["table", "json"]), default="table", help="Output format")
def list_link_types(limit: int, output: str):
    """List all link types."""
    client = VoyantClient()
    response = client.get("/ontology/link-types", params={"limit": limit})
    data = handle_response(response, output)
    click.echo(format_output(data, output))
