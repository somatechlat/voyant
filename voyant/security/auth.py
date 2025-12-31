"""
Keycloak Authentication for Voyant

JWT token validation and user extraction from Keycloak.
Implements OAuth 2.0 / OpenID Connect.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx
from ninja.errors import HttpError
from ninja.security import HttpBearer

from voyant.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class User:
    """Authenticated user from Keycloak token."""
    user_id: str
    email: str
    username: str
    tenant_id: str
    roles: List[str]
    permissions: List[str]
    token: str

    def has_role(self, role: str) -> bool:
        return role in self.roles or "voyant-admin" in self.roles

    def has_permission(self, permission: str) -> bool:
        if "*" in self.permissions:
            return True
        return permission in self.permissions


class KeycloakAuth:
    """Keycloak authentication handler."""

    def __init__(self) -> None:
        self.keycloak_url = settings.keycloak_url
        self.realm = settings.keycloak_realm
        self.client_id = settings.keycloak_client_id
        self.client_secret = settings.keycloak_client_secret
        self._jwks: Optional[Dict[str, Any]] = None
        self._jwks_url = f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/certs"
        self._issuer = f"{self.keycloak_url}/realms/{self.realm}"

    def _get_jwks(self) -> Dict[str, Any]:
        if self._jwks is None:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(self._jwks_url)
                response.raise_for_status()
                self._jwks = response.json()
        return self._jwks

    def validate_token(self, token: str) -> User:
        """Validate JWT token and extract user info."""
        try:
            from jose import JWTError, jwt
            from jose.exceptions import ExpiredSignatureError

            unverified = jwt.get_unverified_header(token)
            kid = unverified.get("kid")

            jwks = self._get_jwks()
            key = None
            for jwk in jwks.get("keys", []):
                if jwk.get("kid") == kid:
                    key = jwk
                    break

            if not key:
                raise HttpError(401, "Invalid token: key not found")

            payload = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=self._issuer,
            )

            user_id = payload.get("sub", "")
            email = payload.get("email", "")
            username = payload.get("preferred_username", email)

            realm_access = payload.get("realm_access", {})
            roles = realm_access.get("roles", [])

            tenant_id = payload.get("tenant_id", "default")
            permissions = self._derive_permissions(roles)

            return User(
                user_id=user_id,
                email=email,
                username=username,
                tenant_id=tenant_id,
                roles=roles,
                permissions=permissions,
                token=token,
            )

        except ExpiredSignatureError as exc:
            raise HttpError(401, "Token expired") from exc
        except JWTError as exc:
            logger.error("JWT validation error: %s", exc)
            raise HttpError(401, "Invalid token") from exc
        except httpx.HTTPError as exc:
            logger.error("Keycloak connection error: %s", exc)
            raise HttpError(503, "Authentication service unavailable") from exc

    def _derive_permissions(self, roles: List[str]) -> List[str]:
        permissions = []

        role_map = {
            "voyant-admin": ["*"],
            "voyant-engineer": [
                "read:*",
                "write:sources",
                "write:jobs",
                "execute:sql",
                "execute:presets",
            ],
            "voyant-analyst": ["read:*", "execute:sql", "execute:presets"],
            "voyant-viewer": ["read:dashboards", "read:reports", "read:artifacts"],
        }

        for role in roles:
            if role in role_map:
                permissions.extend(role_map[role])

        return list(set(permissions))


class KeycloakBearer(HttpBearer):
    """Django Ninja bearer auth wrapper for Keycloak."""

    def authenticate(self, request, token):
        return get_auth().validate_token(token)


_auth: Optional[KeycloakAuth] = None


def get_auth() -> KeycloakAuth:
    global _auth
    if _auth is None:
        _auth = KeycloakAuth()
    return _auth


def _get_bearer_token(request) -> Optional[str]:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1].strip()
    return None


def get_current_user(request) -> User:
    token = _get_bearer_token(request)
    if not token:
        raise HttpError(401, "Not authenticated")
    return get_auth().validate_token(token)


def get_optional_user(request) -> Optional[User]:
    token = _get_bearer_token(request)
    if not token:
        return None
    try:
        return get_auth().validate_token(token)
    except HttpError:
        return None


def require_role(required_role: str):
    def role_checker(request) -> User:
        user = get_current_user(request)
        if not user.has_role(required_role):
            raise HttpError(403, f"Role '{required_role}' required")
        return user

    return role_checker


def require_permission(required_permission: str):
    def permission_checker(request) -> User:
        user = get_current_user(request)
        if not user.has_permission(required_permission):
            raise HttpError(403, f"Permission '{required_permission}' required")
        return user

    return permission_checker
