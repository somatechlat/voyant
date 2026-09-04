"""
DeepResearchWorkflowV2 — Temporal workflow for autonomous multi-source research.

Orchestrates a deterministic pipeline:
  1. Query expansion (breadth parallel)
  2. Multi-engine search (SearXNG + Brave + Google CSE)
  3. Parallel content fetch (Octopus ARM-2/3)
  4. Content extraction (trafilatura / readability / newspaper / crawl4ai)
  5. Source scoring (domain credibility DB + freshness)
  6. Deduplication (MinHash/LSH)
  7. Synthesis (structured findings with attribution)
  8. Recursive follow-up queries when depth > 1
  9. Cross-reference validation (>=2 independent sources)
  10. Markdown report generation + ArtifactStore persistence

Zero LLM usage. All algorithms are deterministic and reproducible.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from apps.scraper.deep_research.schemas import ResearchConfig


@workflow.defn(name="DeepResearchWorkflowV2")
class DeepResearchWorkflowV2:
    """
    Temporal workflow that executes deep research across multiple search engines,
    scrapes content via Octopus, and produces a validated Markdown report.
    """

    @workflow.run
    async def run(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Execute the deep research pipeline.

        Args:
            params: Dictionary compatible with ResearchConfig.
                - query (str): Primary research query.
                - breadth (int): Number of parallel sub-queries.
                - depth (int): Recursive depth levels.
                - tenant_id (str): Tenant identifier.
                - realm (str): Security realm.
                - user_id (str): Initiating user.
                - max_urls_per_query (int): Max URLs to fetch per sub-query.
                - min_source_score (float): Minimum source credibility.
                - dedup_threshold (float): Jaccard threshold for dedup.
                - require_cross_validation (bool): Require >=2 sources.

        Returns:
            Dict with status, job_id, report, artifact_hash, and metadata.
        """
        config = ResearchConfig(**params)
        job_id = params.get("job_id", workflow.info().workflow_id)
        tenant_id = config.tenant_id

        workflow.logger.info(
            f"[DeepResearchV2] start query='{config.query}' "
            f"breadth={config.breadth} depth={config.depth} "
            f"job_id={job_id}"
        )

        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2.0,
            maximum_interval=timedelta(seconds=60),
            maximum_attempts=3,
            non_retryable_error_types=[
                "ValidationError",
                "AuthenticationError",
                "AuthorizationError",
                "ApplicationError",
            ],
        )

        # ------------------------------------------------------------------
        # STEP 1: Generate sub-queries
        # ------------------------------------------------------------------
        queries = await workflow.execute_activity(
            "dr_generate_queries",
            {"query": config.query, "breadth": config.breadth},
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=retry_policy,
        )

        if not queries:
            workflow.logger.warning("[DeepResearchV2] no queries generated")
            return self._error_result(job_id, "Query generation returned nothing")

        # ------------------------------------------------------------------
        # STEP 2 + 3 + 4 + 5 + 6 + 7: Execute per-depth layer
        # ------------------------------------------------------------------
        all_url_texts: dict[str, str] = {}
        all_search_results: list[dict[str, Any]] = []
        total_urls_processed = 0
        total_deduplicated = 0

        current_queries = queries
        for layer in range(1, config.depth + 1):
            workflow.logger.info(
                f"[DeepResearchV2] depth layer {layer}/{config.depth} "
                f"queries={len(current_queries)}"
            )

            # 2a. Search all engines in parallel per query.
            search_futures = []
            for q in current_queries:
                search_futures.append(
                    workflow.execute_activity(
                        "dr_search_all_engines",
                        {
                            "query": q,
                            "max_results": config.max_urls_per_query,
                            "tenant_id": tenant_id,
                        },
                        start_to_close_timeout=timedelta(minutes=2),
                        retry_policy=retry_policy,
                    )
                )

            per_query_results: list[list[dict[str, Any]]] = await asyncio.gather(
                *search_futures
            )

            # Flatten and deduplicate by URL.
            layer_results: list[dict[str, Any]] = []
            seen_urls: set[str] = set()
            for batch in per_query_results:
                for item in batch:
                    url = item.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        layer_results.append(item)

            if not layer_results:
                workflow.logger.warning(
                    f"[DeepResearchV2] no search results at layer {layer}"
                )
                break

            all_search_results.extend(layer_results)

            # 3. Fetch content in parallel.
            fetch_futures = []
            for idx, item in enumerate(layer_results):
                url = item.get("url", "")
                if not url:
                    continue
                fetch_futures.append(
                    workflow.execute_activity(
                        "dr_fetch_octopus",
                        {
                            "url": url,
                            "tenant_id": tenant_id,
                            "job_id": f"{job_id}_layer{layer}_fetch{idx}",
                            "arm": "auto",
                        },
                        start_to_close_timeout=timedelta(minutes=3),
                        retry_policy=retry_policy,
                    )
                )

            fetched_pages: list[dict[str, Any]] = []
            if fetch_futures:
                fetched_pages = await asyncio.gather(*fetch_futures)

            # 4. Extract content in parallel.
            extract_futures = []
            for page in fetched_pages:
                html = page.get("html", "")
                url = page.get("url", "")
                if not html or not url:
                    continue
                extract_futures.append(
                    workflow.execute_activity(
                        "dr_extract_content",
                        {"url": url, "html": html},
                        start_to_close_timeout=timedelta(minutes=1),
                        retry_policy=retry_policy,
                    )
                )

            extracted_items: list[dict[str, Any]] = []
            if extract_futures:
                extracted_items = await asyncio.gather(*extract_futures)

            # Map URL -> extracted text.
            url_texts: dict[str, str] = {}
            fetch_meta: dict[str, dict[str, Any]] = {}
            for page in fetched_pages:
                url = page.get("url", "")
                if url:
                    fetch_meta[url] = page

            for ex in extracted_items:
                if ex.get("success"):
                    url = ex.get("url", "")
                    text = ex.get("text", "")
                    if url and text:
                        url_texts[url] = text

            total_urls_processed += len(url_texts)

            if not url_texts:
                workflow.logger.warning(
                    f"[DeepResearchV2] no extractable content at layer {layer}"
                )
                break

            # 5. Source scoring.
            scored = await workflow.execute_activity(
                "dr_score_sources",
                {
                    "url_texts": url_texts,
                    "min_score": config.min_source_score,
                    "fetched_at": workflow.now().isoformat(),
                },
                start_to_close_timeout=timedelta(minutes=1),
                retry_policy=retry_policy,
            )

            # Retain only scored URLs.
            scored_url_texts = {
                url: txt for url, txt in url_texts.items() if url in scored
            }

            if not scored_url_texts:
                workflow.logger.warning(
                    f"[DeepResearchV2] all sources failed scoring at layer {layer}"
                )
                break

            # 6. Deduplication.
            dedup = await workflow.execute_activity(
                "dr_deduplicate",
                {
                    "url_texts": scored_url_texts,
                    "threshold": config.dedup_threshold,
                },
                start_to_close_timeout=timedelta(minutes=1),
                retry_policy=retry_policy,
            )

            keep_urls = dedup.get("keep_urls", [])
            removed_urls = dedup.get("removed_urls", [])
            total_deduplicated += len(removed_urls)

            deduped_texts = {u: scored_url_texts[u] for u in keep_urls if u in scored_url_texts}

            # Merge into global corpus.
            all_url_texts.update(deduped_texts)

            # 7. Synthesize.
            synthesis_raw = await workflow.execute_activity(
                "dr_synthesize",
                {
                    "url_texts": deduped_texts,
                    "search_results": [
                        item for item in layer_results
                        if item.get("url") in deduped_texts
                    ],
                },
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=retry_policy,
            )

            findings = synthesis_raw.get("findings", [])
            follow_ups = synthesis_raw.get("follow_up_queries", [])

            workflow.logger.info(
                f"[DeepResearchV2] layer {layer} findings={len(findings)} "
                f"follow_ups={len(follow_ups)}"
            )

            # 8. Recursion — prepare next layer queries.
            if layer < config.depth and follow_ups:
                # Limit follow-ups to breadth.
                current_queries = follow_ups[: config.breadth]
            else:
                break

        if not all_url_texts:
            return self._error_result(
                job_id, "No usable content found across all search layers"
            )

        # ------------------------------------------------------------------
        # STEP 9: Cross-reference validation (full corpus)
        # ------------------------------------------------------------------
        # Re-synthesize on the full merged corpus to get unified findings.
        full_synthesis_raw = await workflow.execute_activity(
            "dr_synthesize",
            {
                "url_texts": all_url_texts,
                "search_results": all_search_results,
            },
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=retry_policy,
        )

        validated_raw = await workflow.execute_activity(
            "dr_cross_validate",
            {
                "findings": full_synthesis_raw.get("findings", []),
                "url_texts": all_url_texts,
            },
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=retry_policy,
        )

        validated_findings = validated_raw.get("findings", [])
        citations = full_synthesis_raw.get("citations", [])

        # ------------------------------------------------------------------
        # STEP 10: Generate report
        # ------------------------------------------------------------------
        report_raw = await workflow.execute_activity(
            "dr_generate_report",
            {
                "query": config.query,
                "findings": validated_findings,
                "citations": citations,
                "urls_processed": total_urls_processed,
                "sources_deduplicated": total_deduplicated,
                "depth": config.depth,
                "breadth": config.breadth,
            },
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=retry_policy,
        )

        # ------------------------------------------------------------------
        # Store artifact
        # ------------------------------------------------------------------
        artifact_info = await workflow.execute_activity(
            "dr_store_artifact",
            {
                "job_id": job_id,
                "tenant_id": tenant_id,
                "report": report_raw,
            },
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=retry_policy,
        )

        artifact_hash = artifact_info.get("artifact_hash", "")
        report_raw["artifact_hash"] = artifact_hash

        workflow.logger.info(
            f"[DeepResearchV2] complete job_id={job_id} "
            f"confidence={report_raw.get('confidence_score', 0)} "
            f"artifact={artifact_hash[:24]}..."
        )

        return {
            "status": "success",
            "job_id": job_id,
            "query": config.query,
            "depth": config.depth,
            "breadth": config.breadth,
            "urls_processed": total_urls_processed,
            "sources_deduplicated": total_deduplicated,
            "findings_count": len(validated_findings),
            "confidence_score": report_raw.get("confidence_score", 0.0),
            "artifact_hash": artifact_hash,
            "report": report_raw,
        }

    @staticmethod
    def _error_result(job_id: str, reason: str) -> dict[str, Any]:
        return {
            "status": "failed",
            "job_id": job_id,
            "error": reason,
        }
