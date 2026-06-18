"""Email service: send Q&A questions to a target company via SMTP."""
from __future__ import annotations

from datetime import datetime, timezone

import aiosmtplib

from app.core.config import settings
from app.models.management_qa import ManagementQuestion


def _format_email_body(
    deal_room_name: str, questions: list[ManagementQuestion]
) -> str:
    by_category: dict[str, list[ManagementQuestion]] = {}
    for q in questions:
        by_category.setdefault(q.category.title(), []).append(q)

    lines = [
        f"Management Q&A — {deal_room_name}",
        "=" * 60,
        "",
    ]
    for category, items in sorted(by_category.items()):
        lines.append(f"{category}")
        lines.append("-" * len(category))
        for i, q in enumerate(items, 1):
            lines.append(f"{i}. [{q.priority.upper()}] {q.question}")
        lines.append("")

    lines.append(
        "Please respond to each question with your management's perspective."
    )
    return "\n".join(lines)


async def send_qa_email(
    to: str,
    deal_room_name: str,
    questions: list[ManagementQuestion],
    from_addr: str | None = None,
) -> datetime:
    """Format Q&A questions and send via aiosmtplib. Returns sent timestamp."""
    sender = from_addr or getattr(settings, "smtp_user", "noreply@dealroom.ai")
    body = _format_email_body(deal_room_name, questions)

    message = (
        f"From: {sender}\r\n"
        f"To: {to}\r\n"
        f"Subject: Management Q&A — {deal_room_name}\r\n"
        f"Content-Type: text/plain; charset=utf-8\r\n"
        f"\r\n"
        f"{body}"
    )

    smtp_host = getattr(settings, "SMTP_HOST", "smtp")
    smtp_port = int(getattr(settings, "SMTP_PORT", 1025))
    smtp_user = getattr(settings, "smtp_user", "")
    smtp_password = getattr(settings, "smtp_password", "")

    kwargs: dict = {
        "hostname": smtp_host,
        "port": smtp_port,
        "start_tls": False,
        "use_tls": False,
    }
    if smtp_user and smtp_password:
        kwargs["username"] = smtp_user
        kwargs["password"] = smtp_password

    await aiosmtplib.send(message, sender=sender, recipients=[to], **kwargs)
    return datetime.now(timezone.utc)
