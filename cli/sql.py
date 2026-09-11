"""SQL query commands for the Voyant CLI."""

from __future__ import annotations

import click

from cli.client import VoyantClient, format_output, handle_response


@click.group()
def sql():
    """Execute SQL queries against the data platform."""
    pass


@sql.command("query")
@click.argument("sql_text")
@click.option("--limit", "-l", default=1000, help="Maximum number of rows to return")
@click.option("--output", "-o", type=click.Choice(["table", "json"]), default="table", help="Output format")
def run_query(sql_text: str, limit: int, output: str):
    """Execute a SQL query. Only SELECT queries are allowed."""
    client = VoyantClient()
    response = client.post("/sql/query", json_body={"sql": sql_text, "limit": limit})
    data = handle_response(response, output)

    if output == "json":
        click.echo(format_output(data, output))
    else:
        # Format as a proper table with columns
        columns = data.get("columns", [])
        rows = data.get("rows", [])
        if not columns:
            click.echo("No results.")
            return

        # Compute column widths
        widths = [len(c) for c in columns]
        for row in rows:
            for i, val in enumerate(row):
                if i < len(widths):
                    widths[i] = max(widths[i], len(str(val)))

        # Header
        header = "  ".join(c.ljust(widths[i]) for i, c in enumerate(columns))
        separator = "  ".join("-" * widths[i] for i in range(len(columns)))
        click.echo(header)
        click.echo(separator)
        for row in rows:
            line = "  ".join(str(row[i]).ljust(widths[i]) if i < len(row) else "" for i in range(len(columns)))
            click.echo(line)

        click.echo(f"\n{data.get('row_count', len(rows))} rows returned"
                    + (" (truncated)" if data.get("truncated") else "")
                    + f" [{data.get('execution_time_ms', '?')}ms]")


@sql.command("tables")
@click.option("--schema", "-s", help="Filter by schema name")
@click.option("--output", "-o", type=click.Choice(["table", "json"]), default="table", help="Output format")
def list_tables(schema: str | None, output: str):
    """List available tables."""
    client = VoyantClient()
    params = {}
    if schema:
        params["schema"] = schema
    response = client.get("/sql/tables", params=params)
    data = handle_response(response, output)
    click.echo(format_output(data, output))


@sql.command("columns")
@click.argument("table_name")
@click.option("--schema", "-s", help="Schema name")
@click.option("--output", "-o", type=click.Choice(["table", "json"]), default="table", help="Output format")
def get_columns(table_name: str, schema: str | None, output: str):
    """Get columns for a specific table."""
    client = VoyantClient()
    params = {}
    if schema:
        params["schema"] = schema
    response = client.get(f"/sql/tables/{table_name}/columns", params=params)
    data = handle_response(response, output)
    click.echo(format_output(data, output))
