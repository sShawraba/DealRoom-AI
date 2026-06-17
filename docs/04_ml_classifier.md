# DealRoom AI — ML Financial Risk Classifier

## Purpose

Predict a financial risk tier for the target company based on normalised financial ratios. Provides a reproducible, auditable, quantitative signal that complements the qualitative analysis from the synthesis agent.

---

## Problem Framing

- **Task:** Multi-class classification
- **Classes:** `low`, `medium`, `high`, `critical`
- **Input:** 8 financial ratio features (nullable — model must handle missing values)
- **Output:** Risk tier + 0–100 risk score + SHAP factor explanations

---

## Features

| Feature | Column Name | Formula | Notes |
|---|---|---|---|
| Current Ratio | `current_ratio` | Current Assets / Current Liabilities | < 1.0 = distress signal |
| Debt-to-Equity | `debt_to_equity` | Total Debt / Shareholders Equity | High = refinancing risk |
| Interest Coverage | `interest_coverage` | EBIT / Interest Expense | < 2.0 = concerning |
| EBITDA Margin | `ebitda_margin` | EBITDA / Revenue | Negative = burning cash |
| Revenue Growth YoY | `revenue_growth_yoy` | (Rev_t - Rev_{t-1}) / Rev_{t-1} | Negative = contraction |
| Cash Burn Rate | `cash_burn_rate` | Net Cash Flow / Cash Reserves | Months of runway |
| Working Capital Ratio | `working_capital_ratio` | Working Capital / Total Assets | Operational buffer |
| Gross Margin | `gross_margin` | (Revenue - COGS) / Revenue | Pricing power |

---

## Training Pipeline

### Data

```python
# ml/train.py

"""
Training data sources:
1. SEC EDGAR financial data for S&P 1500 companies (public, free)
   - Pull via EDGAR full-text API or use pre-packaged datasets
   - Extract 8 ratio features from 10-K filings
2. Labels: financial distress within 24-month window
   - Critical: bankruptcy filed OR debt covenant breach
   - High: credit downgrade >= 2 notches OR revenue decline > 30%
   - Medium: revenue decline 10-30% OR interest coverage < 2.0
   - Low: none of the above
3. Minimum dataset: ~2,000 companies
   If public data is sparse, augment with synthetic samples using known
   financial distress thresholds from Altman Z-Score research.

Store raw data in ml/data/financial_ratios.csv
Columns: company_id, year, current_ratio, debt_to_equity, interest_coverage,
         ebitda_margin, revenue_growth_yoy, cash_burn_rate,
         working_capital_ratio, gross_margin, label
"""
```

### scikit-learn Pipeline

```python
import pandas as pd
import numpy as np
import joblib
import shap
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.metrics import classification_report, roc_auc_score
from xgboost import XGBClassifier

FEATURES = [
    "current_ratio", "debt_to_equity", "interest_coverage",
    "ebitda_margin", "revenue_growth_yoy", "cash_burn_rate",
    "working_capital_ratio", "gross_margin"
]
LABEL_MAP = {"low": 0, "medium": 1, "high": 2, "critical": 3}
RISK_TIERS = ["low", "medium", "high", "critical"]

def build_pipeline() -> Pipeline:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),  # handles nulls
        ("scaler", StandardScaler()),
        ("model", XGBClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            use_label_encoder=False,
            eval_metric="mlogloss",
            random_state=42
        ))
    ])

def train(data_path: str, output_path: str):
    df = pd.read_csv(data_path)
    X = df[FEATURES]
    y = df["label"].map(LABEL_MAP)

    pipeline = build_pipeline()

    # 5-fold stratified cross-validation
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_results = cross_validate(
        pipeline, X, y, cv=cv,
        scoring=["f1_macro", "roc_auc_ovr"],
        return_train_score=True
    )
    print("CV F1 Macro:", cv_results["test_f1_macro"].mean())
    print("CV ROC-AUC:", cv_results["test_roc_auc_ovr"].mean())

    # Final fit on full dataset
    pipeline.fit(X, y)

    # Save artifact
    joblib.dump(pipeline, output_path)
    print(f"Model saved to {output_path}")

if __name__ == "__main__":
    train("ml/data/financial_ratios.csv", "ml/artifacts/risk_classifier.pkl")
```

---

## RiskClassifier Class (Serving)

