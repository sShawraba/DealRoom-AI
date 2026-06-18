"""Management Q&A endpoints — generate, list, answer, send email."""
from __future__ import annotations

import json
import uuid

import structlog
from fastapi import APIRouter, HTTPException, Request, status
from openai import AsyncOpenAI

from app.core.audit import AuditAction, log_event
from app.core.config import settings
from app.core.deps import CurrentUserDep, SessionDep
from app.core.guardrails import moderate_content
from app.models.report import ReportItem
from app.repositories.deal_room import DealRoomRepository
from app.repositories.management_qa import ManagementQuestionRepository
from app.repositories.report import ReportRepository
from app.schemas.management_qa import (
    ManagementQuestionResponse,
    QAAnswerPatch,
    QAGenerateResponse,
    QAGroupedResponse,
    QASendEmailRequest,
)
from app.schemas.pagination import PaginatedResponse
from app.services.email_service import send_qa_email

log = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/deal-rooms/{deal_room_id}/reports/{report_id}",
    tags=["management-qa"],
)

_QA_SYSTEM_PROMPT = """You are a due diligence analyst.
Given the following findings, generate sharp management questions for the target company.
Group them by: financial | legal | operational | strategic
Priority: critical | high | medium
Each question must cite the source_item_id (UUID) of the finding that triggered it.
Return ONLY valid JSON in this exact format:
{"categories": [{"name": "<category>", "questions": [{"question": "<text>", "priority": "<priority>", "source_item_id": "<uuid>"}]}]}"""


