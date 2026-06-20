"""Generate mock due diligence documents for two deal rooms: Stripe and Databricks."""
from fpdf import FPDF, XPos, YPos
import os

OUT = "mock_documents"
os.makedirs(f"{OUT}/Stripe", exist_ok=True)
os.makedirs(f"{OUT}/Databricks", exist_ok=True)


def clean(text: str) -> str:
    return text.replace("—", "-").replace("–", "-").replace("’", "'").replace("“", '"').replace("”", '"')


def make_pdf(path: str, title: str, sections: list[tuple[str, str]]):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, clean(title), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(0, 6, "CONFIDENTIAL - For Deloitte Due Diligence Use Only", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)
    for heading, body in sections:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, clean(heading), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 6, clean(body))
        pdf.ln(3)
    pdf.output(path)
    print(f"  Created: {path}")


# ─── STRIPE ──────────────────────────────────────────────────────────────────

make_pdf(
    f"{OUT}/Stripe/stripe_financial_summary_2024.pdf",
    "Stripe, Inc. — Financial Summary FY2024",
    [
        ("Company Overview",
         "Stripe, Inc. is a privately held financial infrastructure platform headquartered in San Francisco, CA. "
         "Founded 2010. Total payment volume processed in FY2024: $1.4 trillion."),
        ("Revenue",
         "Total Net Revenue: $5.6B (+21% YoY)\n"
         "Gross Profit: $2.9B (Gross Margin: 52%)\n"
         "EBITDA: $870M (Margin: 15.5%)\n"
         "Net Income (Loss): ($140M) — reflects continued infrastructure investment."),
        ("Key Balance Sheet Items (as of Dec 31, 2024)",
         "Cash & Equivalents: $8.2B\n"
         "Total Assets: $19.4B\n"
         "Long-Term Debt: $2.1B (convertible notes, due 2027)\n"
         "Total Equity: $11.0B"),
        ("Risk Factors",
         "1. Regulatory exposure in EU (PSD2 compliance costs estimated $120M/yr).\n"
         "2. Concentration risk: top 10 merchants represent ~18% of TPV.\n"
         "3. Chargeback reserve: $340M accrued as of Q4 2024."),
    ],
)

make_pdf(
    f"{OUT}/Stripe/stripe_nda_and_legal_overview.pdf",
    "Stripe, Inc. — Legal & Compliance Overview",
    [
        ("Corporate Structure",
         "Parent entity: Stripe, Inc. (Delaware C-Corp)\n"
         "Key subsidiaries: Stripe Payments Europe Ltd (Ireland), Stripe Technology Europe Ltd, "
         "Stripe Japan KK, Stripe Australia Pty Ltd.\n"
         "Total subsidiaries: 38 across 46 jurisdictions."),
        ("Pending Litigation",
         "Case 1: Merchant class action (N.D. Cal.) re: alleged price-fixing of interchange routing. "
         "Status: Discovery phase. Estimated exposure: $60M–$180M.\n\n"
         "Case 2: Employment dispute (CA) re: misclassification of 120 contractors. "
         "Status: Mediation scheduled Q2 2025. Estimated exposure: $8M."),
        ("Regulatory Licenses",
         "Licensed as a Money Transmitter in all 50 US states.\n"
         "EU: Authorised Electronic Money Institution under Central Bank of Ireland.\n"
         "UK: FCA-authorised Payment Institution (FRN 900461).\n"
         "No material regulatory sanctions in past 36 months."),
        ("Material Contracts",
         "Exclusive processing agreement with Shopify (expires Dec 2026, auto-renew).\n"
         "AWS infrastructure contract: $1.1B committed spend through 2028.\n"
         "No change-of-control provisions triggered by proposed acquisition."),
    ],
)

