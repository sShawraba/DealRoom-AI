"""
ml/data/generate_data.py
========================
Synthetic fallback data generator for DealRoom AI.

Generates 600 rows of realistic financial ratios labelled with 4-class
risk tiers using Altman Z-Score thresholds and domain-grounded distributions.
Introduces ~15% null values per feature and calibrated noise.

Usage:
    python ml/data/generate_data.py
    python ml/data/generate_data.py --rows 1200 --out ml/data/financial_ratios.csv

When to use this:
    - UCI/Kaggle download fails or is too slow
    - You need a fast smoke-test of the training pipeline
    - CI environment has no internet access

Label methodology:
    Each synthetic company is assigned a risk tier based on a composite
    distress score derived from Altman Z-Score component ratios, with
    Gaussian noise layered on top to avoid perfectly separable classes
    (which would produce unrealistically high model accuracy).

    Altman Z' thresholds (private firm variant):
        Z' > 2.9  → low      (0)
        1.23 < Z' ≤ 2.9 → medium  (1)
        0.0  < Z' ≤ 1.23 → high    (2)
        Z' ≤ 0.0  → critical (3)

    Z' = 0.717*X1 + 0.847*X2 + 3.107*X3 + 0.420*X4 + 0.998*X5
    where X1..X5 are Altman's original ratios mapped to our 8 features.
"""

import argparse
import os

import numpy as np
import pandas as pd

DEFAULT_OUT = os.path.join(os.path.dirname(__file__), "financial_ratios.csv")
SEED = 42
NULL_RATE = 0.15


# ── Per-class distribution parameters ─────────────────────────────────────────
# Each dict entry: (mean, std) calibrated to realistic corporate finance ranges.
# Sources: Damodaran industry averages, Altman (1968, 2000 update),
#          and Shumway (2001) default prediction literature.

CLASS_PARAMS = {
    # Class 0: Low risk — healthy, growing companies
    0: {
        "current_ratio":        (2.10, 0.50),   # >1.5 is healthy
        "debt_to_equity":       (0.55, 0.30),   # <1 is conservative
        "interest_coverage":    (8.50, 2.50),   # >3x is safe
        "ebitda_margin":        (0.22, 0.06),   # 22% EBITDA margin
        "revenue_growth_yoy":   (0.12, 0.08),   # 12% growth
        "cash_burn_rate":       (-0.05, 0.03),  # slightly negative = cash generative
        "working_capital_ratio": (0.25, 0.08),
        "gross_margin":         (0.45, 0.10),
    },
    # Class 1: Medium risk — adequate but some pressure
    1: {
        "current_ratio":        (1.30, 0.35),
        "debt_to_equity":       (1.20, 0.45),
        "interest_coverage":    (3.50, 1.20),
        "ebitda_margin":        (0.12, 0.05),
        "revenue_growth_yoy":   (0.04, 0.10),
        "cash_burn_rate":       (0.05, 0.08),
        "working_capital_ratio": (0.10, 0.06),
        "gross_margin":         (0.30, 0.10),
    },
    # Class 2: High risk — stressed financials, covenant pressure
    2: {
        "current_ratio":        (0.90, 0.25),
        "debt_to_equity":       (2.80, 0.90),
        "interest_coverage":    (1.20, 0.60),
        "ebitda_margin":        (0.03, 0.06),
        "revenue_growth_yoy":   (-0.05, 0.12),
        "cash_burn_rate":       (0.25, 0.12),
        "working_capital_ratio": (-0.02, 0.07),
        "gross_margin":         (0.15, 0.09),
    },
    # Class 3: Critical — near-distress / bankruptcy imminent
    3: {
        "current_ratio":        (0.55, 0.25),
        "debt_to_equity":       (6.50, 2.50),   # extreme leverage
        "interest_coverage":    (-0.30, 0.80),  # negative = can't cover interest
        "ebitda_margin":        (-0.08, 0.08),  # negative EBITDA
        "revenue_growth_yoy":   (-0.18, 0.15),
        "cash_burn_rate":       (0.65, 0.20),
        "working_capital_ratio": (-0.15, 0.08),
        "gross_margin":         (0.05, 0.10),
    },
}

FEATURES = list(next(iter(CLASS_PARAMS.values())).keys())

# Class proportions: roughly match real-world M&A deal pipeline composition
# (most targets are healthy/medium; few are critical-stage)
CLASS_PROPORTIONS = {0: 0.40, 1: 0.30, 2: 0.20, 3: 0.10}


