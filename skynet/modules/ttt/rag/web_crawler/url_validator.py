"""
URL validation utilities.
"""

import ipaddress
import socket
from urllib.parse import urlparse

from skynet.logs import get_logger

log = get_logger(__name__)

ALLOWED_SCHEMES = {'https'}
MAX_URL_DEPTH = 3
MAX_URLS_PER_REQUEST = 10

BLOCKED_NETWORKS = [
    # IPv4 private networks (RFC 1918)
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
    # Loopback
    ipaddress.ip_network('127.0.0.0/8'),
    # Link-local
    ipaddress.ip_network('169.254.0.0/16'),
    # IPv6 equivalents
    ipaddress.ip_network('::1/128'),
    ipaddress.ip_network('fc00::/7'),
    ipaddress.ip_network('fe80::/10'),
]


class URLValidationError(ValueError):
    """Raised when URL validation fails."""


def validate_url_scheme(url: str) -> None:
    """
    Validate that the URL uses an allowed scheme.

    Args:
        url: The URL to validate.

    Raises:
        URLValidationError: If the scheme is not allowed.
    """
    parsed = urlparse(url)

    if not parsed.scheme:
        raise URLValidationError(f"URL '{url}' has no scheme. Only {ALLOWED_SCHEMES} are allowed.")

    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise URLValidationError(f"URL scheme '{parsed.scheme}' is not allowed. Only {ALLOWED_SCHEMES} are allowed.")


def is_private_ip(ip_str: str) -> bool:
    """
    Check if an IP address is in a private/reserved range.

    Args:
        ip_str: The IP address as a string.

    Returns:
        True if the IP is private/reserved, False otherwise.
    """
    try:
        ip = ipaddress.ip_address(ip_str)
        return any(ip in network for network in BLOCKED_NETWORKS)
    except ValueError:
        # If we can't parse it as an IP, it's not a valid IP
        return False


def resolve_hostname(hostname: str) -> list[str]:
    """
    Resolve a hostname to its IP addresses.

    Args:
        hostname: The hostname to resolve.

    Returns:
        List of IP addresses the hostname resolves to.

    Raises:
        URLValidationError: If the hostname cannot be resolved.
    """
    try:
        # getaddrinfo returns a list of 5-tuples with address info
        # We extract just the IP addresses (index 4, first element)
        addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        return list(set(info[4][0] for info in addr_info))
    except socket.gaierror as e:
        raise URLValidationError(f"Cannot resolve hostname '{hostname}': {e}")


def validate_url_host(url: str) -> None:
    """
    Validate that the URL's host does not resolve to a private IP.

    Args:
        url: The URL to validate.

    Raises:
        URLValidationError: If the host resolves to a private IP.
    """
    parsed = urlparse(url)
    hostname = parsed.hostname

    if not hostname:
        raise URLValidationError(f"URL '{url}' has no hostname.")

    # First check if the hostname is already an IP address
    if is_private_ip(hostname):
        raise URLValidationError(f"URL host '{hostname}' is a private/reserved IP address.")

    # Resolve the hostname and check all resolved IPs
    resolved_ips = resolve_hostname(hostname)

    for ip in resolved_ips:
        if is_private_ip(ip):
            raise URLValidationError(f"URL host '{hostname}' resolves to private/reserved IP address '{ip}'.")


def validate_url(url: str) -> None:
    """
    Perform full validation on a URL.

    Args:
        url: The URL to validate.

    Raises:
        URLValidationError: If the URL fails any validation check.
    """
    validate_url_scheme(url)
    validate_url_host(url)


def validate_urls(urls: list[str]) -> None:
    """
    Validate a list of URLs.

    Args:
        urls: The list of URLs to validate.

    Raises:
        URLValidationError: If any URL fails validation or if there are too many URLs.
    """
    if len(urls) > MAX_URLS_PER_REQUEST:
        raise URLValidationError(f"Too many URLs provided ({len(urls)}). Maximum allowed is {MAX_URLS_PER_REQUEST}.")

    for url in urls:
        validate_url(url)


__all__ = [
    'ALLOWED_SCHEMES',
    'MAX_URL_DEPTH',
    'MAX_URLS_PER_REQUEST',
    'URLValidationError',
    'validate_url',
    'validate_urls',
    'validate_url_scheme',
    'validate_url_host',
    'is_private_ip',
]
