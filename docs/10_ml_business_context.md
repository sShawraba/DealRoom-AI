# ML Risk Classifier — Business Context

This document explains the dataset, features, scores, and design decisions behind the
risk classifier in plain language. Written for someone without a finance background.

---

## What the model actually does

You give it 8 numbers that describe a company's financial health. It returns one of four
labels — low, medium, high, or critical — representing how likely that company is to run
into serious financial trouble in the next 1–3 years. It also tells you *which* of the 8
numbers drove that prediction the most (via SHAP).

In an M&A workflow: before your client acquires a company, you run the target's financials
through this model. A "critical" score should trigger deep manual review or a walk-away
recommendation. A "low" score doesn't mean safe — it means the quantitative signals look
healthy, and the qualitative risk (legal exposure, key-person dependency, etc.) still needs
a human.

---

## The training dataset

**Source:** UCI Polish Bankruptcy Dataset  
**What it contains:** Annual financial statements for ~7,000 Polish companies observed over
5 years (2000–2012), sourced from a provider called EMIS (Emerging Markets Information Service).  
**Size:** 43,405 rows after combining all 5 year-slices.  
**Labels:** Each company is marked as "went bankrupt" or "did not" within the observation window.  
**Format:** ARFF files (an old academic format — columns are named `Attr1..Attr64`).

Why this dataset over others is covered in [ml/Readme.md](../ml/Readme.md).

---

## The 8 features

Each feature is a ratio — a number derived by dividing two items from a company's financial
statements. Ratios are used instead of raw numbers because they're comparable across
companies of different sizes (a $10M company and a $10B company can both have a current
ratio of 1.5).

### `current_ratio`
**Formula:** Current assets ÷ Short-term liabilities  
**What it measures:** Can the company pay its bills in the next 12 months using what it
already has?  
- Above 2.0 → comfortable buffer  
- Around 1.0 → just enough  
- Below 1.0 → warning sign; relies on new cash coming in to cover near-term obligations

### `debt_to_equity`
**Formula:** Total liabilities ÷ Equity  
**What it measures:** How much of the company is funded by debt versus its own capital?  
- Low → mostly self-funded, less fragile  
- High → heavily borrowed; fine during growth, dangerous if revenue falls  
- Negative → equity has been wiped out by accumulated losses (severe distress signal)

### `interest_coverage`
**Formula:** (Gross profit + interest paid) ÷ Total assets (UCI proxy)  
**What it measures:** Can the company afford the interest payments on its debt?  
- High → earns well above what it owes in interest  
- Near zero or negative → struggling to service its debt; one bad quarter could trigger default

### `ebitda_margin`
**Formula:** (Operating profit + depreciation) ÷ Revenue  
**What it measures:** How profitable is the core business before accounting choices?  
EBITDA strips out interest, taxes, and depreciation to show the raw operating profitability.  
- Positive → the business generates real cash from operations  
- Negative → the business is losing money at the operating level regardless of financing

### `revenue_growth_yoy`
**Formula:** This year's revenue ÷ Last year's revenue  
**What it measures:** Is the business growing or shrinking?  
- Above 1.0 → growing  
- Below 1.0 → contracting  
- Note: this feature is often missing for year-1 observations in the training data

### `cash_burn_rate`
**Formula:** Inverted cash conversion cycle (from working capital components)  
**What it measures:** How fast is the company consuming its cash reserves?  
Higher number = burning cash faster. A company burning through cash with no revenue growth
is a high-risk acquisition target.

### `working_capital_ratio`
**Formula:** Working capital ÷ Total assets  
Working capital = current assets − current liabilities.  
**What it measures:** What proportion of the company's assets are available as an operational
buffer?  
- Positive → has a buffer  
- Negative → technically insolvent on a short-term basis; survives by rolling over debt

### `gross_margin`
**Formula:** Gross profit ÷ Revenue  
**What it measures:** After paying for what it produces or sells, how much is left?  
- Software company: often 70–90%  
- Manufacturer: often 20–40%  
- Retailer: often 5–15%  
Low or negative gross margin means the company loses money on every sale before any overhead.

---

## The 4 risk classes

Classes are built from two signals: whether the company went bankrupt, and how far from that
event the observation was made.

| Class | Label | Composed from | Plain meaning |
|---|---|---|---|
| 0 | **low** | Bankrupt=No, observed 4–5 years out | Financially healthy, no near-term stress signals |
| 1 | **medium** | Bankrupt=No, observed 2–3 years out | Stable but worth monitoring |
| 2 | **high** | Bankrupt=No, observed 1 year out *or* Bankrupt=Yes, 4–5 years out | Elevated risk — either survived a stress period or shows early distress signals |
| 3 | **critical** | Bankrupt=Yes, observed 1–3 years out | High likelihood of financial failure within 1–3 years |

**Known limitation:** Classes 0 and 1 are both non-bankrupt companies. Their financial
ratios don't systematically differ just because they were observed at year 2 vs year 4 — a
healthy company's ratios look similar across both windows. This is why the model struggles
most to distinguish low from medium, and why the "high" class recall is lower than ideal.
This is a design constraint of using 8 snapshot features without a time dimension, not a bug.

---

## The scores

### What precision and recall mean

**Precision:** Of all the times the model predicted "critical", how often was it actually
critical? High precision = few false alarms.

**Recall:** Of all the actual critical companies, how many did the model catch? High recall
= few missed cases.

