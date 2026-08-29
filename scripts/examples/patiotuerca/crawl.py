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
import json
from dataclasses import dataclass

import httpx
from extractors import (
    RateLimiter,
    _extract_images_from_json,
    _json_contains_vehicle_id,
    extract_listing,
    fetch_via_tool,
)
from loaders import _connect, _utcnow_iso, load_targets, writer
from transformers import _sanitize_json


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
                j = await fetch_via_tool(client, limiter, cfg.scrape_fetch_url, url, cfg.engine)
            html = j.get("html") or ""

            extracted = extract_listing(html, url)
            captured = j.get("captured_json") if isinstance(j, dict) else None

            # If SSR HTML lacks rich sections, fall back to Playwright JSON capture.
            if (
                cfg.engine == "auto"
                and not extracted.get("technical_data")
                and not extracted.get("additional_properties")
            ):
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
                            json.dumps(attrs, ensure_ascii=True, separators=(",", ":")),
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
        workers = [asyncio.create_task(worker(client, limiter, cfg, inq, outq)) for _ in range(cfg.concurrency)]
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
