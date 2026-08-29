#!/usr/bin/env python3
"""Site-specific extractors: HTTP requests and HTML parsing."""

from __future__ import annotations

import asyncio
import html as htmlmod
import json
import re
import time

import httpx
from bs4 import BeautifulSoup
from transformers import (
    _drop_personal_kv,
    _parse_kv_section,
    _parse_list_section,
    _safe_vehicle_data,
)

PRICE_RE = re.compile(r"\$\s*([0-9][0-9\.,]*)")
YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")
LOC_RE = re.compile(
    r"\ben\s+([A-Za-z\u00C0-\u017F\s]+\s*-\s*[A-Za-z\u00C0-\u017F\s]+)\s+en\s+\$",
    re.IGNORECASE,
)

META_PROP_RE_TPL = r"<meta[^>]+property=['\"]{prop}['\"][^>]+content=['\"]([^'\"]+)['\"]"
META_CONTENT_RE_TPL = r"<meta[^>]+content=['\"]([^'\"]+)['\"][^>]+property=['\"]{prop}['\"]"


def pick_meta(html: str, prop: str) -> str | None:
    if not html:
        return None
    m = re.search(META_PROP_RE_TPL.format(prop=re.escape(prop)), html, re.IGNORECASE)
    if not m:
        m = re.search(META_CONTENT_RE_TPL.format(prop=re.escape(prop)), html, re.IGNORECASE)
    return m.group(1).strip() if m else None


def parse_og_description(desc: str | None) -> dict:
    if not desc:
        return {}
    out: dict[str, object] = {}

    m = PRICE_RE.search(desc)
    if m:
        out["price"] = f"{m.group(1)} USD"

    m = YEAR_RE.search(desc)
    if m:
        out["year"] = int(m.group(1))

    m = LOC_RE.search(desc)
    if m:
        out["location"] = m.group(1).strip()

    return out


def _extract_vehicle_data_array(html: str) -> dict | None:
    # Example:
    # data-vehicleDataArray="{&quot;type&quot;:&quot;Autos&quot;,...}"
    m = re.search(r'data-vehicleDataArray="(.*?)"', html, re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    try:
        dec = htmlmod.unescape(m.group(1))
        obj = json.loads(dec)
        if isinstance(obj, dict):
            return _safe_vehicle_data(obj)
    except Exception:
        return None
    return None


def _extract_additional_properties(soup: BeautifulSoup) -> dict[str, str]:
    props: dict[str, str] = {}
    for sp in soup.find_all("span", attrs={"itemprop": "additionalProperty"}):
        name = sp.find("meta", attrs={"itemprop": "name", "content": True})
        val = sp.find("meta", attrs={"itemprop": "value", "content": True})
        if not name or not val:
            continue
        k = str(name.get("content")).strip()
        v = str(val.get("content")).strip()
        if not k:
            continue
        # Prefer first value to avoid random overwrites.
        props.setdefault(k, v)
    return props


def _extract_images(html: str, soup: BeautifulSoup) -> list[str]:
    urls: list[str] = []
    og = soup.find("meta", attrs={"property": "og:image", "content": True})
    if og:
        urls.append(str(og.get("content")).strip())
    # Include all Patiotuerca CDN images we can see in HTML (gallery/thumbs).
    for u in re.findall(
        r"https?://[^\"']+images\.patiotuerca\.com[^\"']+",
        html,
        flags=re.IGNORECASE,
    ):
        urls.append(u)
    for img in soup.find_all("img", attrs={"src": True}):
        src = str(img.get("src")).strip()
        if src.startswith("//"):
            src = "https:" + src
        if "images.patiotuerca.com" in src:
            urls.append(src)
    # De-dup preserving order.
    seen = set()
    out = []
    for u in urls:
        if not u or u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out


def _extract_images_from_json(obj) -> list[str]:
    urls: list[str] = []

    def walk(v):
        if v is None:
            return
        if isinstance(v, dict):
            for vv in v.values():
                walk(vv)
            return
        if isinstance(v, list):
            for vv in v:
                walk(vv)
            return
        if isinstance(v, str):
            s = v.strip()
            if s.startswith("//"):
                s = "https:" + s
            if "images.patiotuerca.com" in s:
                urls.append(s)
            return

    walk(obj)
    seen = set()
    out = []
    for u in urls:
        if not u or u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out


def _json_contains_vehicle_id(obj, vehicle_id: int) -> bool:
    target_s = str(vehicle_id)
    target_i = vehicle_id

    def walk(v, depth: int) -> bool:
        if depth > 8:
            return False
        if v is None:
            return False
        if isinstance(v, dict):
            for k, vv in v.items():
                if k in ("vehicleId", "vehicle_id", "id") and vv in (
                    target_s,
                    target_i,
                ):
                    return True
                if walk(vv, depth + 1):
                    return True
            return False
        if isinstance(v, list):
            return any(walk(vv, depth + 1) for vv in v[:200])
        return v in (target_s, target_i)

    return walk(obj, 0)


def extract_listing(html: str, url: str) -> dict:
    soup = BeautifulSoup(html or "", "lxml")
    og_title = pick_meta(html, "og:title")
    og_desc = pick_meta(html, "og:description")
    parsed_og = parse_og_description(og_desc)

    additional_props = _drop_personal_kv(_extract_additional_properties(soup))
    vehicle_data = _extract_vehicle_data_array(html)

    summary: dict[str, str] = {}
    technical: dict[str, str] = {}
    extras: list[str] = []
    equipment: list[str] = []

    summary_el = soup.find(id="summary")
    if summary_el:
        summary = _drop_personal_kv(_parse_kv_section(summary_el))
    tech_el = soup.find(id="technicalData")
    if tech_el:
        technical = _drop_personal_kv(_parse_kv_section(tech_el))
    extras_el = soup.find(id="extras")
    if extras_el:
        extras = _parse_list_section(extras_el)
    equip_el = soup.find(id="equipment")
    if equip_el:
        equipment = _parse_list_section(equip_el)

    return {
        "url": url,
        "og_title": og_title,
        "og_description": og_desc,
        "parsed_og": parsed_og,
        "vehicle_data": vehicle_data,
        "additional_properties": additional_props,
        "summary": summary,
        "technical_data": technical,
        "extras": extras,
        "equipment": equipment,
        "images": _extract_images(html, soup),
    }


class RateLimiter:
    def __init__(self, min_interval_sec: float) -> None:
        self._min = min_interval_sec
        self._lock = asyncio.Lock()
        self._next = 0.0

    async def wait(self) -> None:
        async with self._lock:
            now = time.monotonic()
            if now < self._next:
                await asyncio.sleep(self._next - now)
            self._next = time.monotonic() + self._min


async def fetch_via_tool(
    client: httpx.AsyncClient,
    limiter: RateLimiter,
    scrape_fetch_url: str,
    url: str,
    engine: str,
    capture_json: bool = False,
) -> dict:
    await limiter.wait()
    r = await client.post(
        scrape_fetch_url,
        # Note: endpoint schema expects `timeout` (seconds). Keep it explicit.
        json={
            "url": url,
            "engine": engine,
            "timeout": 60,
            "capture_json": capture_json,
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json()
