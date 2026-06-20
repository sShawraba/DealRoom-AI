"""Email service: SMTP sending for Q&A and user invitations."""
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

    await aiosmtplib.send(message, sender=sender, recipients=[to], **_smtp_kwargs())
    return datetime.now(timezone.utc)


def _smtp_kwargs() -> dict:
    smtp_host = getattr(settings, "SMTP_HOST", "mailhog")
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
    return kwargs


async def send_invite_email(
    to: str,
    invited_by_name: str,
    deal_room_name: str | None,
    accept_url: str,
) -> None:
    """Send a deal-room invitation email with a one-click accept link."""
    sender = getattr(settings, "smtp_user", "") or "noreply@dealroom.ai"

    if deal_room_name:
        subject = f"You've been invited to join {deal_room_name} on DealRoom AI"
        body_lines = [
            f"{invited_by_name} has invited you to collaborate on the deal room",
            f'"{deal_room_name}" in DealRoom AI.',
            "",
            "Click the link below to set your password and join:",
            accept_url,
            "",
            "This link expires in 7 days.",
        ]
    else:
        subject = "You've been invited to DealRoom AI"
        body_lines = [
            f"{invited_by_name} has invited you to join their team on DealRoom AI.",
            "",
            "Click the link below to set your password and get started:",
            accept_url,
            "",
            "This link expires in 7 days.",
        ]

    body = "\n".join(body_lines)
    message = (
        f"From: {sender}\r\n"
        f"To: {to}\r\n"
        f"Subject: {subject}\r\n"
        f"Content-Type: text/plain; charset=utf-8\r\n"
        f"\r\n"
        f"{body}"
    )
    await aiosmtplib.send(message, sender=sender, recipients=[to], **_smtp_kwargs())
