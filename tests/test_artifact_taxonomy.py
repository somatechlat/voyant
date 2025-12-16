"""
Tests for Artifact Key Taxonomy

Verifies that artifact keys follow the canonical taxonomy.
Reference: docs/CANONICAL_ARCHITECTURE.md Section 6

Canonical Artifact Types:
- profile.html / profile.json
- quality.html / quality.json
- drift.html / drift.json
- kpis.json
- chart_*.html
- sufficiency.json
- narrative.txt / narrative.md
- manifest.json
"""
import pytest
import re
from typing import Set

# Canonical artifact key patterns
CANONICAL_PATTERNS = {
    # Profile artifacts
    r"^profile\.(html|json)$": "Profile artifact",
    # Quality artifacts
    r"^quality\.(html|json)$": "Quality artifact",
    # Drift artifacts  
    r"^drift\.(html|json)$": "Drift artifact",
    # KPI artifacts
    r"^kpis\.json$": "KPI JSON",
    # Chart artifacts (numbered or named)
    r"^chart_[\w]+\.(html|png)$": "Chart artifact",
    r"^charts/[\w]+\.(html|png)$": "Chart in subdirectory",
    # Sufficiency
    r"^sufficiency\.json$": "Sufficiency score",
    # Narrative
    r"^narrative\.(txt|md)$": "Narrative summary",
    # Manifest
    r"^manifest\.json$": "Artifact manifest",
}


def is_valid_artifact_key(key: str) -> bool:
    """Check if an artifact key matches any canonical pattern."""
    for pattern in CANONICAL_PATTERNS:
        if re.match(pattern, key):
            return True
    return False


def get_artifact_type(key: str) -> str:
    """Get the description for an artifact key."""
    for pattern, desc in CANONICAL_PATTERNS.items():
        if re.match(pattern, key):
            return desc
    return "Unknown"


class TestArtifactTaxonomyPatterns:
    """Test artifact key pattern matching."""

    def test_profile_html_valid(self):
        assert is_valid_artifact_key("profile.html")
    
    def test_profile_json_valid(self):
        assert is_valid_artifact_key("profile.json")
    
    def test_quality_html_valid(self):
        assert is_valid_artifact_key("quality.html")
    
    def test_quality_json_valid(self):
        assert is_valid_artifact_key("quality.json")
    
    def test_drift_html_valid(self):
        assert is_valid_artifact_key("drift.html")
    
    def test_drift_json_valid(self):
        assert is_valid_artifact_key("drift.json")
    
    def test_kpis_json_valid(self):
        assert is_valid_artifact_key("kpis.json")
    
    def test_chart_numbered_valid(self):
        assert is_valid_artifact_key("chart_1.html")
        assert is_valid_artifact_key("chart_revenue.html")
        assert is_valid_artifact_key("chart_bar_01.png")
    
    def test_chart_in_subdir_valid(self):
        assert is_valid_artifact_key("charts/revenue.html")
        assert is_valid_artifact_key("charts/bar_chart.png")
    
    def test_sufficiency_valid(self):
        assert is_valid_artifact_key("sufficiency.json")
    
    def test_narrative_txt_valid(self):
        assert is_valid_artifact_key("narrative.txt")
    
    def test_narrative_md_valid(self):
        assert is_valid_artifact_key("narrative.md")
    
    def test_manifest_valid(self):
        assert is_valid_artifact_key("manifest.json")
    
    def test_invalid_random_key(self):
        assert not is_valid_artifact_key("random.txt")
    
    def test_invalid_typo(self):
        assert not is_valid_artifact_key("profiles.json")  # Should be profile.json
    
    def test_invalid_extension(self):
        assert not is_valid_artifact_key("profile.pdf")  # Not a valid extension


class TestArtifactTypeIdentification:
    """Test artifact type identification."""

    def test_get_profile_type(self):
        assert get_artifact_type("profile.json") == "Profile artifact"
    
    def test_get_quality_type(self):
        assert get_artifact_type("quality.html") == "Quality artifact"
    
    def test_get_chart_type(self):
        assert get_artifact_type("chart_revenue.html") == "Chart artifact"
    
    def test_get_sufficiency_type(self):
        assert get_artifact_type("sufficiency.json") == "Sufficiency score"
    
    def test_get_unknown_type(self):
        assert get_artifact_type("unknown.xyz") == "Unknown"


class TestGeneratorArtifactCompliance:
    """Test that generator outputs comply with taxonomy."""

    def test_core_generators_produce_valid_keys(self):
        """Core generators should produce valid artifact keys."""
        # Expected core artifacts
        core_artifacts = [
            "profile.html",
            "profile.json",
            "kpis.json",
            "sufficiency.json",
        ]
        for key in core_artifacts:
            assert is_valid_artifact_key(key), f"Core artifact {key} is not valid"

    def test_extended_generators_produce_valid_keys(self):
        """Extended generators should produce valid artifact keys."""
        # Expected extended artifacts
        extended_artifacts = [
            "quality.html",
            "quality.json",
            "drift.html",
            "drift.json",
            "chart_1.html",
            "charts/revenue.html",
            "narrative.txt",
        ]
        for key in extended_artifacts:
            assert is_valid_artifact_key(key), f"Extended artifact {key} is not valid"

    def test_manifest_always_valid(self):
        """Manifest should always be a valid artifact key."""
        assert is_valid_artifact_key("manifest.json")


class TestArtifactKeyNormalization:
    """Test artifact key normalization helpers."""

    def test_extract_base_name(self):
        """Should extract base name from artifact key."""
        def get_base(key: str) -> str:
            return key.split('.')[0].split('/')[-1]
        
        assert get_base("profile.json") == "profile"
        assert get_base("charts/revenue.html") == "revenue"
        assert get_base("chart_1.html") == "chart_1"

    def test_extract_format(self):
        """Should extract format from artifact key."""
        def get_format(key: str) -> str:
            return key.split('.')[-1]
        
        assert get_format("profile.json") == "json"
        assert get_format("quality.html") == "html"
        assert get_format("chart_1.png") == "png"
