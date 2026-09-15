"""Collect raw HTML for the dataset to enable the HTML retrain (Tier-2).

The v2/v3 models train URL-only because no fetched-HTML corpus exists;
scraping 1.2M live URLs takes machine-days, not minutes. This script makes
that run possible: polite (rate-limited, identifiable UA, fail-open),
resumable (manifest of completed URLs on disk), and bounded (subset-first).

Output layout under --out-dir:
    manifest.json   {"done": [urls...], "failed": [urls...], "source": ...}
    shard-00000.jsonl  one {"url","fetched_at","redirect_count","html"} per line
                         (html null when the fetch failed; full body as
                         returned within the scraper's 2 MB cap so training
                         features match serving features exactly)

Usage (from phishing_detector/backend):
    python ml/collect_html.py --max-urls 50000
    python ml/collect_html.py --dataset ml/data/phish_urls.csv --workers 8 --delay 0.05

Re-running resumes from the manifest; delete the out dir for a fresh pass.
Exit 0 when the requested budget is exhausted (failures recorded, not fatal).
"""

import argparse
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.scraper import fetch_page  # noqa: E402

SHARD_ROWS = 5000


def load_targets(dataset: Path, max_urls: int) -> list[str]:
    """Read URL strings from a labeled CSV (same discovery as training)."""

    frame = pd.read_csv(dataset)
    url_columns = [c for c in frame.columns if c.lower() in {"url", "domain"}]
    if not url_columns:
        raise ValueError(f"Dataset {dataset.name} has no URL column")
    urls = [str(u) for u in frame[url_columns[0]].dropna().tolist()]
    return urls[:max_urls] if max_urls > 0 else urls


def load_manifest(out_dir: Path) -> dict:
    """Load progress (missing manifest = fresh start)."""

    try:
        state = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
        return {"done": set(state.get("done", [])), "failed": set(state.get("failed", []))}
    except (OSError, ValueError):
        return {"done": set(), "failed": set()}


def save_manifest(out_dir: Path, source: str, done: set, failed: set) -> None:
    """Persist progress atomically (write-temp + replace survives Ctrl+C)."""

    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = out_dir / "manifest.json.tmp"
    tmp.write_text(json.dumps({"source": source, "updated": datetime.now(timezone.utc).isoformat(),
                               "done": sorted(done), "failed": sorted(failed)}), encoding="utf-8")
    tmp.replace(out_dir / "manifest.json")


def collect(dataset: Path, out_dir: Path, max_urls: int, workers: int, delay: float,
            fetch=fetch_page) -> dict[str, int]:
    """Fetch HTML for pending URLs with threads; returns outcome counts."""

    targets = load_targets(dataset, max_urls)
    out_dir.mkdir(parents=True, exist_ok=True)
    state = load_manifest(out_dir)
    pending = [u for u in targets if u not in state["done"] and u not in state["failed"]]
    print(f"Targets: {len(targets)} total, {len(pending)} pending "
          f"({len(state['done'])} done, {len(state['failed'])} failed).", flush=True)
    counts = {"ok": 0, "failed": 0}
    lock = threading.Lock()
    shard = {"handle": None, "rows": 0, "index": len(list(out_dir.glob("shard-*.jsonl")))}

    def writerow(record: dict) -> None:
        if shard["handle"] is None or shard["rows"] >= SHARD_ROWS:
            if shard["handle"] is not None:
                shard["handle"].close()
                shard["index"] += 1
            path = out_dir / f"shard-{shard['index']:05d}.jsonl"
            shard["handle"] = path.open("a", encoding="utf-8")
            shard["rows"] = 0
        shard["handle"].write(json.dumps(record) + "\n")
        shard["rows"] += 1

    def one(url: str) -> None:
        try:
            if delay > 0:
                time.sleep(delay)
            page = fetch(url)
            record = {"url": url, "fetched_at": datetime.now(timezone.utc).isoformat(),
                      "redirect_count": page.redirect_count, "html": page.html}
            outcome = "ok" if page.html is not None else "failed"
        except Exception:
            record = {"url": url, "fetched_at": datetime.now(timezone.utc).isoformat(),
                      "redirect_count": 0, "html": None}
            outcome = "failed"
        with lock:
            writerow(record)
            (state["done"] if outcome == "ok" else state["failed"]).add(url)
            counts[outcome] += 1
            if sum(counts.values()) % 500 == 0:
                if shard["handle"] is not None:
                    shard["handle"].flush()
                save_manifest(out_dir, dataset.name, state["done"], state["failed"])
                print(f"  progress: {sum(counts.values())}/{len(pending)} "
                      f"(ok={counts['ok']}, failed={counts['failed']})", flush=True)

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        list(pool.map(one, pending))
    if shard["handle"] is not None:
        shard["handle"].close()
    save_manifest(out_dir, dataset.name, state["done"], state["failed"])
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect HTML corpus for the HTML retrain")
    parser.add_argument("--dataset", type=Path, default=ROOT / "ml" / "data" / "phish_urls.csv")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "ml" / "data" / "html_corpus")
    parser.add_argument("--max-urls", type=int, default=50000)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--delay", type=float, default=0.05)
    args = parser.parse_args()

    counts = collect(args.dataset, args.out_dir, args.max_urls, args.workers, args.delay)
    print(f"Done: ok={counts['ok']} failed={counts['failed']}.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
