"""
CAPTCHA Solver Service — Multi-provider CAPTCHA solving engine.

Supports reCAPTCHA v2/v3, hCaptcha, and Cloudflare Turnstile via
three commercial solving services (2Captcha, AntiCaptcha, CapSolver).
The ``MultiProviderCaptchaSolver`` chains providers for resilience.

SRS: SCR-F-020, SCR-F-021, SCR-F-022 — >90% solve rate target.
"""

from __future__ import annotations

import abc
import asyncio
import logging
import time
from typing import Any

import httpx

from apps.core.config import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Polling / timeout defaults
# ---------------------------------------------------------------------------
_DEFAULT_POLL_INTERVAL_S: float = 5.0
_DEFAULT_TIMEOUT_S: float = 300.0  # 5 min max wait for a solve


class CaptchaSolveError(Exception):
    """Raised when CAPTCHA solving fails across all providers."""


class CaptchaProviderError(Exception):
    """Raised when a single provider returns an error."""


# ===================================================================
# Abstract base
# ===================================================================


class CaptchaSolver(abc.ABC):
    """Abstract base for all CAPTCHA solver implementations.

    Each concrete solver talks to one commercial API.  All methods are
    async and return the solution token string on success or raise
    ``CaptchaProviderError`` on failure.
    """

    provider_name: str = "abstract"

    def __init__(self, api_key: str, timeout: float = _DEFAULT_TIMEOUT_S) -> None:
        self.api_key = api_key
        self.timeout = timeout

    # ── Public interface ──────────────────────────────────────────
    @abc.abstractmethod
    async def solve_recaptcha_v2(
        self,
        site_key: str,
        page_url: str,
        *,
        is_invisible: bool = False,
        action: str | None = None,
    ) -> str:
        """Solve reCAPTCHA v2 and return the response token."""

    @abc.abstractmethod
    async def solve_recaptcha_v3(
        self,
        site_key: str,
        page_url: str,
        *,
        action: str = "verify",
        min_score: float = 0.3,
    ) -> str:
        """Solve reCAPTCHA v3 and return the response token."""

    @abc.abstractmethod
    async def solve_hcaptcha(
        self,
        site_key: str,
        page_url: str,
        *,
        is_invisible: bool = False,
    ) -> str:
        """Solve hCaptcha and return the response token."""

    @abc.abstractmethod
    async def solve_turnstile(
        self,
        site_key: str,
        page_url: str,
        *,
        action: str | None = None,
    ) -> str:
        """Solve Cloudflare Turnstile and return the response token."""

    # ── Shared helpers ────────────────────────────────────────────
    async def _poll_result(
        self,
        client: httpx.AsyncClient,
        get_url: str,
        params: dict[str, Any],
        *,
        result_key: str = "request",
        ready_values: set[str] | None = None,
    ) -> str:
        """Poll a provider until the solution is ready or timeout."""
        if ready_values is None:
            ready_values = {"CAPCHA_NOT_READY", "CAPTCHA_NOT_READY"}

        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            resp = await client.get(get_url, params=params)
            resp.raise_for_status()
            data = resp.json()

            status = str(data.get("status", ""))
            if status == "1" or (
                data.get(result_key) and data.get(result_key) not in ready_values
            ):
                token = str(data.get(result_key, ""))
                if token and token not in ready_values:
                    return token

            request_val = str(data.get("request", ""))
            if request_val.lower().startswith("error"):
                raise CaptchaProviderError(
                    f"[{self.provider_name}] Solve error: {request_val}"
                )

            await asyncio.sleep(_DEFAULT_POLL_INTERVAL_S)

        raise CaptchaProviderError(
            f"[{self.provider_name}] Timeout after {self.timeout}s waiting for CAPTCHA solve"
        )


# ===================================================================
# 2Captcha  (https://2captcha.com)
# ===================================================================


