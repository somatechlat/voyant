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
from typing import Any, Dict, List, Optional

import httpx
from ninja.errors import HttpError
from ninja.security import HttpBearer

from apps.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


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
    roles: List[str]
    permissions: List[str]
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
        self.keycloak_url = settings.keycloak_url
        self.realm = settings.keycloak_realm
        self.client_id = settings.keycloak_client_id
        self.client_secret = settings.keycloak_client_secret
        self._jwks: Optional[Dict[str, Any]] = None  # Cached JWKS.
        self._jwks_url = (
            f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/certs"
        )
        self._issuer = f"{self.keycloak_url}/realms/{self.realm}"

    def _get_jwks(self) -> Dict[str, Any]:
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
                raise HttpError(
                    503, "Authentication service (Keycloak) unavailable."
                ) from exc
        return self._jwks

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
            from jose import JWTError, jwt
            from jose.exceptions import ExpiredSignatureError

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
                raise HttpError(
                    401, "Invalid authentication token: signing key not found."
                )

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

            tenant_id = payload.get(
                "tenant_id", "default"
            )  # Custom claim for multi-tenancy.
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
            logger.warning("JWT token is expired.")
            raise HttpError(401, "Authentication token has expired.") from exc
        except JWTError as exc:
            logger.error("JWT validation error: %s", exc)
            raise HttpError(401, f"Invalid authentication token: {exc}.") from exc
        except HttpError:  # Re-raise HttpErrors from _get_jwks
            raise
        except Exception as exc:
            logger.exception("An unexpected error occurred during token validation.")
            raise HttpError(
                500, "Authentication failed due to internal error."
            ) from exc

    def _derive_permissions(self, roles: List[str]) -> List[str]:
        """
        Derives a list of granular permissions based on the user's assigned roles.

        Args:
            roles (List[str]): A list of role names assigned to the user.

        Returns:
            List[str]: A unique list of permissions the user possesses.
        """
        permissions = []

        # Define a mapping from roles to their associated permissions.
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

        # Aggregate permissions from all assigned roles.
        for role in roles:
            if role in role_map:
                permissions.extend(role_map[role])

        return list(set(permissions))  # Return unique permissions.


class KeycloakBearer(HttpBearer):
    """
    A Django Ninja `HttpBearer` authentication scheme for Keycloak-issued JWTs.

    This class integrates directly with Django Ninja's security mechanisms to
    authenticate requests using a Bearer token provided in the 'Authorization' header.
    """

    def authenticate(self, request, token: str) -> Optional[User]:
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
_auth: Optional[KeycloakAuth] = None


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


def _get_bearer_token(request) -> Optional[str]:
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
        raise HttpError(401, "Authentication required: No Bearer token provided.")
    return get_auth().validate_token(token)


def get_optional_user(request) -> Optional[User]:
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
        user = get_current_user(request)
        if not user.has_role(required_role):
            logger.warning(
                f"User {user.username} (tenant: {user.tenant_id}) attempted to access "
                f"resource requiring role '{required_role}' without permission."
            )
            raise HttpError(403, f"Access denied: Role '{required_role}' required.")
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
        user = get_current_user(request)
        if not user.has_permission(required_permission):
            logger.warning(
                f"User {user.username} (tenant: {user.tenant_id}) attempted to access "
                f"resource requiring permission '{required_permission}' without permission."
            )
            raise HttpError(
                403, f"Access denied: Permission '{required_permission}' required."
            )
        return user

    return permission_checker
