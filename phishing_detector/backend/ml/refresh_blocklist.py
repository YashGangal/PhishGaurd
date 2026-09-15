"""Refresh the vendored threat-feed blocklist snapshot.

Downloads currently-online malicious URLs from URLhaus (abuse.ch, free for
research use - keep the attribution in the manifest), normalizes and
dedupes them, and writes phishing_detector/backend/ml/data/feed_blocklist.csv
consumed by app/services/blocklist.py at serving time.

Usage (from phishing_detector/backend):
    python ml/refresh_blocklist.py
    python ml/refresh_blocklist.py --cap 20000 --source-url <override>

The snapshot is deliberately vendored (not fetched per-request): lookups
stay offline, instant, and private. Re-run weekly; old snapshots keep
working, they just miss newly listed URLs. Exit 0 on success.
"""

import argparse
import csv
import sys
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.blocklist import normalize_url  # noqa: E402

DEFAULT_SOURCE_URL = "https://urlhaus.abuse.ch/downloads/text_online/"
DEFAULT_OUTPUT = ROOT / "ml" / "data" / "feed_blocklist.csv"
ATTRIBUTION = "URLhaus (abuse.ch) - free for research/non-commercial use"


def fetch_snapshot(source_url: str, timeout: float = 60.0) -> list[str]:
    """Download raw feed lines (comment lines start with '#')."""

    request = urllib.request.Request(source_url, headers={"User-Agent": "PhishGuard-feed-refresh/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", "replace").splitlines()


def build_rows(lines: list[str], cap: int) -> list[dict[str, str]]:
    """Normalize, dedupe (order-preserving), and cap the snapshot."""

    seen: set[str] = set()
    rows: list[dict[str, str]] = []
    today = date.today().isoformat()
    for line in lines:
        candidate = normalize_url(line)
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        rows.append({"url": candidate, "source": "urlhaus-online", "added_on": today})
        if len(rows) >= cap:
            break
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh the vendored threat-feed snapshot")
    parser.add_argument("--source-url", default=DEFAULT_SOURCE_URL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--cap", type=int, default=20000)
    args = parser.parse_args()

    print(f"Fetching threat feed: {args.source_url}")
    try:
        lines = fetch_snapshot(args.source_url)
    except Exception as exc:
        print(f"FAIL: unable to download feed: {exc}")
        return 1
    rows = build_rows(lines, args.cap)
    if not rows:
        print("FAIL: feed yielded zero usable URLs; keeping the previous snapshot.")
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["url", "source", "added_on"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} URLs -> {args.output.name} ({ATTRIBUTION})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
