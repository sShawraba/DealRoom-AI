"""Ingestion tools: PDF parsing, CSV parsing, and document-type classification."""
from __future__ import annotations

import structlog

log = structlog.get_logger(__name__)

_CSV_ROWS_PER_TABLE = 100


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


def parse_csv(file_path: str) -> dict:
    """
    Parse a CSV file and return the same structure as parse_pdf.

    Large CSVs are split into table chunks of _CSV_ROWS_PER_TABLE rows each.
    A pipe-delimited text preview is added to text_blocks so classify_document_type
    can see enough content to classify the file correctly.
    """
    import csv as csv_mod

    with open(file_path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv_mod.reader(f))

    if not rows:
        return {"pages": [], "page_count": 0}

    headers = rows[0]
    data_rows = rows[1:]

    tables = []
    for start in range(0, max(len(data_rows), 1), _CSV_ROWS_PER_TABLE):
        batch = data_rows[start : start + _CSV_ROWS_PER_TABLE]
        tables.append({"headers": headers, "rows": batch, "caption": ""})

    if not tables:
        tables = [{"headers": headers, "rows": [], "caption": ""}]

    preview = "\n".join(
        " | ".join(str(c) for c in row) for row in ([headers] + data_rows[:5])
    )

    page = {"page_number": 1, "text_blocks": [preview], "tables": tables}
    log.info("csv.parsed", file_path=file_path, rows=len(data_rows), table_chunks=len(tables))
    return {"pages": [page], "page_count": 1}


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
