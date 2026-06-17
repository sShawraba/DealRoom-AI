"""
ml/data/prepare_data.py
=======================
Loads the UCI Polish Companies Bankruptcy dataset (5-year combined),
maps its 64 financial ratios to the 8 DealRoom AI feature columns,
creates 4-class risk tier labels from the temporal distress signal,
handles outliers + imbalance, and saves ml/data/financial_ratios.csv.

DATA SOURCE
-----------
UCI Polish Bankruptcy Dataset — 5 ARFF files spanning years 1-5.
Download URL: https://archive.ics.uci.edu/static/public/365/polish+companies+bankruptcy+data.zip
Direct Kaggle mirror: https://www.kaggle.com/datasets/nitindantu/polish-bankruptcy-data

Quick download (no Kaggle login required):
    python -c "
    import urllib.request, zipfile, io, os
    url = 'https://archive.ics.uci.edu/static/public/365/polish+companies+bankruptcy+data.zip'
    data = urllib.request.urlopen(url).read()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        z.extractall('raw_polish')
    "
Then set RAW_DIR = 'raw_polish' below.

LABEL STRATEGY
--------------
The Polish dataset has 5 temporal slices (year 1..5 before/after observation).
Year index encodes *how far from bankruptcy*:
  year 5 (5 years ahead) = earliest warning → low urgency if NOT bankrupt
  year 1 (1 year ahead)  = critical window  → high urgency if bankrupt

We use both the binary label AND which year slice the row came from to build
a 4-class ordinal risk tier:

  Class 0 (low)      – bankrupt=0, observed in years 4-5 (distant horizon)
  Class 1 (medium)   – bankrupt=0, observed in years 2-3 (medium horizon)
  Class 2 (high)     – bankrupt=0, observed in year 1  (imminent but survived)
                       OR bankrupt=1, years 4-5
  Class 3 (critical) – bankrupt=1, years 1-3 (distress within 3 years)

This mirrors a real M&A 24-month forward-looking window and creates
meaningful gradient in the label, far better for a 4-class model than
simply bucketing synthetic Z-scores.
"""

import os
import sys
import zipfile
import io
import urllib.request
import warnings

import numpy as np
import pandas as pd
from scipy.io import arff

warnings.filterwarnings("ignore")

# ── Paths ─────────────────────────────────────────────────────────────────────
RAW_DIR = os.environ.get("RAW_DIR", "raw_polish")
OUT_PATH = os.path.join(os.path.dirname(__file__), "financial_ratios.csv")
UCI_ZIP_URL = (
    "https://archive.ics.uci.edu/static/public/365/"
    "polish+companies+bankruptcy+data.zip"
)

# ── Feature mapping: UCI column → DealRoom AI feature ────────────────────────
# Polish dataset attribute list (X1..X64) documented at UCI.
# We pick the closest semantic match for each of the 8 required features.
#
#  current_ratio        ≈ X4  (current assets / short-term liabilities)
#  debt_to_equity       ≈ X31 (liabilities / (equity + reserves)) — inverted of X8
#  interest_coverage    ≈ X14 ((gross profit + interest) / total assets) — proxy
#  ebitda_margin        ≈ X13 ((gross profit + depreciation) / sales)
#  revenue_growth_yoy   ≈ X35 (sales growth compared to previous year)  [often null]
#  cash_burn_rate       ≈ X5  ([(cash+sec+rec-STL)/(op_exp-dep)]*365, inverted)
#  working_capital_ratio≈ X3  (working capital / total assets)
#  gross_margin         ≈ X19 (gross profit / sales)
#
# Note: X35 (revenue_growth) is present in years 2-5 only; heavy nulls in yr1.
FEATURE_MAP = {
    "Attr4":  "current_ratio",
    "Attr31": "debt_to_equity",
    "Attr14": "interest_coverage",
    "Attr13": "ebitda_margin",
    "Attr35": "revenue_growth_yoy",
    "Attr5":  "cash_burn_rate",
    "Attr3":  "working_capital_ratio",
    "Attr19": "gross_margin",
}

TARGET_FEATURES = list(FEATURE_MAP.values())


