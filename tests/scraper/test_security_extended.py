"""Extended tests for apps.scraper.security module."""

import ipaddress

import pytest

from apps.scraper.security import (
    ALLOWED_SCHEMES,
    BLOCKED_EXTENSIONS,
    BLOCKED_HOSTS,
    BLOCKED_NETWORKS,
    RATE_LIMITS,
    RateLimitExceeded,
    SSRFError,
    URLValidationError,
    get_rate_limit,
    is_ip_blocked,
    resolve_hostname,
    sanitize_selector,
    validate_url,
    validate_url_ssrf,
    validate_urls,
)


# ---------------------------------------------------------------------------
# is_ip_blocked
# ---------------------------------------------------------------------------


class TestIsIpBlocked:
    def test_loopback_ipv4_blocked(self):
        assert is_ip_blocked("127.0.0.1") is True

    def test_loopback_range_blocked(self):
        assert is_ip_blocked("127.0.0.2") is True
        assert is_ip_blocked("127.255.255.255") is True

    def test_private_class_a_blocked(self):
        assert is_ip_blocked("10.0.0.1") is True
        assert is_ip_blocked("10.255.255.255") is True

    def test_private_class_b_blocked(self):
        assert is_ip_blocked("172.16.0.1") is True
        assert is_ip_blocked("172.31.255.255") is True

    def test_private_class_c_blocked(self):
        assert is_ip_blocked("192.168.0.1") is True
        assert is_ip_blocked("192.168.255.255") is True

    def test_link_local_blocked(self):
        assert is_ip_blocked("169.254.1.1") is True

    def test_multicast_blocked(self):
        assert is_ip_blocked("224.0.0.1") is True

    def test_broadcast_blocked(self):
        assert is_ip_blocked("255.255.255.255") is True

    def test_ipv6_loopback_blocked(self):
        assert is_ip_blocked("::1") is True

    def test_ipv6_link_local_blocked(self):
        assert is_ip_blocked("fe80::1") is True

    def test_public_ip_not_blocked(self):
        assert is_ip_blocked("8.8.8.8") is False
        assert is_ip_blocked("1.1.1.1") is False

    def test_invalid_ip_returns_false(self):
        assert is_ip_blocked("not-an-ip") is False
        assert is_ip_blocked("") is False

    def test_carrier_grade_nat_blocked(self):
        assert is_ip_blocked("100.64.0.1") is True

    def test_test_net_blocked(self):
        assert is_ip_blocked("192.0.2.1") is True
        assert is_ip_blocked("198.51.100.1") is True
        assert is_ip_blocked("203.0.113.1") is True


# ---------------------------------------------------------------------------
# validate_url_ssrf
# ---------------------------------------------------------------------------


class TestValidateUrlSsrf:
    def test_empty_url(self):
        safe, reason = validate_url_ssrf("")
        assert safe is False
        assert "empty" in reason.lower()

    def test_missing_scheme(self):
        safe, reason = validate_url_ssrf("example.com/path")
        assert safe is False
        assert "scheme" in reason.lower()

    def test_blocked_scheme_ftp(self):
        safe, reason = validate_url_ssrf("ftp://example.com/file")
        assert safe is False
        assert "scheme" in reason.lower()

    def test_blocked_scheme_file(self):
        safe, reason = validate_url_ssrf("file:///etc/passwd")
        assert safe is False

    def test_allowed_scheme_http(self):
        safe, reason = validate_url_ssrf("http://example.com", resolve_dns=False)
        assert safe is True

    def test_allowed_scheme_https(self):
        safe, reason = validate_url_ssrf("https://example.com", resolve_dns=False)
        assert safe is True

    def test_blocked_host_localhost(self):
        safe, reason = validate_url_ssrf("http://localhost:8080/api", resolve_dns=False)
        assert safe is False
        assert "blocked host" in reason.lower() or "blocked" in reason.lower()

    def test_blocked_host_metadata_aws(self):
        safe, reason = validate_url_ssrf("http://169.254.169.254/latest/meta-data/", resolve_dns=False)
        assert safe is False

    def test_blocked_extension_exe(self):
        safe, reason = validate_url_ssrf("http://example.com/malware.exe", resolve_dns=False)
        assert safe is False
        assert "extension" in reason.lower()

    def test_blocked_extension_php(self):
        safe, reason = validate_url_ssrf("http://example.com/script.php", resolve_dns=False)
        assert safe is False

    def test_blocked_extension_jar(self):
        safe, reason = validate_url_ssrf("http://example.com/app.jar", resolve_dns=False)
        assert safe is False

    def test_safe_url_passes(self):
        safe, reason = validate_url_ssrf("https://example.com/page.html", resolve_dns=False)
        assert safe is True
        assert "safe" in reason.lower()

    def test_decimal_ip_bypass_blocked(self):
        # 2130706433 = 127.0.0.1 in decimal
        safe, reason = validate_url_ssrf("http://2130706433/", resolve_dns=False)
        assert safe is False
        assert "decimal" in reason.lower()

    def test_url_with_credentials_blocked_host(self):
        safe, reason = validate_url_ssrf("http://user:pass@localhost/admin", resolve_dns=False)
        assert safe is False

    def test_missing_hostname(self):
        safe, reason = validate_url_ssrf("http://", resolve_dns=False)
        assert safe is False
        assert "hostname" in reason.lower()

    def test_private_ip_direct(self):
        safe, reason = validate_url_ssrf("http://10.0.0.1/admin", resolve_dns=False)
        assert safe is False

    def test_allowed_extensions_pass(self):
        safe, reason = validate_url_ssrf("https://example.com/document.pdf", resolve_dns=False)
        assert safe is True

    def test_case_insensitive_scheme(self):
        safe, reason = validate_url_ssrf("HTTPS://example.com", resolve_dns=False)
        assert safe is True


