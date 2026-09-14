"""Optional, bounded HTML fetching for webpage-based features."""

from dataclasses import dataclass
import ipaddress
import logging
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

_BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]


@dataclass(frozen=True)
class ScrapeResult:
    """Result of a best-effort page fetch."""

    html: str | None
    redirect_count: int


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

    try:
        resolved = ipaddress.ip_address(hostname)
        for network in _BLOCKED_NETWORKS:
            if resolved in network:
                logger.warning("blocked_internal_url", extra={"url": url, "ip": str(resolved)})
                return False
    except ValueError:
        pass

    return True


def fetch_page(url: str, timeout: float = 4.0) -> ScrapeResult:
    """Fetch a URL without raising network errors to the API layer."""

    if not _is_safe_url(url):
        logger.info("unsafe_url_skipped", extra={"url": url})
        return ScrapeResult(None, 0)

    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "PhishGuard/1.0"},
            allow_redirects=True,
            max_redirects=5,
        )
        response.raise_for_status()
        return ScrapeResult(response.text, len(response.history))
    except requests.RequestException as exc:
        logger.info("page_fetch_unavailable", extra={"url": url, "error": str(exc)})
        return ScrapeResult(None, 0)
