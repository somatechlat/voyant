#!/usr/bin/env python3
"""Output formatting and database loading."""

from __future__ import annotations

import asyncio
import sqlite3
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from crawl import CrawlConfig


def _utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


def _connect(db_path: str) -> sqlite3.Connection:
    con = sqlite3.connect(db_path, timeout=30)
    con.execute("pragma busy_timeout=30000")
    con.execute("pragma journal_mode=WAL")
    return con


def _ensure_tables(con: sqlite3.Connection) -> None:
    # listings + listing_urls already exist in this repo DB; keep schema compatible.
    con.execute("""
        create table if not exists fetch_errors(
          vehicle_id integer,
          url text,
          error text,
          at text
        )
        """)
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
                    (
                        vehicle_id,
                        url,
                        title,
                        price,
                        location,
                        attrs_json,
                        html,
                        fetched_at,
                    ),
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