# ---------------------------------------------------------------------------
# validate_url (wrapper with exceptions)
# ---------------------------------------------------------------------------


class TestValidateUrl:
    def test_empty_raises_url_validation_error(self):
        with pytest.raises(URLValidationError, match="empty"):
            validate_url("")

    def test_too_long_raises(self):
        long_url = "https://example.com/" + "a" * 2050
        with pytest.raises(URLValidationError, match="length"):
            validate_url(long_url)

    def test_ssrf_blocked_raises_ssrf_error(self):
        with pytest.raises(SSRFError):
            validate_url("http://169.254.169.254/latest/")

    def test_valid_url_returns_stripped(self):
        result = validate_url("  https://example.com  ")
        assert result == "https://example.com"

    def test_max_length_url_accepted(self):
        # Exactly 2048 chars should be fine
        url = "https://example.com/" + "a" * (2048 - len("https://example.com/"))
        result = validate_url(url)
        assert len(result) == 2048


# ---------------------------------------------------------------------------
# validate_urls (batch)
# ---------------------------------------------------------------------------


class TestValidateUrls:
    def test_empty_list_raises(self):
        with pytest.raises(URLValidationError, match="empty"):
            validate_urls([])

    def test_too_many_urls_raises(self):
        urls = [f"https://example.com/{i}" for i in range(1001)]
        with pytest.raises(URLValidationError, match="1000"):
            validate_urls(urls)

    def test_valid_batch(self):
        urls = ["https://example.com", "https://google.com"]
        result = validate_urls(urls)
        assert len(result) == 2

    def test_bad_url_reports_index(self):
        urls = ["https://example.com", "http://169.254.169.254/"]
        with pytest.raises(SSRFError, match="index 1"):
            validate_urls(urls)


# ---------------------------------------------------------------------------
# sanitize_selector
# ---------------------------------------------------------------------------


class TestSanitizeSelector:
    def test_empty_selector(self):
        assert sanitize_selector("") == ""

    def test_normal_css_selector(self):
        sel = "div.class > span"
        assert sanitize_selector(sel) == sel

    def test_javascript_uri_stripped(self):
        result = sanitize_selector("javascript:alert(1)")
        assert "javascript:" not in result

    def test_data_uri_stripped(self):
        result = sanitize_selector("data:text/html,<script>")
        assert "data:" not in result

    def test_max_length_enforced(self):
        long_sel = "a" * 1500
        result = sanitize_selector(long_sel)
        assert len(result) == 1000

    def test_whitespace_stripped(self):
        result = sanitize_selector("  div  ")
        assert result == "div"

    def test_case_insensitive_javascript_removal(self):
        result = sanitize_selector("JaVaScRiPt:alert(1)")
        assert "javascript" not in result.lower() or result == "alert(1)"


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------


class TestRateLimiting:
    def test_default_tier(self):
        limits = get_rate_limit("tenant-1", "default")
        assert limits["requests_per_hour"] == 100
        assert limits["urls_per_request"] == 1000
        assert limits["concurrent_jobs"] == 10

    def test_premium_tier(self):
        limits = get_rate_limit("tenant-2", "premium")
        assert limits["requests_per_hour"] == 1000
        assert limits["urls_per_request"] == 10000
        assert limits["concurrent_jobs"] == 50

    def test_unknown_tier_falls_back_to_default(self):
        limits = get_rate_limit("tenant-3", "nonexistent")
        assert limits == RATE_LIMITS["default"]

    def test_rate_limit_exceeded_exception(self):
        exc = RateLimitExceeded("Too many requests", retry_after=120)
        assert str(exc) == "Too many requests"
        assert exc.retry_after == 120

    def test_rate_limit_exceeded_default_retry(self):
        exc = RateLimitExceeded("Limit hit")
        assert exc.retry_after == 3600


# ---------------------------------------------------------------------------
# Constants sanity checks
# ---------------------------------------------------------------------------


class TestConstants:
    def test_allowed_schemes_only_http_https(self):
        assert ALLOWED_SCHEMES == {"http", "https"}

    def test_blocked_hosts_contains_localhost(self):
        assert "localhost" in BLOCKED_HOSTS

    def test_blocked_hosts_contains_metadata(self):
        assert "169.254.169.254" in BLOCKED_HOSTS
        assert "metadata.google.internal" in BLOCKED_HOSTS

    def test_blocked_extensions_contains_exe(self):
        assert ".exe" in BLOCKED_EXTENSIONS
        assert ".php" in BLOCKED_EXTENSIONS

    def test_blocked_networks_are_ip_networks(self):
        for net in BLOCKED_NETWORKS:
            assert isinstance(net, ipaddress.IPv4Network | ipaddress.IPv6Network)

    def test_rate_limits_have_required_keys(self):
        for tier_name, tier_config in RATE_LIMITS.items():
            assert "requests_per_hour" in tier_config
            assert "urls_per_request" in tier_config
            assert "concurrent_jobs" in tier_config
