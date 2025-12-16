"""
OAuth Full Integration Module

Complete OAuth 2.0 implementation with PKCE, token refresh, and expiry.
Reference: STATUS.md Gap #1 - OAuth Full Integration

Features:
- Authorization Code Flow with PKCE
- Token storage with expiry tracking
- Automatic token refresh
- Multi-provider support (generic, Google, GitHub)
- Secure state parameter generation

Personas Applied:
- PhD Developer: OAuth 2.0 RFC compliance
- Analyst: Token lifecycle tracking
- QA: Error handling for all OAuth failures
- ISO Documenter: Complete flow documentation
- Security: PKCE, state validation, secure storage
- Performance: Token caching
- UX: Clear error messages

Usage:
    from voyant.core.oauth import (
        OAuthClient, create_authorization_url,
        exchange_code, refresh_token, get_valid_token
    )
    
    # Create authorization URL
    auth_url, state = create_authorization_url(
        provider="google",
        redirect_uri="http://localhost/callback",
        scopes=["openid", "email"],
    )
    
    # Exchange code for tokens
    tokens = await exchange_code(provider, code, state, code_verifier)
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode, urlparse, parse_qs

logger = logging.getLogger(__name__)


class OAuthProvider(str, Enum):
    """Supported OAuth providers."""
    GENERIC = "generic"
    GOOGLE = "google"
    GITHUB = "github"
    MICROSOFT = "microsoft"
    OKTA = "okta"


@dataclass
class OAuthConfig:
    """OAuth provider configuration."""
    provider: OAuthProvider
    client_id: str
    client_secret: str
    authorization_endpoint: str
    token_endpoint: str
    userinfo_endpoint: Optional[str] = None
    scopes: List[str] = field(default_factory=list)
    
    @classmethod
    def from_env(cls, provider: OAuthProvider) -> "OAuthConfig":
        """Load configuration from environment variables."""
        prefix = f"VOYANT_OAUTH_{provider.value.upper()}_"
        
        # Provider-specific defaults
        defaults = {
            OAuthProvider.GOOGLE: {
                "authorization_endpoint": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_endpoint": "https://oauth2.googleapis.com/token",
                "userinfo_endpoint": "https://openidconnect.googleapis.com/v1/userinfo",
                "scopes": ["openid", "email", "profile"],
            },
            OAuthProvider.GITHUB: {
                "authorization_endpoint": "https://github.com/login/oauth/authorize",
                "token_endpoint": "https://github.com/login/oauth/access_token",
                "userinfo_endpoint": "https://api.github.com/user",
                "scopes": ["read:user", "user:email"],
            },
            OAuthProvider.MICROSOFT: {
                "authorization_endpoint": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
                "token_endpoint": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
                "userinfo_endpoint": "https://graph.microsoft.com/v1.0/me",
                "scopes": ["openid", "email", "profile"],
            },
        }
        
        provider_defaults = defaults.get(provider, {})
        
        return cls(
            provider=provider,
            client_id=os.getenv(f"{prefix}CLIENT_ID", ""),
            client_secret=os.getenv(f"{prefix}CLIENT_SECRET", ""),
            authorization_endpoint=os.getenv(
                f"{prefix}AUTH_ENDPOINT",
                provider_defaults.get("authorization_endpoint", ""),
            ),
            token_endpoint=os.getenv(
                f"{prefix}TOKEN_ENDPOINT",
                provider_defaults.get("token_endpoint", ""),
            ),
            userinfo_endpoint=os.getenv(
                f"{prefix}USERINFO_ENDPOINT",
                provider_defaults.get("userinfo_endpoint"),
            ),
            scopes=provider_defaults.get("scopes", []),
        )


@dataclass
class TokenSet:
    """OAuth token set with metadata."""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    refresh_token: Optional[str] = None
    scope: str = ""
    id_token: Optional[str] = None
    
    # Metadata
    provider: str = ""
    issued_at: float = 0
    
    def __post_init__(self):
        if self.issued_at == 0:
            self.issued_at = time.time()
    
    @property
    def expires_at(self) -> float:
        return self.issued_at + self.expires_in
    
    @property
    def is_expired(self) -> bool:
        # Consider expired 60 seconds before actual expiry
        return time.time() > (self.expires_at - 60)
    
    @property
    def ttl_remaining(self) -> int:
        return max(0, int(self.expires_at - time.time()))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "access_token": self.access_token[:10] + "..." if len(self.access_token) > 10 else "***",
            "token_type": self.token_type,
            "expires_in": self.expires_in,
            "has_refresh_token": self.refresh_token is not None,
            "scope": self.scope,
            "provider": self.provider,
            "expires_at": datetime.fromtimestamp(self.expires_at).isoformat(),
            "is_expired": self.is_expired,
            "ttl_remaining": self.ttl_remaining,
        }


@dataclass
class PKCEChallenge:
    """PKCE code challenge for secure OAuth."""
    code_verifier: str
    code_challenge: str
    code_challenge_method: str = "S256"
    
    @classmethod
    def generate(cls) -> "PKCEChallenge":
        """Generate a new PKCE challenge."""
        # Generate random 43-128 character verifier
        code_verifier = secrets.token_urlsafe(32)
        
        # SHA256 hash and base64url encode
        digest = hashlib.sha256(code_verifier.encode()).digest()
        code_challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
        
        return cls(
            code_verifier=code_verifier,
            code_challenge=code_challenge,
        )


# =============================================================================
# Token Storage
# =============================================================================

class TokenStore:
    """
    In-memory token storage with expiry tracking.
    
    For production, use encrypted persistent storage.
    """
    
    def __init__(self):
        # Key: (provider, user_id) -> TokenSet
        self._tokens: Dict[tuple, TokenSet] = {}
        # Pending states: state -> (pkce, redirect_uri, created_at)
        self._pending_states: Dict[str, tuple] = {}
    
    def store_token(self, provider: str, user_id: str, token: TokenSet) -> None:
        """Store a token set."""
        key = (provider, user_id)
        token.provider = provider
        self._tokens[key] = token
        logger.info(f"Stored token for {provider}:{user_id}, expires in {token.ttl_remaining}s")
    
    def get_token(self, provider: str, user_id: str) -> Optional[TokenSet]:
        """Get a stored token."""
        return self._tokens.get((provider, user_id))
    
    def delete_token(self, provider: str, user_id: str) -> bool:
        """Delete a stored token."""
        key = (provider, user_id)
        if key in self._tokens:
            del self._tokens[key]
            return True
        return False
    
    def store_pending_state(
        self,
        state: str,
        pkce: PKCEChallenge,
        redirect_uri: str,
    ) -> None:
        """Store pending authorization state."""
        self._pending_states[state] = (pkce, redirect_uri, time.time())
        
        # Cleanup old states (> 10 minutes)
        cutoff = time.time() - 600
        self._pending_states = {
            k: v for k, v in self._pending_states.items()
            if v[2] > cutoff
        }
    
    def get_pending_state(self, state: str) -> Optional[tuple]:
        """Get and remove pending state."""
        return self._pending_states.pop(state, None)


_token_store = TokenStore()


# =============================================================================
# OAuth Client
# =============================================================================

class OAuthClient:
    """
    OAuth 2.0 client with PKCE support.
    
    Security: Uses PKCE for public clients, validates state parameter.
    """
    
    def __init__(self, config: OAuthConfig):
        self.config = config
    
    def create_authorization_url(
        self,
        redirect_uri: str,
        scopes: Optional[List[str]] = None,
        state: Optional[str] = None,
        use_pkce: bool = True,
    ) -> tuple[str, str, Optional[PKCEChallenge]]:
        """
        Create authorization URL for OAuth flow.
        
        Returns: (authorization_url, state, pkce_challenge)
        """
        # Generate state for CSRF protection
        state = state or secrets.token_urlsafe(16)
        
        # Generate PKCE challenge
        pkce = PKCEChallenge.generate() if use_pkce else None
        
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes or self.config.scopes),
            "state": state,
        }
        
        if pkce:
            params["code_challenge"] = pkce.code_challenge
            params["code_challenge_method"] = pkce.code_challenge_method
        
        # Store pending state
        _token_store.store_pending_state(state, pkce, redirect_uri)
        
        url = f"{self.config.authorization_endpoint}?{urlencode(params)}"
        return url, state, pkce
    
    async def exchange_code(
        self,
        code: str,
        redirect_uri: str,
        code_verifier: Optional[str] = None,
    ) -> TokenSet:
        """
        Exchange authorization code for tokens.
        
        Args:
            code: Authorization code from callback
            redirect_uri: Same redirect URI used in authorization
            code_verifier: PKCE code verifier (if PKCE was used)
        """
        import httpx
        
        data = {
            "grant_type": "authorization_code",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        }
        
        if code_verifier:
            data["code_verifier"] = code_verifier
        
        headers = {"Accept": "application/json"}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.config.token_endpoint,
                data=data,
                headers=headers,
            )
            
            if response.status_code != 200:
                error_data = response.json() if response.content else {}
                raise OAuthError(
                    f"Token exchange failed: {error_data.get('error', 'unknown')}",
                    error_data.get("error_description", ""),
                )
            
            token_data = response.json()
        
        return TokenSet(
            access_token=token_data["access_token"],
            token_type=token_data.get("token_type", "Bearer"),
            expires_in=token_data.get("expires_in", 3600),
            refresh_token=token_data.get("refresh_token"),
            scope=token_data.get("scope", ""),
            id_token=token_data.get("id_token"),
            provider=self.config.provider.value,
        )
    
    async def refresh_token(self, refresh_token: str) -> TokenSet:
        """
        Refresh an access token using refresh token.
        """
        import httpx
        
        data = {
            "grant_type": "refresh_token",
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "refresh_token": refresh_token,
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.config.token_endpoint,
                data=data,
                headers={"Accept": "application/json"},
            )
            
            if response.status_code != 200:
                error_data = response.json() if response.content else {}
                raise OAuthError(
                    f"Token refresh failed: {error_data.get('error', 'unknown')}",
                    error_data.get("error_description", ""),
                )
            
            token_data = response.json()
        
        return TokenSet(
            access_token=token_data["access_token"],
            token_type=token_data.get("token_type", "Bearer"),
            expires_in=token_data.get("expires_in", 3600),
            refresh_token=token_data.get("refresh_token", refresh_token),
            scope=token_data.get("scope", ""),
            provider=self.config.provider.value,
        )
    
    async def get_userinfo(self, access_token: str) -> Dict[str, Any]:
        """Get user info from provider."""
        import httpx
        
        if not self.config.userinfo_endpoint:
            raise OAuthError("Provider does not have userinfo endpoint")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.config.userinfo_endpoint,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            
            if response.status_code != 200:
                raise OAuthError(f"Userinfo request failed: {response.status_code}")
            
            return response.json()


class OAuthError(Exception):
    """OAuth error."""
    
    def __init__(self, message: str, description: str = ""):
        self.message = message
        self.description = description
        super().__init__(f"{message}: {description}" if description else message)


# =============================================================================
# High-Level API
# =============================================================================

_clients: Dict[str, OAuthClient] = {}


def get_oauth_client(provider: OAuthProvider) -> OAuthClient:
    """Get or create OAuth client for provider."""
    if provider.value not in _clients:
        config = OAuthConfig.from_env(provider)
        if not config.client_id:
            raise OAuthError(f"OAuth not configured for {provider.value}")
        _clients[provider.value] = OAuthClient(config)
    return _clients[provider.value]


def create_authorization_url(
    provider: str,
    redirect_uri: str,
    scopes: Optional[List[str]] = None,
) -> tuple[str, str]:
    """
    Create authorization URL.
    
    Returns: (url, state)
    """
    client = get_oauth_client(OAuthProvider(provider))
    url, state, _ = client.create_authorization_url(redirect_uri, scopes)
    return url, state


async def exchange_code(
    provider: str,
    code: str,
    state: str,
    redirect_uri: Optional[str] = None,
) -> TokenSet:
    """
    Exchange authorization code for tokens.
    
    Validates state and uses PKCE verifier if available.
    """
    # Validate state
    pending = _token_store.get_pending_state(state)
    if not pending:
        raise OAuthError("Invalid or expired state parameter")
    
    pkce, stored_redirect_uri, _ = pending
    redirect_uri = redirect_uri or stored_redirect_uri
    
    client = get_oauth_client(OAuthProvider(provider))
    code_verifier = pkce.code_verifier if pkce else None
    
    return await client.exchange_code(code, redirect_uri, code_verifier)


async def get_valid_token(
    provider: str,
    user_id: str,
) -> Optional[TokenSet]:
    """
    Get a valid token, refreshing if expired.
    
    Returns None if no token or refresh fails.
    """
    token = _token_store.get_token(provider, user_id)
    if not token:
        return None
    
    if not token.is_expired:
        return token
    
    # Try refresh
    if not token.refresh_token:
        logger.warning(f"Token expired and no refresh token for {provider}:{user_id}")
        return None
    
    try:
        client = get_oauth_client(OAuthProvider(provider))
        new_token = await client.refresh_token(token.refresh_token)
        _token_store.store_token(provider, user_id, new_token)
        return new_token
    except OAuthError as e:
        logger.error(f"Token refresh failed: {e}")
        return None


def store_token(provider: str, user_id: str, token: TokenSet) -> None:
    """Store a token for a user."""
    _token_store.store_token(provider, user_id, token)


def clear_token(provider: str, user_id: str) -> bool:
    """Clear a stored token."""
    return _token_store.delete_token(provider, user_id)


def reset_oauth():
    """Reset OAuth state (testing)."""
    global _clients
    _clients = {}
    _token_store._tokens.clear()
    _token_store._pending_states.clear()