class TwoCaptchaSolver(CaptchaSolver):
    """2Captcha API implementation.

    API docs: https://2captcha.com/2captcha-api
    """

    provider_name = "2captcha"
    _BASE = "https://2captcha.com"

    def __init__(self, api_key: str, **kwargs: Any) -> None:
        super().__init__(api_key, **kwargs)

    # ── reCAPTCHA v2 ──────────────────────────────────────────────
    async def solve_recaptcha_v2(
        self,
        site_key: str,
        page_url: str,
        *,
        is_invisible: bool = False,
        action: str | None = None,
    ) -> str:
        async with httpx.AsyncClient(timeout=self.timeout + 30) as client:
            payload = {
                "key": self.api_key,
                "method": "userrecaptcha",
                "googlekey": site_key,
                "pageurl": page_url,
                "json": 1,
            }
            if is_invisible:
                payload["invisible"] = 1

            resp = await client.post(f"{self._BASE}/in.php", data=payload)
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") != 1:
                raise CaptchaProviderError(
                    f"[2captcha] Submit error: {data.get('request', data)}"
                )
            task_id = str(data["request"])

            return await self._poll_result(
                client,
                f"{self._BASE}/res.php",
                {"key": self.api_key, "action": "get", "id": task_id, "json": 1},
            )

    # ── reCAPTCHA v3 ──────────────────────────────────────────────
    async def solve_recaptcha_v3(
        self,
        site_key: str,
        page_url: str,
        *,
        action: str = "verify",
        min_score: float = 0.3,
    ) -> str:
        async with httpx.AsyncClient(timeout=self.timeout + 30) as client:
            payload = {
                "key": self.api_key,
                "method": "userrecaptcha",
                "googlekey": site_key,
                "pageurl": page_url,
                "version": "v3",
                "action": action,
                "min_score": min_score,
                "json": 1,
            }
            resp = await client.post(f"{self._BASE}/in.php", data=payload)
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") != 1:
                raise CaptchaProviderError(
                    f"[2captcha] Submit error: {data.get('request', data)}"
                )
            task_id = str(data["request"])

            return await self._poll_result(
                client,
                f"{self._BASE}/res.php",
                {"key": self.api_key, "action": "get", "id": task_id, "json": 1},
            )

    # ── hCaptcha ──────────────────────────────────────────────────
    async def solve_hcaptcha(
        self,
        site_key: str,
        page_url: str,
        *,
        is_invisible: bool = False,
    ) -> str:
        async with httpx.AsyncClient(timeout=self.timeout + 30) as client:
            payload = {
                "key": self.api_key,
                "method": "hcaptcha",
                "sitekey": site_key,
                "pageurl": page_url,
                "json": 1,
            }
            if is_invisible:
                payload["invisible"] = 1

            resp = await client.post(f"{self._BASE}/in.php", data=payload)
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") != 1:
                raise CaptchaProviderError(
                    f"[2captcha] Submit error: {data.get('request', data)}"
                )
            task_id = str(data["request"])

            return await self._poll_result(
                client,
                f"{self._BASE}/res.php",
                {"key": self.api_key, "action": "get", "id": task_id, "json": 1},
            )

    # ── Turnstile ─────────────────────────────────────────────────
    async def solve_turnstile(
        self,
        site_key: str,
        page_url: str,
        *,
        action: str | None = None,
    ) -> str:
        async with httpx.AsyncClient(timeout=self.timeout + 30) as client:
            payload = {
                "key": self.api_key,
                "method": "turnstile",
                "sitekey": site_key,
                "pageurl": page_url,
                "json": 1,
            }
            if action:
                payload["action"] = action

            resp = await client.post(f"{self._BASE}/in.php", data=payload)
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") != 1:
                raise CaptchaProviderError(
                    f"[2captcha] Submit error: {data.get('request', data)}"
                )
            task_id = str(data["request"])

            return await self._poll_result(
                client,
                f"{self._BASE}/res.php",
                {"key": self.api_key, "action": "get", "id": task_id, "json": 1},
            )


# ===================================================================
# AntiCaptcha  (https://anti-captcha.com)
# ===================================================================


