"""案件业务逻辑：CRUD、阶段推进、批量操作、搜索筛选"""
from datetime import datetime, date
from typing import Optional
from sqlalchemy.orm import Session
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
