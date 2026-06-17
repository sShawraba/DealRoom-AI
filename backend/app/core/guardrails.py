import re
from dataclasses import dataclass, field


INJECTION_PATTERNS = [
    "ignore previous instructions",
    "ignore all instructions",
    "disregard the above",
    "you are now",
    "forget everything",
    "new instructions:",
    "system prompt:",
    "jailbreak",
    "ignore your",
    "override instructions",
    "pretend you are",
    "act as if",
    "disregard your",
    "bypass",
]

PII_PATTERNS: dict[str, re.Pattern] = {
    "email":       re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
    "phone":       re.compile(r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'),
    "ssn":         re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
    "credit_card": re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
    "passport":    re.compile(r'\b[A-Z]{1,2}\d{6,9}\b'),
}


@dataclass
class ModerationResult:
    flagged: bool
    categories: list[str] = field(default_factory=list)


def detect_prompt_injection(text: str) -> bool:
    """Return True if *text* contains a known prompt-injection pattern."""
    lowered = text.lower()
    return any(pattern in lowered for pattern in INJECTION_PATTERNS)


def redact_pii(text: str) -> tuple[str, list[str]]:
    """
    Redact PII from *text*.

    Returns (redacted_text, list_of_pii_types_found). Used before storing
    document chunks in pgvector.
    """
    found: list[str] = []
    for pii_type, pattern in PII_PATTERNS.items():
        if pattern.search(text):
            found.append(pii_type)
            text = pattern.sub(f"[REDACTED_{pii_type.upper()}]", text)
    return text, found


async def moderate_content(text: str) -> ModerationResult:
    """
    Check user-generated content against OpenAI's moderation API.

    Used for annotation text, Q&A answers, and approval sign-off notes.
    Returns a ModerationResult with flagged=True and affected categories if
    the content violates policy. NOT used for document chunks (cost).
    """
    from openai import AsyncOpenAI
    from app.core.config import settings

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    resp = await client.moderations.create(input=text)
    result = resp.results[0]
    flagged_cats = [k for k, v in result.categories.__dict__.items() if v]
    return ModerationResult(flagged=result.flagged, categories=flagged_cats)
