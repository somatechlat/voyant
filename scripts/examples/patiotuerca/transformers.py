#!/usr/bin/env python3
"""Data normalization: cleaning, deduplicating, PII removal."""

from __future__ import annotations

import re

_PERSONAL_KEY_RE = re.compile(
    r"(tel[eé]fono|celular|whats\s*app|correo|e-?mail|direcci[oó]n|contacto|nombre)",
    re.IGNORECASE,
)

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)")


def _safe_vehicle_data(vehicle_data: dict) -> dict:
    # Keep non-personal, listing-level fields only.
    allow = {
        "type",
        "subtype",
        "vehicleId",
        "brand",
        "model",
        "year",
        "price",
        "priceOriginal",
        "discountUntil",
        "city",
        "province",
        "dealer",
        "negotiable",
        "mileage",
        "mileageType",
        "mileageRange",
        "priceRange",
        "section",
        "mechanicalWarrantyStatus",
    }
    return {k: v for k, v in (vehicle_data or {}).items() if k in allow}


def _drop_personal_kv(d: dict[str, str]) -> dict[str, str]:
    if not d:
        return {}
    out: dict[str, str] = {}
    for k, v in d.items():
        if not k:
            continue
        if _PERSONAL_KEY_RE.search(k):
            continue
        out[k] = v
    return out


def _sanitize_json(value):
    # Remove any seller contact details (strict): drop keys and also redact
    # any email/phone-like strings anywhere.
    if value is None:
        return None
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if isinstance(k, str) and _PERSONAL_KEY_RE.search(k):
                continue
            sv = _sanitize_json(v)
            if sv is None:
                continue
            out[k] = sv
        return out
    if isinstance(value, list):
        out_list = []
        for v in value:
            sv = _sanitize_json(v)
            if sv is None:
                continue
            out_list.append(sv)
        return out_list
    if isinstance(value, str):
        if _EMAIL_RE.search(value):
            return None
        digits = re.sub(r"\D", "", value)
        if len(digits) >= 9 and _PHONE_RE.search(value):
            return None
        return value
    return value


def _parse_kv_section(section) -> dict[str, str]:
    # Patiotuerca sections render as: Title, then alternating key/value tokens.
    tokens = [t for t in section.get_text("\n", strip=True).split("\n") if t.strip()]
    if not tokens:
        return {}
    tokens = tokens[1:]  # drop heading
    out: dict[str, str] = {}
    i = 0
    while i + 1 < len(tokens):
        k = tokens[i].strip()
        v = tokens[i + 1].strip()
        if k and v:
            out.setdefault(k, v)
        i += 2
    return out


def _parse_list_section(section) -> list[str]:
    tokens = [t for t in section.get_text("\n", strip=True).split("\n") if t.strip()]
    if not tokens:
        return []
    tokens = tokens[1:]  # drop heading
    # De-dup preserving order.
    seen = set()
    out: list[str] = []
    for t in tokens:
        t = t.strip()
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out
