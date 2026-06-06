"""律师路由"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app.schemas import LawyerResponse

router = APIRouter(prefix="/api/lawyers", tags=["lawyers"])


@router.get("", response_model=list[LawyerResponse])
def list_lawyers(db: Session = Depends(get_db)):
    lawyers = db.query(models.Lawyer).filter(models.Lawyer.is_active == True).all()
    return [
        {
            "id": l.id, "name": l.name, "initials": l.initials,
            "role": l.role, "email": l.email or "", "phone": l.phone or "",
            "is_active": l.is_active,
            "case_count": db.query(models.Case).filter(
                models.Case.lawyer_id == l.id, models.Case.stage != "closed",
                models.Case.is_archived == False
            ).count()
        }
        for l in lawyers
    ]


@router.get("/{lawyer_id}/cases")
def lawyer_cases(lawyer_id: int, db: Session = Depends(get_db)):
    from app.services.case_service import get_cases
    return get_cases(db, lawyer_id=lawyer_id)
