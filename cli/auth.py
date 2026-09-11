"""Authentication commands for the Voyant CLI."""

from __future__ import annotations

import sys

import click

from cli.client import VoyantClient, handle_response
from cli.config import load_config, save_config, save_credentials


@click.group()
def auth():
    """Manage authentication with Voyant."""
    pass


@auth.command()
@click.option("--username", "-u", prompt="Username", help="Voyant username")
@click.option("--password", "-p", prompt=True, hide_input=True, help="Password")
@click.option("--keycloak-url", envvar="VOYANT_KEYCLOAK_URL", help="Keycloak server URL")
@click.option("--realm", default="voyant", help="Keycloak realm name")
@click.option("--client-id", default="voyant-cli", help="Keycloak client ID")
def login(username: str, password: str, keycloak_url: str | None, realm: str, client_id: str):
    """Authenticate with Voyant via Keycloak."""
    config = load_config()

    if not keycloak_url:
        keycloak_url = config.get("keycloak_url") or "http://localhost:8080/realms"

    token_url = f"{keycloak_url}/{realm}/protocol/openid-connect/token"

    import httpx

    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(
                token_url,
                data={
                    "grant_type": "password",
                    "client_id": client_id,
                    "username": username,
                    "password": password,
                    "scope": "openid profile email",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
    except httpx.ConnectError:
        click.echo(f"Error: Cannot connect to Keycloak at {token_url}", err=True)
        sys.exit(1)

    if response.status_code != 200:
        click.echo(f"Error: Authentication failed ({response.status_code})", err=True)
        try:
            detail = response.json()
            click.echo(f"  {detail.get('error_description', detail.get('error', 'Unknown error'))}", err=True)
        except Exception:
            click.echo(f"  {response.text}", err=True)
        sys.exit(1)

    token_data = response.json()
    save_credentials({
        "access_token": token_data["access_token"],
        "refresh_token": token_data.get("refresh_token"),
        "token_type": token_data.get("token_type", "Bearer"),
        "expires_in": token_data.get("expires_in"),
        "username": username,
    })

    config["keycloak_url"] = keycloak_url
    config["realm"] = realm
    save_config(config)

    click.echo(f"Authenticated successfully as {username}")


@auth.command()
def whoami():
    """Show the currently authenticated user."""
    from cli.config import get_auth_token, load_credentials

    creds = load_credentials()
    token = get_auth_token()

    if not token:
        click.echo("Not authenticated. Run 'voyant auth login' first.", err=True)
        sys.exit(1)

    username = creds.get("username", "unknown")
    click.echo(f"Authenticated as: {username}")


@auth.command()
def logout():
    """Remove stored credentials."""
    from cli.config import get_credentials_file

    cred_file = get_credentials_file()
    if cred_file.exists():
        cred_file.unlink()
    click.echo("Logged out successfully.")