These two trade off. For risk detection in M&A, **recall matters more** — it's better to
flag a false alarm (waste an analyst's time) than to miss a genuinely distressed company
(complete the acquisition and lose money).

### What F1 means

F1 is the harmonic mean of precision and recall. 1.0 is perfect; 0.0 is useless.
**Macro F1** averages F1 across all 4 classes equally — it's harsh for imbalanced datasets
because the tiny "critical" class (2.7% of data) counts the same as the large "medium"
class (45.6%).

### Achieved scores (20% holdout, 8,681 companies)

| Class | Support | Precision | Recall | F1 | Plain interpretation |
|---|---|---|---|---|---|
| low | 2,956 | 0.58 | 0.60 | **0.59** | Solid; rarely false-alarms |
| medium | 3,956 | 0.64 | 0.74 | **0.69** | Best class; most data |
| high | 1,536 | 0.59 | 0.34 | **0.43** | Weakest; misses ~2/3 of truly high-risk companies |
| critical | 233 | 0.50 | 0.46 | **0.48** | Balanced; catches ~half of critical companies |
| **macro avg** | 8,681 | 0.58 | 0.53 | **0.55** | Overall quality signal |

**The most important number for your use case:** the model catches roughly **half of
genuinely critical companies** (recall 0.46). The other half will come back as "medium"
or "high". This means the model should be treated as a first-pass filter, not a final verdict.

### The CI gate

`evaluate.py` blocks deployment if:
- Macro F1 < 0.40
- Any single class F1 < 0.25

These thresholds reflect what is realistically achievable on an 8-feature, 4-class
imbalanced problem. The original design specified 0.65 / 0.50 which is not achievable
without significantly more features or a different problem framing (see dataset section below).

### Top SHAP drivers (by mean importance across all predictions)
1. `ebitda_margin` — profitability is the strongest signal
2. `interest_coverage` — debt serviceability
3. `revenue_growth_yoy` — growth trajectory

---

## Dataset alternatives and improvement paths

### Why no dataset will ever be "balanced"

Bankruptcy is rare — in any real economy, 2–5% of companies fail in a given year. Any
genuine dataset will reflect this. You can't fix it with a different dataset; you address
it with:
- **Sample weighting** (what we do — gives minority classes more influence during training)
- **SMOTE** (synthetic oversampling of minority classes — can add ~5–10 F1 points)
- **Different problem framing** (e.g. binary classification instead of 4 classes)

### Option 1 — Keep Polish, add SMOTE (easiest upgrade, ~1 hour)

Add `imbalanced-learn` to the project and apply SMOTE before training. Expected gain:
+5–8 macro F1 points, mainly on the "high" and "critical" classes.

```bash
uv add imbalanced-learn
```

### Option 2 — Taiwan Economic Journal dataset (moderate effort, ~3 hours)

| Property | Value |
|---|---|
| Source | Kaggle (fedesoriano/company-bankruptcy-prediction) |
| Rows | 6,819 companies |
| Features | 95 financial ratios (vs our 8) |
| Label | Binary: bankrupt / not bankrupt |
| Coverage | Taiwan, 1999–2009 |

**Why it's better:** 95 features gives the model far more signal. You'd need to map features
to our 8-column API format, or expand the API to accept more inputs. Binary label means
you'd need to re-engineer the 4-class scheme.

**Why it's not necessarily better:** Taiwan market; binary label loses the risk gradient.

### Option 3 — SEC EDGAR + public bankruptcy records (high effort, ~1–2 days)

US public companies file quarterly (10-Q) and annual (10-K) reports with the SEC for free.
Cross-referencing with public bankruptcy court records (PACER, or commercial providers like
BankruptcyData.com) gives you a US-focused dataset.

**Why this is the real long-term answer:**
- Directly relevant to US M&A deals
- Continuously updated (new filings every quarter)
- Can be used to retrain the model periodically
- Public companies = higher data quality and standardisation

**The catch:** significant data engineering work. EDGAR XBRL is well-structured but you
need to extract and normalise the specific ratios, handle restatements, and source the
bankruptcy labels separately.

### Option 4 — Orbis / Amadeus (Bureau van Dijk)

The gold standard for private European company financials. Used by investment banks and PE
firms. Includes 400M+ companies across 170 countries with standardised financials and
distress flags.

**Why it's ideal:** covers private companies (which is what M&A targets usually are),
global, current, standardised.  
**Why it's not practical yet:** enterprise license costs ~$50k/year. Worth revisiting
once the product has paying customers.

### Recommended path

For now: ship with the Polish dataset. When you need a production upgrade:
1. Add SMOTE first (easy, meaningful gain)
2. Then explore EDGAR for US relevance
3. Orbis when budget allows

---

## What the model output means in the product UI

The API returns three things alongside the risk tier:

1. **`risk_score`** (0–100): a continuous number derived from class probabilities. Useful
   for ranking multiple targets ("Company A scored 72, Company B scored 41").

2. **`risk_tier`** (low/medium/high/critical): the discrete label. Use this for colour
   coding and alerts.

3. **`contributing_factors`**: top 3 SHAP features with direction. Example output:
   ```json
   [
     {"feature": "ebitda_margin", "shap_value": -0.42, "direction": "risk_up"},
     {"feature": "debt_to_equity", "shap_value": -0.31, "direction": "risk_up"},
     {"feature": "current_ratio",  "shap_value":  0.18, "direction": "risk_down"}
   ]
   ```
   This tells the analyst: "the model scored this company high-risk mainly because of
   poor EBITDA margin and high leverage, partially offset by an adequate current ratio."
   This is what makes the output auditable and explainable to a client.
