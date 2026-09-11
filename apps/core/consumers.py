"""
WebSocket consumers for real-time event subscriptions.

Provides authenticated WebSocket endpoints for subscribing to:
- Ontology change notifications
- Job status updates
- Agent events
- Scraper events

Authentication is performed via JWT token supplied as a query parameter
(`?token=<jwt>`) or in the first JSON message (`{"action": "auth", "token": "<jwt>"}`).

Protocol:
  Client → Server:
    {"action": "subscribe", "channels": ["ontology_changes", "job_status"]}
    {"action": "unsubscribe", "channels": ["job_status"]}
    {"action": "ping"}

  Server → Client:
    {"type": "subscription.confirmed", "channels": [...]}
    {"type": "event", "channel": "ontology_changes", "data": {...}}
    {"type": "pong"}
    {"type": "error", "message": "..."}
"""

from __future__ import annotations

import logging
from urllib.parse import parse_qs

from channels.generic.websocket import AsyncJsonWebsocketConsumer

logger = logging.getLogger(__name__)

# ── Valid channel names that clients may subscribe to ──────────────────────
VALID_CHANNELS = frozenset(
    {
        "ontology_changes",
        "job_status",
        "agent_events",
        "scraper_events",
    }
)


class VoyantConsumer(AsyncJsonWebsocketConsumer):
    """
    Generic real-time event consumer.

    Each connection can subscribe to any combination of the valid channels.
    Messages published to those channel-layer groups are forwarded to the
    connected client as JSON.
    """

    # Set during connect; used for tenant-scoped group names
    tenant_id: str = ""
    user_id: str = ""
    # Channels this connection is currently subscribed to
    _subscribed_channels: set[str]

    # ── Connection lifecycle ───────────────────────────────────────────────

    async def connect(self) -> None:
        """Accept connection if a valid JWT is present in the query string."""
        self._subscribed_channels = set()

        # Attempt JWT auth from query parameter
        query_params = parse_qs(self.scope.get("query_string", b"").decode())
        token = (query_params.get("token") or [None])[0]

        if token:
            user = await self._authenticate(token)
            if user is None:
                await self.close(code=4001)
                return
            self._set_user_context(user)
            await self.accept()
            await self.send_json(
                {
                    "type": "connected",
                    "user_id": self.user_id,
                    "tenant_id": self.tenant_id,
                }
            )
            logger.info(
                "WebSocket authenticated via query param: user=%s tenant=%s",
                self.user_id,
                self.tenant_id,
            )
        else:
            # Accept without auth; client must send auth message first
            await self.accept()
            await self.send_json(
                {
                    "type": "auth_required",
                    "message": 'Send {"action": "auth", "token": "<jwt>"} to authenticate.',
                }
            )

    async def disconnect(self, close_code: int) -> None:  # type: ignore[reportIncompatibleMethodOverride]
        """Leave all channel-layer groups on disconnect."""
        for channel in self._subscribed_channels:
            group_name = self._group_name(channel)
            await self.channel_layer.group_discard(group_name, self.channel_name)
        self._subscribed_channels.clear()
        logger.info(
            "WebSocket disconnected: user=%s tenant=%s code=%d",
            self.user_id,
            self.tenant_id,
            close_code,
        )

    # ── Incoming message handling ──────────────────────────────────────────

    async def receive_json(self, content: dict, **kwargs) -> None:
        """Route incoming client messages by ``action`` field."""
        action = content.get("action", "")

        if action == "auth":
            await self._handle_auth(content)
        elif action == "subscribe":
            await self._handle_subscribe(content)
        elif action == "unsubscribe":
            await self._handle_unsubscribe(content)
        elif action == "ping":
            await self.send_json({"type": "pong"})
        else:
            await self._send_error(f"Unknown action: {action}")

    # ── Action handlers ────────────────────────────────────────────────────

    async def _handle_auth(self, content: dict) -> None:
        """Authenticate via a message-level token (alternative to query param)."""
        if self.user_id:
            await self._send_error("Already authenticated")
            return

        token = content.get("token", "")
        if not token:
            await self._send_error("Missing token")
            return

        user = await self._authenticate(token)
        if user is None:
            await self.send_json(
                {"type": "auth_failed", "message": "Invalid or expired token"}
            )
            await self.close(code=4001)
            return

        self._set_user_context(user)
        await self.send_json(
            {
                "type": "authenticated",
                "user_id": self.user_id,
                "tenant_id": self.tenant_id,
            }
        )
        logger.info(
            "WebSocket authenticated via message: user=%s tenant=%s",
            self.user_id,
            self.tenant_id,
        )

    async def _handle_subscribe(self, content: dict) -> None:
        """Subscribe to one or more event channels."""
        if not self.user_id:
            await self._send_error("Not authenticated. Send auth action first.")
            return

        channels = content.get("channels", [])
        if not isinstance(channels, list) or not channels:
            await self._send_error("'channels' must be a non-empty list")
            return

        added = []
        for ch in channels:
            if ch not in VALID_CHANNELS:
                await self._send_error(f"Invalid channel: {ch}")
                continue
            if ch not in self._subscribed_channels:
                group = self._group_name(ch)
                await self.channel_layer.group_add(group, self.channel_name)
                self._subscribed_channels.add(ch)
                added.append(ch)

        if added:
            await self.send_json(
                {
                    "type": "subscription.confirmed",
                    "channels": sorted(self._subscribed_channels),
                }
            )
            logger.info(
                "User %s subscribed to %s (total: %s)",
                self.user_id,
                added,
                sorted(self._subscribed_channels),
            )

    async def _handle_unsubscribe(self, content: dict) -> None:
        """Unsubscribe from one or more event channels."""
        channels = content.get("channels", [])
        if not isinstance(channels, list):
            await self._send_error("'channels' must be a list")
            return

        removed = []
        for ch in channels:
            if ch in self._subscribed_channels:
                group = self._group_name(ch)
                await self.channel_layer.group_discard(group, self.channel_name)
                self._subscribed_channels.discard(ch)
                removed.append(ch)

        if removed:
            await self.send_json(
                {
                    "type": "unsubscription.confirmed",
                    "channels": sorted(self._subscribed_channels),
                }
            )

    # ── Channel-layer message handlers ─────────────────────────────────────
    # These are called by Channels when a message arrives on a group this
    # consumer belongs to.  The ``type`` key maps to ``event_{type}``.

    async def event_ontology_change(self, event: dict) -> None:
        """Forward an ontology change event to the WebSocket client."""
        await self.send_json(
            {
                "type": "event",
                "channel": "ontology_changes",
                "data": event.get("data", {}),
            }
        )

    async def event_job_status(self, event: dict) -> None:
        """Forward a job status update to the WebSocket client."""
        await self.send_json(
            {
                "type": "event",
                "channel": "job_status",
                "data": event.get("data", {}),
            }
        )

    async def event_agent_event(self, event: dict) -> None:
        """Forward an agent event to the WebSocket client."""
        await self.send_json(
            {
                "type": "event",
                "channel": "agent_events",
                "data": event.get("data", {}),
            }
        )

    async def event_scraper_event(self, event: dict) -> None:
        """Forward a scraper event to the WebSocket client."""
        await self.send_json(
            {
                "type": "event",
                "channel": "scraper_events",
                "data": event.get("data", {}),
            }
        )

    # ── Helpers ────────────────────────────────────────────────────────────

    def _group_name(self, channel: str) -> str:
        """Build a tenant-scoped channel-layer group name."""
        tenant = self.tenant_id or "global"
        return f"voyant_{tenant}_{channel}"

    def _set_user_context(self, user) -> None:
        """Store user identity from the validated auth result."""
        self.user_id = user.get("user_id", "")
        self.tenant_id = user.get("tenant_id", "default")
        # Store in scope so downstream middleware / handlers can access
        self.scope["user_id"] = self.user_id  # type: ignore[reportGeneralTypeIssues]
        self.scope["tenant_id"] = self.tenant_id  # type: ignore[reportGeneralTypeIssues]

    async def _authenticate(self, token: str) -> dict | None:
        """
        Validate a JWT token using the project's KeycloakAuth backend.

        Returns a dict with ``user_id`` and ``tenant_id`` on success, or
        ``None`` if the token is invalid.
        """
        try:
            from apps.core.security.auth import get_auth

            auth = get_auth()
            # validate_token is sync (CPU-bound JWT decode) — run in thread
            import asyncio

            loop = asyncio.get_running_loop()
            user = await loop.run_in_executor(None, auth.validate_token, token)
            return {
                "user_id": user.user_id,
                "tenant_id": user.tenant_id,
            }
        except Exception as exc:
            logger.warning("WebSocket auth failed: %s", exc)
            return None

    async def _send_error(self, message: str) -> None:
        """Send a structured error message to the client."""
        await self.send_json({"type": "error", "message": message})