```python
# app/ml/classifier.py

import joblib
import shap
import numpy as np
from app.schemas.ml import FinancialRatios, RiskScoreResponse, SHAPFactor
from app.core.config import settings

FEATURES = [
    "current_ratio", "debt_to_equity", "interest_coverage",
    "ebitda_margin", "revenue_growth_yoy", "cash_burn_rate",
    "working_capital_ratio", "gross_margin"
]
RISK_TIERS = ["low", "medium", "high", "critical"]

class RiskClassifier:
    """Loaded once at app startup. Thread-safe for concurrent reads."""

    def __init__(self):
        self.pipeline = joblib.load(settings.ML_MODEL_PATH)
        # SHAP explainer wraps the XGBoost model (extract from pipeline)
        self.explainer = shap.TreeExplainer(self.pipeline.named_steps["model"])
        self._preprocessing = self.pipeline[:-1]  # all steps except model

    def predict(self, ratios: FinancialRatios) -> RiskScoreResponse:
        # Build feature vector (preserving None as NaN for imputer)
        feature_vector = np.array([[
            ratios.current_ratio,
            ratios.debt_to_equity,
            ratios.interest_coverage,
            ratios.ebitda_margin,
            ratios.revenue_growth_yoy,
            ratios.cash_burn_rate,
            ratios.working_capital_ratio,
            ratios.gross_margin
        ]], dtype=float)  # NaN for None fields

        # Track which features were missing
        missing = [FEATURES[i] for i, v in enumerate(feature_vector[0]) if np.isnan(v)]

        # Get class probabilities
        proba = self.pipeline.predict_proba(feature_vector)[0]  # shape (4,)

        # Risk score: weighted average of class indices (0-3) scaled to 0-100
        risk_score = float(np.dot(proba, [0, 33, 66, 100]))
        predicted_class = int(np.argmax(proba))
        risk_tier = RISK_TIERS[predicted_class]

        # SHAP values for the predicted class
        preprocessed = self._preprocessing.transform(feature_vector)
        shap_values = self.explainer.shap_values(preprocessed)
        # shap_values shape: (n_classes, n_samples, n_features) for multi-class
        class_shap = shap_values[predicted_class][0]  # shape (n_features,)

        # Build top 3 SHAP factors
        sorted_idx = np.argsort(np.abs(class_shap))[::-1][:3]
        factors = [
            SHAPFactor(
                feature=FEATURES[i],
                value=float(feature_vector[0][i]) if not np.isnan(feature_vector[0][i]) else None,
                direction="increases_risk" if class_shap[i] > 0 else "decreases_risk",
                magnitude=float(abs(class_shap[i]))
            )
            for i in sorted_idx
        ]

        return RiskScoreResponse(
            risk_score=round(risk_score, 1),
            risk_tier=risk_tier,
            contributing_factors=factors,
            missing_features=missing
        )

# Singleton — instantiated in main.py lifespan
risk_classifier: RiskClassifier | None = None

def get_risk_classifier() -> RiskClassifier:
    return risk_classifier
```

### Load at Startup

```python
# app/main.py
from contextlib import asynccontextmanager
from app.ml.classifier import RiskClassifier
import app.ml.classifier as ml_module

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    ml_module.risk_classifier = RiskClassifier()
    print("ML model loaded")
    yield
    # Shutdown — nothing to clean up

app = FastAPI(lifespan=lifespan, ...)
```

---

## Evaluation Script

```python
# ml/evaluate.py

"""
Run offline evaluation. Call this before promoting a new model version.

Outputs:
- Classification report (precision, recall, F1 per class)
- ROC-AUC per class (one-vs-rest)
- SHAP summary plot saved to ml/artifacts/shap_summary.png
- Confusion matrix saved to ml/artifacts/confusion_matrix.png

Pass/fail gate:
- macro F1 >= 0.65
- No single class F1 < 0.50
If gate fails, print warning and exit with code 1 (blocks CI pipeline).
"""

import sys
import joblib
import shap
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from sklearn.metrics import classification_report, roc_auc_score, ConfusionMatrixDisplay
from sklearn.model_selection import train_test_split

FEATURES = [...]  # same as train.py
LABEL_MAP = {"low": 0, "medium": 1, "high": 2, "critical": 3}
F1_GATE = 0.65
MIN_CLASS_F1 = 0.50

def evaluate(model_path: str, data_path: str):
    pipeline = joblib.load(model_path)
    df = pd.read_csv(data_path)
    X = df[FEATURES]
    y = df["label"].map(LABEL_MAP)

    _, X_test, _, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

    y_pred = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)

    report = classification_report(y_test, y_pred, output_dict=True)
    macro_f1 = report["macro avg"]["f1-score"]

    print(classification_report(y_test, y_pred, target_names=["low","medium","high","critical"]))
    print(f"ROC-AUC (OvR): {roc_auc_score(y_test, y_proba, multi_class='ovr', average='macro'):.4f}")

    # Gate check
    class_f1s = [report[str(i)]["f1-score"] for i in range(4)]
    if macro_f1 < F1_GATE or min(class_f1s) < MIN_CLASS_F1:
        print(f"FAILED eval gate. macro_f1={macro_f1:.3f}, min_class_f1={min(class_f1s):.3f}")
        sys.exit(1)

    print("Eval gate PASSED.")
```

---

## Feature Extraction from Report

```python
# app/ml/features.py

"""
When financial documents are available in the deal room, attempt to
automatically extract ratio values from the indexed chunks.

Strategy:
1. Run targeted pgvector query: "current ratio debt equity EBITDA revenue"
2. Pass top 5 chunks to gpt-4o-mini with extraction prompt
3. Return FinancialRatios object (nulls where not found)

This is best-effort. The /api/ml/risk-score endpoint also accepts
manually entered ratios from the analyst.
"""

EXTRACTION_PROMPT = """
Extract the following financial metrics from the provided text.
Return ONLY a JSON object with these exact keys.
Use null for any metric not found.
Do not calculate or infer — only extract explicitly stated values.

Keys: current_ratio, debt_to_equity, interest_coverage, ebitda_margin,
      revenue_growth_yoy, cash_burn_rate, working_capital_ratio, gross_margin

Text:
{text}
"""
```
