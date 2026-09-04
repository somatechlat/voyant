"""
Report generator agent.

Produces a Markdown research report from synthesized findings, citations,
and confidence metadata. No LLM — pure deterministic templating.
"""

from __future__ import annotations

from datetime import UTC, datetime

from apps.scraper.deep_research.schemas import Citation, Finding, ResearchReport


class ReportGenerator:
    def generate(
        self,
        query: str,
        findings: list[Finding],
        citations: list[Citation],
        urls_processed: int,
        sources_deduplicated: int,
        depth: int = 1,
        breadth: int = 1,
    ) -> ResearchReport:
        now = datetime.now(UTC).isoformat()

        # Aggregate confidence.
        if findings:
            avg_confidence = sum(f.confidence_score for f in findings) / len(findings)
            cross_validated_count = sum(1 for f in findings if f.cross_validated)
            validation_rate = cross_validated_count / len(findings)
        else:
            avg_confidence = 0.0
            validation_rate = 0.0

        overall_confidence = round(avg_confidence * validation_rate, 4)

        # Executive summary.
        summary = self._build_executive_summary(
            query, findings, overall_confidence, urls_processed, sources_deduplicated
        )

        # Markdown body.
        markdown = self._build_markdown(
            query,
            summary,
            findings,
            citations,
            overall_confidence,
            urls_processed,
            sources_deduplicated,
            depth,
            breadth,
            now,
        )

        return ResearchReport(
            markdown=markdown,
            executive_summary=summary,
            findings=findings,
            citations=citations,
            confidence_score=overall_confidence,
            generated_at=now,
            query=query,
            breadth=breadth,
            depth=depth,
            urls_processed=urls_processed,
            sources_deduplicated=sources_deduplicated,
        )

    @staticmethod
    def _build_executive_summary(
        query: str,
        findings: list[Finding],
        confidence: float,
        urls_processed: int,
        deduplicated: int,
    ) -> str:
        """Compose a short executive summary paragraph."""
        validated = sum(1 for f in findings if f.cross_validated)
        parts = [
            f'Deep research on "{query}" processed {urls_processed} sources',
            f"({deduplicated} near-duplicates removed)",
            f"and produced {len(findings)} findings,",
            f"of which {validated} are cross-validated by multiple independent sources.",
            f"Aggregate confidence score: {confidence:.0%}.",
        ]
        return " ".join(parts)

    def _build_markdown(
        self,
        query: str,
        summary: str,
        findings: list[Finding],
        citations: list[Citation],
        confidence: float,
        urls_processed: int,
        deduplicated: int,
        depth: int,
        breadth: int,
        generated_at: str,
    ) -> str:
        """Assemble the full Markdown document."""
        lines = [
            f"# Deep Research Report: {query}",
            "",
            f"*Generated: {generated_at}*  ",
            f"*Depth: {depth} | Breadth: {breadth} | Confidence: {confidence:.0%}*",
            "",
            "## Executive Summary",
            "",
            summary,
            "",
            "## Findings",
            "",
        ]

        for idx, finding in enumerate(findings, start=1):
            status = "✅" if finding.cross_validated else "⚠️"
            lines.append(f"### {status} Finding {idx}: {finding.claim[:80]}...")
            lines.append("")
            lines.append(f"**Confidence:** {finding.confidence_score:.0%}")
            lines.append("")
            lines.append("**Evidence:**")
            for chunk in finding.evidence_chunks[:5]:
                snippet = chunk.text.replace("\n", " ")[:200]
                lines.append(f"- {snippet}... *[{chunk.source_url}]*")
            lines.append("")
            lines.append(f"**Supporting sources:** {len(finding.supporting_sources)}")
            lines.append("")

        lines.extend(
            [
                "## Citations",
                "",
                "| # | Domain | Title | URL | Credibility |",
                "|---|--------|-------|-----|-------------|",
            ]
        )
        for idx, cite in enumerate(citations, start=1):
            title = cite.title.replace("|", "\\|") or "—"
            lines.append(
                f"| {idx} | {cite.domain} | {title} | {cite.url} | {cite.credibility_score:.0%} |"
            )

        lines.extend(
            [
                "",
                "## Methodology",
                "",
                "1. **Query Expansion** — deterministic keyword-driven sub-query generation.",
                "2. **Multi-Source Search** — SearXNG, Brave Search, Google CSE.",
                "3. **Content Fetch** — Octopus ARM-2 (dynamic) and ARM-3 (evasion).",
                "4. **Extraction** — trafilatura / readability-lxml / newspaper3k / crawl4ai.",
                "5. **Source Scoring** — static domain credibility DB + freshness heuristics.",
                "6. **Deduplication** — MinHash/LSH on character n-grams.",
                "7. **Synthesis** — TF-IDF sentence salience + keyword clustering.",
                "8. **Recursion** — follow-up queries when depth > 1.",
                "9. **Cross-Validation** — claims verified by >=2 independent sources.",
                "10. **Report Generation** — deterministic Markdown templating.",
                "",
                f"*URLs processed: {urls_processed} | Deduplicated: {deduplicated}*",
                "",
            ]
        )

        return "\n".join(lines)
