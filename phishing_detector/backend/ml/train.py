"""Train and compare candidate classifiers (v2: 25 URL-side features)."""

from datetime import datetime, timezone
import json
from pathlib import Path
import pickle
from typing import Any

import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import LinearSVC

from app.services.feature_engineering import extract_all
from app.services.explainability import FEATURE_NAMES
from ml.evaluate import evaluate_model

# SMOTE on ~500k minority rows costs hours of RAM-heavy kNN for ~zero gain:
# every candidate already uses class_weight="balanced" (or equivalent).
# Keep the code path behind this flag for ablation runs only.
USE_SMOTE = False

# V3 candidate signals (ml/v3_signals.py: free-host + RDAP domain age).
# Off by default: flipping it changes the feature matrix (25 -> 27) and
# therefore requires the full retrain + gate + ship cycle, never a hot flip.
USE_V3_SIGNALS = False


def _load_xgboost() -> Any:
    """Import XGBoost lazily so feature-only development does not require it."""

    from xgboost import XGBClassifier

    return XGBClassifier


def load_dataset(path: Path) -> tuple[pd.DataFrame, pd.Series]:
    """Load a CSV and discover common URL and label column names."""

    frame = pd.read_csv(path)
    url_columns = [column for column in frame.columns if column.lower() in {"url", "domain"}]
    if not url_columns:
        raise ValueError(f"Dataset {path.name} has no URL column; found columns: {list(frame.columns)}")
    label_columns = [column for column in frame.columns if column.lower() in {"label", "class", "type", "prediction", "status"}]
    if not label_columns:
        raise ValueError(f"Dataset {path.name} has no label column; found columns: {list(frame.columns)}")
    frame = frame.drop_duplicates(subset=[url_columns[0]])
    url_column = url_columns[0]
    label_column = label_columns[0]
    labels = frame[label_column].map(lambda value: 1 if str(value).strip().lower() in {"1", "phishing", "malicious", "bad"} else 0)
    if labels.nunique() < 2:
        raise ValueError(f"Dataset {path.name} needs both classes for stratified training; found only: {sorted(labels.unique())}")
    feature_rows = [extract_all(str(url)) for url in frame[url_column].fillna("")]
    features = pd.DataFrame([{name: row[name] for name in FEATURE_NAMES} for row in feature_rows]).fillna(0)

    # Hard negatives: top-site login/account pages that are ~80%-phishing in
    # the wild. Appended after dedup, before the split, so every retrain
    # rebalances the exact neighborhood the v1 model false-positived on
    # (github/login, microsoftonline, docs.python.org).
    hard_path = Path(__file__).resolve().parent / "data" / "hard_negatives.csv"
    hard_urls: list[str] = []
    if hard_path.exists():
        hard = pd.read_csv(hard_path)
        hard_urls = [str(url) for url in hard["url"].fillna("").tolist()]
        hard_rows = [extract_all(url) for url in hard_urls]
        hard_features = pd.DataFrame([{name: row[name] for name in FEATURE_NAMES} for row in hard_rows]).fillna(0)
        features = pd.concat([features, hard_features], ignore_index=True)
        labels = pd.concat([labels, hard["label"].astype(int)], ignore_index=True)
        print(f"Added {len(hard)} hard-negative row(s) from {hard_path.name}.", flush=True)

    if USE_V3_SIGNALS:
        from ml.v3_signals import EXTRA_FEATURE_NAMES, RDAP_ENABLED, extract_extra
        from ml.rdap import RDAPClient

        rdap = RDAPClient() if RDAP_ENABLED else None
        ordered = [str(url) for url in frame[url_column].fillna("").tolist()] + hard_urls
        extra = pd.DataFrame([extract_extra(url, rdap) for url in ordered])
        features = pd.concat([features.reset_index(drop=True), extra.reset_index(drop=True)], axis=1)
        print(f"V3 signals enabled: +{len(EXTRA_FEATURE_NAMES)} columns {EXTRA_FEATURE_NAMES}.", flush=True)

    return features, labels


