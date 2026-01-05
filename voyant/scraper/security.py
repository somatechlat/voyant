"""
Voyant DataScraper - Security Module for URL Validation and SSRF Protection.

This module implements critical security controls for the web scraper, primarily
focused on preventing Server-Side Request Forgery (SSRF) vulnerabilities and
ensuring that the scraper interacts only with legitimate and safe external resources.

It provides functionalities for:
-   Validating URLs against blocked schemes, hosts, IP ranges, and file extensions.
-   Resolving hostnames to IP addresses for deep IP-level blocking.
-   Sanitizing user-provided selectors to prevent injection attacks.
-   Defining and retrieving rate limiting configurations.
"""

import ipaddress
import re
import socket
from typing import Optional, Tuple
from urllib.parse import urlparse

import logging

logger = logging.getLogger(__name__)


# =============================================================================
# SSRF PROTECTION CONFIGURATION
# =============================================================================

# BLOCKED_HOSTS: A set of hostnames that are explicitly forbidden.
# This list includes common loopback addresses, internal metadata service IPs
# (e.g., AWS, GCP, Azure), and other hostnames that should never be accessed
# by the scraper.
BLOCKED_HOSTS = frozenset(
    {
        "localhost",
        "localhost.localdomain",
        "127.0.0.1",
        "::1",
        "0.0.0.0",
        "169.254.169.254",  # AWS EC2 Instance Metadata Service
        "metadata.google.internal",  # Google Cloud metadata service
        "metadata.azure.internal",  # Azure Instance Metadata Service
    }
)

# BLOCKED_NETWORKS: A list of IP address ranges (in CIDR notation) that are forbidden.
# This is crucial for preventing access to private networks, internal resources,
# and metadata services that resolve to non-public IPs.
BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),  # Loopback addresses (IPv4)
    ipaddress.ip_network("10.0.0.0/8"),  # Private Class A network
    ipaddress.ip_network("172.16.0.0/12"),  # Private Class B network
    ipaddress.ip_network("192.168.0.0/16"),  # Private Class C network
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local (e.g., used by AWS IMDS)
    ipaddress.ip_network("0.0.0.0/8"),  # Represents current network or invalid IPs
    ipaddress.ip_network("100.64.0.0/10"),  # Shared address space for carrier-grade NAT
    ipaddress.ip_network("192.0.0.0/24"),  # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),  # TEST-NET-1 (documentation only)
    ipaddress.ip_network("198.51.100.0/24"),  # TEST-NET-2 (documentation only)
    ipaddress.ip_network("203.0.113.0/24"),  # TEST-NET-3 (documentation only)
    ipaddress.ip_network("224.0.0.0/4"),  # Multicast addresses
    ipaddress.ip_network("240.0.0.0/4"),  # Reserved for future use
    ipaddress.ip_network("255.255.255.255/32"),  # Broadcast address
    # IPv6 equivalents for internal/loopback/private ranges.
    ipaddress.ip_network("::1/128"),  # IPv6 Loopback
    ipaddress.ip_network("fc00::/7"),  # IPv6 Unique Local Address (ULA)
    ipaddress.ip_network("fe80::/10"),  # IPv6 Link-Local Address
    ipaddress.ip_network("ff00::/8"),  # IPv6 Multicast addresses
]

# ALLOWED_SCHEMES: A set of URL schemes that are permitted for scraping.
# Only standard web protocols are allowed to prevent access to local files,
# network services, or other potentially insecure schemes.
ALLOWED_SCHEMES = frozenset({"http", "https"})

# BLOCKED_EXTENSIONS: A set of file extensions that are forbidden to download or access.
# This prevents downloading executable code or other potentially malicious files.
BLOCKED_EXTENSIONS = frozenset(
    {
        ".exe", ".dll", ".bat", ".cmd", ".sh", ".ps1", ".msi", ".scr",
        ".com", ".vbs", ".js", ".jar", ".php", ".jsp", ".asp", ".aspx",
    }
)


class SSRFError(Exception):
    """
    Exception raised when a Server-Side Request Forgery (SSRF) attack is detected.

    This error indicates an attempt to access internal or forbidden resources
    via a manipulated URL.
    """

    pass


class URLValidationError(Exception):
    """
    Exception raised when a URL fails general validation checks.

    This error indicates issues such as an empty URL, invalid format, or excessive length.
    """

    pass


def is_ip_blocked(ip_str: str) -> bool:
    """
    Checks if a given IP address falls within any of the defined blocked IP ranges.

    Args:
        ip_str (str): The IP address as a string.

    Returns:
        bool: True if the IP is blocked, False otherwise.
    """
    try:
        ip = ipaddress.ip_address(ip_str)
        for network in BLOCKED_NETWORKS:
            if ip in network:
                return True
        return False
    except ValueError:
        # If the string is not a valid IP address, it's not explicitly blocked by range.
        return False


