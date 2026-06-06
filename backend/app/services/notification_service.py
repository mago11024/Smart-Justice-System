"""提醒/预警业务逻辑"""
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from app import models


def generate_notifications(db: Session):
    """扫描全部活跃案件，生成超期/即将到期/明日开庭提醒"""
    today = date.today()
    week_later = today + timedelta(days=7)
    yesterday = today - timedelta(days=1)

    active = db.query(models.Case).filter(
        models.Case.is_archived == False,
        models.Case.stage != "closed"
    ).all()

    generated = 0
    for case in active:
        # 超期提醒
        if case.deadline and case.deadline <= yesterday:
            exists = db.query(models.Notification).filter(
                models.Notification.case_id == case.id,
                models.Notification.type == "overdue",
                models.Notification.created_at >= datetime.utcnow().replace(hour=0, minute=0, second=0)
            ).first()
            if not exists:
                d = (today - case.deadline).days
                db.add(models.Notification(
                    case_id=case.id, type="overdue",
                    message=f"「{case.case_name}」已超期 {d} 天"
                ))
                generated += 1

        # 即将到期提醒
        if case.deadline and today <= case.deadline <= week_later:
            exists = db.query(models.Notification).filter(
                models.Notification.case_id == case.id,
                models.Notification.type == "due_soon"
            ).first()
            if not exists:
                d = (case.deadline - today).days
                db.add(models.Notification(
                    case_id=case.id, type="due_soon",
                    message=f"「{case.case_name}」还有 {d} 天到期"
                ))
                generated += 1

        # 明日开庭提醒
        if case.court_date:
            court_day = case.court_date.date()
            if court_day == today + timedelta(days=1) or court_day == today:
                label = "今天" if court_day == today else "明天"
                exists = db.query(models.Notification).filter(
                    models.Notification.case_id == case.id,
                    models.Notification.type == "court_tomorrow"
                ).first()
                if not exists:
                    db.add(models.Notification(
                        case_id=case.id, type="court_tomorrow",
                        message=f"「{case.case_name}」{label}开庭"
                    ))
                    generated += 1

    db.commit()
    return generated
