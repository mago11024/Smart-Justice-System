"""文档上传 & AI 分析路由"""
import os, uuid, json
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, Depends, BackgroundTasks, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app import models
from app.schemas import DocumentResponse, DocumentUploadResponse
from app.services.ai_service import analyze_document, extract_text, match_to_case

UPLOAD_DIR = "uploads"
router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    case_id: int = Form(...),
    db: Session = Depends(get_db),
):
    os.makedirs(f"{UPLOAD_DIR}/{case_id}", exist_ok=True)
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "txt"
    stored_name = f"{uuid.uuid4().hex}.{ext}"
    file_path = f"{UPLOAD_DIR}/{case_id}/{stored_name}"

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    doc = models.CaseDocument(
        case_id=case_id, filename=file.filename, file_path=file_path,
        file_type=ext, file_size=len(content), ai_analysis_status="pending"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    background_tasks.add_task(_run_analysis, doc.id, file_path, ext)

    return {"document_id": doc.id, "status": "pending"}


@router.get("/ingest-tasks")
def list_ingest_tasks(
    status: str = Query(None),
    db: Session = Depends(get_db),
):
    """列出所有智能收件任务（case_id 为空的文档）"""
    q = db.query(models.CaseDocument).filter(models.CaseDocument.case_id == None)
    if status:
        q = q.filter(models.CaseDocument.ai_analysis_status == status)
    tasks = q.order_by(models.CaseDocument.uploaded_at.desc()).limit(100).all()

    return [
        {
            "id": t.id, "filename": t.filename, "file_type": t.file_type or "", "file_size": t.file_size or 0,
            "ai_analysis_status": t.ai_analysis_status,
            "ai_extracted_stage": t.ai_extracted_stage, "ai_extracted_cause": t.ai_extracted_cause,
            "ai_extracted_parties": None,
            "ai_extracted_deadline": str(t.ai_extracted_deadline) if t.ai_extracted_deadline else None,
            "ai_extracted_court_date": t.ai_extracted_court_date.isoformat() if t.ai_extracted_court_date else None,
            "ai_raw_response": (t.ai_raw_response or "")[:200] if t.ai_raw_response else None,
            "ai_match_result": _parse_match_preview(t.ai_match_result),
            "ai_progress": t.ai_progress or "",
            "uploaded_at": t.uploaded_at.isoformat(),
        }
        for t in tasks
    ]


@router.get("/ingest-tasks/count")
def ingest_task_counts(db: Session = Depends(get_db)):
    """轻量计数，供侧边栏角标使用，不返回大文本"""
    from sqlalchemy import func
    q = db.query(
        models.CaseDocument.ai_analysis_status,
        func.count(models.CaseDocument.id)
    ).filter(models.CaseDocument.case_id == None).group_by(models.CaseDocument.ai_analysis_status).all()
    counts = {row[0]: row[1] for row in q}
    return {
        "active": counts.get("pending", 0) + counts.get("processing", 0),
        "pending": counts.get("pending", 0),
        "processing": counts.get("processing", 0),
        "completed": counts.get("completed", 0),
        "failed": counts.get("failed", 0),
    }


@router.get("/ingest-tasks/{task_id}/text")
def get_ingest_text(task_id: int, db: Session = Depends(get_db)):
    """返回任务对应文件的原始提取文本（供任务中心预览）"""
    doc = db.query(models.CaseDocument).filter(models.CaseDocument.id == task_id).first()
    if not doc:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="文档不存在")

    file_path = doc.file_path
    if not file_path or not os.path.exists(file_path):
        return {"text": "", "length": 0}

    ext = doc.file_type or file_path.rsplit(".", 1)[-1]
    text = extract_text(file_path, ext)
    return {"text": text, "length": len(text)}


