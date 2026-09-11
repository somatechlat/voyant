"""
Temporal activities for the Deep Research v2 pipeline.

Each activity is a deterministic, retryable unit of work that wraps one or
more agents. Activities are invoked by DeepResearchWorkflowV2.
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import UTC, datetime
from typing import Any

from temporalio import activity

from apps.core.config import get_settings
from apps.scraper.deep_research.agents.content_extractor import ContentExtractor
from apps.scraper.deep_research.agents.cross_validator import CrossValidator
from apps.scraper.deep_research.agents.query_generator import QueryGenerator
from apps.scraper.deep_research.agents.report_generator import ReportGenerator
from apps.scraper.deep_research.agents.source_scorer import SourceScorer
from apps.scraper.deep_research.agents.synthesizer import Synthesizer
from apps.scraper.deep_research.credibility.domain_db import get_domain_credibility_db
from apps.scraper.deep_research.schemas import (
    SearchResultItem,
)
from apps.scraper.deep_research.sources.brave_search import BraveSearchClient
from apps.scraper.deep_research.sources.google_cse import GoogleCSEClient
from apps.scraper.deep_research.sources.searxng_client import SearXNGClient

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# MinHash deduplication utilities
# ---------------------------------------------------------------------------

_NUM_HASHES = 64
_SHINGLE_SIZE = 5


def _shingles(text: str, k: int = _SHINGLE_SIZE) -> set[str]:
    """Return character k-shingles for the text."""
    cleaned = re.sub(r"\s+", " ", text.lower().strip())
    if len(cleaned) < k:
        return set()
    return {cleaned[i : i + k] for i in range(len(cleaned) - k + 1)}


def _minhash_signature(shingles: set[str], num_hashes: int = _NUM_HASHES) -> list[int]:
    """Compute a MinHash signature from a set of shingles."""
    if not shingles:
        return [0] * num_hashes
    sig: list[int] = []
    max_hash = 2**128  # MD5 produces 128-bit hashes
    for seed in range(num_hashes):
        min_val = max_hash
        for s in shingles:
            h = hashlib.md5((s + str(seed)).encode("utf-8")).hexdigest()
            val = int(h, 16)
            if val < min_val:
                min_val = val
        sig.append(min_val)
    return sig


def _jaccard_from_signatures(sig_a: list[int], sig_b: list[int]) -> float:
    """Estimate Jaccard similarity from two MinHash signatures."""
    if not sig_a or not sig_b:
        return 0.0
    matches = sum(1 for a, b in zip(sig_a, sig_b) if a == b)
    return matches / len(sig_a)


class DeepResearchActivities:
    """
    Temporal activities for deep research orchestration.
    """

    @activity.defn(name="dr_generate_queries")
    async def generate_queries(self, params: dict[str, Any]) -> list[str]:
        """
        Generate search-optimized sub-queries.

        Args:
            params:
                - query (str): Original query.
                - breadth (int): Number of sub-queries.

        Returns:
            List of sub-query strings.
        """
        query = str(params.get("query", ""))
        breadth = int(params.get("breadth", 3))
        generator = QueryGenerator()
        return generator.generate(query, breadth)

    @activity.defn(name="dr_search_all_engines")
    async def search_all_engines(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Search across SearXNG, Brave, and Google CSE in parallel.

        Args:
            params:
                - query (str): The sub-query.
                - max_results (int): Per engine.
                - tenant_id (str): Tenant identifier.

        Returns:
            List of serialized SearchResultItem dicts.
        """
        query = str(params.get("query", ""))
        max_results = int(params.get("max_results", 5))
        tenant_id = str(params.get("tenant_id", "default"))
        settings = get_settings()

        results: list[SearchResultItem] = []
        seen_urls: set[str] = set()

        # SearXNG (sovereign, zero-cost)
        try:
            sx = SearXNGClient()
            sx_results = await sx.search(query, max_results, tenant_id)
            for r in sx_results:
                if r.url and r.url not in seen_urls:
                    seen_urls.add(r.url)
                    results.append(r)
        except Exception as exc:
            logger.warning(f"[dr_search_all_engines] SearXNG failed: {exc}")

        # Brave Search
        try:
            brave = BraveSearchClient(api_key=settings.serper_api_key or None)
            brave_results = await brave.search(query, max_results, tenant_id)
            for r in brave_results:
                if r.url and r.url not in seen_urls:
                    seen_urls.add(r.url)
                    results.append(r)
            await brave.close()
        except Exception as exc:
            logger.warning(f"[dr_search_all_engines] Brave failed: {exc}")

        # Google CSE
        try:
            # Re-use serper key or expect separate env vars.
            g_cx = getattr(settings, "google_cse_cx", "")
            g_key = getattr(settings, "google_cse_api_key", "")
            g = GoogleCSEClient(api_key=g_key or None, cx=g_cx or None)
            g_results = await g.search(query, max_results, tenant_id)
            for r in g_results:
                if r.url and r.url not in seen_urls:
                    seen_urls.add(r.url)
                    results.append(r)
            await g.close()
        except Exception as exc:
            logger.warning(f"[dr_search_all_engines] Google CSE failed: {exc}")

        logger.info(f"[dr_search_all_engines] query='{query}' total={len(results)}")
        return [r.model_dump(mode="json") for r in results]

    @activity.defn(name="dr_fetch_octopus")
    async def fetch_octopus(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Fetch a URL via Octopus ARM-2 (dynamic) or ARM-3 (evasion).

        Falls back to the existing ScrapeActivities.fetch_page if Octopus
        arms are not yet available in the runtime.

        Args:
            params:
                - url (str)
                - tenant_id (str)
                - job_id (str)
                - arm (str): "dynamic" | "evasion" | "auto"

        Returns:
            Dict with html, url, status_code, fetched_at, error.
        """
        url = str(params.get("url", ""))
        tenant_id = str(params.get("tenant_id", "default"))
        job_id = str(params.get("job_id", ""))
        arm = str(params.get("arm", "auto"))

        # Try Octopus dispatcher first.
        try:
            from apps.scraper.octopus import OctopusDispatcher, OctopusRequest
            from apps.scraper.octopus.schemas import OctopusARM

            if arm == "auto":
                # Prefer evasion for known high-bot pages, else dynamic.
                arm_enum = OctopusARM.EVASION
            else:
                arm_enum = OctopusARM(arm)

            request = OctopusRequest(
                url=url,
                arm=arm_enum,
                tenant_id=tenant_id,
                job_id=job_id,
                block_resources=True,
                settle_ms=2000,
            )
            dispatcher = OctopusDispatcher()
            result = await dispatcher.dispatch(request)
            return {
                "html": result.html or "",
                "url": url,
                "status_code": result.status_code or 0,
                "fetched_at": datetime.now(UTC).isoformat(),
                "error": result.error_message,
            }
        except Exception as exc:
            logger.debug(f"[dr_fetch_octopus] Octopus unavailable ({exc}); fallback")

        # Fallback to legacy fetch_page activity.
        from apps.scraper.activities import ScrapeActivities

        fetch_result = await ScrapeActivities().fetch_page(
            {
                "url": url,
                "engine": "playwright",
                "tenant_id": tenant_id,
                "job_id": job_id,
            }
        )
        return {
            "html": fetch_result.get("html", ""),
            "url": url,
            "status_code": fetch_result.get("status_code", 0),
            "fetched_at": fetch_result.get("fetched_at", ""),
            "error": None,
        }

    @activity.defn(name="dr_extract_content")
    async def extract_content(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Extract text from HTML using the extraction agent.

        Args:
            params:
                - url (str)
                - html (str)

        Returns:
            Extraction result dict (text, title, method, success).
        """
        url = str(params.get("url", ""))
        html = str(params.get("html", ""))
        extractor = ContentExtractor()
        return extractor.extract(html, url)

    @activity.defn(name="dr_score_sources")
    async def score_sources(
        self, params: dict[str, Any]
    ) -> dict[str, dict[str, float]]:
        """
        Score sources by credibility and freshness.

        Args:
            params:
                - url_texts (Dict[str, str]): URL -> extracted text.
                - min_score (float): Minimum total score.
                - fetched_at (str): ISO timestamp.

        Returns:
            Dict of URL -> score dict for passing sources.
        """
        url_texts = params.get("url_texts", {})
        min_score = float(params.get("min_score", 0.15))
        fetched_at = params.get("fetched_at")

        scorer = SourceScorer(db=get_domain_credibility_db())
        return scorer.filter_sources(url_texts, min_score, fetched_at)

    @activity.defn(name="dr_deduplicate")
    async def deduplicate(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Remove near-duplicate sources using MinHash/LSH.

        Args:
            params:
                - url_texts (Dict[str, str]): URL -> extracted text.
                - threshold (float): Jaccard threshold for deduplication.

        Returns:
            Dict with:
                - keep_urls (List[str])
                - removed_urls (List[str])
                - duplicate_groups (Dict[str, List[str]])
        """
        url_texts: dict[str, str] = params.get("url_texts", {})
        threshold = float(params.get("threshold", 0.85))

        signatures: dict[str, list[int]] = {}
        for url, text in url_texts.items():
            sig = _minhash_signature(_shingles(text))
            signatures[url] = sig

        keep: list[str] = []
        removed: list[str] = []
        groups: dict[str, list[str]] = {}

        processed: set[str] = set()
        for url, sig in signatures.items():
            if url in processed:
                continue
            group = [url]
            for other_url, other_sig in signatures.items():
                if other_url == url or other_url in processed:
                    continue
                sim = _jaccard_from_signatures(sig, other_sig)
                if sim >= threshold:
                    group.append(other_url)
                    processed.add(other_url)
                    removed.append(other_url)
            keep.append(url)
            processed.add(url)
            groups[url] = group

        logger.info(f"[dr_deduplicate] keep={len(keep)} removed={len(removed)}")
        return {
            "keep_urls": keep,
            "removed_urls": removed,
            "duplicate_groups": groups,
        }

    @activity.defn(name="dr_synthesize")
    async def synthesize(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Synthesize extracted text into findings, citations, and follow-ups.

        Args:
            params:
                - url_texts (Dict[str, str])
                - search_results (List[Dict]): Serialized SearchResultItems.

        Returns:
            Serialized SynthesisOutput dict.
        """
        url_texts: dict[str, str] = params.get("url_texts", {})
        raw_results: list[dict[str, Any]] = params.get("search_results", [])

        search_results = {
            r["url"]: SearchResultItem(**r) for r in raw_results if r.get("url")
        }

        synthesizer = Synthesizer()
        output = synthesizer.synthesize(url_texts, search_results)
        return output.model_dump(mode="json")

    @activity.defn(name="dr_cross_validate")
    async def cross_validate(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Cross-validate findings against the full source corpus.

        Args:
            params:
                - findings (List[Dict]): Serialized Finding objects.
                - url_texts (Dict[str, str])

        Returns:
            Serialized list of validated Finding dicts.
        """
        from apps.scraper.deep_research.schemas import Finding

        raw_findings: list[dict[str, Any]] = params.get("findings", [])
        url_texts: dict[str, str] = params.get("url_texts", {})

        findings = [Finding(**f) for f in raw_findings]
        validator = CrossValidator()
        validated = validator.validate(findings, url_texts)
        return {"findings": [f.model_dump(mode="json") for f in validated]}

    @activity.defn(name="dr_generate_report")
    async def generate_report(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Generate the final Markdown research report.

        Args:
            params:
                - query (str)
                - findings (List[Dict])
                - citations (List[Dict])
                - urls_processed (int)
                - sources_deduplicated (int)
                - depth (int)
                - breadth (int)

        Returns:
            Serialized ResearchReport dict.
        """
        from apps.scraper.deep_research.schemas import Citation, Finding

        query = str(params.get("query", ""))
        findings = [Finding(**f) for f in params.get("findings", [])]
        citations = [Citation(**c) for c in params.get("citations", [])]
        urls_processed = int(params.get("urls_processed", 0))
        deduped = int(params.get("sources_deduplicated", 0))
        depth = int(params.get("depth", 1))
        breadth = int(params.get("breadth", 1))

        generator = ReportGenerator()
        report = generator.generate(
            query=query,
            findings=findings,
            citations=citations,
            urls_processed=urls_processed,
            sources_deduplicated=deduped,
            depth=depth,
            breadth=breadth,
        )
        return report.model_dump(mode="json")

    @activity.defn(name="dr_store_artifact")
    async def store_artifact(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Store a research report artifact via ArtifactStore.

        Args:
            params:
                - job_id (str)
                - tenant_id (str)
                - report (Dict): Serialized ResearchReport.

        Returns:
            Dict with artifact_hash and artifact_ref.
        """
        from apps.core.lib.artifact_store import store_artifact

        job_id = str(params.get("job_id", ""))
        tenant_id = str(params.get("tenant_id", "default"))
        report_dict = params.get("report", {})

        ref = store_artifact(
            content=report_dict,
            artifact_type="deep_research_report",
            metadata={
                "job_id": job_id,
                "tenant_id": tenant_id,
                "query": report_dict.get("query", ""),
                "confidence_score": report_dict.get("confidence_score", 0.0),
            },
        )
        return {
            "artifact_hash": ref.hash,
            "artifact_ref": ref.to_dict(),
        }
