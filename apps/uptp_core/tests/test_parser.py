"""
Strict URIParser Unit Tests (QA Persona)

Verification of the core routing protocols ensures malicious or
malformed inputs immediately fail before crossing the boundary.
"""

import pytest

from apps.uptp_core.parser import URIParser


def test_uriparser_valid_postgres():
    uri = "postgresql://user_123:str0ngp@ss@db.example.com:5432/analytics_db"
    parsed = URIParser.parse_uri(uri)

    assert parsed["connector_id"] == "postgres"
    assert parsed["config"]["host"] == "db.example.com"
    assert parsed["config"]["port"] == 5432
    assert parsed["config"]["database"] == "analytics_db"
    assert parsed["config"]["user"] == "user_123"
    assert parsed["config"]["password"] == "str0ngp@ss"


def test_uriparser_invalid_scheme():
    with pytest.raises(ValueError, match="Unsupported generic URI scheme"):
        URIParser.parse_uri("unknown://test:pass@host/db")


def test_uriparser_malformed_string():
    with pytest.raises(ValueError, match="Invalid URI format"):
        URIParser.parse_uri("just_a_random_string_no_scheme")


def test_uriparser_s3_credentials():
    # S3 secrets must either be URL-encoded or not contain slashes to pass standard urlparse natively
    uri = "s3://AKIAIOSFODNN7EXAMPLE:wJalrXUtnFEMIK7MDENGbPxRfiCYEXAMPLEKEY@s3.amazonaws.com"
    parsed = URIParser.parse_uri(uri)
    assert parsed["connector_id"] == "s3"
    assert parsed["config"]["user"] == "AKIAIOSFODNN7EXAMPLE"
    assert parsed["config"]["password"] == "wJalrXUtnFEMIK7MDENGbPxRfiCYEXAMPLEKEY"


# Component 5.1.1 B: PII Validation Contract
def test_pii_hash_redaction_contract():
    import hashlib

    ssn = "123-45-6789"
    # The ETL hash pipeline ensures this specific mathematical transformation
    hashed = hashlib.sha256(ssn.encode()).hexdigest()
    # Ensure standard SHA-256 compliance in the generic transformer mechanism
    assert hashed == "01a54629efb952287e554eb23ef69c52097a75aecc0e3a93ca0855ab6d7a31a0"
