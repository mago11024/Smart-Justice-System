"""通知路由"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app.schemas import NotificationResponse
from app.services.sse_manager import sse_manager

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationResponse])
def list_notifications(
    unread_only: bool = Query(False),
    db: Session = Depends(get_db),
):
    q = db.query(models.Notification)
    if unread_only:
        q = q.filter(models.Notification.is_read == False)
    items = q.order_by(models.Notification.created_at.desc()).limit(50).all()
    return [
        {
            "id": n.id, "case_id": n.case_id,
            "case_name": n.case.case_name if n.case else "",
            "case_number": n.case.case_number if n.case else "",
            "document_id": n.document_id,
            "document_filename": n.document.filename if n.document else "",
            "type": n.type, "message": n.message,
            "is_read": n.is_read, "created_at": n.created_at
        }
        for n in items
    ]


@router.put("/{nid}/read")
def mark_read(nid: int, db: Session = Depends(get_db)):
    n = db.query(models.Notification).filter(models.Notification.id == nid).first()
    if n:
        n.is_read = True
        db.commit()
        sse_manager.broadcast("notification_changed", {})
    return {"ok": True}


@router.post("/read-all")
def read_all(db: Session = Depends(get_db)):
    db.query(models.Notification).filter(models.Notification.is_read == False).update({"is_read": True})
    db.commit()
    sse_manager.broadcast("notification_changed", {})
    return {"ok": True}


@router.get("/stats")
def notification_stats(db: Session = Depends(get_db)):
    """按类型统计未读通知数"""
    from sqlalchemy import func
    rows = (
        db.query(models.Notification.type, func.count(models.Notification.id))
        .filter(models.Notification.is_read == False)
        .group_by(models.Notification.type)
        .all()
    )
    by_type = {r[0]: r[1] for r in rows}
    total_unread = sum(by_type.values())
    total_all = db.query(models.Notification).count()
    return {
        "total_unread": total_unread,
        "total_all": total_all,
        "overdue_count": by_type.get("overdue", 0),
        "due_soon_count": by_type.get("due_soon", 0),
        "court_count": by_type.get("court_tomorrow", 0),
        "analysis_count": by_type.get("analysis_complete", 0),
    }
