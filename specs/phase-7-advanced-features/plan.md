# Phase 7 — Advanced Features
## plan.md

### New Files
```
backend/app/routers/
  comparison.py       GET /compare, GET /search
  permissions.py      PATCH and GET document permissions
```

### Comparison Endpoint
```python
@router.get("/deal-rooms/compare")
async def compare_deal_rooms(ids: str, ...):  # ids = "uuid1,uuid2"
    id_list = [UUID(i.strip()) for i in ids.split(",")]
    assert len(id_list) == 2
    rooms = [await deal_room_repo.get_by_id(id) for id in id_list]
    # Raises 404 if either is None (membership-gated via repo)
    reports = [await report_repo.get_latest_approved(room.id) for room in rooms]
    return {"deal_rooms": [build_comparison_obj(room, report) for room, report in zip(rooms, reports)]}
```

### Precedent Search
Embed the query, run pgvector search over `report_items` where `section_type='executive_summary'` filtered by tenant_id. Return parent deal_room info.

### Permission Management
```python
@router.patch("/documents/{doc_id}/permissions")
async def update_permissions(doc_id, body: PermissionUpdateRequest, ...):
    # Assert caller is owner or senior_analyst in the deal room
    # Delete existing rows for this document
    # Insert new rows from body.grants
    # Log permission.document_restricted
    # If mode="default": re-run grant_default_permissions()
```

---