@router.get("/smart-ingest/result/{doc_id}")
def get_smart_ingest_result(doc_id: int, db: Session = Depends(get_db)):
    """获取智能收件完整结果（供任务中心弹窗使用）"""
    doc = db.query(models.CaseDocument).filter(models.CaseDocument.id == doc_id).first()
    if not doc:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="文档不存在")

    parties = {}
    if doc.ai_extracted_parties:
        try: parties = json.loads(doc.ai_extracted_parties)
        except Exception: pass

    raw = {}
    if doc.ai_raw_response:
        try: raw = json.loads(doc.ai_raw_response)
        except Exception: pass

    extracted = {
        "success": doc.ai_analysis_status == "completed",
        "document_type": raw.get("document_type"),
        "stage": doc.ai_extracted_stage,
        "plaintiff": parties.get("plaintiff"),
        "defendant": parties.get("defendant"),
        "cause_of_action": doc.ai_extracted_cause,
        "deadline": str(doc.ai_extracted_deadline) if doc.ai_extracted_deadline else None,
        "court_date": doc.ai_extracted_court_date.isoformat() if doc.ai_extracted_court_date else None,
        "key_facts": raw.get("key_facts"),
        "next_action": raw.get("next_action"),
        "urgency": raw.get("urgency"),
        "confidence": raw.get("confidence", 0),
        "raw": doc.ai_raw_response or "",
    }

    match_result = {"matched_case": None, "candidates": []}
    if doc.ai_match_result:
        try: match_result = json.loads(doc.ai_match_result)
        except Exception: pass
    elif doc.ai_analysis_status == "completed":
        try:
            active = db.query(models.Case).filter(
                models.Case.is_archived == False, models.Case.stage != "closed"
            ).all()
            match_result["candidates"] = [{"id": c.id, "case_name": c.case_name} for c in active[:10]]
        except Exception: pass

    return {
        "document_id": doc.id, "status": doc.ai_analysis_status,
        "extracted": extracted,
        "matched_case": match_result.get("matched_case"),
        "candidates": match_result.get("candidates", []),
    }


@router.get("/{doc_id}", response_model=DocumentResponse)
def get_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(models.CaseDocument).filter(models.CaseDocument.id == doc_id).first()
    if not doc:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="文档不存在")
    return doc


@router.post("/{doc_id}/reanalyze")
def reanalyze(doc_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    doc = db.query(models.CaseDocument).filter(models.CaseDocument.id == doc_id).first()
    if not doc:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="文档不存在")
    doc.ai_analysis_status = "pending"
    db.commit()
    background_tasks.add_task(_run_analysis, doc.id, doc.file_path, doc.file_type)
    return {"document_id": doc.id, "status": "pending"}


