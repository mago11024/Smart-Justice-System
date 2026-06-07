"""案件业务逻辑：CRUD、阶段推进、批量操作、搜索筛选"""
import re
import unicodedata
from datetime import datetime, date
from typing import Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from fastapi import HTTPException
from app import models
from app.utils.stage_utils import get_next_stage, compute_overdue_status, days_in_stage, STAGE_LABELS


def case_to_dict(case: models.Case) -> dict:
    lawyer = case.lawyer
    status, days = compute_overdue_status(case.deadline)
    return {
        "id": case.id,
        "case_number": case.case_number,
        "case_name": case.case_name,
        "plaintiff": case.plaintiff or "",
        "defendant": case.defendant or "",
        "cause_of_action": case.cause_of_action or "",
        "stage": case.stage,
        "stage_label": STAGE_LABELS.get(case.stage, case.stage),
        "stage_entered_at": case.stage_entered_at,
        "days_in_stage": days_in_stage(case.stage_entered_at),
        "deadline": case.deadline,
        "court_date": case.court_date,
        "overdue_status": status,
        "overdue_days": days,
        "lawyer_id": case.lawyer_id,
        "lawyer_name": lawyer.name if lawyer else None,
        "lawyer_initials": lawyer.initials if lawyer else None,
        "outcome": case.outcome,
        "outcome_note": case.outcome_note,
        "notes": case.notes or "",
        "core_summary": case.core_summary or "",
        "created_at": case.created_at,
        "updated_at": case.updated_at,
    }


def get_cases(
    db: Session,
    search: Optional[str] = None,
    stage: Optional[str] = None,
    lawyer_id: Optional[int] = None,
    overdue: bool = False,
):
    q = db.query(models.Case).filter(models.Case.is_archived == False)

    if search:
        kw = f"%{search}%"
        q = q.filter(or_(
            models.Case.case_number.like(kw),
            models.Case.case_name.like(kw),
            models.Case.plaintiff.like(kw),
            models.Case.defendant.like(kw),
            models.Case.cause_of_action.like(kw),
        ))

    if stage:
        q = q.filter(models.Case.stage == stage)

    if lawyer_id:
        q = q.filter(models.Case.lawyer_id == lawyer_id)

    cases = q.order_by(models.Case.updated_at.desc()).all()

    if overdue:
        today = date.today()
        cases = [c for c in cases if c.deadline and c.deadline < today and c.stage != "closed"]

    return [case_to_dict(c) for c in cases]


def _normalize_search_text(value: str | None) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    return re.sub(r"[\s\(\)\[\]\{\}<>,.，。:：;；、/\\\-_\|]+", "", text)


def _contains_keyword(value: str | None, keyword: str) -> bool:
    raw_value = unicodedata.normalize("NFKC", str(value or "")).lower()
    raw_keyword = unicodedata.normalize("NFKC", str(keyword or "")).lower()
    normalized_keyword = _normalize_search_text(raw_keyword)
    return raw_keyword in raw_value or (
        bool(normalized_keyword)
        and normalized_keyword in _normalize_search_text(raw_value)
    )


def _make_snippet(text: str | None, keyword: str, size: int = 90) -> str:
    if not text:
        return ""
    text = " ".join(str(text).split())
    idx = text.lower().find(keyword.lower())
    if idx < 0:
        return text[:size * 2]
    start = max(0, idx - size)
    end = min(len(text), idx + len(keyword) + size)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(text) else ""
    return f"{prefix}{text[start:end]}{suffix}"


def search_existing_cases(db: Session, keyword: str, limit: int = 50) -> list[dict]:
    """按当事人、案号、案由和文书内容检索现有案件。"""
    keyword = (keyword or "").strip()
    if not keyword:
        return []

    candidates = db.query(models.Case).options(
        joinedload(models.Case.documents)
    ).filter(
        models.Case.is_archived == False
    ).order_by(models.Case.updated_at.desc()).all()

    results = []
    for case in candidates:
        matched_fields = []
        if _contains_keyword(case.plaintiff, keyword) or _contains_keyword(case.defendant, keyword):
            matched_fields.append("当事人")
        if _contains_keyword(case.case_number, keyword):
            matched_fields.append("案号")
        if _contains_keyword(case.cause_of_action, keyword):
            matched_fields.append("案由")
        if _contains_keyword(case.case_name, keyword):
            matched_fields.append("案件名称")
        if _contains_keyword(case.notes, keyword) or _contains_keyword(case.core_summary, keyword):
            matched_fields.append("案件备注")

        document_matches = []
        for doc in sorted(case.documents, key=lambda d: d.uploaded_at or datetime.min, reverse=True):
            doc_parts = [
                doc.filename or "",
                doc.ai_raw_response or "",
                doc.ai_extracted_cause or "",
                doc.ai_extracted_parties or "",
            ]
            if any(_contains_keyword(part, keyword) for part in doc_parts):
                document_matches.append({
                    "id": doc.id,
                    "filename": doc.filename,
                    "file_type": doc.file_type or "",
                    "uploaded_at": doc.uploaded_at,
                    "snippet": _make_snippet(doc.ai_raw_response or doc.filename, keyword),
                })

        if document_matches:
            matched_fields.append("文书内容")

        if not matched_fields:
            continue

        data = case_to_dict(case)
        data.update({
            "matched_fields": list(dict.fromkeys(matched_fields)),
            "document_matches": document_matches[:3],
            "snippet": (
                _make_snippet(case.core_summary, keyword)
                or _make_snippet(case.notes, keyword)
                or (document_matches[0]["snippet"] if document_matches else "")
            ),
        })
        results.append(data)
        if len(results) >= limit:
            break

    return results


