#!/usr/bin/env python3
"""
Crawl public Patiotuerca listing pages via the Voyant scrape tool endpoint and
store normalized metadata + raw HTML into the repo SQLite database.

This script intentionally does NOT fetch target pages directly. It only calls:
  POST {VOYANT_SCRAPE_FETCH_URL}
so the scrape happens through Voyant's tool layer.
"""

from __future__ import annotations

import argparse
import asyncio
import html as htmlmod
import json
import re
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup


@dataclass(frozen=True)
class CrawlConfig:
    scrape_fetch_url: str
    db_path: str
    only_autos: bool
    engine: str
    concurrency: int
    min_interval_sec: float
    log_every: int
    limit: int | None
    mode: str


PRICE_RE = re.compile(r"\$\s*([0-9][0-9\.,]*)")
YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")
LOC_RE = re.compile(
    r"\ben\s+([A-Za-z\u00C0-\u017F\s]+\s*-\s*[A-Za-z\u00C0-\u017F\s]+)\s+en\s+\$",
    re.IGNORECASE,
)

META_PROP_RE_TPL = r"<meta[^>]+property=['\"]{prop}['\"][^>]+content=['\"]([^'\"]+)['\"]"
META_CONTENT_RE_TPL = r"<meta[^>]+content=['\"]([^'\"]+)['\"][^>]+property=['\"]{prop}['\"]"


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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


_PERSONAL_KEY_RE = re.compile(
    r"(tel[eé]fono|celular|whats\s*app|correo|e-?mail|direcci[oó]n|contacto|nombre)",
    re.IGNORECASE,
)

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)")


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
                if k in ("vehicleId", "vehicle_id", "id") and vv in (target_s, target_i):
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


def _connect(db_path: str) -> sqlite3.Connection:
    con = sqlite3.connect(db_path, timeout=30)
    con.execute("pragma busy_timeout=30000")
    con.execute("pragma journal_mode=WAL")
    return con


def _ensure_tables(con: sqlite3.Connection) -> None:
    # listings + listing_urls already exist in this repo DB; keep schema compatible.
    con.execute(
        """
        create table if not exists fetch_errors(
          vehicle_id integer,
          url text,
          error text,
          at text
        )
        """
    )
    con.commit()


def load_targets(cfg: CrawlConfig) -> list[tuple[int, str]]:
    con = _connect(cfg.db_path)
    try:
        q = """
          select u.vehicle_id, u.sitemap_url
          from listing_urls u
          left join listings l on l.id=u.vehicle_id
          where (l.id is null or l.source_html is null)
        """
        params: tuple[object, ...] = ()

        if cfg.only_autos:
            q += " and u.sitemap_url like '%/vehicle/autos-%'"

        if cfg.limit is not None:
            q += " limit ?"
            params = (cfg.limit,)

        rows = con.execute(q, params).fetchall()
        return [(int(r[0]), str(r[1])) for r in rows]
    finally:
        con.close()


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
        json={"url": url, "engine": engine, "timeout": 60, "capture_json": capture_json},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()


async def worker(
    client: httpx.AsyncClient,
    limiter: RateLimiter,
    cfg: CrawlConfig,
    inq: asyncio.Queue,
    outq: asyncio.Queue,
) -> None:
    while True:
        item = await inq.get()
        if item is None:
            inq.task_done()
            return

        vehicle_id, url = item
        try:
            if cfg.engine == "auto":
                j = await fetch_via_tool(client, limiter, cfg.scrape_fetch_url, url, "httpx")
            else:
                j = await fetch_via_tool(
                    client, limiter, cfg.scrape_fetch_url, url, cfg.engine
                )
            html = j.get("html") or ""

            extracted = extract_listing(html, url)
            captured = j.get("captured_json") if isinstance(j, dict) else None

            # If SSR HTML lacks rich sections, fall back to Playwright JSON capture.
            if cfg.engine == "auto" and not extracted.get("technical_data") and not extracted.get("additional_properties"):
                j2 = await fetch_via_tool(
                    client,
                    limiter,
                    cfg.scrape_fetch_url,
                    url,
                    "playwright",
                    capture_json=True,
                )
                html2 = j2.get("html") or ""
                extracted2 = extract_listing(html2, url)
                extracted = extracted2 or extracted
                captured = j2.get("captured_json")
                if html2:
                    html = html2
                # Prefer Playwright metadata
                j = j2

            if captured and isinstance(captured, list):
                # Keep only JSON bodies related to this vehicle id, and sanitize PII.
                related = []
                for item in captured:
                    body = item.get("body") if isinstance(item, dict) else None
                    if body is None:
                        continue
                    if not _json_contains_vehicle_id(body, int(vehicle_id)):
                        continue
                    safe_body = _sanitize_json(body)
                    if safe_body is None:
                        continue
                    related.append({"url": item.get("url"), "body": safe_body})

                extracted["captured_json"] = related
                # Merge images from captured JSON too.
                imgs = list(extracted.get("images") or [])
                for rj in related:
                    imgs.extend(_extract_images_from_json(rj.get("body")))
                # de-dup
                seen = set()
                merged = []
                for u in imgs:
                    if not u:
                        continue
                    if u.startswith("//"):
                        u = "https:" + u
                    if u in seen:
                        continue
                    seen.add(u)
                    merged.append(u)
                extracted["images"] = merged

            og_title = extracted.get("og_title")
            og_desc = extracted.get("og_description")
            parsed = extracted.get("parsed_og") or {}

            attrs = {
                "source": "patiotuerca",
                "og_description": og_desc,
                "year": parsed.get("year"),
                "extracted": extracted,
                "fetched_status_code": j.get("status_code"),
                "fetched_url": j.get("url"),
                "fetched_at": j.get("fetched_at"),
            }

            await outq.put(
                (
                    vehicle_id,
                    url,
                    og_title,
                    parsed.get("price"),
                    parsed.get("location"),
                    json.dumps(attrs, ensure_ascii=True, separators=(",", ":")),
                    html,
                    j.get("fetched_at") or _utcnow_iso(),
                    None,
                )
            )
        except Exception as e:  # noqa: BLE001 - this is a long-running crawl loop
            await outq.put((vehicle_id, url, None, None, None, None, None, None, repr(e)))
        finally:
            inq.task_done()