def altman_z_prime(row: pd.Series) -> float:
    """
    Approximate Altman Z' score (private firm variant) from our 8 features.
    Used to add a secondary label-check layer on the generated data.

    Z' = 0.717*WC/TA + 0.847*RE/TA + 3.107*EBIT/TA + 0.420*BVE/BVL + 0.998*S/TA

    Mapping to our features (approximate):
        X1 (WC/TA)    ≈ working_capital_ratio
        X2 (RE/TA)    ≈ ebitda_margin * 0.5  (proxy for retained earnings accumulation)
        X3 (EBIT/TA)  ≈ interest_coverage * 0.04  (rough scaling)
        X4 (BVE/BVL)  ≈ 1 / max(debt_to_equity, 0.01)
        X5 (S/TA)     ≈ gross_margin  (proxy for revenue efficiency)
    """
    wc_ta = row.get("working_capital_ratio", 0.0) or 0.0
    re_ta = (row.get("ebitda_margin", 0.0) or 0.0) * 0.5
    ebit_ta = (row.get("interest_coverage", 0.0) or 0.0) * 0.04
    bve_bvl = 1.0 / max(abs(row.get("debt_to_equity", 1.0) or 1.0), 0.01)
    s_ta = row.get("gross_margin", 0.0) or 0.0

    return (
        0.717 * wc_ta
        + 0.847 * re_ta
        + 3.107 * ebit_ta
        + 0.420 * bve_bvl
        + 0.998 * s_ta
    )


def z_to_label(z: float) -> int:
    if z > 2.9:
        return 0
    elif z > 1.23:
        return 1
    elif z > 0.0:
        return 2
    else:
        return 3


def generate_class(cls: int, n: int, rng: np.random.Generator) -> pd.DataFrame:
    params = CLASS_PARAMS[cls]
    rows = {}
    for feature, (mean, std) in params.items():
        rows[feature] = rng.normal(loc=mean, scale=std, size=n)

    df = pd.DataFrame(rows)

    # Hard-clip to domain-valid ranges
    df["current_ratio"] = df["current_ratio"].clip(0.01, 10.0)
    df["debt_to_equity"] = df["debt_to_equity"].clip(-5.0, 30.0)
    df["interest_coverage"] = df["interest_coverage"].clip(-5.0, 30.0)
    df["ebitda_margin"] = df["ebitda_margin"].clip(-0.5, 0.8)
    df["revenue_growth_yoy"] = df["revenue_growth_yoy"].clip(-0.9, 2.0)
    df["cash_burn_rate"] = df["cash_burn_rate"].clip(-1.0, 2.0)
    df["working_capital_ratio"] = df["working_capital_ratio"].clip(-0.5, 0.8)
    df["gross_margin"] = df["gross_margin"].clip(-0.2, 0.9)

    df["risk_tier"] = cls
    return df


def inject_nulls(df: pd.DataFrame, null_rate: float, rng: np.random.Generator) -> pd.DataFrame:
    """Randomly null out ~null_rate fraction of each feature column."""
    df = df.copy()
    for col in FEATURES:
        mask = rng.random(len(df)) < null_rate
        df.loc[mask, col] = np.nan
    return df


def generate(n_rows: int = 600, null_rate: float = NULL_RATE, seed: int = SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    frames = []
    for cls, proportion in CLASS_PROPORTIONS.items():
        n = round(n_rows * proportion)
        frames.append(generate_class(cls, n, rng))

    df = pd.concat(frames, ignore_index=True).sample(frac=1, random_state=seed).reset_index(drop=True)

    # Secondary validation: compute Z' and flag if label looks misaligned
    # (due to noise). Flip ~20% of borderline cases to the Z'-derived label
    # to add realistic uncertainty without making classes trivially separable.
    z_scores = df[FEATURES].apply(
        lambda row: altman_z_prime(row.where(row.notna(), other=0)), axis=1
    )
    z_labels = z_scores.map(z_to_label)
    flip_mask = (rng.random(len(df)) < 0.20) & (z_labels != df["risk_tier"])
    df.loc[flip_mask, "risk_tier"] = z_labels[flip_mask]

    # Inject nulls AFTER label assignment
    df = inject_nulls(df, null_rate, rng)

    return df


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic financial ratios data")
    parser.add_argument("--rows", type=int, default=600, help="Number of rows to generate")
    parser.add_argument("--out", default=DEFAULT_OUT, help="Output CSV path")
    parser.add_argument("--null-rate", type=float, default=NULL_RATE)
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()

    print(f"[INFO] Generating {args.rows} synthetic rows (null_rate={args.null_rate:.0%})...")
    df = generate(n_rows=args.rows, null_rate=args.null_rate, seed=args.seed)

    # Report
    counts = df["risk_tier"].value_counts().sort_index()
    tier_names = {0: "low", 1: "medium", 2: "high", 3: "critical"}
    print("\n[INFO] Class distribution:")
    for cls, cnt in counts.items():
        print(f"       Class {cls} ({tier_names.get(cls, '?'):8s}): {cnt:4d}  ({cnt/len(df)*100:.1f}%)")

    null_pcts = df[FEATURES].isnull().mean() * 100
    print("\n[INFO] Null % per feature:")
    for col, pct in null_pcts.items():
        print(f"       {col:25s}: {pct:.1f}%")

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    df.to_csv(args.out, index=False)
    print(f"\n[INFO] Saved {len(df):,} rows → {args.out}")
    print("       Columns:", list(df.columns))
    print("\n[NOTE] This is SYNTHETIC data generated with Altman Z-Score thresholds.")
    print("       For production, replace with real data from:")
    print("       UCI Polish Bankruptcy: https://archive.ics.uci.edu/dataset/365/")
    print("       Kaggle (Taiwan):       https://kaggle.com/datasets/fedesoriano/company-bankruptcy-prediction")


if __name__ == "__main__":
    main()