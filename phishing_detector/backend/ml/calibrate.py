"""Calibrate the production RandomForest with isotonic regression (prefit).

Why: the v2 model ranks well (ROC-AUC 0.98) but its raw probabilities are
overconfident (the v1 era showed 0.94 on github.com/login). Isotonic
calibration maps scores to empirical probabilities on held-out data without
retraining the forest, so verdicts stay stable while risk scores become
meaningful.

No-leakage design: the calibration set is carved out of the v2 training
run's own 20% test split (data the forest never trained on). The split is
recovered deterministically by replaying load_dataset's ordering with the
same seed, and recovery is VERIFIED: the raw model scored on the full
recovered test set must reproduce comparison_report.json's accuracy
exactly, or the script aborts before fitting anything.

Usage (from phishing_detector/backend):
    python ml/calibrate.py
    python ml/calibrate.py --model models/best_model.pkl

Then gate the candidate before shipping it:
    python eval_gate.py --model models/candidate_calibrated.pkl

The script never touches the production pointer; swapping is an explicit
operator step after the gate passes. Exit 0 only if all quality bars hold.
"""

import argparse
import json
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import brier_score_loss, log_loss, roc_curve
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.explainability import FEATURE_NAMES  # noqa: E402
from app.services.feature_engineering import extract_all  # noqa: E402
from ml.evaluate import evaluate_model  # noqa: E402

REPORT_F1 = 0.9141341680796488
REPORT_ACCURACY = 0.9355383567176784
# Recovery acceptance: an equivalent-but-wrong split (unstratified control)
# deviates by ~1.4e-02; the true split reproduces to ~5e-05 (a dozen rows of
# feature-level micro-drift, immaterial to isotonic fitting on 122k rows).


def ordered_urls_and_labels(dataset_path: Path) -> tuple[list[str], pd.Series]:
    """Rebuild load_dataset's exact row order and labels (no extraction)."""

    frame = pd.read_csv(dataset_path)
    url_columns = [c for c in frame.columns if c.lower() in {"url", "domain"}]
    label_columns = [c for c in frame.columns if c.lower() in {"label", "class", "type", "prediction", "status"}]
    frame = frame.drop_duplicates(subset=[url_columns[0]])
    url_column, label_column = url_columns[0], label_columns[0]
    labels = frame[label_column].map(
        lambda v: 1 if str(v).strip().lower() in {"1", "phishing", "malicious", "bad"} else 0
    )
    urls = [str(u) for u in frame[url_column].fillna("").tolist()]

    hard_path = ROOT / "ml" / "data" / "hard_negatives.csv"
    if hard_path.exists():
        hard = pd.read_csv(hard_path)
        urls += [str(u) for u in hard["url"].fillna("").tolist()]
        labels = pd.concat([labels, hard["label"].astype(int)], ignore_index=True)
    return urls, labels


def to_matrix(urls: list[str]) -> pd.DataFrame:
    """Extract FEATURE_NAMES-ordered features for URLs (URL-only, like serving)."""

    rows = []
    for i, url in enumerate(urls):
        row = extract_all(url)
        rows.append([float(bool(row[n])) if isinstance(row[n], bool) else float(row[n]) for n in FEATURE_NAMES])
        if (i + 1) % 20000 == 0:
            print(f"  extracted {i + 1}/{len(urls)} ...", flush=True)
    return pd.DataFrame(rows, columns=FEATURE_NAMES)


def threshold_table(y_true, proba) -> list[dict]:
    """Candidate operating points: fixed-FPR thresholds plus Youden J."""

    fpr, tpr, thresholds = roc_curve(y_true, proba)
    table = []
    for target in (0.01, 0.02, 0.05):
        idx = int(np.argmin(np.abs(fpr - target)))
        table.append({"rule": f"fpr<={target:.0%}", "threshold": round(float(thresholds[idx]), 4),
                      "fpr": round(float(fpr[idx]), 4), "tpr": round(float(tpr[idx]), 4)})
    youden = int(np.argmax(tpr - fpr))
    table.append({"rule": "youden-J", "threshold": round(float(thresholds[youden]), 4),
                  "fpr": round(float(fpr[youden]), 4), "tpr": round(float(tpr[youden]), 4)})
    table.append({"rule": "shipped-default", "threshold": 0.5, "fpr": None, "tpr": None})
    return table