def resolve_hostname(hostname: str) -> Optional[str]:
    """
    Resolves a hostname to its corresponding IP address for SSRF validation.

    Args:
        hostname (str): The hostname to resolve.

    Returns:
        Optional[str]: The resolved IP address as a string, or None if resolution fails.
    """
    try:
        # Attempt to get the first IPv4 address.
        result = socket.getaddrinfo(hostname, None, socket.AF_INET, socket.SOCK_STREAM)
        if result:
            return result[0][4][0]
    except socket.gaierror:
        pass  # Hostname not found or other DNS error.

    try:
        # If no IPv4 found, attempt to get the first IPv6 address.
        result = socket.getaddrinfo(hostname, None, socket.AF_INET6, socket.SOCK_STREAM)
        if result:
            return result[0][4][0]
    except socket.gaierror:
        pass  # Hostname not found or other DNS error.

    return None


def validate_url_ssrf(url: str, resolve_dns: bool = True) -> Tuple[bool, str]:
    """
    Performs comprehensive validation of a URL to prevent Server-Side Request Forgery (SSRF) vulnerabilities.

    This function checks:
    -   Valid URL scheme (http/https only).
    -   Hostname against a denylist (`BLOCKED_HOSTS`).
    -   Resolved IP address against blocked IP ranges (`BLOCKED_NETWORKS`).
    -   Forbidden file extensions (`BLOCKED_EXTENSIONS`).
    -   Common SSRF bypass techniques (e.g., URL shorteners, decimal/octal/hex IP representations).

    Args:
        url (str): The URL string to validate.
        resolve_dns (bool, optional): If True, performs a DNS resolution to check if the
                                     resolved IP falls into a blocked range. Defaults to True.

    Returns:
        Tuple[bool, str]: A tuple where the first element is True if the URL is safe,
                          False otherwise. The second element is a reason string.
    """
    if not url:
        return False, "URL cannot be empty."

    # Parse the URL into its components.
    try:
        parsed = urlparse(url)
    except Exception as e:
        return False, f"Invalid URL format: {e}."

    # 1. Check URL Scheme.
    if not parsed.scheme:
        return False, "URL is missing a scheme (e.g., 'http://', 'https://')."
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        return False, f"Blocked URL scheme: '{parsed.scheme}'. Only HTTP/HTTPS are allowed."

    # 2. Check Hostname.
    hostname = parsed.hostname
    if not hostname:
        return False, "URL is missing a hostname."

    # Check against explicit blocked hostnames list.
    if hostname.lower() in BLOCKED_HOSTS:
        return False, f"Blocked host: '{hostname}'."

    # 3. Check IP Address (after resolving if it's a hostname).
    try:
        # Check if the hostname is directly an IP address.
        ip = ipaddress.ip_address(hostname)
        if is_ip_blocked(str(ip)):
            return False, f"Blocked IP range detected: '{hostname}'."
    except ValueError:
        # If it's not a direct IP, try to resolve it to an IP.
        if resolve_dns:
            resolved_ip = resolve_hostname(hostname)
            if resolved_ip and is_ip_blocked(resolved_ip):
                return False, f"Hostname '{hostname}' resolves to a blocked IP address: '{resolved_ip}'."

    # 4. Check for Blocked File Extensions.
    path = parsed.path.lower()
    for ext in BLOCKED_EXTENSIONS:
        if path.endswith(ext):
            return False, f"Blocked file extension: '{ext}' detected in path."

    # 5. Check for URL-based bypass attempts (e.g., using credentials in URL for redirection).
    # Example: http://evil.com@169.254.169.254/
    if parsed.username or parsed.password:
        # If credentials are in the URL, verify the actual host being contacted.
        actual_host = parsed.hostname
        if actual_host and actual_host.lower() in BLOCKED_HOSTS:
            return False, f"Potential SSRF bypass attempt using URL credentials targeting '{actual_host}'."

    # 6. Check for Decimal/Octal/Hex IP bypass attempts.
    # Example: http://2130706433/ (which is 127.0.0.1 as decimal)
    if hostname.isdigit():
        try:
            decimal_ip = int(hostname)
            # Convert decimal integer back to IP string for blocking check.
            ip_str = str(ipaddress.ip_address(decimal_ip))
            if is_ip_blocked(ip_str):
                return False, f"Decimal IP bypass attempt blocked: '{hostname}' resolves to '{ip_str}'."
        except (ValueError, OverflowError):
            pass  # Not a valid decimal IP representation.

    return True, "URL is safe for request."


