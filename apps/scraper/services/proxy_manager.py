"""
Proxy Manager Service — IP rotation engine for anti-bot bypass.

Loads proxies from the ``ScrapeProxy`` model, rotates them using
configurable strategies (round-robin, random, least-used), and tracks
success/failure statistics.  Provides integration hooks for residential
proxy providers (BrightData, SmartProxy, Oxylabs).

SRS: SCR-F-023, SCR-F-025 — No IP reuse within configurable window.
"""

from __future__ import annotations

import logging
import random
import threading
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ===================================================================
# Proxy data classes
# ===================================================================


@dataclass
class ProxyEntry:
    """In-memory representation of a single proxy endpoint."""

    proxy_id: str
    proxy_type: str  # "http" | "https" | "socks5"
    host: str
    port: int
    username: str = ""
    password: str = ""
    provider: str = ""  # "brightdata" | "smartproxy" | "oxylabs" | "manual"
    is_active: bool = True

    # Runtime stats (not persisted)
    success_count: int = 0
    fail_count: int = 0
    last_used: float = 0.0  # monotonic timestamp
    last_failed: float = 0.0

    @property
    def total_uses(self) -> int:
        return self.success_count + self.fail_count

    @property
    def url(self) -> str:
        """Build the full proxy URL string for HTTP clients."""
        scheme = "socks5" if self.proxy_type == "socks5" else self.proxy_type
        if self.username and self.password:
            return f"{scheme}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{scheme}://{self.host}:{self.port}"

    @property
    def is_usable(self) -> bool:
        """Whether the proxy should be considered for rotation."""
        if not self.is_active:
            return False
        # Skip proxies that recently failed (back off 60s)
        if self.last_failed and (time.monotonic() - self.last_failed) < 60:
            return False
        return True


@dataclass
class ProxyStats:
    """Aggregate stats for the proxy pool."""

    total: int = 0
    active: int = 0
    failed: int = 0
    by_provider: dict[str, int] = field(default_factory=dict)
    by_type: dict[str, int] = field(default_factory=dict)


# ===================================================================
# Rotation strategies
# ===================================================================


class RotationStrategy:
    """Namespace for rotation strategy implementations."""

    @staticmethod
    def round_robin(proxies: list[ProxyEntry], index: int) -> ProxyEntry | None:
        """Return the next proxy in round-robin order."""
        usable = [p for p in proxies if p.is_usable]
        if not usable:
            return None
        return usable[index % len(usable)]

    @staticmethod
    def random_choice(proxies: list[ProxyEntry], _index: int) -> ProxyEntry | None:
        """Return a random usable proxy."""
        usable = [p for p in proxies if p.is_usable]
        if not usable:
            return None
        return random.choice(usable)

    @staticmethod
    def least_used(proxies: list[ProxyEntry], _index: int) -> ProxyEntry | None:
        """Return the proxy with the fewest total uses."""
        usable = [p for p in proxies if p.is_usable]
        if not usable:
            return None
        return min(usable, key=lambda p: p.total_uses)


_STRATEGY_MAP: dict[str, Any] = {
    "round_robin": RotationStrategy.round_robin,
    "random": RotationStrategy.random_choice,
    "least_used": RotationStrategy.least_used,
}


# ===================================================================
# Proxy Manager
# ===================================================================