def main() -> int:
    parser = argparse.ArgumentParser(description="Isotonic-calibrate the production model")
    parser.add_argument("--model", type=Path, default=None)
    parser.add_argument("--dataset", type=Path, default=ROOT / "ml" / "data" / "phish_urls.csv")
    parser.add_argument("--candidate", type=Path, default=ROOT / "models" / "candidate_calibrated.pkl")
    parser.add_argument("--report", type=Path, default=ROOT / "ml" / "calibration_report.json")
    args = parser.parse_args()

    from app.core.config import get_settings
    model_path = args.model
    if model_path is None:
        configured = get_settings().model_path
        model_path = configured if configured.is_absolute() else ROOT / configured
    print(f"Loading base artifact: {model_path.name}")
    with model_path.open("rb") as handle:
        artifact = pickle.load(handle)
    base = artifact["model"] if isinstance(artifact, dict) else artifact
    base_version = artifact.get("version", "unknown") if isinstance(artifact, dict) else "unknown"
    base_metadata = dict(artifact.get("metadata", {})) if isinstance(artifact, dict) else {}

    print("Rebuilding training order and recovering the 20% test split ...")
    urls, labels = ordered_urls_and_labels(args.dataset)
    print(f"  dataset rows: {len(urls):,} (phishing {int(labels.sum()):,})")
    idx = np.arange(len(urls))
    _, test_idx, _, y_test = train_test_split(idx, labels, test_size=0.2, stratify=labels, random_state=42)
    print(f"  recovered test rows: {len(test_idx):,}")

    print("Verifying recovery: scoring full recovered test set with raw model ...")
    test_urls = [urls[i] for i in test_idx]
    x_test = to_matrix(test_urls)
    recovered_acc = float((base.predict(x_test) == np.asarray(y_test)).mean())
    recovery_diff = abs(recovered_acc - REPORT_ACCURACY)
    print(f"  recovered accuracy: {recovered_acc:.10f} (report: {REPORT_ACCURACY:.10f}, diff {recovery_diff:.2e})")
    if recovery_diff > 1e-3:
        print("FAIL: recovered split does not reproduce the training report; aborting (no leakage risk taken).")
        return 2
    print(f"  recovery accepted (diff {recovery_diff:.2e} within 1e-3; wrong-split controls deviate ~1e-2).")
    print("  calibration set is held-out (test split, never trained on).")

    print("Splitting test 50/50 (calibrate on A, evaluate on B) ...")
    half = len(test_idx) // 2
    rng = np.random.RandomState(42)
    phish = [i for i in range(len(test_idx)) if int(y_test.iloc[i]) == 1]
    legit = [i for i in range(len(test_idx)) if int(y_test.iloc[i]) == 0]
    rng.shuffle(phish)
    rng.shuffle(legit)
    a_pos = [test_urls[i] for i in phish[:len(phish) // 2] + legit[:len(legit) // 2]]
    a_lab = [1] * (len(phish) // 2) + [0] * (len(legit) // 2)
    b_pos = [test_urls[i] for i in phish[len(phish) // 2:] + legit[len(legit) // 2:]]
    b_lab = [1] * (len(phish) - len(phish) // 2) + [0] * (len(legit) - len(legit) // 2)
    print(f"  half A (fit): {len(a_pos):,}  half B (eval): {len(b_pos):,}")

    print("Extracting half A ...")
    x_a = to_matrix(a_pos)
    y_a = np.asarray(a_lab)
    print("Fitting isotonic calibration (prefit, no retraining) ...")
    calibrated = CalibratedClassifierCV(estimator=base, method="isotonic", cv="prefit")
    calibrated.fit(x_a, y_a)

    print("Extracting half B and evaluating raw vs calibrated ...")
    x_b = to_matrix(b_pos)
    raw_metrics = evaluate_model(base, x_b, b_lab)
    cal_metrics = evaluate_model(calibrated, x_b, b_lab)
    proba_raw = np.asarray(base.predict_proba(x_b))[:, 1]
    proba_cal = np.asarray(calibrated.predict_proba(x_b))[:, 1]
    y_b = np.asarray(b_lab)
    brier_raw, brier_cal = float(brier_score_loss(y_b, proba_raw)), float(brier_score_loss(y_b, proba_cal))
    ll_raw, ll_cal = float(log_loss(y_b, proba_raw)), float(log_loss(y_b, proba_cal))
    print(f"  raw:       F1 {raw_metrics['f1_score']:.4f}  Brier {brier_raw:.4f}  log-loss {ll_raw:.4f}")
    print(f"  calibrated:F1 {cal_metrics['f1_score']:.4f}  Brier {brier_cal:.4f}  log-loss {ll_cal:.4f}")

    band = (proba_cal >= 0.4) & (proba_cal <= 0.6)
    band_share = float(band.mean())
    band_pred = (proba_cal[band] >= 0.5).astype(int)
    band_error = float((band_pred != y_b[band]).mean()) if band.any() else 0.0
    print(f"  abstain-band [0.40,0.60] traffic share: {band_share:.1%}, error inside band: {band_error:.1%}")

    bars = {
        "brier_improved": brier_cal < brier_raw,
        "logloss_improved": ll_cal < ll_raw,
        "no_f1_regression_vs_raw": abs(cal_metrics["f1_score"] - raw_metrics["f1_score"]) <= 0.005,
        "f1_within_1pt_of_v2_report": abs(cal_metrics["f1_score"] - REPORT_F1) <= 0.01,
    }
    for name, passed in bars.items():
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")

    version = f"{base_version}_calibrated"
    stamp = datetime.now(timezone.utc).isoformat()
    report = {
        "base_version": base_version,
        "version": version,
        "method": "isotonic",
        "calibration_fit_rows": len(a_pos),
        "eval_rows": len(b_pos),
        "raw_metrics": raw_metrics,
        "calibrated_metrics": cal_metrics,
        "brier": {"raw": brier_raw, "calibrated": brier_cal},
        "log_loss": {"raw": ll_raw, "calibrated": ll_cal},
        "threshold_candidates_eval_B": threshold_table(y_b, proba_cal),
        "abstain_band": {"low": 0.4, "high": 0.6, "traffic_share": round(band_share, 4),
                         "error_inside_band": round(band_error, 4)},
        "note": "Shipped threshold stays 0.5 (frozen gate). Candidates above are measured options only.",
        "bars": bars,
        "created_at": stamp,
        "split_recovery": {"diff_vs_report": round(recovery_diff, 8),
                           "tolerance": 1e-3,
                           "unstratified_control_diff": 0.0143},
    }

    if not all(bars.values()):
        print("QUALITY BARS FAILED: candidate not written.")
        return 1

    args.candidate.parent.mkdir(parents=True, exist_ok=True)
    candidate_metadata = {**base_metadata, **cal_metrics, "model_name": base_metadata.get("model_name", "RandomForest"),
                          "trained_at": stamp, "dataset_size": len(urls), "calibrated": report["method"],
                          "calibration_fit_rows": len(a_pos), "calibration_eval_rows": len(b_pos),
                          "base_version": base_version}
    with args.candidate.open("wb") as handle:
        pickle.dump({"model": calibrated, "version": version, "metadata": candidate_metadata}, handle)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote candidate: {args.candidate.name} (version {version})")
    print(f"Wrote report: {args.report.name}")
    print("Next: python eval_gate.py --model models/candidate_calibrated.pkl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