# ── Download ──────────────────────────────────────────────────────────────────
def download_raw(raw_dir: str) -> None:
    """Download and unzip the UCI Polish Bankruptcy dataset."""
    if os.path.isdir(raw_dir) and any(
        f.endswith(".arff") for f in os.listdir(raw_dir)
    ):
        print(f"[INFO] Raw ARFF files already present in {raw_dir!r}. Skipping download.")
        return

    print(f"[INFO] Downloading Polish Bankruptcy dataset from UCI...")
    print(f"       {UCI_ZIP_URL}")
    try:
        data = urllib.request.urlopen(UCI_ZIP_URL, timeout=30).read()
    except Exception as e:
        print(f"[ERROR] Download failed: {e}")
        print(
            "\nManual fallback:\n"
            "  1. Visit https://archive.ics.uci.edu/dataset/365/polish+companies+bankruptcy+data\n"
            "  2. Download the ZIP and unzip to a folder\n"
            "  3. Set RAW_DIR env var to that folder path\n"
            "  OR run ml/data/generate_data.py for the synthetic fallback."
        )
        sys.exit(1)

    os.makedirs(raw_dir, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        z.extractall(raw_dir)
    print(f"[INFO] Extracted to {raw_dir!r}")


# ── Load ARFF slices ──────────────────────────────────────────────────────────
def load_arff_files(raw_dir: str) -> pd.DataFrame:
    """
    Load all 5 ARFF year slices and concatenate with a 'year' column.
    The year column encodes how far from the forecasting event the observation is.
    """
    frames = []
    for yr in range(1, 6):
        # Typical file names in the UCI zip
        candidates = [
            os.path.join(raw_dir, f"{yr}year.arff"),
            os.path.join(raw_dir, f"year_{yr}.arff"),
            os.path.join(raw_dir, f"polish_{yr}year.arff"),
        ]
        # Also search recursively
        for root, _, files in os.walk(raw_dir):
            for f in files:
                if f.endswith(".arff") and str(yr) in f:
                    candidates.append(os.path.join(root, f))

        path = next((p for p in candidates if os.path.exists(p)), None)
        if path is None:
            print(f"[WARN] Could not find year {yr} ARFF file, skipping.")
            continue

        raw_data, meta = arff.loadarff(path)
        df = pd.DataFrame(raw_data)
        df.columns = [c.strip() for c in df.columns]

        # Decode bytes columns (ARFF quirk)
        for col in df.select_dtypes(["object"]).columns:
            df[col] = df[col].apply(
                lambda x: x.decode("utf-8").strip() if isinstance(x, bytes) else x
            )

        # The target column is named 'class' in the UCI file
        if "class" not in df.columns:
            print(f"[WARN] No 'class' column in {path}. Columns: {df.columns.tolist()}")
            continue

        df["bankrupt"] = pd.to_numeric(df["class"], errors="coerce").fillna(0).astype(int)
        df["year"] = yr
        frames.append(df)
        print(f"[INFO] Loaded year {yr}: {len(df):,} rows")

    if not frames:
        print("[ERROR] No ARFF files could be loaded.")
        sys.exit(1)

    combined = pd.concat(frames, ignore_index=True)
    print(f"[INFO] Combined dataset: {len(combined):,} rows across {len(frames)} year slices")
    return combined


# ── Label Engineering ─────────────────────────────────────────────────────────
def build_risk_labels(df: pd.DataFrame) -> pd.Series:
    """
    Create 4-class risk tier from (bankrupt, year) pairs.

    Tier mapping (see module docstring for rationale):
      0 (low)      bankrupt=0  AND year in {4,5}
      1 (medium)   bankrupt=0  AND year in {2,3}
      2 (high)     (bankrupt=0 AND year=1) OR (bankrupt=1 AND year in {4,5})
      3 (critical) bankrupt=1  AND year in {1,2,3}
    """
    conditions = [
        (df["bankrupt"] == 0) & (df["year"].isin([4, 5])),
        (df["bankrupt"] == 0) & (df["year"].isin([2, 3])),
        ((df["bankrupt"] == 0) & (df["year"] == 1))
        | ((df["bankrupt"] == 1) & (df["year"].isin([4, 5]))),
        (df["bankrupt"] == 1) & (df["year"].isin([1, 2, 3])),
    ]
    choices = [0, 1, 2, 3]
    labels = np.select(conditions, choices, default=-1)
    n_unmatched = (labels == -1).sum()
    if n_unmatched > 0:
        print(f"[WARN] {n_unmatched} rows had no label assigned; dropping them.")
    return pd.Series(labels, index=df.index, name="risk_tier")


# ── Feature Extraction ────────────────────────────────────────────────────────
def extract_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Select and rename the 8 source columns to DealRoom AI feature names.
    Columns that are missing in the raw file are filled with NaN.
    """
    result = pd.DataFrame(index=df.index)
    for src_col, target_col in FEATURE_MAP.items():
        if src_col in df.columns:
            result[target_col] = pd.to_numeric(df[src_col], errors="coerce")
        else:
            print(f"[WARN] Source column {src_col!r} not found; {target_col} will be all-NaN")
            result[target_col] = np.nan

    # cash_burn_rate: Attr5 is a *days* metric (higher = more cash runway).
    # Invert so that higher number = more burning (negative cash flow risk).
    # Cap to avoid ±inf from near-zero denominators.
    result["cash_burn_rate"] = -result["cash_burn_rate"].clip(-9999, 9999)

    # debt_to_equity: Attr31 is liabilities/equity — already correct direction.
    # Clip extreme leverage ratios.
    result["debt_to_equity"] = result["debt_to_equity"].clip(-100, 200)

    return result


# ── Outlier Handling ──────────────────────────────────────────────────────────
def clip_outliers(df: pd.DataFrame, lower: float = 0.01, upper: float = 0.99) -> pd.DataFrame:
    """Winsorize each feature at the 1st and 99th percentile."""
    df = df.copy()
    for col in TARGET_FEATURES:
        lo = df[col].quantile(lower)
        hi = df[col].quantile(upper)
        df[col] = df[col].clip(lo, hi)
    return df


# ── Class Balance Report ──────────────────────────────────────────────────────
def report_class_balance(labels: pd.Series) -> None:
    counts = labels.value_counts().sort_index()
    total = len(labels)
    print("\n[INFO] Class distribution (after label engineering):")
    tier_names = {0: "low", 1: "medium", 2: "high", 3: "critical"}
    for cls, cnt in counts.items():
        print(f"       Class {cls} ({tier_names.get(cls, '?'):8s}): {cnt:6,}  ({cnt/total*100:.1f}%)")
    print()


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    # 1. Download raw data
    download_raw(RAW_DIR)

    # 2. Load all 5 ARFF slices
    raw = load_arff_files(RAW_DIR)

    # 3. Build risk tier labels
    labels = build_risk_labels(raw)
    valid_mask = labels != -1
    raw = raw[valid_mask].copy()
    labels = labels[valid_mask]

    # 4. Extract and rename features
    features = extract_features(raw)

    # 5. Clip outliers
    features = clip_outliers(features)

    # 6. Attach label
    features["risk_tier"] = labels.values

    # 7. Drop rows where ALL 8 features are null (completely empty record)
    all_null_mask = features[TARGET_FEATURES].isnull().all(axis=1)
    n_dropped = all_null_mask.sum()
    if n_dropped > 0:
        print(f"[INFO] Dropping {n_dropped} rows with all-null features.")
        features = features[~all_null_mask]

    # 8. Report
    report_class_balance(features["risk_tier"])

    null_pct = features[TARGET_FEATURES].isnull().mean() * 100
    print("[INFO] Null % per feature (will be imputed by training pipeline):")
    for col, pct in null_pct.items():
        print(f"       {col:25s}: {pct:.1f}%")
    print()

    # 9. Save
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    features.to_csv(OUT_PATH, index=False)
    print(f"[INFO] Saved {len(features):,} rows → {OUT_PATH}")
    print(f"       Columns: {list(features.columns)}")


if __name__ == "__main__":
    main()