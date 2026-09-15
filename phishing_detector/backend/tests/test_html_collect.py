"""HTML collector tests (offline: fetch transport is injected)."""

import json

import pandas as pd

from app.services.scraper import ScrapeResult
from ml.collect_html import collect, load_manifest


def _dataset(path, urls):
    pd.DataFrame({"url": urls, "label": [0] * len(urls)}).to_csv(path, index=False)
    return path


def _fake_fetch(mapping):
    def fetch(url, timeout=4.0):
        if url not in mapping:
            raise AssertionError(f"unexpected fetch: {url}")
        html = mapping[url]
        return ScrapeResult(html, 1 if html else 0)
    return fetch


def test_collect_writes_shards_and_manifest(tmp_path):
    """OK/failed outcomes land in JSONL + manifest with identical content."""

    dataset = _dataset(tmp_path / "urls.csv", [f"https://example{i}.com/" for i in range(6)])
    mapping = {f"https://example{i}.com/": ("<html>hi</html>" if i < 4 else None) for i in range(6)}
    out = tmp_path / "corpus"
    counts = collect(dataset, out, max_urls=0, workers=2, delay=0, fetch=_fake_fetch(mapping))
    assert counts == {"ok": 4, "failed": 2}
    rows = [json.loads(line) for line in (out / "shard-00000.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 6
    assert all(set(row) == {"url", "fetched_at", "redirect_count", "html"} for row in rows)
    state = load_manifest(out)
    assert len(state["done"]) == 4 and len(state["failed"]) == 2
    assert sum(1 for row in rows if row["html"] is None) == 2


def test_collect_resumes_without_duplicates(tmp_path):
    """A second run picks up where the first stopped (manifest-driven)."""

    dataset = _dataset(tmp_path / "urls.csv", [f"https://example{i}.com/" for i in range(4)])
    mapping = {f"https://example{i}.com/": "<html>x</html>" for i in range(4)}
    out = tmp_path / "corpus"
    collect(dataset, out, max_urls=2, workers=1, delay=0, fetch=_fake_fetch(mapping))
    counts = collect(dataset, out, max_urls=0, workers=1, delay=0, fetch=_fake_fetch(mapping))
    assert counts == {"ok": 2, "failed": 0}
    rows = []
    for shard in sorted(out.glob("shard-*.jsonl")):
        rows += shard.read_text(encoding="utf-8").splitlines()
    assert len(rows) == 4
    assert len({json.loads(line)["url"] for line in rows}) == 4


def test_collect_failing_fetch_is_recorded(tmp_path):
    """Transport explosions become failed rows, never a crash."""

    def boom(url, timeout=4.0):
        raise ConnectionError("net down")

    dataset = _dataset(tmp_path / "urls.csv", ["https://example.com/"])
    counts = collect(dataset, tmp_path / "corpus", max_urls=0, workers=1, delay=0, fetch=boom)
    assert counts == {"ok": 0, "failed": 1}
