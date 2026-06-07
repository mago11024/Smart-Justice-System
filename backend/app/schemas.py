"""Pydantic 请求/响应模型"""
from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional, List


# ===== 律师 =====
class LawyerResponse(BaseModel):
    id: int
    name: str
    initials: str
    role: str
    email: str
    phone: str
    is_active: bool
    case_count: int = 0

    class Config:
        orm_mode = True


# ===== 案件 =====
class CaseCreate(BaseModel):
    case_name: str = Field(..., max_length=200)
    case_number: str = Field(..., max_length=100)
    plaintiff: Optional[str] = ""
    defendant: Optional[str] = ""
    cause_of_action: Optional[str] = ""
    stage: str = "consultation"
    deadline: Optional[date] = None
    court_date: Optional[datetime] = None
    lawyer_id: Optional[int] = None
    notes: Optional[str] = ""


class CaseUpdate(BaseModel):
    case_name: Optional[str] = None
    case_number: Optional[str] = None
    plaintiff: Optional[str] = None
    defendant: Optional[str] = None
    cause_of_action: Optional[str] = None
    deadline: Optional[date] = None
    court_date: Optional[datetime] = None
    lawyer_id: Optional[int] = None
    outcome: Optional[str] = None
    outcome_note: Optional[str] = None
    notes: Optional[str] = None
    core_summary: Optional[str] = None


class AdvanceRequest(BaseModel):
    note: Optional[str] = ""


class AssignRequest(BaseModel):
    lawyer_id: int


class BatchIdsRequest(BaseModel):
    case_ids: List[int]


class BatchAssignRequest(BaseModel):
    case_ids: List[int]
    lawyer_id: int


class CaseResponse(BaseModel):
    id: int
    case_number: str
    case_name: str
    plaintiff: str
    defendant: str
    cause_of_action: str
    stage: str
    stage_label: str
    stage_entered_at: datetime
    days_in_stage: int
    deadline: Optional[date]
    court_date: Optional[datetime]
    overdue_status: str
    overdue_days: int
    lawyer_id: Optional[int]
    lawyer_name: Optional[str]
    lawyer_initials: Optional[str]
    outcome: Optional[str]
    outcome_note: Optional[str]
    notes: str
    core_summary: Optional[str] = ""
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class CaseDetailResponse(CaseResponse):
    logs: List[dict] = []
    documents: List[dict] = []


# ===== 智能收件 =====
class SmartIngestResponse(BaseModel):
    document_id: int
    status: str  # "completed" | "failed"
    extracted: dict = {}
    matched_case: Optional[dict] = None
    candidates: List[dict] = []


class ConfirmIngestRequest(BaseModel):
    document_id: int
    action: str  # "link" | "new"
    case_id: Optional[int] = None
    new_case: Optional[dict] = None


# ===== 统计 =====
class StatsResponse(BaseModel):
    total_active: int
    overdue_count: int
    due_3_days_count: int = 0
    due_7_days_count: int = 0
    due_14_days_count: int = 0
    due_30_days_count: int = 0
    due_soon_count: int
    by_stage: dict
    this_week_court: int


# ===== 通知 =====
class NotificationResponse(BaseModel):
    id: int
    case_id: Optional[int] = None
    case_name: str
    case_number: str
    document_id: Optional[int] = None
    document_filename: str = ""
    type: str
    message: str
    is_read: bool
    is_pinned: bool = False
    created_at: datetime

    class Config:
        orm_mode = True


# ===== 文档 =====
class DocumentResponse(BaseModel):
    id: int
    case_id: Optional[int] = None
    filename: str
    file_type: str
    file_size: int
    ai_analysis_status: str
    ai_extracted_stage: Optional[str]
    ai_extracted_parties: Optional[str]
    ai_extracted_deadline: Optional[date]
    ai_extracted_cause: Optional[str]
    ai_extracted_court_date: Optional[datetime]
    ai_raw_response: Optional[str]
    uploaded_at: datetime

    class Config:
        orm_mode = True


class DocumentUploadResponse(BaseModel):
    document_id: int
    status: str
