"""
Domain credibility subsystem for Deep Research v2.

Provides a static, deterministic credibility database for scoring web sources.
"""

from apps.scraper.deep_research.credibility.domain_db import (
    DomainCredibilityDB,
    get_domain_credibility_db,
)

__all__ = ["DomainCredibilityDB", "get_domain_credibility_db"]
