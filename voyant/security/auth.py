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
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from voyant.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# JWT Bearer scheme
bearer_scheme = HTTPBearer(auto_error=False)


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
    
    def __init__(self):
        self.keycloak_url = settings.keycloak_url
        self.realm = settings.keycloak_realm
        self.client_id = settings.keycloak_client_id
        self.client_secret = settings.keycloak_client_secret
        self._jwks = None
        self._jwks_url = f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/certs"
        self._issuer = f"{self.keycloak_url}/realms/{self.realm}"
    
    async def _get_jwks(self) -> Dict[str, Any]:
        """Fetch JWKS from Keycloak."""
        if self._jwks is None:
            async with httpx.AsyncClient() as client:
                response = await client.get(self._jwks_url)
                response.raise_for_status()
                self._jwks = response.json()
        return self._jwks
    
    async def validate_token(self, token: str) -> User:
        """Validate JWT token and extract user info."""
        try:
            from jose import jwt, JWTError
            from jose.exceptions import ExpiredSignatureError
            
            # Decode without verification first to get kid
            unverified = jwt.get_unverified_header(token)
            kid = unverified.get("kid")
            
            # Get JWKS and find matching key
            jwks = await self._get_jwks()
            key = None
            for jwk in jwks.get("keys", []):
                if jwk.get("kid") == kid:
                    key = jwk
                    break
            
            if not key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: key not found",
                )
            
            # Verify and decode token
            payload = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=self._issuer,
            )
            
            # Extract user info
            user_id = payload.get("sub", "")
            email = payload.get("email", "")
            username = payload.get("preferred_username", email)
            
            # Extract roles from realm_access
            realm_access = payload.get("realm_access", {})
            roles = realm_access.get("roles", [])
            
            # Extract tenant from custom claim or use default
            tenant_id = payload.get("tenant_id", "default")
            
            # Derive permissions from roles
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
            
        except ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
            )
        except JWTError as e:
            logger.error(f"JWT validation error: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
        except httpx.HTTPError as e:
            logger.error(f"Keycloak connection error: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable",
            )
    
    def _derive_permissions(self, roles: List[str]) -> List[str]:
        """Derive permissions from roles."""
        permissions = []
        
        role_map = {
            "voyant-admin": ["*"],
            "voyant-engineer": [
                "read:*", "write:sources", "write:jobs", 
                "execute:sql", "execute:presets"
            ],
            "voyant-analyst": [
                "read:*", "execute:sql", "execute:presets"
            ],
            "voyant-viewer": [
                "read:dashboards", "read:reports", "read:artifacts"
            ],
        }
        
        for role in roles:
            if role in role_map:
                permissions.extend(role_map[role])
        
        return list(set(permissions))


# Singleton auth handler
_auth: Optional[KeycloakAuth] = None

def get_auth() -> KeycloakAuth:
    global _auth
    if _auth is None:
        _auth = KeycloakAuth()
    return _auth


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> User:
    """Dependency to get current authenticated user."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    auth = get_auth()
    return await auth.validate_token(credentials.credentials)


async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[User]:
    """Dependency to get user if authenticated (optional)."""
    if credentials is None:
        return None
    
    try:
        auth = get_auth()
        return await auth.validate_token(credentials.credentials)
    except HTTPException:
        return None


def require_role(required_role: str):
    """Dependency factory to require specific role."""
    async def role_checker(user: User = Depends(get_current_user)) -> User:
        if not user.has_role(required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required",
            )
        return user
    return role_checker


def require_permission(required_permission: str):
    """Dependency factory to require specific permission."""
    async def permission_checker(user: User = Depends(get_current_user)) -> User:
        if not user.has_permission(required_permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{required_permission}' required",
            )
        return user
    return permission_checker