def build_models() -> dict[str, Any]:
    """Construct the four required candidate models."""

    xgb_classifier = _load_xgboost()
    return {
        "LogisticRegression": Pipeline([("scale", StandardScaler()), ("model", LogisticRegression(max_iter=1000, random_state=42))]),
        # max_depth/min_samples_leaf bound the artifact size (v1 grew to
        # ~3 GB); tune on a subset run if holdout F1 slips.
        "RandomForest": RandomForestClassifier(n_estimators=200, max_depth=25, min_samples_leaf=2, random_state=42, n_jobs=-1, class_weight="balanced"),
        "XGBoost": xgb_classifier(n_estimators=200, max_depth=5, learning_rate=0.08, subsample=0.9, colsample_bytree=0.9, random_state=42, eval_metric="logloss"),
        # RBF SVM does not scale to hundreds of thousands of URLs. Calibrating
        # a linear SVM preserves probability output for the API while keeping
        # training practical for large datasets.
        "SVM": CalibratedClassifierCV(
            estimator=Pipeline([
                ("scale", StandardScaler()),
                ("model", LinearSVC(dual="auto", max_iter=5000, random_state=42, class_weight="balanced")),
            ]),
            method="sigmoid",
            cv=3,
            n_jobs=-1,
        ),
    }


def _show_progress(completed: int, total: int, message: str) -> None:
    """Print overall training progress without adding a console dependency."""

    percentage = (completed / total * 100) if total else 100.0
    remaining = max(total - completed, 0)
    print(
        f"[Training progress] {percentage:5.1f}% complete | "
        f"{message} | {remaining} model(s) remaining",
        flush=True,
    )


def train(dataset_path: Path, output_root: Path) -> dict[str, Any]:
    """Train models, write the best artifact and comparison report."""

    x, y = load_dataset(dataset_path)
    print(f"Loaded {len(x)} unique URL(s) from {dataset_path.name}.", flush=True)
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, stratify=y, random_state=42)
    if USE_SMOTE:
        try:
            from imblearn.over_sampling import SMOTE

            x_train, y_train = SMOTE(random_state=42).fit_resample(x_train, y_train)
            print(f"Applied SMOTE to the training split: {len(x_train)} sample(s) ready.", flush=True)
        except ImportError:
            print("SMOTE is unavailable; continuing without oversampling.", flush=True)
        except (MemoryError, ValueError) as exc:
            print(f"SMOTE skipped ({exc}); continuing without oversampling.", flush=True)
    else:
        print("SMOTE disabled (USE_SMOTE=False); class_weight handles imbalance.", flush=True)
    results = []
    trained: dict[str, Any] = {}
    models = build_models()
    total_models = len(models)
    _show_progress(0, total_models, f"Starting {total_models} candidate model(s)")
    for index, (name, model) in enumerate(models.items(), start=1):
        completed_before = index - 1
        _show_progress(completed_before, total_models, f"Training {name} ({index}/{total_models})")
        model.fit(x_train, y_train)
        trained[name] = model
        results.append({"name": name, **evaluate_model(model, x_test, y_test)})
        _show_progress(index, total_models, f"Finished {name} ({index}/{total_models})")
    selected = max(results, key=lambda item: (item["f1_score"], item["roc_auc"]))
    print(f"All {total_models} candidate model(s) trained. Selecting the best model...", flush=True)
    timestamp = datetime.now(timezone.utc)
    version = f"{selected['name'].lower()}_v2_{timestamp.date().isoformat()}"
    models_dir = output_root / "models"
    ml_dir = output_root / "ml"
    if (models_dir / "best_model.pkl").exists():
        # Same-day retrain must not silently overwrite the previous artifact.
        version += timestamp.strftime("_%H%M%S")
    models_dir.mkdir(parents=True, exist_ok=True)
    ml_dir.mkdir(parents=True, exist_ok=True)
    artifact = {"model": trained[selected["name"]], "version": version, "metadata": {**selected, "model_name": selected["name"], "trained_at": timestamp.isoformat(), "dataset_size": len(x)}}
    with (models_dir / "best_model.pkl").open("wb") as handle:
        pickle.dump(artifact, handle)
    report = {"trained_at": timestamp.isoformat(), "dataset_size": len(x), "models": results, "selected_model": selected["name"], "selection_reason": "highest F1 and ROC-AUC among candidates"}
    (ml_dir / "comparison_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Training complete: selected {selected['name']}. 100.0% complete | 0 model(s) remaining.", flush=True)
    return report


if __name__ == "__main__":
    """Run training from the backend directory."""

    root = Path(__file__).resolve().parents[1]
    candidates = [p for p in (root / "ml" / "data").glob("*.csv") if p.name != "hard_negatives.csv"]
    if not candidates:
        raise FileNotFoundError("Place a labeled CSV in phishing_detector/backend/ml/data before training")
    # The reputation list (reputation_top1m.csv) also lives in ml/data but is
    # far smaller than any real dataset; the largest CSV is the training set.
    dataset = max(candidates, key=lambda p: p.stat().st_size)
    train(dataset, root)