def create_case(db: Session, data: dict) -> models.Case:
    case = models.Case(**data)
    db.add(case)
    db.flush()

    db.add(models.CaseLog(
        case_id=case.id,
        action="created",
        new_value=case.stage,
        note="创建案件"
    ))
    db.commit()
    db.refresh(case)
    return case_to_dict(case)


def update_case(db: Session, case_id: int, data: dict) -> dict:
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="案件不存在")

    updates = {k: v for k, v in data.items() if v is not None}
    for k, v in updates.items():
        setattr(case, k, v)

    db.commit()
    db.refresh(case)
    return case_to_dict(case)


def delete_case(db: Session, case_id: int):
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="案件不存在")
    case.is_archived = True
    db.commit()


def advance_case(db: Session, case_id: int, note: str = "") -> dict:
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="案件不存在")

    next_stage = get_next_stage(case.stage)
    if not next_stage:
        raise HTTPException(status_code=400, detail="已是最终阶段，无法继续推进")

    old = case.stage
    case.stage = next_stage
    case.stage_entered_at = datetime.utcnow()

    db.add(models.CaseLog(
        case_id=case.id,
        action="stage_changed",
        old_value=old,
        new_value=next_stage,
        note=note or f"推进至{STAGE_LABELS.get(next_stage, next_stage)}"
    ))
    db.commit()
    db.refresh(case)
    return case_to_dict(case)


def batch_advance(db: Session, case_ids: list[int]) -> dict:
    succeeded, skipped, failed = [], [], []
    for cid in case_ids:
        try:
            advance_case(db, cid)
            succeeded.append(cid)
        except HTTPException as e:
            if e.status_code == 400:
                skipped.append(cid)
            else:
                failed.append(cid)
        except Exception:
            failed.append(cid)
    return {"succeeded": succeeded, "skipped": skipped, "failed": failed}


def assign_lawyer(db: Session, case_id: int, lawyer_id: int) -> dict:
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="案件不存在")

    lawyer = db.query(models.Lawyer).filter(models.Lawyer.id == lawyer_id).first()
    if not lawyer:
        raise HTTPException(status_code=404, detail="律师不存在")

    old = case.lawyer_id
    case.lawyer_id = lawyer_id

    db.add(models.CaseLog(
        case_id=case.id,
        action="lawyer_assigned",
        old_value=str(old) if old else "",
        new_value=str(lawyer_id),
        note=f"指派给{lawyer.name}"
    ))
    db.commit()
    db.refresh(case)
    return case_to_dict(case)


def batch_assign(db: Session, case_ids: list[int], lawyer_id: int) -> dict:
    lawyer = db.query(models.Lawyer).filter(models.Lawyer.id == lawyer_id).first()
    if not lawyer:
        raise HTTPException(status_code=404, detail="律师不存在")

    succeeded, failed = [], []
    for cid in case_ids:
        try:
            assign_lawyer(db, cid, lawyer_id)
            succeeded.append(cid)
        except Exception:
            failed.append(cid)
    return {"succeeded": succeeded, "failed": failed}


def get_flow_view(db: Session) -> list[dict]:
    """按阶段分组返回案件，排序与 stage_order 一致"""
    from app.utils.stage_utils import STAGE_ORDER
    all_cases = get_cases(db)
    grouped = {}
    for c in all_cases:
        s = c["stage"]
        grouped.setdefault(s, {"stage": s, "stage_label": STAGE_LABELS.get(s, s), "count": 0, "overdue_count": 0, "cases": []})
        grouped[s]["count"] += 1
        if c["overdue_status"] == "overdue":
            grouped[s]["overdue_count"] += 1
        grouped[s]["cases"].append(c)

    return [grouped[s] for s in STAGE_ORDER if s in grouped] + \
           [v for k, v in grouped.items() if k not in STAGE_ORDER]