async def writer(cfg: CrawlConfig, outq: asyncio.Queue, total: int) -> None:
    con = _connect(cfg.db_path)
    _ensure_tables(con)

    done = 0
    start = time.time()
    while done < total:
        vehicle_id, url, title, price, location, attrs_json, html, fetched_at, err = await outq.get()
        try:
            if err is not None:
                con.execute(
                    "insert into fetch_errors(vehicle_id,url,error,at) values(?,?,?,?)",
                    (vehicle_id, url, err, _utcnow_iso()),
                )
            else:
                con.execute(
                    """
                    insert into listings(id,url,title,price,location,attributes_json,source_html,fetched_at)
                    values(?,?,?,?,?,?,?,?)
                    on conflict(id) do update set
                      url=excluded.url,
                      title=excluded.title,
                      price=coalesce(excluded.price, listings.price),
                      location=coalesce(excluded.location, listings.location),
                      attributes_json=excluded.attributes_json,
                      source_html=excluded.source_html,
                      fetched_at=excluded.fetched_at
                    """,
                    (vehicle_id, url, title, price, location, attrs_json, html, fetched_at),
                )
            con.commit()
        finally:
            outq.task_done()

        done += 1
        if done % cfg.log_every == 0 or done == total:
            elapsed = time.time() - start
            rate = done / elapsed if elapsed > 0 else 0.0
            print(f"progress {done}/{total} ({rate:.2f} items/sec)")

    con.close()


async def run(cfg: CrawlConfig) -> None:
    if cfg.mode == "enrich":
        con = _connect(cfg.db_path)
        try:
            cur = con.cursor()
            base = "from listings where source_html is not null"
            if cfg.only_autos:
                base += " and url like '%/vehicle/autos-%'"

            if cfg.limit is not None:
                total = int(cur.execute(f"select count(*) {base}").fetchone()[0])
                total = min(total, int(cfg.limit))
                sel = f"select id, url, source_html, attributes_json {base} limit ?"
                it = cur.execute(sel, (int(cfg.limit),))
            else:
                total = int(cur.execute(f"select count(*) {base}").fetchone()[0])
                sel = f"select id, url, source_html, attributes_json {base}"
                it = cur.execute(sel)

            print(f"enrich_total {total}")
            done = 0
            while True:
                batch = it.fetchmany(25)
                if not batch:
                    break
                for vehicle_id, url, source_html, attrs_json in batch:
                    try:
                        attrs = json.loads(attrs_json) if attrs_json else {}
                    except Exception:
                        attrs = {}
                    extracted = extract_listing(source_html or "", url)
                    attrs["source"] = "patiotuerca"
                    attrs["extracted"] = extracted
                    cur.execute(
                        "update listings set attributes_json=? where id=?",
                        (
                            json.dumps(
                                attrs, ensure_ascii=True, separators=(",", ":")
                            ),
                            vehicle_id,
                        ),
                    )
                    done += 1
                    if done % cfg.log_every == 0 or done == total:
                        con.commit()
                        print(f"enrich_progress {done}/{total}")
            con.commit()
        finally:
            con.close()
        return

    targets = load_targets(cfg)
    total = len(targets)
    print(f"remaining {total}")
    if total == 0:
        return

    inq: asyncio.Queue = asyncio.Queue(maxsize=cfg.concurrency * 3)
    outq: asyncio.Queue = asyncio.Queue(maxsize=cfg.concurrency * 3)

    limiter = RateLimiter(cfg.min_interval_sec)

    async with httpx.AsyncClient() as client:
        workers = [
            asyncio.create_task(worker(client, limiter, cfg, inq, outq))
            for _ in range(cfg.concurrency)
        ]
        writer_task = asyncio.create_task(writer(cfg, outq, total))

        for t in targets:
            await inq.put(t)
        for _ in workers:
            await inq.put(None)

        await inq.join()
        await outq.join()

        for t in workers:
            await t
        await writer_task


def parse_args() -> CrawlConfig:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--scrape-fetch-url",
        default="http://127.0.0.1:45000/v1/scrape/fetch",
        help="Voyant tool endpoint used for page fetches.",
    )
    p.add_argument("--db", default="data/patiotuerca_listings.sqlite")
    p.add_argument("--only-autos", action="store_true", default=True)
    p.add_argument("--include-non-autos", dest="only_autos", action="store_false")
    p.add_argument("--engine", choices=["httpx", "playwright", "auto"], default="httpx")
    p.add_argument("--concurrency", type=int, default=4)
    p.add_argument("--min-interval-sec", type=float, default=0.6)
    p.add_argument("--log-every", type=int, default=100)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--mode", choices=["crawl", "enrich"], default="crawl")
    a = p.parse_args()
    return CrawlConfig(
        scrape_fetch_url=a.scrape_fetch_url,
        db_path=a.db,
        only_autos=a.only_autos,
        engine=a.engine,
        concurrency=a.concurrency,
        min_interval_sec=a.min_interval_sec,
        log_every=a.log_every,
        limit=a.limit,
        mode=a.mode,
    )


def main() -> None:
    cfg = parse_args()
    asyncio.run(run(cfg))


if __name__ == "__main__":
    main()