class AntiCaptchaSolver(CaptchaSolver):
    """Anti-Captcha API implementation.

    API docs: https://anti-captcha.com/apidoc
    """

    provider_name = "anticaptcha"
    _BASE = "https://api.anti-captcha.com"

    def __init__(self, api_key: str, **kwargs: Any) -> None:
        super().__init__(api_key, **kwargs)

    async def _create_task(
        self, client: httpx.AsyncClient, task: dict[str, Any]
    ) -> int:
        """Create a task and return the task ID."""
        resp = await client.post(
            f"{self._BASE}/createTask",
            json={"clientKey": self.api_key, "task": task},
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("errorId", 0) != 0:
            raise CaptchaProviderError(
                f"[anticaptcha] Create task error: {data.get('errorDescription', data)}"
            )
        return int(data["taskId"])

    async def _wait_for_task(self, client: httpx.AsyncClient, task_id: int) -> str:
        """Poll until task is complete and return the solution."""
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            resp = await client.post(
                f"{self._BASE}/getTaskResult",
                json={"clientKey": self.api_key, "taskId": task_id},
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("errorId", 0) != 0:
                raise CaptchaProviderError(
                    f"[anticaptcha] Task error: {data.get('errorDescription', data)}"
                )

            status = data.get("status", "")
            if status == "ready":
                solution = data.get("solution", {})
                token = (
                    solution.get("gRecaptchaResponse")
                    or solution.get("token")
                    or solution.get("text", "")
                )
                if token:
                    return str(token)
                raise CaptchaProviderError(
                    "[anticaptcha] Solution present but token empty"
                )

            await asyncio.sleep(_DEFAULT_POLL_INTERVAL_S)

        raise CaptchaProviderError(
            f"[anticaptcha] Timeout after {self.timeout}s waiting for task {task_id}"
        )

    # ── reCAPTCHA v2 ──────────────────────────────────────────────
    async def solve_recaptcha_v2(
        self,
        site_key: str,
        page_url: str,
        *,
        is_invisible: bool = False,
        action: str | None = None,
    ) -> str:
        task: dict[str, Any] = {
            "type": "RecaptchaV2TaskProxyless",
            "websiteURL": page_url,
            "websiteKey": site_key,
        }
        if is_invisible:
            task["type"] = "RecaptchaV2TaskProxyless"
            task["isInvisible"] = True

        async with httpx.AsyncClient(timeout=30) as client:
            task_id = await self._create_task(client, task)
            return await self._wait_for_task(client, task_id)

    # ── reCAPTCHA v3 ──────────────────────────────────────────────
    async def solve_recaptcha_v3(
        self,
        site_key: str,
        page_url: str,
        *,
        action: str = "verify",
        min_score: float = 0.3,
    ) -> str:
        task: dict[str, Any] = {
            "type": "RecaptchaV3TaskProxyless",
            "websiteURL": page_url,
            "websiteKey": site_key,
            "pageAction": action,
            "minScore": min_score,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            task_id = await self._create_task(client, task)
            return await self._wait_for_task(client, task_id)

    # ── hCaptcha ──────────────────────────────────────────────────
    async def solve_hcaptcha(
        self,
        site_key: str,
        page_url: str,
        *,
        is_invisible: bool = False,
    ) -> str:
        task: dict[str, Any] = {
            "type": "HCaptchaTaskProxyless",
            "websiteURL": page_url,
            "websiteKey": site_key,
        }
        if is_invisible:
            task["isInvisible"] = True

        async with httpx.AsyncClient(timeout=30) as client:
            task_id = await self._create_task(client, task)
            return await self._wait_for_task(client, task_id)

    # ── Turnstile ─────────────────────────────────────────────────
    async def solve_turnstile(
        self,
        site_key: str,
        page_url: str,
        *,
        action: str | None = None,
    ) -> str:
        task: dict[str, Any] = {
            "type": "TurnstileTaskProxyless",
            "websiteURL": page_url,
            "websiteKey": site_key,
        }
        if action:
            task["action"] = action

        async with httpx.AsyncClient(timeout=30) as client:
            task_id = await self._create_task(client, task)
            return await self._wait_for_task(client, task_id)


# ===================================================================
# CapSolver  (https://capsolver.com)
# ===================================================================


class CapSolverSolver(CaptchaSolver):
    """CapSolver API implementation.

    API docs: https://docs.capsolver.com/
    """

    provider_name = "capsolver"
    _BASE = "https://api.capsolver.com"

    def __init__(self, api_key: str, **kwargs: Any) -> None:
        super().__init__(api_key, **kwargs)

    async def _create_task(
        self, client: httpx.AsyncClient, task: dict[str, Any]
    ) -> str:
        """Create a CapSolver task and return the task ID."""
        resp = await client.post(
            f"{self._BASE}/createTask",
            json={"clientKey": self.api_key, "task": task},
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("errorId", 0) != 0:
            raise CaptchaProviderError(
                f"[capsolver] Create task error: {data.get('errorDescription', data)}"
            )
        return str(data["taskId"])

    async def _wait_for_task(self, client: httpx.AsyncClient, task_id: str) -> str:
        """Poll until task is complete and return the solution token."""
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            resp = await client.post(
                f"{self._BASE}/getTaskResult",
                json={"clientKey": self.api_key, "taskId": task_id},
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("errorId", 0) != 0:
                raise CaptchaProviderError(
                    f"[capsolver] Task error: {data.get('errorDescription', data)}"
                )

            status = data.get("status", "")
            if status == "ready":
                solution = data.get("solution", {})
                token = (
                    solution.get("gRecaptchaResponse")
                    or solution.get("token")
                    or solution.get("text", "")
                )
                if token:
                    return str(token)
                raise CaptchaProviderError(
                    "[capsolver] Solution present but token empty"
                )

            await asyncio.sleep(_DEFAULT_POLL_INTERVAL_S)

        raise CaptchaProviderError(
            f"[capsolver] Timeout after {self.timeout}s waiting for task {task_id}"
        )

    # ── reCAPTCHA v2 ──────────────────────────────────────────────
    async def solve_recaptcha_v2(
        self,
        site_key: str,
        page_url: str,
        *,
        is_invisible: bool = False,
        action: str | None = None,
    ) -> str:
        task: dict[str, Any] = {
            "type": "ReCaptchaV2TaskProxyLess",
            "websiteURL": page_url,
            "websiteKey": site_key,
        }
        if is_invisible:
            task["isInvisible"] = True

        async with httpx.AsyncClient(timeout=30) as client:
            task_id = await self._create_task(client, task)
            return await self._wait_for_task(client, task_id)

    # ── reCAPTCHA v3 ──────────────────────────────────────────────
    async def solve_recaptcha_v3(
        self,
        site_key: str,
        page_url: str,
        *,
        action: str = "verify",
        min_score: float = 0.3,
    ) -> str:
        task: dict[str, Any] = {
            "type": "ReCaptchaV3TaskProxyLess",
            "websiteURL": page_url,
            "websiteKey": site_key,
            "pageAction": action,
            "minScore": min_score,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            task_id = await self._create_task(client, task)
            return await self._wait_for_task(client, task_id)

    # ── hCaptcha ──────────────────────────────────────────────────
    async def solve_hcaptcha(
        self,
        site_key: str,
        page_url: str,
        *,
        is_invisible: bool = False,
    ) -> str:
        task: dict[str, Any] = {
            "type": "HCaptchaTaskProxyLess",
            "websiteURL": page_url,
            "websiteKey": site_key,
        }
        if is_invisible:
            task["isInvisible"] = True

        async with httpx.AsyncClient(timeout=30) as client:
            task_id = await self._create_task(client, task)
            return await self._wait_for_task(client, task_id)

    # ── Turnstile ─────────────────────────────────────────────────
    async def solve_turnstile(
        self,
        site_key: str,
        page_url: str,
        *,
        action: str | None = None,
    ) -> str:
        task: dict[str, Any] = {
            "type": "AntiTurnstileTaskProxyLess",
            "websiteURL": page_url,
            "websiteKey": site_key,
        }
        if action:
            task["action"] = action

        async with httpx.AsyncClient(timeout=30) as client:
            task_id = await self._create_task(client, task)
            return await self._wait_for_task(client, task_id)


# ===================================================================
# Multi-Provider Chain
# ===================================================================


class MultiProviderCaptchaSolver(CaptchaSolver):
    """Chains multiple CAPTCHA solving providers for resilience.

    Tries each provider in order.  If a provider fails (timeout or
    error), the next one in the chain is attempted.  Raises
    ``CaptchaSolveError`` only when *all* providers have been exhausted.

    Usage::

        solver = MultiProviderCaptchaSolver.from_settings()
        token = await solver.solve_recaptcha_v2(site_key, page_url)
    """

    provider_name = "multi"

    def __init__(
        self,
        providers: list[CaptchaSolver],
        *,
        timeout: float = _DEFAULT_TIMEOUT_S,
    ) -> None:
        super().__init__(api_key="multi", timeout=timeout)
        if not providers:
            raise ValueError(
                "MultiProviderCaptchaSolver requires at least one provider"
            )
        self.providers = providers

    # ── Factory ───────────────────────────────────────────────────
    @classmethod
    def from_settings(
        cls, timeout: float = _DEFAULT_TIMEOUT_S
    ) -> MultiProviderCaptchaSolver:
        """Build a solver chain from Django settings (VOYANT_CAPTCHA_*_KEY)."""
        settings = get_settings()
        providers: list[CaptchaSolver] = []

        key_2captcha = getattr(settings, "captcha_2captcha_key", "")
        if key_2captcha:
            providers.append(TwoCaptchaSolver(key_2captcha, timeout=timeout))

        key_anticaptcha = getattr(settings, "captcha_anticaptcha_key", "")
        if key_anticaptcha:
            providers.append(AntiCaptchaSolver(key_anticaptcha, timeout=timeout))

        key_capsolver = getattr(settings, "captcha_capsolver_key", "")
        if key_capsolver:
            providers.append(CapSolverSolver(key_capsolver, timeout=timeout))

        if not providers:
            raise CaptchaSolveError(
                "No CAPTCHA provider configured. Set VOYANT_CAPTCHA_2CAPTCHA_KEY, "
                "VOYANT_CAPTCHA_ANTICAPTCHA_KEY, or VOYANT_CAPTCHA_CAPSOLVER_KEY."
            )

        return cls(providers, timeout=timeout)

    @classmethod
    def from_settings_hybrid(cls, timeout: float = _DEFAULT_TIMEOUT_S):
        """Build the best available solver, preferring the 4-tier hybrid chain.

        If AI-native solving is enabled (VOYANT_CAPTCHA_AI_ENABLED=true),
        returns a ``HybridCaptchaSolver`` that chains behavioral → audio →
        vision → human farm.  Otherwise falls back to the classic
        ``MultiProviderCaptchaSolver`` (human farms only).

        This is the recommended factory for production use.
        """
        settings = get_settings()
        ai_enabled = getattr(settings, "captcha_ai_enabled", True)

        if ai_enabled:
            try:
                from apps.scraper.services.captcha_hybrid import HybridCaptchaSolver

                return HybridCaptchaSolver()
            except Exception as exc:
                logger.warning(
                    "HybridCaptchaSolver init failed, falling back to human farm: %s",
                    exc,
                )

        return cls.from_settings(timeout=timeout)

    # ── Chain runner ──────────────────────────────────────────────
    async def _chain_solve(
        self,
        method_name: str,
        *args: Any,
        **kwargs: Any,
    ) -> str:
        """Try each provider in order; return first success."""
        errors: list[str] = []
        for provider in self.providers:
            try:
                method = getattr(provider, method_name)
                return await method(*args, **kwargs)
            except (CaptchaProviderError, httpx.HTTPError, Exception) as exc:
                err_msg = f"[{provider.provider_name}] {exc}"
                logger.warning(
                    "CAPTCHA solve failed (%s): %s", provider.provider_name, exc
                )
                errors.append(err_msg)
                continue

        raise CaptchaSolveError(
            f"All CAPTCHA providers failed for {method_name}: " + "; ".join(errors)
        )

    # ── Public interface delegates to chain ───────────────────────
    async def solve_recaptcha_v2(
        self,
        site_key: str,
        page_url: str,
        *,
        is_invisible: bool = False,
        action: str | None = None,
    ) -> str:
        return await self._chain_solve(
            "solve_recaptcha_v2",
            site_key,
            page_url,
            is_invisible=is_invisible,
            action=action,
        )

    async def solve_recaptcha_v3(
        self,
        site_key: str,
        page_url: str,
        *,
        action: str = "verify",
        min_score: float = 0.3,
    ) -> str:
        return await self._chain_solve(
            "solve_recaptcha_v3",
            site_key,
            page_url,
            action=action,
            min_score=min_score,
        )

    async def solve_hcaptcha(
        self,
        site_key: str,
        page_url: str,
        *,
        is_invisible: bool = False,
    ) -> str:
        return await self._chain_solve(
            "solve_hcaptcha",
            site_key,
            page_url,
            is_invisible=is_invisible,
        )

    async def solve_turnstile(
        self,
        site_key: str,
        page_url: str,
        *,
        action: str | None = None,
    ) -> str:
        return await self._chain_solve(
            "solve_turnstile",
            site_key,
            page_url,
            action=action,
        )
