"""Optional, bounded HTML fetching for webpage-based features."""

from dataclasses import dataclass
import ipaddress
import logging
import socket
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

# Never retain more than this many response bytes for feature extraction.
_MAX_RESPONSE_BYTES = 2_000_000

_BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("::/128"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("fc00::/7"),
]


@dataclass(frozen=True)
class ScrapeResult:
    """Result of a best-effort page fetch."""

    html: str | None
    redirect_count: int


def _address_blocked(address: str) -> bool:
    """Check whether a literal IP address falls in a blocked network."""

    try:
        resolved = ipaddress.ip_address(address)
    except ValueError:
        return False
    return any(resolved in network for network in _BLOCKED_NETWORKS)


def _is_safe_url(url: str) -> bool:
    """Validate that a URL targets a public, non-internal host."""

    try:
        parsed = urlparse(url)
    except (TypeError, ValueError):
        return False

    if parsed.scheme not in ("http", "https"):
        return False

    hostname = parsed.hostname
    if not hostname:
        return False

    if _address_blocked(hostname):
        logger.warning("blocked_internal_url", extra={"host": hostname})
        return False

    # Best-effort DNS check: block hostnames that resolve to internal IPs
    # (covers DNS-rebinding cases the literal-IP check above misses).
    try:
        for _, _, _, _, sockaddr in socket.getaddrinfo(hostname, None):
            if _address_blocked(sockaddr[0]):
                logger.warning("blocked_internal_url", extra={"host": hostname, "ip": sockaddr[0]})
                return False
    except (socket.gaierror, UnicodeError):
        pass

    return True


def fetch_page(url: str, timeout: float = 4.0) -> ScrapeResult:
    """Fetch a URL without raising network errors to the API layer."""

    if not _is_safe_url(url):
        logger.info("unsafe_url_skipped")
        return ScrapeResult(None, 0)

    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "PhishGuard/1.0"},
            allow_redirects=True,
        )
        response.raise_for_status()
        declared = response.headers.get("Content-Length")
        if declared is not None and declared.isdigit() and int(declared) > _MAX_RESPONSE_BYTES:
            logger.info("page_fetch_too_large")
            return ScrapeResult(None, len(response.history))
        if len(response.content) > _MAX_RESPONSE_BYTES:
            logger.info("page_fetch_too_large")
            return ScrapeResult(None, len(response.history))
        return ScrapeResult(response.text, len(response.history))
    except requests.RequestException as exc:
        logger.info("page_fetch_unavailable", extra={"error": str(exc)})
        return ScrapeResult(None, 0)
