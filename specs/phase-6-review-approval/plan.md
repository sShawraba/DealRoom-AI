# Phase 6 — Review & Approval Workflow
## plan.md

### New Files
```
backend/app/
  models/annotation.py        Annotation, AnnotationReply
  models/report_approval.py   ReportApproval
  models/management_qa.py     ManagementQuestion
  schemas/annotation.py
  schemas/management_qa.py
  repositories/annotation.py
  repositories/management_qa.py
  services/
    approval_service.py   assert_can_approve(), approve_report()
    email_service.py      send_qa_email()
  routers/
    annotations.py
    management_qa.py
```

### Models
```python
annotation_type = Enum('comment','verified','disputed', name='annotation_type')
qa_category     = Enum('financial','legal','operational','strategic', name='qa_category')
qa_priority     = Enum('critical','high','medium', name='qa_priority')

class Annotation(Base, TimestampMixin):
    id, tenant_id, deal_room_id
    report_item_id = ForeignKey("report_items.id")
    author_id      = ForeignKey("users.id")
    content, type = Column(annotation_type, default="comment")
    resolved=False, resolved_by, resolved_at

class AnnotationReply(Base):
    id, tenant_id, annotation_id, author_id, content, created_at

class ReportApproval(Base):
    id, tenant_id
    report_id = ForeignKey("reports.id", unique=True)
    approved_by, approved_at, sign_off_notes, disputed_resolved_count

class ManagementQuestion(Base):
    id, tenant_id, deal_room_id, report_id
    source_item_id = ForeignKey("report_items.id", nullable=True)
    category, question, priority, answered=False, answer_notes, answered_by, answered_at
```

### Approval Service
```python
async def assert_can_approve(report_id, current_user, session):
    member = await deal_room_member_repo.get_user_role(deal_room_id, current_user.id)
    if member.role not in ("owner", "senior_analyst"):
        raise HTTPException(403, "Only senior analysts and owners can approve")
    disputed = await session.scalar(
        select(func.count(Annotation.id))
        .join(ReportItem)
        .where(ReportItem.report_id == report_id,
               Annotation.type == "disputed",
               Annotation.resolved == False)
    )
    if disputed > 0:
        raise HTTPException(409, f"{disputed} disputed annotation(s) must be resolved first")
```

### Read-Only Enforcement
In `ReportItemRepository.update()` and `AnnotationRepository.create()`:
```python
report = await self.get_report(item.report_id)
if report.status == "approved":
    raise HTTPException(409, "Report is approved and read-only")
```

### Q&A System Prompt
```
Given these due diligence findings, generate sharp management questions.
Group by: financial | legal | operational | strategic
Priority: critical | high | medium
Each question must cite source_item_id (the finding that triggered it).
Return ONLY valid JSON: {"categories": [{"name": str, "questions": [{"question": str, "priority": str, "source_item_id": str}]}]}
```

### Email Service
```python
async def send_qa_email(to: str, deal_room_name: str, questions: list[ManagementQuestion]):
    # Format questions by category into plain text email body
    # Send via aiosmtplib using SMTP_HOST/PORT/USER/PASSWORD from settings
    # Return sent timestamp
```

---