# ===== 智能收件：上传 + AI 匹配 =====
@router.post("/smart-ingest")
async def smart_ingest(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """上传文档 → AI 提取信息 → 匹配已有案件"""
    os.makedirs(f"{UPLOAD_DIR}/_inbox", exist_ok=True)
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "txt"
    stored_name = f"{uuid.uuid4().hex}.{ext}"
    file_path = f"{UPLOAD_DIR}/_inbox/{stored_name}"

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    doc = models.CaseDocument(
        case_id=None, filename=file.filename, file_path=file_path,
        file_type=ext, file_size=len(content), ai_analysis_status="processing"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # async 端点直接用 await，不用 asyncio_run
    try:
        text = extract_text(file_path, ext)
        if not text.strip():
            doc.ai_analysis_status = "failed"
            doc.ai_raw_response = "文件内容为空或无法提取文本"
            db.commit()
            return {"document_id": doc.id, "status": "failed", "extracted": {}, "matched_case": None, "candidates": []}

        extracted = await analyze_document(text)

        if extracted.get("success"):
            doc.ai_analysis_status = "completed"
            doc.ai_extracted_stage = extracted.get("stage")
            doc.ai_extracted_cause = extracted.get("cause_of_action")
            doc.ai_extracted_parties = json.dumps({
                "plaintiff": extracted.get("plaintiff"),
                "defendant": extracted.get("defendant"),
            }, ensure_ascii=False)
            if extracted.get("deadline"):
                try:
                    doc.ai_extracted_deadline = datetime.strptime(extracted["deadline"], "%Y-%m-%d").date()
                except Exception:
                    pass
            if extracted.get("court_date"):
                try:
                    doc.ai_extracted_court_date = datetime.strptime(
                        extracted["court_date"].replace("T", " ")[:16], "%Y-%m-%d %H:%M"
                    )
                except Exception:
                    pass
            doc.ai_raw_response = extracted.get("raw", "")

            active = db.query(models.Case).filter(
                models.Case.is_archived == False, models.Case.stage != "closed"
            ).all()
            cases_list = [
                {"id": c.id, "case_name": c.case_name, "plaintiff": c.plaintiff or "",
                 "defendant": c.defendant or "", "cause_of_action": c.cause_of_action or ""}
                for c in active
            ]
            match = await match_to_case(extracted, cases_list)
            matched_case = None
            if match.get("matched_id"):
                for c in active:
                    if c.id == match["matched_id"]:
                        matched_case = {"id": c.id, "case_name": c.case_name, "confidence": match.get("confidence", 0)}
                        break

            db.commit()
            return {
                "document_id": doc.id, "status": "completed",
                "extracted": extracted,
                "matched_case": matched_case,
                "candidates": [{"id": c.id, "case_name": c.case_name} for c in active[:10]]
            }
        else:
            doc.ai_analysis_status = "failed"
            doc.ai_raw_response = extracted.get("raw", extracted.get("error", ""))
            db.commit()
            return {"document_id": doc.id, "status": "failed", "extracted": extracted, "matched_case": None, "candidates": []}

    except Exception as e:
        import logging
        logging.getLogger("documents").exception("smart_ingest failed")
        doc.ai_analysis_status = "failed"
        doc.ai_raw_response = str(e)
        db.commit()
        return {"document_id": doc.id, "status": "failed", "extracted": {}, "matched_case": None, "candidates": []}


@router.post("/smart-ingest/confirm")
def confirm_ingest(data: dict, db: Session = Depends(get_db)):
    """确认文档归属：link 关联已有案件，new 创建新案件"""
    doc = db.query(models.CaseDocument).filter(models.CaseDocument.id == data["document_id"]).first()
    if not doc:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="文档不存在")

    if data["action"] == "link":
        case_id = data.get("case_id")
        if not case_id:
            raise HTTPException(status_code=400, detail="缺少 case_id")
        doc.case_id = case_id
        new_dir = f"{UPLOAD_DIR}/{case_id}"
        os.makedirs(new_dir, exist_ok=True)
        new_path = f"{new_dir}/{doc.filename}"
        try:
            os.rename(doc.file_path, new_path)
            doc.file_path = new_path
        except Exception:
            pass
        db.commit()
        return {"ok": True, "action": "linked", "case_id": case_id}

    elif data["action"] == "new":
        nc = data.get("new_case", {})

        # 从文档 AI 分析结果中读取扩展字段
        notes_parts = []
        try:
            raw = json.loads(doc.ai_raw_response or "{}")
            if raw.get("court"): notes_parts.append(f"管辖法院: {raw['court']}")
            if raw.get("judge"): notes_parts.append(f"审判员: {raw['judge']}")
            if raw.get("key_facts"): notes_parts.append(raw["key_facts"])
            if raw.get("next_action"): notes_parts.append(f"建议: {raw['next_action']}")
            if raw.get("amount_in_dispute"): notes_parts.append(f"标的: {raw['amount_in_dispute']}元")
        except Exception:
            pass

        case = models.Case(
            case_name=nc.get("case_name", "新案件"),
            case_number=nc.get("case_number", ""),
            plaintiff=nc.get("plaintiff", ""),
            defendant=nc.get("defendant", ""),
            cause_of_action=nc.get("cause_of_action", ""),
            stage=nc.get("stage", "consultation"),
            deadline=nc.get("deadline"),
            court_date=nc.get("court_date"),
            notes="\n".join(notes_parts),
        )
        db.add(case)
        db.flush()
        doc.case_id = case.id
        new_dir = f"{UPLOAD_DIR}/{case.id}"
        os.makedirs(new_dir, exist_ok=True)
        new_path = f"{new_dir}/{doc.filename}"
        try:
            os.rename(doc.file_path, new_path)
            doc.file_path = new_path
        except Exception:
            pass
        db.add(models.CaseLog(case_id=case.id, action="created", new_value=case.stage, note="AI 智能收件创建"))
        db.commit()
        return {"ok": True, "action": "created", "case_id": case.id}

    raise HTTPException(status_code=400, detail="无效的 action")


# ===== 异步智能收件 =====
@router.post("/smart-ingest/async")
async def smart_ingest_async(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """异步智能收件：立即返回，后台处理"""
    os.makedirs(f"{UPLOAD_DIR}/_inbox", exist_ok=True)
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "txt"
    stored_name = f"{uuid.uuid4().hex}.{ext}"
    file_path = f"{UPLOAD_DIR}/_inbox/{stored_name}"

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    doc = models.CaseDocument(
        case_id=None, filename=file.filename, file_path=file_path,
        file_type=ext, file_size=len(content), ai_analysis_status="pending"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    import threading
    threading.Thread(
        target=_run_smart_ingest, args=(doc.id, file_path, ext),
        daemon=True
    ).start()
    return {"document_id": doc.id, "status": "pending"}


def _run_smart_ingest(doc_id: int, file_path: str, ext: str):
    """后台任务：OCR → AI 分析 → 匹配 → 通知，每步更新 ai_progress"""
    import logging as _log
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        doc = db.query(models.CaseDocument).filter(models.CaseDocument.id == doc_id).first()
        if not doc: return

        doc.ai_analysis_status = "processing"
        doc.ai_progress = "正在提取文本…"
        db.commit()

        text = extract_text(file_path, ext)
        if not text.strip():
            doc.ai_analysis_status = "failed"
            doc.ai_raw_response = "文件内容为空或无法提取文本"
            doc.ai_progress = "文本提取失败"
            db.commit()
            _create_analysis_notification(db, doc, "failed")
            return

        doc.ai_progress = f"文本提取完成 ({len(text)} 字符)，正在 AI 分析…"
        db.commit()

        result = asyncio_run(analyze_document(text))

        if result.get("success"):
            doc.ai_analysis_status = "completed"
            doc.ai_extracted_stage = result.get("stage")
            doc.ai_extracted_cause = result.get("cause_of_action")
            doc.ai_extracted_parties = json.dumps({
                "plaintiff": result.get("plaintiff"),
                "defendant": result.get("defendant"),
            }, ensure_ascii=False)
            if result.get("deadline"):
                try:
                    doc.ai_extracted_deadline = datetime.strptime(result["deadline"], "%Y-%m-%d").date()
                except Exception:
                    pass
            if result.get("court_date"):
                try:
                    doc.ai_extracted_court_date = datetime.strptime(
                        result["court_date"].replace("T", " ")[:16], "%Y-%m-%d %H:%M"
                    )
                except Exception:
                    pass
            doc.ai_raw_response = result.get("raw", "")
            doc.ai_progress = "AI 分析完成，正在匹配已有案件…"
            db.commit()

            # 案件匹配
            active = db.query(models.Case).filter(
                models.Case.is_archived == False, models.Case.stage != "closed"
            ).all()
            cases_list = [
                {"id": c.id, "case_name": c.case_name, "plaintiff": c.plaintiff or "",
                 "defendant": c.defendant or "", "cause_of_action": c.cause_of_action or "",
                 "case_number": c.case_number or "", "stage": c.stage}
                for c in active
            ]
            match = asyncio_run(match_to_case(result, cases_list))
            matched_case = None
            candidates = [{"id": c.id, "case_name": c.case_name} for c in active[:10]]
            if match.get("matched_id"):
                for c in active:
                    if c.id == match["matched_id"]:
                        matched_case = {"id": c.id, "case_name": c.case_name, "confidence": match.get("confidence", 0)}
                        break
            doc.ai_match_result = json.dumps({
                "matched_case": matched_case,
                "candidates": candidates,
                "reason": match.get("reason", ""),
                "confidence": match.get("confidence", 0),
            }, ensure_ascii=False)
            doc.ai_progress = "分析完成"
            db.commit()
            _create_analysis_notification(db, doc, "completed")
        else:
            doc.ai_analysis_status = "failed"
            doc.ai_raw_response = result.get("raw", result.get("error", ""))
            doc.ai_progress = "AI 分析失败"
            db.commit()
            _create_analysis_notification(db, doc, "failed")
    except Exception as e:
        import traceback
        err_msg = f"{e}\n{traceback.format_exc()}"
        _log.getLogger("documents").error("_run_smart_ingest failed: %s", err_msg[:500])
        try:
            doc = db.query(models.CaseDocument).filter(models.CaseDocument.id == doc_id).first()
            if doc:
                doc.ai_analysis_status = "failed"
                doc.ai_raw_response = err_msg[:2000]  # 截断保存
                doc.ai_progress = "处理异常"
                db.commit()
                _create_analysis_notification(db, doc, "failed")
        except Exception as inner_e:
            _log.getLogger("documents").error("Failed to save error: %s", inner_e)
    finally:
        db.close()


def _create_analysis_notification(db, doc, status: str):
    """为分析完成/失败创建通知"""
    suffix = "完成，点击查看结果" if status == "completed" else "失败"
    notif = models.Notification(
        case_id=None,
        document_id=doc.id,
        type="analysis_complete",
        message=f"文档「{doc.filename}」AI 分析{suffix}"
    )
    db.add(notif)
    db.commit()


def _parse_match_preview(match_json: str) -> dict | None:
    """提取匹配预览 — 只保留 matched_case, 去掉 candidates 大数组"""
    if not match_json:
        return None
    try:
        m = json.loads(match_json)
        mc = m.get("matched_case")
        return {"has_match": mc is not None, "case_name": mc.get("case_name", "") if mc else ""}
    except Exception:
        return None


# ===== 知识搜索 =====
@router.get("/search")
def search_documents(q: str = "", db: Session = Depends(get_db)):
    """全文搜索文档（按文件名/案件名/当事人）"""
    from sqlalchemy import or_
    kw = f"%{q}%"
    docs = db.query(models.CaseDocument).filter(
        or_(
            models.CaseDocument.filename.like(kw),
            models.CaseDocument.ai_raw_response.like(kw),
        )
    ).order_by(models.CaseDocument.uploaded_at.desc()).limit(30).all()

    results = []
    for d in docs:
        case = d.case
        results.append({
            "id": d.id,
            "case_id": d.case_id,
            "case_name": case.case_name if case else "未关联案件",
            "case_number": case.case_number if case else "",
            "filename": d.filename,
            "file_type": d.file_type or "",
            "file_size": d.file_size or 0,
            "ai_analysis_status": d.ai_analysis_status,
            "uploaded_at": d.uploaded_at,
            "snippet": (d.ai_raw_response or "")[:200],
        })
    return results


def _run_analysis(doc_id: int, file_path: str, ext: str):
    """后台任务（同步函数）—— 用 asyncio_run 桥接异步引擎"""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        doc = db.query(models.CaseDocument).filter(models.CaseDocument.id == doc_id).first()
        if not doc:
            return
        doc.ai_analysis_status = "processing"
        db.commit()

        text = extract_text(file_path, ext)
        result = asyncio_run(analyze_document(text))

        if result.get("success"):
            doc.ai_analysis_status = "completed"
            doc.ai_extracted_stage = result.get("stage")
            doc.ai_extracted_parties = json.dumps({
                "plaintiff": result.get("plaintiff"),
                "defendant": result.get("defendant")
            }, ensure_ascii=False)
            doc.ai_extracted_cause = result.get("cause_of_action")
            if result.get("deadline"):
                try:
                    doc.ai_extracted_deadline = datetime.strptime(result["deadline"], "%Y-%m-%d").date()
                except Exception:
                    pass
            if result.get("court_date"):
                try:
                    doc.ai_extracted_court_date = datetime.strptime(result["court_date"], "%Y-%m-%dT%H:%M")
                except Exception:
                    try:
                        doc.ai_extracted_court_date = datetime.strptime(result["court_date"], "%Y-%m-%dT%H:%M:%S")
                    except Exception:
                        pass
            doc.ai_raw_response = result.get("raw", "")
        else:
            doc.ai_analysis_status = "failed"
            doc.ai_raw_response = result.get("raw", result.get("error", ""))
        db.commit()
    except Exception as e:
        try:
            doc = db.query(models.CaseDocument).filter(models.CaseDocument.id == doc_id).first()
            if doc:
                doc.ai_analysis_status = "failed"
                doc.ai_raw_response = str(e)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


def asyncio_run(coro):
    """在同步函数中运行异步协程"""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 当前线程已有运行中的 loop，用 nest_asyncio 或新建线程
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(_run_in_new_loop, coro)
                return future.result(timeout=120)
    except RuntimeError:
        pass
    return _run_in_new_loop(coro)


def _run_in_new_loop(coro):
    """在新事件循环中运行协程"""
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        loop.close()
