"""Ingestion tools: PDF parsing and document-type classification."""
from __future__ import annotations

import structlog

log = structlog.get_logger(__name__)


def parse_pdf(file_path: str) -> dict:
    """
    Parse a PDF file with pdfplumber and return structured content.

    Returns a dict with keys:
      - pages: list of {page_number, text_blocks, tables}
      - page_count: int

    This is a CPU-bound operation — callers must wrap it with asyncio.to_thread().
    """
    import pdfplumber

    pages = []
    with pdfplumber.open(file_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            text_blocks = [b for b in text.split("\n\n") if b.strip()]

            raw_tables = page.extract_tables() or []
            tables = []
            for tbl in raw_tables:
                if not tbl:
                    continue
                headers = [str(cell or "") for cell in tbl[0]]
                rows = [[str(cell or "") for cell in row] for row in tbl[1:]]
                tables.append({"headers": headers, "rows": rows, "caption": ""})

            pages.append(
                {
                    "page_number": i,
                    "text_blocks": text_blocks,
                    "tables": tables,
                }
            )

    log.info("pdf.parsed", file_path=file_path, page_count=len(pages))
    return {"pages": pages, "page_count": len(pages)}


async def classify_document_type(filename: str, first_500_chars: str) -> str:
    """
    Classify the document type using gpt-4o-mini with a single prompt.

    Returns one of: financial_statement, legal_contract, market_report,
    management_presentation, other
    """
    from openai import AsyncOpenAI
    from app.core.config import settings

    client = AsyncOpenAI(api_key=settings.openai_api_key)

    prompt = (
        "Classify the following document into exactly one category.\n"
        "Categories: financial_statement, legal_contract, market_report, "
        "management_presentation, other\n\n"
        f"Filename: {filename}\n"
        f"Preview:\n{first_500_chars}\n\n"
        "Reply with only the category name, nothing else."
    )

    response = await client.chat.completions.create(
        model=settings.CHEAP_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=20,
        temperature=0,
    )

    raw = response.choices[0].message.content.strip().lower()
    valid = {
        "financial_statement",
        "legal_contract",
        "market_report",
        "management_presentation",
        "other",
    }
    doc_type = raw if raw in valid else "other"
    log.info("document.classified", filename=filename, doc_type=doc_type)
    return doc_type
