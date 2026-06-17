"""All prompt templates and section configuration for the synthesis agent."""

SECTION_QUERIES: dict[str, str] = {
    "executive_summary":     "company overview business model revenue operations strategy",
    "financial_health":      "revenue profit EBITDA margin debt cash flow balance sheet",
    "legal_flags":           "contracts litigation IP indemnity warranties representations",
    "commercial_assessment": "market customers competitors pricing growth",
    "red_flags":             "risks liabilities disputes defaults write-offs anomalies",
    "key_questions":         "gaps inconsistencies projections assumptions anomalies",
}

# Three concurrent groups — sections within a group run in parallel
SECTION_GROUPS: list[list[str]] = [
    ["executive_summary", "commercial_assessment"],  # Group 1 — market context
    ["financial_health", "red_flags"],               # Group 2 — financial depth
    ["legal_flags", "key_questions"],                # Group 3 — legal + gaps
]

SYSTEM_PROMPT = """You are a senior M&A due diligence analyst. Based on the retrieved document excerpts:
- Cite every factual claim: [SOURCE: filename.pdf, p.N]
- Be specific — name figures, dates, amounts, clause numbers
- 1–3 sentences per item
- Do not make claims you cannot cite
- Return ONLY valid JSON matching the schema provided"""

QUERY_VARIANTS_PROMPT = (
    "Generate {n} different search queries to find information about: {query}\n"
    "Use different vocabulary and phrasings. "
    "Return ONLY valid JSON in this format: {{\"queries\": [\"...\", \"...\", \"...\"]}}"
)

HYDE_PROMPT = (
    "Write a 2-sentence passage from a corporate due diligence document that answers: {query}\n"
    "Be specific and factual. Return only the passage."
)

ROUTING_PROMPT = (
    "Classify this query to the most relevant document types: {query}\n"
    "Options: financial_statement, legal_contract, market_report, management_presentation, other\n"
    "Return ONLY valid JSON in this format: {{\"types\": [\"type1\", \"type2\"]}}"
)

DD_CHECKLIST = [
    "financial_statement",
    "legal_contract",
    "market_report",
    "management_presentation",
]

MISSING_CONTEXT_PROMPT = (
    "The deal room has these document types: {found_types}.\n"
    "A standard M&A due diligence requires: {required_types}.\n"
    "List the missing document types and what information gaps this creates. "
    "Return a concise JSON object: {{\"missing\": [{{\"doc_type\": \"...\", \"impact\": \"...\"}}]}}"
)