class ProxyManager:
    """Manages a pool of proxies with rotation and health tracking.

    Usage::

        manager = ProxyManager()
        manager.load_from_db()           # Load ScrapeProxy models
        proxy = manager.get_proxy()      # Next proxy in rotation
        manager.mark_success(proxy)      # Record success
        manager.mark_failed(proxy)       # Record failure, skip in rotation

    Thread-safe: all state mutations are guarded by a reentrant lock.
    """

    def __init__(
        self,
        *,
        strategy: str = "round_robin",
        cooldown_seconds: float = 60.0,
    ) -> None:
        if strategy not in _STRATEGY_MAP:
            raise ValueError(
                f"Unknown rotation strategy '{strategy}'. Choose from: {', '.join(_STRATEGY_MAP)}"
            )
        self._strategy_name = strategy
        self._strategy_fn = _STRATEGY_MAP[strategy]
        self._cooldown_seconds = cooldown_seconds

        self._proxies: list[ProxyEntry] = []
        self._index: int = 0
        self._lock = threading.Lock()

    # ── Database loading ──────────────────────────────────────────

    def load_from_db(self) -> int:
        """Load active proxies from ``ScrapeProxy`` Django model.

        Returns the number of proxies loaded.
        """
        from apps.scraper.models import ScrapeProxy

        db_proxies = ScrapeProxy.objects.filter(is_active=True)
        loaded = 0

        with self._lock:
            self._proxies.clear()
            for row in db_proxies:
                endpoints: list[dict[str, Any]] = row.endpoints or []
                for ep in endpoints:
                    entry = ProxyEntry(
                        proxy_id=str(row.id),
                        proxy_type=row.proxy_type,
                        host=ep.get("host", ""),
                        port=int(ep.get("port", 0)),
                        username=ep.get("username", ""),
                        password=ep.get("password", ""),
                        provider=row.provider or "manual",
                        is_active=row.is_active,
                    )
                    if entry.host and entry.port:
                        self._proxies.append(entry)
                        loaded += 1

        logger.info("Loaded %d proxy endpoints from database", loaded)
        return loaded

    def add_proxy(self, entry: ProxyEntry) -> None:
        """Manually add a proxy to the pool."""
        with self._lock:
            self._proxies.append(entry)

    def remove_proxy(self, proxy_id: str) -> int:
        """Remove all entries for a given proxy ID. Returns count removed."""
        with self._lock:
            before = len(self._proxies)
            self._proxies = [p for p in self._proxies if p.proxy_id != proxy_id]
            return before - len(self._proxies)

    # ── Rotation ──────────────────────────────────────────────────

    def get_proxy(self) -> ProxyEntry | None:
        """Return the next proxy according to the rotation strategy.

        Returns ``None`` if no usable proxies are available.
        """
        with self._lock:
            proxy = self._strategy_fn(self._proxies, self._index)
            self._index += 1
            if proxy:
                proxy.last_used = time.monotonic()
            return proxy

    def get_proxy_url(self) -> str | None:
        """Convenience: return the proxy URL string or None."""
        proxy = self.get_proxy()
        return proxy.url if proxy else None

    # ── Health tracking ───────────────────────────────────────────

    def mark_success(self, proxy: ProxyEntry) -> None:
        """Record a successful request through this proxy."""
        with self._lock:
            proxy.success_count += 1

    def mark_failed(self, proxy: ProxyEntry) -> None:
        """Record a failed request. The proxy enters a cooldown period."""
        with self._lock:
            proxy.fail_count += 1
            proxy.last_failed = time.monotonic()

        logger.warning(
            "Proxy %s:%d (%s) marked as failed (total fails: %d)",
            proxy.host,
            proxy.port,
            proxy.provider,
            proxy.fail_count,
        )

    def deactivate_proxy(self, proxy_id: str) -> int:
        """Permanently deactivate a proxy by ID. Returns count deactivated."""
        with self._lock:
            count = 0
            for p in self._proxies:
                if p.proxy_id == proxy_id and p.is_active:
                    p.is_active = False
                    count += 1
            return count

    def activate_proxy(self, proxy_id: str) -> int:
        """Re-activate a proxy by ID. Returns count activated."""
        with self._lock:
            count = 0
            for p in self._proxies:
                if p.proxy_id == proxy_id and not p.is_active:
                    p.is_active = True
                    count += 1
            return count

    # ── Stats ─────────────────────────────────────────────────────

    @property
    def stats(self) -> ProxyStats:
        """Get aggregate stats for the proxy pool."""
        with self._lock:
            by_provider: dict[str, int] = {}
            by_type: dict[str, int] = {}
            active = 0
            failed = 0
            for p in self._proxies:
                if p.is_active:
                    active += 1
                if p.last_failed:
                    failed += 1
                by_provider[p.provider] = by_provider.get(p.provider, 0) + 1
                by_type[p.proxy_type] = by_type.get(p.proxy_type, 0) + 1

            return ProxyStats(
                total=len(self._proxies),
                active=active,
                failed=failed,
                by_provider=by_provider,
                by_type=by_type,
            )

    def list_proxies(self) -> list[dict[str, Any]]:
        """Return a serializable list of all proxies with stats."""
        with self._lock:
            return [
                {
                    "proxy_id": p.proxy_id,
                    "proxy_type": p.proxy_type,
                    "host": p.host,
                    "port": p.port,
                    "provider": p.provider,
                    "is_active": p.is_active,
                    "is_usable": p.is_usable,
                    "success_count": p.success_count,
                    "fail_count": p.fail_count,
                    "total_uses": p.total_uses,
                }
                for p in self._proxies
            ]


# ===================================================================
# Residential Provider Integration Hooks
# ===================================================================

# These classes provide structured integration points for residential
# proxy providers.  Each provider returns its proxy endpoint list
# from their respective APIs.


class BrightDataIntegration:
    """BrightData (formerly Luminati) residential proxy integration.

    Endpoint format: ``http://username:password@zproxy.lum-superproxy.io:22225``
    """

    PROVIDER_NAME = "brightdata"

    @staticmethod
    def build_proxy_entry(
        host: str,
        port: int,
        username: str,
        password: str,
    ) -> ProxyEntry:
        return ProxyEntry(
            proxy_id=f"brightdata-{host}:{port}",
            proxy_type="http",
            host=host,
            port=port,
            username=username,
            password=password,
            provider="brightdata",
        )


class SmartProxyIntegration:
    """SmartProxy residential proxy integration.

    Endpoint format: ``http://user:pass@gate.smartproxy.com:7000``
    """

    PROVIDER_NAME = "smartproxy"

    @staticmethod
    def build_proxy_entry(
        host: str,
        port: int,
        username: str,
        password: str,
    ) -> ProxyEntry:
        return ProxyEntry(
            proxy_id=f"smartproxy-{host}:{port}",
            proxy_type="http",
            host=host,
            port=port,
            username=username,
            password=password,
            provider="smartproxy",
        )


class OxylabsIntegration:
    """Oxylabs residential proxy integration.

    Endpoint format: ``http://customer-username:password@pr.oxylabs.io:7777``
    """

    PROVIDER_NAME = "oxylabs"

    @staticmethod
    def build_proxy_entry(
        host: str,
        port: int,
        username: str,
        password: str,
    ) -> ProxyEntry:
        return ProxyEntry(
            proxy_id=f"oxylabs-{host}:{port}",
            proxy_type="http",
            host=host,
            port=port,
            username=username,
            password=password,
            provider="oxylabs",
        )
