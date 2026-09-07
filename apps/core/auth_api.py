"""
Authentication API — Keycloak login endpoints for humans and agents.

Human login:  POST /auth/login  {username, password} → {access_token, refresh_token, user}
Agent login:  POST /auth/token  {client_id, client_secret} → {access_token, token_type}
Token refresh: POST /auth/refresh {refresh_token} → {access_token}
Logout:       POST /auth/logout
Who am I:     GET /auth/me
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from ninja import Router, Schema
from ninja.errors import HttpError

from apps.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

auth_router = Router(tags=["auth"])


# ── Schemas ─────────────────────────────────────────────────────────────────


class LoginRequest(Schema):
    username: str
    password: str


class TokenRequest(Schema):
    client_id: str
    client_secret: str


class RefreshRequest(Schema):
    refresh_token: str


class AuthResponse(Schema):
    access_token: str
    refresh_token: str = ""
    expires_in: int = 0
    token_type: str = "Bearer"
    user: dict[str, Any] = {}


class UserInfo(Schema):
    user_id: str
    email: str
    username: str
    tenant_id: str
    realm: str
    roles: list[str]
    permissions: list[str]


# ── Keycloak helpers ────────────────────────────────────────────────────────


def _keycloak_token(body: dict[str, str]) -> dict[str, Any]:
    """Exchange credentials for a Keycloak token."""
    token_url = (
        f"{settings.keycloak_url}/realms/{settings.keycloak_realm}"
        f"/protocol/openid-connect/token"
    )
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(token_url, data=body)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.json().get("error_description", str(exc))
        raise HttpError(401, f"Authentication failed: {detail}")
    except httpx.HTTPError as exc:
        raise HttpError(503, f"Keycloak unavailable: {exc}")


def _decode_token_info(token: str) -> dict[str, Any]:
    """Decode JWT without verification to extract user info (for response only)."""
    try:
        from jose import jwt  # type: ignore

        payload = jwt.get_unverified_claims(token)
        realm_access = payload.get("realm_access", {})
        roles = realm_access.get("roles", [])

        return {
            "user_id": payload.get("sub", ""),
            "email": payload.get("email", ""),
            "username": payload.get("preferred_username", ""),
            "tenant_id": payload.get("tenant_id", "default"),
            "realm": _extract_realm(payload.get("iss", "")),
            "roles": roles,
            "permissions": _derive_permissions(roles),
        }
    except Exception:
        return {}


def _extract_realm(issuer: str) -> str:
    parts = issuer.rstrip("/").split("/")
    return parts[-1] if len(parts) >= 2 and parts[-2].lower() == "realms" else "default"


def _derive_permissions(roles: list[str]) -> list[str]:
    role_map = {
        "voyant-admin": ["*"],
        "voyant-engineer": ["read:*", "write:sources", "write:jobs", "execute:sql", "execute:presets"],
        "voyant-analyst": ["read:*", "execute:sql", "execute:presets"],
        "voyant-viewer": ["read:dashboards", "read:reports", "read:artifacts"],
    }
    permissions = []
    for role in roles:
        if role in role_map:
            permissions.extend(role_map[role])
    return list(set(permissions))


# ── Endpoints ───────────────────────────────────────────────────────────────


@auth_router.post("/login", response=AuthResponse)
def login(request, payload: LoginRequest):
    """
    Human login via Keycloak password grant.

    Exchanges username + password for an access token.
    Returns user info decoded from the JWT.
    """
    data = _keycloak_token({
        "grant_type": "password",
        "client_id": settings.keycloak_client_id,
        "client_secret": settings.keycloak_client_secret,
        "username": payload.username,
        "password": payload.password,
        "scope": "openid profile email",
    })

    access_token = data.get("access_token", "")
    refresh_token = data.get("refresh_token", "")
    expires_in = data.get("expires_in", 300)
    user = _decode_token_info(access_token)

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        user=user,
    )


@auth_router.post("/token", response=AuthResponse)
def agent_token(request, payload: TokenRequest):
    """
    Agent/service login via Keycloak client credentials grant.

    For MCP tools, automated agents, and service-to-service auth.
    """
    data = _keycloak_token({
        "grant_type": "client_credentials",
        "client_id": payload.client_id,
        "client_secret": payload.client_secret,
        "scope": "openid",
    })

    access_token = data.get("access_token", "")
    expires_in = data.get("expires_in", 300)
    user = _decode_token_info(access_token)

    return AuthResponse(
        access_token=access_token,
        expires_in=expires_in,
        user=user,
    )


@auth_router.post("/refresh", response=AuthResponse)
def refresh(request, payload: RefreshRequest):
    """Refresh an expired access token."""
    data = _keycloak_token({
        "grant_type": "refresh_token",
        "client_id": settings.keycloak_client_id,
        "client_secret": settings.keycloak_client_secret,
        "refresh_token": payload.refresh_token,
    })

    access_token = data.get("access_token", "")
    refresh_token = data.get("refresh_token", "")
    expires_in = data.get("expires_in", 300)
    user = _decode_token_info(access_token)

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        user=user,
    )


@auth_router.get("/me", response=UserInfo)
def me(request):
    """Get current authenticated user info from the Bearer token."""
    from apps.core.security.auth import get_current_user

    user = get_current_user(request)
    return UserInfo(
        user_id=user.user_id,
        email=user.email,
        username=user.username,
        tenant_id=user.tenant_id,
        realm=user.realm,
        roles=user.roles,
        permissions=user.permissions,
    )


@auth_router.post("/logout")
def logout(request):
    """Logout — client should discard tokens."""
    return {"status": "ok", "message": "Discard your tokens. Keycloak session revoked client-side."}
