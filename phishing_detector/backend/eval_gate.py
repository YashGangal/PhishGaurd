"""PhishGuard frozen model acceptance gate.

Usage:
    python eval_gate.py
    python eval_gate.py --model models/best_model.pkl

Exit 0 only if ALL gates pass:
    - overall accuracy >= 85%
    - github.com/login phishing-probability < 0.30
    - zero misses on the topsite-legit group

Supports 22- or 25-feature artifacts using the model's own n_features_in_.
(New features were appended at the end of FEATURE_NAMES, so slicing the
first N names reproduces exactly what an older artifact was trained on.)
"""

import argparse
import json
import pickle
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from app.services.explainability import FEATURE_NAMES  # noqa: E402
from app.services.feature_engineering import extract_all  # noqa: E402


def resolve_default_model() -> Path:
    from app.core.config import get_settings

    path = get_settings().model_path
    return path if path.is_absolute() else ROOT / path


def load_model(path: Path):
    with path.open("rb") as handle:
        artifact = pickle.load(handle)
    model = artifact["model"] if isinstance(artifact, dict) else artifact
    version = artifact.get("version", "unknown") if isinstance(artifact, dict) else "unknown"
    return model, version


def feature_count(model) -> int:
    if hasattr(model, "n_features_in_"):
        return int(model.n_features_in_)
    for seq_attr in ("calibrated_classifiers_", "estimators_"):
        seq = getattr(model, seq_attr, None)
        if seq:
            inner = getattr(seq[0], "estimator", getattr(seq[0], "base_estimator", None))
            if inner is not None and hasattr(inner, "n_features_in_"):
                return int(inner.n_features_in_)
    return len(FEATURE_NAMES)


def main() -> int:
    parser = argparse.ArgumentParser(description="PhishGuard acceptance gate")
    parser.add_argument("--model", type=Path, default=None)
    parser.add_argument("--gate", type=Path, default=ROOT / "ml" / "data" / "eval_gate.json")
    parser.add_argument("--threshold", type=float, default=0.5,
                        help="Experimental operating point for analysis; the frozen verdict always uses 0.5.")
    args = parser.parse_args()

    print("PhishGuard frozen acceptance gate")
    print("=================================")

    model_path = args.model or resolve_default_model()
    try:
        model, version = load_model(model_path)
    except Exception as exc:
        print(f"FAIL: unable to load model {model_path}: {exc}")
        return 1

    n_feat = feature_count(model)
    if n_feat > len(FEATURE_NAMES):
        print(f"FAIL: artifact requires {n_feat} features, but code provides {len(FEATURE_NAMES)}.")
        return 1
    names = FEATURE_NAMES[:n_feat]
    print(f"Artifact: {model_path.name}  version={version}  features={n_feat}  gate={args.gate.name}")

    try:
        cases = json.loads(args.gate.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        print(f"FAIL: unable to load evaluation gate {args.gate}: {exc}")
        return 1

    total = len(cases)
    hits = 0
    github_p = None
    topsite_misses = []
    analysis_threshold = args.threshold != 0.5
    if analysis_threshold:
        print(f"NOTE: experimental --threshold {args.threshold} (frozen verdict uses 0.5).")

    print(f"\nScoring {total} case(s)...")
    print(f"{'OK':<4} {'EXPECTED':<11} {'PREDICTED':<11} {'P(phish)':<9} URL")
    for case in cases:
        row = extract_all(case["url"])
        vector = pd.DataFrame(
            [[float(bool(row[n])) if isinstance(row[n], bool) else float(row[n]) for n in names]],
            columns=names,
        )
        proba = float(model.predict_proba(vector)[0][1])
        verdict = "phishing" if proba >= args.threshold else "legitimate"
        ok = verdict == case["expected"]
        if ok:
            hits += 1
        if "github.com/login" in case["url"]:
            github_p = proba
        if case.get("group") == "topsite-legit" and not ok:
            topsite_misses.append(case["url"])
        print(f"{'ok' if ok else 'MISS':<4} {case['expected']:<11} {verdict:<11} {proba:<9.3f} {case['url']}")

    acc = hits / total if total else 0.0
    accuracy_ok = acc >= 0.85
    github_ok = github_p is not None and github_p < 0.30
    topsite_ok = not topsite_misses

    print("\nEvaluation summary")
    print(f"  accuracy:          {hits}/{total} ({acc:.1%}) [{'PASS' if accuracy_ok else 'FAIL'}]")
    print(f"  github.com/login:  {github_p if github_p is None else f'{github_p:.3f}'} (threshold < 0.300) [{'PASS' if github_ok else 'FAIL'}]")
    print(f"  topsite-legit:     {len(topsite_misses)} miss(es) [{'PASS' if topsite_ok else 'FAIL'}]")
    if topsite_misses:
        for url in topsite_misses:
            print(f"    MISS {url}")

    gates = [accuracy_ok, github_ok, topsite_ok]
    print(f"\nAcceptance gate: {sum(gates)}/{len(gates)} gates satisfied")
    if all(gates):
        print("ACCEPTANCE GATE PASSED: model is cleared for production.")
        return 0
    print("ACCEPTANCE GATE FAILED: model does not satisfy production requirements.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