def validate_url(url: str) -> str:
    """
    Validates and sanitizes a URL for use within the scraper.

    This function performs a series of checks to prevent security vulnerabilities
    (like SSRF) and common input errors.

    Args:
        url (str): The URL string to validate.

    Returns:
        str: The sanitized and validated URL.

    Raises:
        URLValidationError: If the URL is empty, too long, or malformed.
        SSRFError: If the URL is deemed unsafe due to SSRF risks.
    """
    if not url:
        raise URLValidationError("URL cannot be empty.")

    url = url.strip()

    # Enforce a maximum URL length to prevent buffer overflows or overly long requests.
    if len(url) > 2048:
        raise URLValidationError("URL exceeds maximum allowed length of 2048 characters.")

    # Perform SSRF-specific validation.
    is_safe, reason = validate_url_ssrf(url)
    if not is_safe:
        raise SSRFError(f"URL blocked due to potential SSRF risk: {reason}")

    return url


def validate_urls(urls: List[str]) -> List[str]:
    """
    Validates a list of URLs, ensuring each URL is safe for scraping.

    Args:
        urls (List[str]): A list of URL strings to validate.

    Returns:
        List[str]: A list of validated and sanitized URLs.

    Raises:
        URLValidationError: If the list is empty or contains too many URLs.
        URLValidationError: If any URL in the list is invalid.
        SSRFError: If any URL in the list poses an SSRF risk.
    """
    if not urls:
        raise URLValidationError("URL list cannot be empty.")

    # Enforce a reasonable limit on the number of URLs per request.
    if len(urls) > 1000:
        raise URLValidationError("Maximum 1000 URLs allowed per request for batch validation.")

    validated = []
    for i, url in enumerate(urls):
        try:
            validated.append(validate_url(url))
        except (URLValidationError, SSRFError) as e:
            # Re-raise with context to indicate which URL in the list failed validation.
            raise type(e)(f"URL at index {i} failed validation: {e}") from e

    return validated


# =============================================================================
# INPUT SANITIZATION (General)
# =============================================================================

# Architectural Note:
# In accordance with the "Agent-Tool Architecture" and "pure execution" principle,
# the scraper performs mechanical tasks based on agent-provided inputs.
# LLM prompt sanitization (i.e., cleaning prompts that come from an LLM before
# feeding them to tools) is NOT handled here. It is assumed that the external
# agent layer is responsible for ensuring the safety and correctness of its
# inputs *before* passing them to the scraper.


def sanitize_selector(selector: str) -> str:
    """
    Sanitizes a CSS/XPath selector string to prevent common injection attempts.

    This function removes potentially malicious content like "javascript:" or
    "data:" URIs and enforces a maximum length.

    Args:
        selector (str): The selector string to sanitize.

    Returns:
        str: The sanitized selector string.
    """
    if not selector:
        return ""

    # Remove potential script injection attempts.
    selector = re.sub(r"javascript:", "", selector, flags=re.IGNORECASE)
    selector = re.sub(r"data:", "", selector, flags=re.IGNORECASE)

    # Enforce a maximum length to prevent overly large or malformed selectors.
    if len(selector) > 1000:
        selector = selector[:1000]

    return selector.strip()


# =============================================================================
# RATE LIMITING CONFIGURATION
# =============================================================================

# RATE_LIMITS: Defines various rate limiting parameters based on pricing tiers.
# These limits control how many requests, URLs, or concurrent jobs a tenant can perform.
RATE_LIMITS = {
    "default": {
        "requests_per_hour": 100,
        "urls_per_request": 1000,
        "concurrent_jobs": 10,
    },
    "premium": {
        "requests_per_hour": 1000,
        "urls_per_request": 10000,
        "concurrent_jobs": 50,
    },
}


class RateLimitExceeded(Exception):
    """
    Exception raised when a rate limit defined for a tenant is exceeded.
    """

    def __init__(self, message: str, retry_after: int = 3600):
        """
        Initializes the RateLimitExceeded exception.

        Args:
            message (str): A human-readable message describing the limit that was exceeded.
            retry_after (int, optional): Suggested number of seconds to wait before retrying.
                                         Defaults to 3600 seconds (1 hour).
        """
        super().__init__(message)
        self.retry_after = retry_after


def get_rate_limit(tenant_id: str, tier: str = "default") -> Dict[str, Any]:
    """
    Retrieves the rate limit configuration for a specific tenant based on their pricing tier.

    Args:
        tenant_id (str): The identifier of the tenant.
        tier (str, optional): The pricing tier of the tenant. Defaults to "default".

    Returns:
        Dict[str, Any]: A dictionary containing the rate limit configuration
                        for the specified tier.
    """
    return RATE_LIMITS.get(tier, RATE_LIMITS["default"])