make_pdf(
    f"{OUT}/Stripe/stripe_ip_and_technology_audit.pdf",
    "Stripe, Inc. — IP & Technology Audit",
    [
        ("Patent Portfolio",
         "Active US patents: 214\nPending applications: 67\n"
         "Core patents cover tokenisation, payment routing optimisation, and fraud ML models. "
         "No active infringement claims against Stripe as of the report date."),
        ("Open Source Obligations",
         "Stripe uses GPL-licensed components in 3 internal tools. Legal has confirmed none are distributed externally. "
         "No copyleft contamination risk identified."),
        ("Cybersecurity Posture",
         "PCI-DSS Level 1 certified (last audit: March 2024).\n"
         "SOC 2 Type II: issued November 2024, zero material findings.\n"
         "One data incident in 2023: inadvertent logging of 4,200 card BINs — remediated within 72 hours, regulators notified."),
    ],
)

# ─── DATABRICKS ──────────────────────────────────────────────────────────────

make_pdf(
    f"{OUT}/Databricks/databricks_financial_summary_2024.pdf",
    "Databricks, Inc. — Financial Summary FY2024",
    [
        ("Company Overview",
         "Databricks, Inc. is a privately held data and AI company headquartered in San Francisco, CA. "
         "Founded 2013 by the creators of Apache Spark. ARR as of Q4 2024: $2.4B."),
        ("Revenue",
         "Total Revenue: $2.35B (+56% YoY)\n"
         "Gross Profit: $1.62B (Gross Margin: 69%)\n"
         "EBITDA: ($310M) — heavy R&D and go-to-market investment phase.\n"
         "Net Loss: ($530M)\n"
         "Remaining Performance Obligations (RPO): $4.1B"),
        ("Key Balance Sheet Items (as of Oct 31, 2024)",
         "Cash & Equivalents: $3.9B\n"
         "Total Assets: $7.2B\n"
         "Long-Term Debt: $0 (fully equity-funded)\n"
         "Total Equity: $5.8B\n"
         "Last valuation (Series J, Sept 2024): $62B at $62.00/share."),
        ("Risk Factors",
         "1. Customer concentration: top 5 cloud customers = 24% of revenue.\n"
         "2. Gross margin pressure from GPU compute costs for Mosaic AI workloads.\n"
         "3. Competitive pressure from Snowflake, Google BigQuery, and Microsoft Fabric.\n"
         "4. Key-person dependency: CEO Ali Ghodsi holds significant voting control."),
    ],
)

make_pdf(
    f"{OUT}/Databricks/databricks_legal_and_employment.pdf",
    "Databricks, Inc. — Legal & Employment Review",
    [
        ("Corporate Structure",
         "Parent entity: Databricks, Inc. (Delaware C-Corp)\n"
         "Key subsidiaries: Databricks UK Ltd, Databricks Germany GmbH, Databricks Singapore Pte Ltd.\n"
         "Total subsidiaries: 22. No golden-share or special voting structures held by third parties."),
        ("Pending Litigation",
         "Case 1: IP dispute with Snowflake re: alleged misappropriation of trade secrets by 3 former engineers. "
         "Status: Pre-trial. Estimated exposure: $25M–$75M.\n\n"
         "Case 2: EEOC charge (gender discrimination) filed by 2 former employees. "
         "Status: Early investigation. Estimated exposure: <$5M."),
        ("Employment & Equity",
         "Total headcount: 6,800 (FTEs). Avg tenure: 2.9 years.\n"
         "Equity overhang: 18.4% of fully-diluted shares outstanding.\n"
         "Key retention: 14 C-level / VP executives have cliff dates within 12 months of close — "
         "retention packages estimated at $120M total."),
        ("Material Contracts",
         "Preferred cloud partner: Microsoft Azure (5-year co-sell agreement, $1B+ committed).\n"
         "OEM agreement with Nvidia for GPU allocation priority through 2026.\n"
         "Change-of-control clause in Azure agreement: 90-day notice required, no consent needed."),
    ],
)

print("\nDone! Documents saved to ./mock_documents/")
print("  Stripe/    — 3 documents")
print("  Databricks/ — 2 documents")