@router.post(
    "/qa/generate",
    response_model=QAGenerateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_qa(
    deal_room_id: uuid.UUID,
    report_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> QAGenerateResponse:
    dr_repo = DealRoomRepository(session, current_user.tenant_id, current_user.id)
    if await dr_repo.get_by_id(deal_room_id) is None:
        raise HTTPException(404, "Deal room not found")

    report_repo = ReportRepository(session, current_user.tenant_id, current_user.id)
    report = await report_repo.get_by_id(report_id)
    if report is None or report.deal_room_id != deal_room_id:
        raise HTTPException(404, "Report not found")

    from sqlalchemy import select

    relevant_sections = {"red_flags", "financial_health", "legal_flags"}
    result = await session.execute(
        select(ReportItem).where(
            ReportItem.report_id == report_id,
            ReportItem.section_type.in_(relevant_sections),
        )
    )
    items = result.scalars().all()
    if not items:
        raise HTTPException(422, "No relevant findings to generate questions from")

    findings_text = "\n".join(
        f"[{item.id}] ({item.section_type}) {item.edited_content or item.content}"
        for item in items
    )

    valid_item_ids = {str(item.id) for item in items}

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    resp = await client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[
            {"role": "system", "content": _QA_SYSTEM_PROMPT},
            {"role": "user", "content": findings_text},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
    )
    raw = resp.choices[0].message.content or "{}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        log.error("qa.generate.json_parse_failed", raw=raw[:200])
        raise HTTPException(500, "LLM returned invalid JSON")

    qa_repo = ManagementQuestionRepository(session, current_user.tenant_id)
    to_insert = []
    for cat_obj in data.get("categories", []):
        cat_name = cat_obj.get("name", "").lower()
        for q in cat_obj.get("questions", []):
            src_id_str = q.get("source_item_id")
            try:
                # Only accept source_item_ids that exist in this report
                src_id = uuid.UUID(src_id_str) if src_id_str and src_id_str in valid_item_ids else None
            except (ValueError, AttributeError):
                src_id = None
            to_insert.append(
                {
                    "deal_room_id": deal_room_id,
                    "report_id": report_id,
                    "source_item_id": src_id,
                    "category": cat_name if cat_name in ("financial", "legal", "operational", "strategic") else "strategic",
                    "question": q.get("question", ""),
                    "priority": q.get("priority", "medium") if q.get("priority") in ("critical", "high", "medium") else "medium",
                }
            )

    if not to_insert:
        raise HTTPException(422, "LLM returned no questions")

    inserted = await qa_repo.bulk_insert(to_insert)

    await log_event(
        session=session,
        actor_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        tenant_id=current_user.tenant_id,
        action=AuditAction.QA_GENERATED,
        resource_type="report",
        resource_id=report_id,
        deal_room_id=deal_room_id,
        metadata={"count": len(inserted)},
        request=request,
    )
    await session.commit()

    return QAGenerateResponse(
        generated=len(inserted),
        questions=[ManagementQuestionResponse.model_validate(q) for q in inserted],
    )


@router.get("/qa", response_model=PaginatedResponse[ManagementQuestionResponse])
async def list_qa(
    deal_room_id: uuid.UUID,
    report_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUserDep,
    page: int = 1,
    page_size: int = 20,
    category: str | None = None,
) -> PaginatedResponse[ManagementQuestionResponse]:
    dr_repo = DealRoomRepository(session, current_user.tenant_id, current_user.id)
    if await dr_repo.get_by_id(deal_room_id) is None:
        raise HTTPException(404, "Deal room not found")

    qa_repo = ManagementQuestionRepository(session, current_user.tenant_id)
    items, total = await qa_repo.list_by_report(
        report_id=report_id, page=page, page_size=page_size, category=category
    )
    return PaginatedResponse(
        items=[ManagementQuestionResponse.model_validate(q) for q in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/qa/send-email", response_model=dict)
async def send_email(
    deal_room_id: uuid.UUID,
    report_id: uuid.UUID,
    body: QASendEmailRequest,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> dict:
    dr_repo = DealRoomRepository(session, current_user.tenant_id, current_user.id)
    deal_room = await dr_repo.get_by_id(deal_room_id)
    if deal_room is None:
        raise HTTPException(404, "Deal room not found")

    qa_repo = ManagementQuestionRepository(session, current_user.tenant_id)
    grouped = await qa_repo.list_by_report_grouped(report_id)
    all_questions = [q for qs in grouped.values() for q in qs]
    if not all_questions:
        raise HTTPException(422, "No questions to send")

    sent_at = await send_qa_email(
        to=body.recipient_email,
        deal_room_name=deal_room.name,
        questions=all_questions,
    )

    await log_event(
        session=session,
        actor_id=current_user.id,
        actor_email=current_user.email,
        actor_role=current_user.role,
        tenant_id=current_user.tenant_id,
        action=AuditAction.QA_EMAIL_SENT,
        resource_type="report",
        resource_id=report_id,
        deal_room_id=deal_room_id,
        metadata={"recipient": body.recipient_email, "sent_at": sent_at.isoformat()},
        request=request,
    )
    await session.commit()
    return {"sent_at": sent_at.isoformat(), "recipient": body.recipient_email}


# ── PATCH /api/v1/management-questions/{id}/answer ───────────────────────────

_mq_router = APIRouter(prefix="/api/v1/management-questions", tags=["management-qa"])


@_mq_router.patch("/{question_id}/answer", response_model=ManagementQuestionResponse)
async def record_answer(
    question_id: uuid.UUID,
    body: QAAnswerPatch,
    request: Request,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> ManagementQuestionResponse:
    moderation = await moderate_content(body.answer_notes)
    if moderation.flagged:
        await log_event(
            session=session,
            actor_id=current_user.id,
            actor_email=current_user.email,
            actor_role=current_user.role,
            tenant_id=current_user.tenant_id,
            action=AuditAction.GUARDRAIL_CONTENT_FLAGGED,
            resource_type="management_question",
            resource_id=question_id,
            metadata={"categories": moderation.categories, "user_id": str(current_user.id)},
            request=request,
        )
        await session.commit()
        raise HTTPException(422, f"Content flagged: {moderation.categories}")

    qa_repo = ManagementQuestionRepository(session, current_user.tenant_id)
    q = await qa_repo.record_answer(
        question_id=question_id,
        answer_notes=body.answer_notes,
        answered_by=current_user.id,
    )
    if q is None:
        raise HTTPException(404, "Question not found")
    await session.commit()
    return ManagementQuestionResponse.model_validate(q)
