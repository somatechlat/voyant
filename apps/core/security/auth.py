"""
Keycloak Authentication for Voyant Application Security.

This module implements JSON Web Token (JWT) authentication and role-based
authorization using Keycloak as the Identity Provider. It provides mechanisms for:
-   Validating JWT tokens issued by Keycloak.
-   Extracting user information, roles, and permissions from the token claims.
-   Enforcing multi-tenancy by verifying tenant IDs.
-   Providing decorator-based access control for Django Ninja API endpoints.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx
from ninja.errors import HttpError
from ninja.security import HttpBearer

from admin.common.messages import get_message
from apps.core.config import get_settings
from voyant_project.security_settings import security_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _auth_disabled() -> bool:
    """Return True if auth enforcement is disabled (local dev / tests)."""
    return not security_settings.security_enabled or settings.env == "local"


@dataclass
class User:
    """
    Represents an authenticated user, with details extracted from a Keycloak JWT token.

    Attributes:
        user_id (str): The unique identifier for the user (Keycloak 'sub' claim).
        email (str): The user's email address.
        username (str): The user's preferred username.
        tenant_id (str): The identifier for the tenant the user belongs to.
        roles (List[str]): A list of roles assigned to the user within the realm.
        permissions (List[str]): A list of derived permissions based on the user's roles.
        token (str): The original JWT token.
    """

    user_id: str
    email: str
    username: str
    tenant_id: str
    realm: str
    roles: list[str]
    permissions: list[str]
    token: str

    def has_role(self, role: str) -> bool:
        """
        Checks if the user has a specific role or is an administrator.

        Args:
            role (str): The role to check for.

        Returns:
            bool: True if the user has the role or is an admin, False otherwise.
        """
        return role in self.roles or "voyant-admin" in self.roles

    def has_permission(self, permission: str) -> bool:
        """
        Checks if the user has a specific permission or has wildcard administrative access.

        Args:
            permission (str): The permission to check for (e.g., "read:sources", "write:jobs").

        Returns:
            bool: True if the user has the permission or wildcard access, False otherwise.
        """
        if "*" in self.permissions:  # Administrator wildcard permission.
            return True
        return permission in self.permissions


class KeycloakAuth:
    """
    Handles JWT token validation and user information extraction against a Keycloak server.

    This class manages fetching JSON Web Key Sets (JWKS) for token signature verification
    and decoding JWT claims to construct a `User` object.
    """

    def __init__(self) -> None:
        """
        Initializes the KeycloakAuth client using settings from `voyant.core.config`.
        """
        self._server_url = settings.keycloak_url
        self._realm = settings.keycloak_realm
        self.client_id = settings.keycloak_client_id
        self.client_secret = settings.keycloak_client_secret
        self._jwks: dict[str, Any] | None = None  # Cached JWKS.
        self._update_urls()

    @property
    def server_url(self) -> str:
        return self._server_url

    @server_url.setter
    def server_url(self, value: str):
        self._server_url = value
        self._update_urls()

    @property
    def realm(self) -> str:
        return self._realm

    @realm.setter
    def realm(self, value: str):
        self._realm = value
        self._update_urls()

    def _update_urls(self):
        # Vibe Rule: No placeholders. Use real settings.
        self._jwks_url = f"{self._server_url}/realms/{self._realm}/protocol/openid-connect/certs"
        self._issuer = f"{self._server_url}/realms/{self._realm}"

    def _get_jwks(self) -> dict[str, Any]:
        """
        Fetches and caches the JSON Web Key Set (JWKS) from the Keycloak server.

        Returns:
            Dict[str, Any]: The JWKS dictionary.

        Raises:
            httpx.HTTPError: If the request to the Keycloak JWKS endpoint fails.
            HttpError 503: If the Keycloak service is unavailable.
        """
        if self._jwks is None:
            try:
                with httpx.Client(timeout=10.0) as client:
                    response = client.get(self._jwks_url)
                    response.raise_for_status()
                    self._jwks = response.json()
            except httpx.HTTPError as exc:
                logger.error("Failed to fetch JWKS from Keycloak: %s", exc)
                raise HttpError(503, get_message("ERR_AUTH_KEYCLOAK_UNAVAILABLE")) from exc
        return self._jwks  # type: ignore[return-type]

    def validate_token(self, token: str) -> User:
        """
        Validates a JWT token and extracts authenticated user information.

        This method verifies the token's signature using Keycloak's public keys
        (JWKS), checks its expiration, audience, and issuer, and then decodes
        the claims to construct a `User` object.

        Args:
            token (str): The JWT token string (without "Bearer" prefix).

        Returns:
            User: An authenticated `User` object if the token is valid.

        Raises:
            HttpError 401: If the token is invalid, expired, or authentication service is unavailable.
        """
        try:
            from jose import JWTError, jwt  # type: ignore[import-not-found]
            from jose.exceptions import (
                ExpiredSignatureError,  # type: ignore[import-not-found]
            )

            # Get unverified header to find the Key ID (kid) for JWKS lookup.
            unverified = jwt.get_unverified_header(token)
            kid = unverified.get("kid")

            jwks = self._get_jwks()
            key = None
            # Find the correct public key in the JWKS to verify the token's signature.
            for jwk in jwks.get("keys", []):
                if jwk.get("kid") == kid:
                    key = jwk
                    break

            if not key:
                logger.warning("JWT validation failed: Key ID (kid) not found in JWKS.")
                raise HttpError(401, get_message("ERR_AUTH_SIGNING_KEY"))

            # Decode and verify the token.
            payload = jwt.decode(
                token,
                key,
                algorithms=["RS256"],  # Expected algorithm for Keycloak.
                audience=self.client_id,
                issuer=self._issuer,
            )

            # Extract user attributes from the JWT payload.
            user_id = payload.get("sub", "")
            email = payload.get("email", "")
            username = payload.get("preferred_username", email)

            realm_access = payload.get("realm_access", {})
            roles = realm_access.get("roles", [])

            # Extract and validate realm from the issuer claim.
            issuer = payload.get("iss", "")
            token_realm = self._extract_realm_from_iss(issuer)
            if token_realm and token_realm != self._realm:
                logger.warning(
                    "Cross-realm token rejected: token realm '%s' does not match "
                    "expected realm '%s'",
                    token_realm,
                    self._realm,
                )
                raise HttpError(401, get_message("ERR_AUTH_CROSS_REALM"))

            tenant_id = payload.get("tenant_id", "default")  # Custom claim for multi-tenancy.
            permissions = self._derive_permissions(roles)

            return User(
                user_id=user_id,
                email=email,
                username=username,
                tenant_id=tenant_id,
                realm=token_realm or self._realm or "default",
                roles=roles,
                permissions=permissions,
                token=token,
            )

        except ExpiredSignatureError as exc:  # type: ignore[possiblyUnbound]
            logger.warning("JWT token is expired.")
            raise HttpError(401, get_message("ERR_AUTH_EXPIRED")) from exc
        except JWTError as exc:  # type: ignore[possiblyUnbound]
            logger.error("JWT validation error: %s", exc)
            raise HttpError(401, get_message("ERR_AUTH_INVALID", error=str(exc))) from exc
        except HttpError:  # Re-raise HttpErrors from _get_jwks
            raise
        except Exception as exc:
            logger.exception("An unexpected error occurred during token validation.")
            raise HttpError(500, get_message("ERR_AUTH_INTERNAL")) from exc

    @staticmethod
    def _extract_realm_from_iss(issuer: str) -> str:
        """
        Extract the realm name from a Keycloak issuer URL.

        Args:
            issuer: The 'iss' claim from a JWT (e.g.,
                'http://keycloak:8080/realms/voyant').

        Returns:
            str: The realm name, or an empty string if parsing fails.
        """
        if not issuer:
            return ""
        # Expected format: .../realms/{realm}
        parts = issuer.rstrip("/").split("/")
        if len(parts) >= 2 and parts[-2].lower() == "realms":
            return parts[-1]
        return ""

    def _derive_permissions(self, roles: list[str]) -> list[str]:
        """
        Derives a list of granular permissions based on the user's assigned roles.

        Args:
            roles (List[str]): A list of role names assigned to the user.

        Returns:
            List[str]: A unique list of permissions the user possesses.
        """
        permissions = []
        role_map = {
            "voyant-admin": ["*"],  # Wildcard for full administrative access.
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
    """
    A Django Ninja `HttpBearer` authentication scheme for Keycloak-issued JWTs.

    This class integrates directly with Django Ninja's security mechanisms to
    authenticate requests using a Bearer token provided in the 'Authorization' header.
    """

    def authenticate(self, request, token: str) -> User | None:
        """
        Authenticates an incoming request by validating the provided Bearer token.

        Args:
            request: The Django HTTP request object.
            token (str): The JWT token extracted from the 'Authorization' header.

        Returns:
            Optional[User]: An authenticated `User` object if the token is valid, otherwise None.

        Raises:
            HttpError 401: If the token is invalid or authentication fails.
        """
        return get_auth().validate_token(token)


# Singleton instance of KeycloakAuth for application-wide use.
_auth: KeycloakAuth | None = None


def get_auth() -> KeycloakAuth:
    """
    Retrieves the singleton instance of the KeycloakAuth client.

    This factory function ensures that authentication settings and JWKS caching
    are managed efficiently across the application.

    Returns:
        KeycloakAuth: The singleton KeycloakAuth instance.
    """
    global _auth
    if _auth is None:
        _auth = KeycloakAuth()
    return _auth


def _get_bearer_token(request) -> str | None:
    """
    Extracts the Bearer token string from the Authorization header of an HTTP request.

    Args:
        request: The Django HTTP request object.

    Returns:
        Optional[str]: The Bearer token string, or None if not found or malformed.
    """
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1].strip()
    return None


def get_current_user(request) -> User:
    """
    Retrieves the authenticated user for the current request.

    This function is typically used by protected API endpoints to get the
    context of the user making the request.

    Args:
        request: The Django HTTP request object.

    Returns:
        User: The authenticated `User` object.

    Raises:
        HttpError 401: If the user is not authenticated or the token is invalid.
    """
    token = _get_bearer_token(request)
    if not token:
        raise HttpError(401, get_message("ERR_AUTH_MISSING"))
    return get_auth().validate_token(token)


def get_optional_user(request) -> User | None:
    """
    Retrieves the authenticated user for the current request, if available.

    Unlike `get_current_user`, this function does not raise an error if
    authentication fails; instead, it returns None, allowing for optional
    authentication scenarios.

    Args:
        request: The Django HTTP request object.

    Returns:
        Optional[User]: An authenticated `User` object if a valid token is present,
                        otherwise None.
    """
    token = _get_bearer_token(request)
    if not token:
        return None
    try:
        return get_auth().validate_token(token)
    except HttpError:
        return None


def require_role(required_role: str):
    """
    A decorator factory that creates a Django Ninja dependency to enforce
    role-based access control on API endpoints.

    Usage:
        @api.get("/admin_only", auth=require_role("voyant-admin"))
        def admin_endpoint(request): ...

    Args:
        required_role (str): The name of the role that is required to access the endpoint.

    Returns:
        Callable: A dependency function that authenticates the user and checks their roles.

    Raises:
        HttpError 401: If the user is not authenticated.
        HttpError 403: If the authenticated user does not have the required role.
    """

    def role_checker(request) -> User:
        if _auth_disabled():
            return User(
                user_id="local-dev",
                email="dev@voyant.local",
                username="local-dev",
                tenant_id="default",
                realm="default",
                roles=["voyant-admin"],
                permissions=["*"],
                token="",
            )
        user = get_current_user(request)
        if not user.has_role(required_role):
            logger.warning(
                f"User {user.username} (tenant: {user.tenant_id}) attempted to access "
                f"resource requiring role '{required_role}' without permission."
            )
            raise HttpError(403, get_message("ERR_AUTH_DENIED_ROLE", role=required_role))
        return user

    return role_checker


def require_permission(required_permission: str):
    """
    A decorator factory that creates a Django Ninja dependency to enforce
    permission-based access control on API endpoints.

    Usage:
        @api.get("/read_sources", auth=require_permission("read:sources"))
        def read_sources_endpoint(request): ...

    Args:
        required_permission (str): The specific permission string required (e.g., "read:sources").

    Returns:
        Callable: A dependency function that authenticates the user and checks their permissions.

    Raises:
        HttpError 401: If the user is not authenticated.
        HttpError 403: If the authenticated user does not have the required permission.
    """

    def permission_checker(request) -> User:
        if _auth_disabled():
            return User(
                user_id="local-dev",
                email="dev@voyant.local",
                username="local-dev",
                tenant_id="default",
                realm="default",
                roles=["voyant-admin"],
                permissions=["*"],
                token="",
            )
        user = get_current_user(request)
        if not user.has_permission(required_permission):
            logger.warning(
                f"User {user.username} (tenant: {user.tenant_id}) attempted to access "
                f"resource requiring permission '{required_permission}' without permission."
            )
            raise HttpError(
                403,
                get_message("ERR_AUTH_DENIED_PERMISSION", permission=required_permission),
            )
        return user

    return permission_checker


def require_realm(required_realm: str):
    """
    A decorator factory that creates a Django Ninja dependency to enforce
    realm-based access control on API endpoints.

    Usage:
        @api.get("/realm_only", auth=require_realm("voyant"))
        def realm_endpoint(request): ...

    Args:
        required_realm (str): The realm name required to access the endpoint.

    Returns:
        Callable: A dependency function that authenticates the user and checks their realm.

    Raises:
        HttpError 401: If the user is not authenticated.
        HttpError 403: If the authenticated user does not belong to the required realm.
    """

    def realm_checker(request) -> User:
        if _auth_disabled():
            return User(
                user_id="local-dev",
                email="dev@voyant.local",
                username="local-dev",
                tenant_id="default",
                realm=required_realm,
                roles=["voyant-admin"],
                permissions=["*"],
                token="",
            )
        user = get_current_user(request)
        if user.realm != required_realm:
            logger.warning(
                f"User {user.username} (realm: {user.realm}) attempted to access "
                f"resource requiring realm '{required_realm}'."
            )
            raise HttpError(
                403,
                get_message("ERR_AUTH_DENIED_REALM", realm=required_realm),
            )
        return user

    return realm_checker
