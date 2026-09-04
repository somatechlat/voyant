"""
Apache Tika Document Processing Client (FR-28).

Provides integration with Apache Tika for universal document extraction —
supports 1000+ file formats including PDF, Office, email, archives, and
multimedia metadata extraction.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

from apps.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class TikaResult:
    """Result from a Tika document extraction."""

    content: str = ""
    content_type: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    language: str = ""
    pages: int = 0


class TikaClient:
    """
    Client for Apache Tika REST API (Tika Server).

    Provides universal document extraction via Tika's /tika endpoint.
    Supports PDF, DOCX, XLSX, PPTX, HTML, XML, email (MSG/EML),
    archives (ZIP, TAR), and 1000+ other formats.
    """

    def __init__(self, base_url: str | None = None):
        settings = get_settings()
        self.base_url = base_url or getattr(settings, "tika_url", "")
        self._client: httpx.Client | None = None

    def _get_client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=120.0,
            )
        return self._client

    def extract_text(self, content: bytes, content_type: str = "") -> TikaResult:
        """Extract text from document bytes."""
        headers: dict[str, str] = {}
        if content_type:
            headers["Content-Type"] = content_type

        resp = self._get_client().put(
            "/tika",
            content=content,
            headers=headers,
        )
        resp.raise_for_status()

        meta_resp = self._get_client().put(
            "/meta",
            content=content,
            headers=headers,
        )
        meta_resp.raise_for_status()

        metadata = {}
        if meta_resp.headers.get("content-type", "").startswith("application/json"):
            metadata = meta_resp.json()

        return TikaResult(
            content=resp.text,
            content_type=resp.headers.get("Content-Type", ""),
            metadata=metadata,
            language=metadata.get("language", ""),
            pages=int(metadata.get("xmpTPg:NPages", 0) or 0),
        )

    def extract_from_url(self, url: str) -> TikaResult:
        """Extract text from a document at a URL."""
        resp = self._get_client().get(
            "/tika",
            params={"url": url},
        )
        resp.raise_for_status()
        return TikaResult(
            content=resp.text,
            content_type=resp.headers.get("Content-Type", ""),
        )

    def detect_language(self, content: bytes) -> str:
        """Detect the language of text content."""
        resp = self._get_client().put(
            "/language/stream",
            content=content,
        )
        resp.raise_for_status()
        return resp.text.strip()

    def get_supported_types(self) -> list[str]:
        """List all MIME types supported by Tika."""
        resp = self._get_client().get("/mime-types")
        resp.raise_for_status()
        return list(resp.json().keys())

    def is_available(self) -> bool:
        """Check if Tika server is reachable."""
        try:
            resp = self._get_client().get("/tika")
            return resp.status_code in (200, 405)
        except Exception:
            return False


def get_tika_client() -> TikaClient:
    """Factory function for the singleton Tika client."""
    return TikaClient()
