# PhishGuard Backend

## Requirements

- Python **3.11** (pinned by `.python-version`). Use 3.11 for the pinned scientific-ML wheels: Python 3.14 currently causes pip to download `scikit-learn` from source, which requires a native C/C++ compiler.
- [`uv`](https://docs.astral.sh/uv/) for reproducible installs (the venv has no `pip`; it is uv-managed).

## Why versions are pinned — do not casually bump them

Every entry in `requirements.txt` is `==`-pinned, and that is load-bearing:

- `scikit-learn==1.5.1` / `xgboost==2.1.0`: the trained artifact (`models/best_model.pkl`) is a pickle. Unpickling a model saved under one sklearn/XGBoost version with a different version can fail outright or, worse, silently change predictions. Retrain before upgrading.
- `shap==0.46.0`: the explainer calls version-fragile APIs (`KernelExplainer` + `l1_reg="num_features(10)"`); other SHAP releases change that surface.
- Everything else (`numpy`, `pandas`, `fastapi`, `pydantic`, …) is pinned so a fresh `git clone` resolves the exact tested matrix. `requirements-dev.txt` (`pytest`, `httpx`) is the only unpinned-by-design split — test tooling, never imported by the app.

## Run locally with uv (recommended)

```powershell
cd phishing_detector/backend
uv python install 3.11
uv venv --python 3.11 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt -r requirements-dev.txt
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

If Python 3.11 is already installed, the equivalent standard-library setup is:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Swagger UI is available at `http://localhost:8000/docs`.

Copy the environment template before first run (real values stay local-only and gitignored):

```powershell
Copy-Item .env.example .env
```

The backend starts with an offline deterministic fallback classifier so the API can be demonstrated before a dataset is supplied. To use a trained model, place a labeled CSV in `ml/data/` and run `python -m ml.train`; the resulting `models/best_model.pkl` is loaded automatically.

## Training a Model

### 1. Prepare the CSV

Create the `ml/data` directory if it does not exist, then place one labeled CSV file in it:

```powershell
New-Item -ItemType Directory -Force ml\data
```

The trainer uses the largest `.csv` file it finds in `ml/data` (excluding `hard_negatives.csv`, which is always appended as extra legitimate rows), so keep only the dataset you want to train on in that directory.

#### Required CSV columns

The CSV must contain:

| Purpose | Accepted column names |
|---|---|
| URL or domain | `url` or `domain` |
| Binary label | `label`, `class`, `type`, `prediction`, or `status` |

Column names are case-insensitive. You do not need to calculate or include the model's feature columns; the trainer extracts them from each URL. Any additional columns are ignored.

Labels are converted to two classes automatically:

- **Phishing (1):** `1`, `phishing`, `malicious`, or `bad`
- **Legitimate (0):** any other value, such as `0`, `legitimate`, or `benign`

Label matching is case-insensitive and ignores leading or trailing spaces. Include examples of both classes in the dataset.

Minimal valid CSV:

```csv
url,label
https://example.com/login,phishing
https://google.com,legitimate
https://bank-secure-update.tk/signin,phishing
https://github.com,legitimate
```

Duplicate URLs are removed automatically before training. Empty URLs are not useful and should be excluded.

### Companion data files (optional but recommended)

| File | Purpose |
|---|---|
| `ml/data/reputation_top1m.csv` | Cisco Umbrella top-1M (`rank,domain` rows) powering the `domain_in_top_list` feature. Missing file = feature always false (warns, never crashes). Gitignored (`*.csv`). |
| `ml/data/hard_negatives.csv` | `url,label` rows (all `0`) of top-site login pages, auto-appended during `load_dataset` to rebalance phishing-heavy neighborhoods. |
| `ml/data/eval_gate.json` | Frozen acceptance set (`[{url, expected, group}]`). Score any artifact without serving it: `python eval_gate.py --model models/best_model.pkl`. Exit 0 = all gates pass. |

### 2. Run training

From `phishing_detector/backend`, activate the virtual environment and start the trainer:

```powershell
.\.venv\Scripts\Activate.ps1
python -m ml.train
```

The training process:

1. Reads the first CSV in `ml/data`.
2. Extracts the 25 model features used by the application (plus the
   `html_features_available` flag, which is metadata, not a model input).
3. Splits the data into a stratified 80% training set and 20% test set.
4. Skips SMOTE by default (`USE_SMOTE = False` in `ml/train.py`;
   `class_weight="balanced"` already handles imbalance; enable the flag
   only for ablation runs).
5. Trains Logistic Regression, Random Forest, XGBoost, and a calibrated linear SVM candidate. The linear SVM is used instead of an RBF SVM so large datasets can finish in a practical amount of time.
6. Evaluates accuracy, precision, recall, F1, and ROC-AUC.
7. Selects the model with the highest F1 score, using ROC-AUC to break ties.

### 3. Use the trained model

Training creates:

| File | Purpose |
|---|---|
| `models/best_model.pkl` | Selected model artifact loaded by the API |
| `ml/comparison_report.json` | Metrics for all candidates and the selected model |

Restart the API after training so it loads the new artifact:

```powershell
uvicorn app.main:app --reload --port 8000
```

### 4. Calibrate probabilities (recommended before shipping)

Raw forest scores rank well but are overconfident. Isotonic calibration
maps them to empirical probabilities on held-out data without retraining:

```powershell
.\.venv\Scripts\Activate.ps1
python ml/calibrate.py
python eval_gate.py --model models/candidate_calibrated.pkl
```

`ml/calibrate.py` recovers the training run's own 20% test split
deterministically (same seed/order) and **aborts unless the raw model
reproduces the report accuracy on it** — so the calibration set is
provably held-out. It then fits `CalibratedClassifierCV(cv="prefit",
method="isotonic")` on half the split, evaluates on the other half, and
writes the candidate plus `ml/calibration_report.json` only if all bars
hold (Brier + log-loss improve, F1 within tolerance, no regression).
Swap the candidate into `models/best_model.pkl` (keep the previous file
as backup) only after the gate passes, then restart the API. The shipped
decision threshold stays 0.5 — measured alternatives live in
`calibration_report.json` (`threshold_candidates_eval_B`).

## Run tests

Activate the virtual environment first:

```powershell
.\.venv\Scripts\Activate.ps1
```

Run all backend tests:

```powershell
pytest
```

Run a specific test file:

```powershell
pytest tests\test_features.py -v
pytest tests\test_api.py -v
```

Run one specific test:

```powershell
pytest tests\test_api.py::test_predict_and_history -v
```
