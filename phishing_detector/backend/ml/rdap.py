"""Minimal RDAP client for domain-age signals (training side only).

Design constraints, all deliberate:
- stdlib only (urllib), so ml tooling gains no new dependency;
- disk-cached (ml/data/.rdap_cache.json) to respect rate limits across runs;
- fail-open everywhere: any network/parse/throttle problem yields None,
  and the feature layer encodes that as a documented -1 sentinel;
- never imported by the serving path (see ml/v3_signals.py).

Usage:
    client = RDAPClient()
    days = client.domain_age_days("example.com")  # int | None
"""

import json
import logging
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

CACHE_PATH = Path(__file__).resolve().parent / "data" / ".rdap_cache.json"
IANA_BOOTSTRAP = "https://data.iana.org/rdap/dns.json"
# Fallback when the IANA bootstrap itself is unreachable.
_KNOWN_RDAP = {
    "com": "https://rdap.verisign.com/com/v1/",
    "net": "https://rdap.verisign.com/net/v1/",
}
_TIMEOUT = 10.0


def _parse_registration_age(payload: dict, now: datetime) -> int | None:
    """Extract whole days since the registration event, if present."""

    for event in payload.get("events", []) or []:
        if event.get("eventAction") == "registration" and event.get("eventDate"):
            try:
                registered = datetime.fromisoformat(str(event["eventDate"]).replace("Z", "+00:00"))
            except ValueError:
                return None
            return max(0, (now - registered).days)
    return None


class RDAPClient:
    """Rate-polite RDAP reader with a persistent JSON cache."""

    def __init__(self, cache_path: Path = CACHE_PATH, min_interval: float = 0.2) -> None:
        self.cache_path = cache_path
        self.min_interval = min_interval
        self._last_call = 0.0
        self._cache: dict[str, int | None] = {}
        self._bootstrap: dict[str, str] = dict(_KNOWN_RDAP)
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            if isinstance(cached, dict):
                self._cache = {str(k).lower(): v for k, v in cached.get("domains", {}).items()}
                if isinstance(cached.get("bootstrap"), dict):
                    self._bootstrap.update({str(k).lower(): str(v) for k, v in cached["bootstrap"].items()})
        except (OSError, ValueError):
            pass

    def _get_json(self, url: str) -> dict | None:
        """GET JSON with politeness delay; None on any failure."""

        wait = self.min_interval - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "PhishGuard-research/1.0", "Accept": "application/rdap+json"})
            with urllib.request.urlopen(request, timeout=_TIMEOUT) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            logger.debug("rdap_fetch_failed", extra={"url": url, "error": str(exc)[:120]})
            return None

    def _service_url(self, suffix: str) -> str | None:
        """Resolve the RDAP base URL for a TLD suffix (cached bootstrap)."""

        if suffix in self._bootstrap:
            return self._bootstrap[suffix]
        bootstrap = self._get_json(IANA_BOOTSTRAP)
        if isinstance(bootstrap, dict):
            for service in bootstrap.get("services", []):
                if len(service) == 2:
                    for tld in service[0]:
                        self._bootstrap[str(tld).lower()] = service[1][0]
            self._save()
            return self._bootstrap.get(suffix)
        return None

    def _save(self) -> None:
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_text(json.dumps({"bootstrap": self._bootstrap, "domains": self._cache}), encoding="utf-8")
        except OSError:
            pass

    def domain_age_days(self, registrable_domain: str) -> int | None:
        """Return whole days since registration, or None when unknowable."""

        domain = (registrable_domain or "").strip().lower().rstrip(".")
        if not domain or "." not in domain:
            return None
        if domain in self._cache:
            return self._cache[domain]
        suffix = domain.rsplit(".", 1)[-1]
        base = self._service_url(suffix)
        age = None
        if base:
            payload = self._get_json(f"{base.rstrip('/')}/domain/{domain}")
            if isinstance(payload, dict):
                age = _parse_registration_age(payload, datetime.now(timezone.utc))
        self._cache[domain] = age
        self._save()
        return age
