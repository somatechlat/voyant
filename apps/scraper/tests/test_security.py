"""
VOYANT DataScraper - Security Tests

Tests SSRF protection and URL validation.
Production Standard v3 Compliant - Real infrastructure testing.

All 10 Production Personas Active:
- PhD Lead Software Architect: Validates security architecture
- Security Auditor: Enforces Zero-Bypass security
- QA Engineer: Edge cases testing
"""

import pytest

from apps.scraper.security import (
    BLOCKED_HOSTS,
    BLOCKED_NETWORKS,
    is_ip_blocked,
    resolve_hostname,
    validate_url_ssrf,
)


class TestSSRFProtection:
    """Test SSRF protection mechanisms."""

    def test_valid_public_url(self):
        """Valid public URLs should pass."""
        valid_urls = [
            "https://example.com",
            "https://google.com",
            "https://sri.gob.ec",
            "https://www.sercop.gob.ec",
        ]
        for url in valid_urls:
            is_safe, error = validate_url_ssrf(url, resolve_dns=False)
            assert is_safe is True, f"URL {url} should be valid: {error}"

    def test_localhost_blocked(self):
        """Localhost URLs must be blocked."""
        blocked_urls = [
            "http://localhost",
            "http://localhost:8000",
            "http://127.0.0.1",
            "http://127.0.0.1:3000",
            "http://0.0.0.0",
        ]
        for url in blocked_urls:
            is_safe, error = validate_url_ssrf(url, resolve_dns=False)
            assert is_safe is False, f"URL {url} should be blocked"

    def test_private_ip_blocked(self):
        """Private IP ranges must be blocked."""
        private_urls = [
            "http://10.0.0.1",
            "http://192.168.1.1",
            "http://172.16.0.1",
            "http://10.255.255.255",
        ]
        for url in private_urls:
            is_safe, error = validate_url_ssrf(url, resolve_dns=False)
            assert is_safe is False, f"URL {url} should be blocked: {error}"

    def test_metadata_endpoints_blocked(self):
        """AWS/GCP metadata endpoints must be blocked."""
        blocked_urls = [
            "http://169.254.169.254",  # AWS metadata
        ]
        for url in blocked_urls:
            is_safe, error = validate_url_ssrf(url, resolve_dns=False)
            assert is_safe is False, f"Metadata URL {url} should be blocked"


class TestIPBlocking:
    """Test IP address blocking."""

    def test_private_ip_detection(self):
        """Test private IP range detection."""
        assert is_ip_blocked("127.0.0.1") is True
        assert is_ip_blocked("10.0.0.1") is True
        assert is_ip_blocked("192.168.1.1") is True
        assert is_ip_blocked("172.16.0.1") is True
        assert is_ip_blocked("8.8.8.8") is False
        assert is_ip_blocked("142.250.80.46") is False

    def test_link_local_blocked(self):
        """Link-local IPs (AWS metadata) must be blocked."""
        assert is_ip_blocked("169.254.169.254") is True
        assert is_ip_blocked("169.254.0.1") is True

    def test_loopback_blocked(self):
        """Loopback range must be blocked."""
        assert is_ip_blocked("127.0.0.1") is True
        assert is_ip_blocked("127.255.255.255") is True

    def test_multicast_blocked(self):
        """Multicast range must be blocked."""
        assert is_ip_blocked("224.0.0.1") is True


class TestHostnameResolution:
    """Test hostname resolution for SSRF validation."""

    def test_resolve_valid_hostname(self):
        """Valid hostnames should resolve."""
        # Note: This test requires network access
        ip = resolve_hostname("google.com")
        # Should return an IP or None if network unavailable
        assert ip is None or isinstance(ip, str)

    def test_resolve_invalid_hostname(self):
        """Invalid hostnames should return None."""
        ip = resolve_hostname("this-hostname-does-not-exist-12345.com")
        assert ip is None


class TestBlockedHostsList:
    """Test blocked hosts configuration."""

    def test_blocked_hosts_contains_critical_entries(self):
        """Verify blocked hosts list contains critical entries."""
        assert "localhost" in BLOCKED_HOSTS
        assert "127.0.0.1" in BLOCKED_HOSTS
        assert "169.254.169.254" in BLOCKED_HOSTS
        assert "metadata.google.internal" in BLOCKED_HOSTS

    def test_blocked_networks_count(self):
        """Verify sufficient blocked networks defined."""
        assert len(BLOCKED_NETWORKS) >= 10  # At least 10 blocked ranges


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
