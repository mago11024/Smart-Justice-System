"""案件路由：CRUD + 推进 + 批量 + 分配 + 导出"""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
import csv, io
from app.database import get_db
from app import models
from app.schemas import (
    CaseCreate, CaseUpdate, AdvanceRequest, AssignRequest,
    BatchIdsRequest, BatchAssignRequest, CaseResponse, CaseDetailResponse
)
from app.services import case_service

router = APIRouter(prefix="/api/cases", tags=["cases"])


@router.get("")
def list_cases(
    search: Optional[str] = Query(None),
    stage: Optional[str] = Query(None),
    lawyer_id: Optional[int] = Query(None),
    overdue: bool = Query(False),
    view: str = Query("flow"),
    db: Session = Depends(get_db),
):
    if view == "flow":
        return case_service.get_flow_view(db)
    return case_service.get_cases(db, search, stage, lawyer_id, overdue)


@router.post("", response_model=dict)
def create(data: CaseCreate, db: Session = Depends(get_db)):
    return case_service.create_case(db, data.model_dump())


@router.get("/{case_id}", response_model=CaseDetailResponse)
def get_one(case_id: int, db: Session = Depends(get_db)):
    cases = case_service.get_cases(db)
    for c in cases:
        if c["id"] == case_id:
            # 加载文档
            doc_records = db.query(models.CaseDocument).filter(
                models.CaseDocument.case_id == case_id
            ).order_by(models.CaseDocument.uploaded_at.desc()).all()
            c["documents"] = [{
                "id": d.id, "case_id": d.case_id, "filename": d.filename,
                "file_type": d.file_type or "", "file_size": d.file_size or 0,
                "ai_analysis_status": d.ai_analysis_status,
                "ai_extracted_stage": d.ai_extracted_stage,
                "ai_extracted_parties": d.ai_extracted_parties,
                "ai_extracted_deadline": d.ai_extracted_deadline,
                "ai_extracted_cause": d.ai_extracted_cause,
                "ai_extracted_court_date": d.ai_extracted_court_date,
                "ai_raw_response": d.ai_raw_response,
                "uploaded_at": d.uploaded_at,
            } for d in doc_records]
            # 加载日志
            log_records = db.query(models.CaseLog).filter(
                models.CaseLog.case_id == case_id
            ).order_by(models.CaseLog.created_at.desc()).limit(20).all()
            c["logs"] = [{
                "id": l.id, "action": l.action, "old_value": l.old_value or "",
                "new_value": l.new_value or "", "note": l.note or "",
                "created_at": l.created_at,
            } for l in log_records]
            return c
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="案件不存在")


@router.put("/{case_id}", response_model=dict)
def update(case_id: int, data: CaseUpdate, db: Session = Depends(get_db)):
    return case_service.update_case(db, case_id, data.model_dump(exclude_none=True))


@router.delete("/{case_id}")
def delete(case_id: int, db: Session = Depends(get_db)):
    case_service.delete_case(db, case_id)
    return {"ok": True}


@router.post("/{case_id}/advance", response_model=dict)
def advance(case_id: int, data: AdvanceRequest = AdvanceRequest(), db: Session = Depends(get_db)):
    return case_service.advance_case(db, case_id, data.note)


@router.post("/batch/advance")
def batch_advance(data: BatchIdsRequest, db: Session = Depends(get_db)):
    return case_service.batch_advance(db, data.case_ids)


@router.post("/{case_id}/assign", response_model=dict)
def assign(case_id: int, data: AssignRequest, db: Session = Depends(get_db)):
    return case_service.assign_lawyer(db, case_id, data.lawyer_id)


@router.post("/batch/assign")
def batch_assign(data: BatchAssignRequest, db: Session = Depends(get_db)):
    return case_service.batch_assign(db, data.case_ids, data.lawyer_id)


@router.post("/{case_id}/log")
def add_log(case_id: int, data: dict, db: Session = Depends(get_db)):
    """添加案件操作日志（快速进展更新）"""
    note = data.get("note", "")
    if not note.strip():
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="内容不能为空")
    from app import models
    log = models.CaseLog(
        case_id=case_id, action="note", new_value="", note=note.strip()
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return {
        "id": log.id, "action": log.action, "note": log.note,
        "created_at": log.created_at,
    }


@router.post("/{case_id}/generate-core-summary")
async def generate_core_summary(case_id: int, db: Session = Depends(get_db)):
    """调用 AI 综合案件信息+文档分析结果，生成核心信息梳理"""
    import json, logging
    from app.services.ai_service import generate_core_summary as gen_cs

    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="案件不存在")

    docs = db.query(models.CaseDocument).filter(
        models.CaseDocument.case_id == case_id
    ).order_by(models.CaseDocument.uploaded_at.desc()).all()

    doc_summaries = [{
        "filename": d.filename,
        "ai_analysis_status": d.ai_analysis_status,
        "ai_extracted_stage": d.ai_extracted_stage,
        "ai_extracted_cause": d.ai_extracted_cause,
        "ai_extracted_parties": d.ai_extracted_parties,
        "ai_raw_response": d.ai_raw_response,
    } for d in docs]

    case_data = {
        "case_name": case.case_name,
        "case_number": case.case_number or "",
        "plaintiff": case.plaintiff or "",
        "defendant": case.defendant or "",
        "cause_of_action": case.cause_of_action or "",
        "stage": case.stage,
        "notes": case.notes or "",
    }

    result = await gen_cs(case_data, doc_summaries)

    if not result.get("success"):
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=result.get("error", "AI 生成失败"))

    core_summary_json = json.dumps(result["data"], ensure_ascii=False)
    case.core_summary = core_summary_json
    db.commit()

    return {"ok": True, "core_summary": result["data"]}


@router.get("/export/csv")
def export_csv(
    search: Optional[str] = Query(None),
    stage: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """导出案件列表为 CSV"""
    from app.utils.stage_utils import STAGE_LABELS
    cases = case_service.get_cases(db, search=search, stage=stage)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["案号", "案件名称", "原告", "被告", "案由", "当前阶段", "截止日期", "超期状态", "超期天数", "承办律师", "创建时间"])
    for c in cases:
        writer.writerow([
            c.get("case_number", ""),
            c.get("case_name", ""),
            c.get("plaintiff", ""),
            c.get("defendant", ""),
            c.get("cause_of_action", ""),
            STAGE_LABELS.get(c.get("stage", ""), c.get("stage", "")),
            str(c.get("deadline", "")) if c.get("deadline") else "",
            c.get("overdue_status", ""),
            c.get("overdue_days", 0),
            c.get("lawyer_name", ""),
            str(c.get("created_at", ""))[:10] if c.get("created_at") else "",
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": "attachment; filename=cases_export.csv"},
    )
