"""
ml/train.py
===========
Trains a 4-class financial risk classifier for DealRoom AI.

Pipeline: SimpleImputer(median) → StandardScaler → XGBClassifier

Usage:
    python ml/train.py
    python ml/train.py --data ml/data/financial_ratios.csv
"""

import argparse
import os
import pickle
import warnings

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.metrics import f1_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, label_binarize
from sklearn.utils.class_weight import compute_sample_weight  # noqa: F401 (kept for reference)
from xgboost import XGBClassifier

warnings.filterwarnings("ignore")

# ── Paths ─────────────────────────────────────────────────────────────────────
DEFAULT_DATA = os.path.join(os.path.dirname(__file__), "data", "financial_ratios.csv")
ARTIFACT_DIR = os.path.join(os.path.dirname(__file__), "artifacts")
ARTIFACT_PATH = os.path.join(ARTIFACT_DIR, "risk_classifier.pkl")

FEATURES = [
    "current_ratio",
    "debt_to_equity",
    "interest_coverage",
    "ebitda_margin",
    "revenue_growth_yoy",
    "cash_burn_rate",
    "working_capital_ratio",
    "gross_margin",
]
TARGET = "risk_tier"
CLASSES = [0, 1, 2, 3]
CLASS_NAMES = ["low", "medium", "high", "critical"]
N_CLASSES = 4


# ── XGBoost params ────────────────────────────────────────────────────────────
XGB_PARAMS = dict(
    n_estimators=400,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    min_child_weight=5,
    max_delta_step=1,   # stabilises gradient updates for imbalanced multiclass
    reg_alpha=0.1,
    reg_lambda=1.0,
    random_state=42,
    eval_metric="mlogloss",
    n_jobs=-1,
)


# ── Sample weight helpers ─────────────────────────────────────────────────────
def _sqrt_sample_weight(y: pd.Series) -> np.ndarray:
    """
    Softer class balancing: weight = 1 / sqrt(class_freq).
    Full inverse-frequency ("balanced") over-boosts rare classes on multiclass
    problems, hurting precision. Sqrt is a proven middle ground.
    """
    counts = np.bincount(y.astype(int))
    w = 1.0 / np.sqrt(counts.clip(1))
    w = w / w.mean()  # normalise so average weight ≈ 1
    return w[y.astype(int)]


# ── Pipeline factory ──────────────────────────────────────────────────────────
def build_pipeline() -> Pipeline:
    return Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("clf", XGBClassifier(**XGB_PARAMS)),
        ]
    )


# ── Load data ─────────────────────────────────────────────────────────────────
def load_data(path: str):
    print(f"[INFO] Loading data from {path}")
    df = pd.read_csv(path)

    missing_features = [f for f in FEATURES if f not in df.columns]
    if missing_features:
        raise ValueError(f"Missing feature columns: {missing_features}")
    if TARGET not in df.columns:
        raise ValueError(f"Missing target column: {TARGET!r}")

    X = df[FEATURES].copy()
    y = df[TARGET].astype(int).copy()

    print(f"[INFO] Dataset: {len(df):,} rows × {len(FEATURES)} features")
    counts = y.value_counts().sort_index()
    for cls, name in zip(CLASSES, CLASS_NAMES):
        n = counts.get(cls, 0)
        print(f"       Class {cls} ({name:8s}): {n:6,}  ({n/len(y)*100:.1f}%)")
    print()

    return X, y


# ── Cross-validation ──────────────────────────────────────────────────────────
def run_cv(X: pd.DataFrame, y: pd.Series, n_splits: int = 5):
    print(f"[INFO] Running {n_splits}-fold stratified cross-validation (balanced weights)...")

    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

    macro_f1_scores = []
    weighted_f1_scores = []
    auc_scores = []

    for train_idx, val_idx in skf.split(X, y):
        X_tr, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_tr, y_val = y.iloc[train_idx], y.iloc[val_idx]

        sw = _sqrt_sample_weight(y_tr)

        fold_pipe = build_pipeline()
        fold_pipe.fit(X_tr, y_tr, clf__sample_weight=sw)

        y_pred = fold_pipe.predict(X_val)
        macro_f1_scores.append(f1_score(y_val, y_pred, average="macro"))
        weighted_f1_scores.append(f1_score(y_val, y_pred, average="weighted"))

        y_prob = fold_pipe.predict_proba(X_val)
        y_val_bin = label_binarize(y_val, classes=CLASSES)
        if y_val_bin.shape[1] == N_CLASSES:
            auc = roc_auc_score(y_val_bin, y_prob, multi_class="ovr", average="macro")
            auc_scores.append(auc)

    macro_f1_scores = np.array(macro_f1_scores)
    weighted_f1_scores = np.array(weighted_f1_scores)

    print(f"\n{'='*55}")
    print(f"  Cross-Validation Results ({n_splits}-Fold Stratified)")
    print(f"{'='*55}")
    for i, (mf1, wf1) in enumerate(zip(macro_f1_scores, weighted_f1_scores), 1):
        print(f"  Fold {i}:  macro-F1 = {mf1:.4f}   weighted-F1 = {wf1:.4f}")
    print(f"{'─'*55}")
    print(
        f"  Mean :  macro-F1 = {macro_f1_scores.mean():.4f} ± {macro_f1_scores.std():.4f}"
    )
    print(
        f"          weighted-F1 = {weighted_f1_scores.mean():.4f} ± {weighted_f1_scores.std():.4f}"
    )
    print(f"{'='*55}\n")

    if auc_scores:
        auc_arr = np.array(auc_scores)
        print(f"[INFO] ROC-AUC (OVR, macro): {auc_arr.mean():.4f} ± {auc_arr.std():.4f}\n")
    else:
        print("[WARN] Could not compute ROC-AUC (class missing in some folds).\n")

    return macro_f1_scores.mean()


# ── Full fit + save ───────────────────────────────────────────────────────────
def fit_and_save(X: pd.DataFrame, y: pd.Series):
    print("[INFO] Fitting pipeline on full dataset (sqrt-balanced weights)...")
    pipe = build_pipeline()
    sw = _sqrt_sample_weight(y)
    pipe.fit(X, y, clf__sample_weight=sw)

    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    with open(ARTIFACT_PATH, "wb") as f:
        pickle.dump(pipe, f)

    print(f"[INFO] Artifact saved → {ARTIFACT_PATH}")
    return pipe


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Train DealRoom AI risk classifier")
    parser.add_argument(
        "--data",
        default=DEFAULT_DATA,
        help="Path to financial_ratios.csv",
    )
    parser.add_argument(
        "--skip-cv",
        action="store_true",
        help="Skip cross-validation (fit only)",
    )
    args = parser.parse_args()

    X, y = load_data(args.data)

    if not args.skip_cv:
        run_cv(X, y)

    fit_and_save(X, y)
    print("\n[DONE] Training complete.")


if __name__ == "__main__":
    main()