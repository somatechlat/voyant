"""Tests for apps.scraper.deep_research.credibility.domain_db."""

import pytest

from apps.scraper.deep_research.credibility.domain_db import (
    TIER_ACADEMIC,
    TIER_ESTABLISHED_MEDIA,
    TIER_FORUM,
    TIER_GOVERNMENT,
    TIER_LOW_QUALITY,
    TIER_MAJOR_NEWS,
    TIER_UNKNOWN,
    DomainCredibilityDB,
    get_domain_credibility_db,
)


@pytest.fixture
def db():
    return DomainCredibilityDB()


# ---------------------------------------------------------------------------
# DomainCredibilityDB.score
# ---------------------------------------------------------------------------


class TestDomainCredibilityDBScore:
    def test_academic_arxiv(self, db):
        assert db.score("https://arxiv.org/abs/1234") == TIER_ACADEMIC

    def test_academic_pubmed(self, db):
        assert db.score("https://pubmed.ncbi.nlm.nih.gov/12345") == TIER_ACADEMIC

    def test_government_cdc(self, db):
        assert db.score("https://cdc.gov/health") == TIER_GOVERNMENT

    def test_government_who(self, db):
        assert db.score("https://who.int/news") == TIER_GOVERNMENT

    def test_major_news_reuters(self, db):
        assert db.score("https://reuters.com/article") == TIER_MAJOR_NEWS

    def test_major_news_bbc(self, db):
        assert db.score("https://bbc.com/news") == TIER_MAJOR_NEWS

    def test_forum_reddit(self, db):
        assert db.score("https://reddit.com/r/python") == TIER_FORUM

    def test_low_quality_hubpages(self, db):
        assert db.score("https://hubpages.com/article") == TIER_LOW_QUALITY

    def test_unknown_domain(self, db):
        assert db.score("https://random-unknown-site.com/page") == TIER_UNKNOWN

    def test_www_prefix_stripped(self, db):
        assert db.score("https://www.arxiv.org/paper") == TIER_ACADEMIC

    def test_subdomain_parent_match(self, db):
        # news.bbc.co.uk should match bbc.co.uk
        assert db.score("https://news.bbc.co.uk/article") == TIER_MAJOR_NEWS

    def test_edu_tld_heuristic(self, db):
        assert db.score("https://stanford.edu/research") == TIER_ACADEMIC

    def test_gov_tld_heuristic(self, db):
        assert db.score("https://energy.gov/policy") == TIER_GOVERNMENT

    def test_mil_tld_heuristic(self, db):
        assert db.score("https://army.mil/news") == TIER_GOVERNMENT

    def test_established_media(self, db):
        assert db.score("https://techcrunch.com/article") == TIER_ESTABLISHED_MEDIA
        assert db.score("https://wired.com/story") == TIER_ESTABLISHED_MEDIA

    def test_bare_domain(self, db):
        """Should handle bare domain without scheme."""
        assert db.score("arxiv.org") == TIER_ACADEMIC

    def test_score_range(self, db):
        """All scores should be in [0, 1]."""
        urls = [
            "https://arxiv.org", "https://cdc.gov", "https://reuters.com",
            "https://reddit.com", "https://unknown.xyz", "https://mit.edu",
        ]
        for url in urls:
            score = db.score(url)
            assert 0.0 <= score <= 1.0, f"Score {score} out of range for {url}"


# ---------------------------------------------------------------------------
# DomainCredibilityDB.bulk_score
# ---------------------------------------------------------------------------


class TestBulkScore:
    def test_bulk_score(self, db):
        urls = ["https://arxiv.org", "https://reddit.com"]
        result = db.bulk_score(urls)
        assert len(result) == 2
        assert result["https://arxiv.org"] == TIER_ACADEMIC
        assert result["https://reddit.com"] == TIER_FORUM


# ---------------------------------------------------------------------------
# Custom DB construction
# ---------------------------------------------------------------------------


class TestCustomDB:
    def test_custom_explicit_scores(self):
        custom = {"mydomain.com": 0.75}
        db = DomainCredibilityDB(explicit_scores=custom)
        assert db.score("https://mydomain.com/page") == 0.75

    def test_custom_tld_scores(self):
        custom_tld = {".custom": 0.88}
        db = DomainCredibilityDB(tld_scores=custom_tld)
        assert db.score("https://site.custom") == 0.88


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------


class TestSingleton:
    def test_get_returns_instance(self):
        instance = get_domain_credibility_db()
        assert isinstance(instance, DomainCredibilityDB)

    def test_get_returns_same_instance(self):
        a = get_domain_credibility_db()
        b = get_domain_credibility_db()
        assert a is b
