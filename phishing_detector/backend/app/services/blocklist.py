"""Offline exact-match threat-feed pre-filter (URLhaus snapshot).

The snapshot (ml/data/feed_blocklist.csv, vendored by ml/refresh_blocklist.py)
is loaded once and matched by normalized exact URL. Matching is deliberately
conservative - no domain-level expansion - so a feed hit has ~zero false
positives (the shared-host lesson: never condemn a whole registrable domain).

Missing/disabled/unreadable snapshot degrades to "no match" with a warning,
never a crash: the ML verdict always remains as the backstop.
"""

import csv
import logging
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_DEFAULT_PORTS = {"http": 80, "https": 443}


def normalize_url(raw: str) -> str | None:
    """Normalize a URL for exact comparison, or None if unusable.

    Lowercases scheme+host, drops fragments, strips default ports and
    trailing slashes; path and query are significant and kept verbatim.
    The same function normalizes feed rows at refresh time and scanned
    URLs at serving time, so the two can never skew.
    """

    if not isinstance(raw, str):
        return None
    text = raw.strip()
    if not text or text.startswith("#"):
        return None
    try:
        parsed = urlparse(text)
    except (TypeError, ValueError):
        return None
    scheme = parsed.scheme.lower()
    if scheme not in ("http", "https"):
        return None
    host = (parsed.hostname or "").lower().rstrip(".")
    if not host:
        return None
    port = parsed.port
    authority = host if port is None or port == _DEFAULT_PORTS[scheme] else f"{host}:{port}"
    path = parsed.path.rstrip("/") or ""
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{scheme}://{authority}{path}{query}"


@dataclass(frozen=True)
class BlocklistMatch:
    """A scanned URL found verbatim in the threat snapshot."""

    url: str
    source: str


class Blocklist:
    """In-memory snapshot matcher (empty matcher when unavailable)."""

    def __init__(self, path: Path | None) -> None:
        self.available = False
        self.entries: dict[str, str] = {}
        if path is None:
            return
        try:
            with path.open(newline="", encoding="utf-8-sig") as handle:
                for row in csv.DictReader(handle):
                    normalized = normalize_url(row.get("url", ""))
                    if normalized and normalized not in self.entries:
                        self.entries[normalized] = (row.get("source") or "feed").strip() or "feed"
            self.available = True
            logger.info("blocklist_loaded", extra={"entries": len(self.entries), "path": str(path)})
        except OSError:
            logger.warning("blocklist_missing", extra={"path": str(path)})

    def check(self, url: str) -> BlocklistMatch | None:
        """Return the feed match for a URL, or None (fail-open)."""

        normalized = normalize_url(url)
        if normalized is None or normalized not in self.entries:
            return None
        return BlocklistMatch(url=normalized, source=self.entries[normalized])


_cached: Blocklist | None = None


def get_blocklist() -> Blocklist:
    """Return the process-wide matcher honoring current settings."""

    global _cached
    if _cached is None:
        # Imported here to keep module import side-effect free for tooling.
        from app.core.config import get_settings

        settings = get_settings()
        path = settings.blocklist_path
        candidate = path if path.is_absolute() else Path(__file__).resolve().parents[2] / path
        _cached = Blocklist(candidate if settings.blocklist_enabled else None)
    return _cached


def clear_cache() -> None:
    """Drop the cached matcher (tests swap snapshot files)."""

    global _cached
    _cached = None
