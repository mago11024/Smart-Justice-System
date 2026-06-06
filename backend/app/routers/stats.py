"""统计路由"""
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import models

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("")
def get_stats(db: Session = Depends(get_db)):
    today = date.today()
    three_days = today + timedelta(days=3)
    week_later = today + timedelta(days=7)
    two_weeks = today + timedelta(days=14)
    one_month = today + timedelta(days=30)

    active_q = db.query(models.Case).filter(
        models.Case.is_archived == False, models.Case.stage != "closed"
    )
    total = active_q.count()

    # 5 级紧急度
    overdue = db.query(models.Case).filter(
        models.Case.is_archived == False, models.Case.stage != "closed",
        models.Case.deadline.isnot(None), models.Case.deadline < today
    ).count()

    due_3_days = db.query(models.Case).filter(
        models.Case.is_archived == False, models.Case.stage != "closed",
        models.Case.deadline.isnot(None),
        models.Case.deadline >= today, models.Case.deadline <= three_days
    ).count()

    due_7_days = db.query(models.Case).filter(
        models.Case.is_archived == False, models.Case.stage != "closed",
        models.Case.deadline.isnot(None),
        models.Case.deadline > three_days, models.Case.deadline <= week_later
    ).count()

    due_14_days = db.query(models.Case).filter(
        models.Case.is_archived == False, models.Case.stage != "closed",
        models.Case.deadline.isnot(None),
        models.Case.deadline > week_later, models.Case.deadline <= two_weeks
    ).count()

    due_30_days = db.query(models.Case).filter(
        models.Case.is_archived == False, models.Case.stage != "closed",
        models.Case.deadline.isnot(None),
        models.Case.deadline > two_weeks, models.Case.deadline <= one_month
    ).count()

    due_soon = due_3_days + due_7_days  # 向后兼容

    by_stage = {
        s: db.query(models.Case).filter(
            models.Case.is_archived == False, models.Case.stage == s
        ).count()
        for s in ["consultation", "document_prep", "court_appearance", "awaiting_result", "closed"]
    }

    week_court = db.query(models.Case).filter(
        models.Case.is_archived == False,
        models.Case.court_date >= datetime.combine(today, datetime.min.time()),
        models.Case.court_date <= datetime.combine(today + timedelta(days=7), datetime.max.time())
    ).count()

    return {
        "total_active": total,
        "overdue_count": overdue,
        "due_3_days_count": due_3_days,
        "due_7_days_count": due_7_days,
        "due_14_days_count": due_14_days,
        "due_30_days_count": due_30_days,
        "due_soon_count": due_soon,
        "by_stage": by_stage,
        "this_week_court": week_court,
    }
