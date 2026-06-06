"""ORM 模型：律师、案件、文档、日志、通知 5 张表"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Date, DateTime, Boolean, ForeignKey
)
from sqlalchemy.orm import relationship
from app.database import Base


class Lawyer(Base):
    __tablename__ = "lawyers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False)
    initials = Column(String(10), nullable=False)
    role = Column(String(50), default="律师")
    email = Column(String(100), default="")
    phone = Column(String(20), default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    cases = relationship("Case", back_populates="lawyer")


class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_number = Column(String(100), default="", nullable=False)
    case_name = Column(String(200), nullable=False)
    plaintiff = Column(String(200), default="")
    defendant = Column(String(200), default="")
    cause_of_action = Column(String(200), default="")
    stage = Column(String(50), default="consultation")
    stage_entered_at = Column(DateTime, default=datetime.utcnow)
    deadline = Column(Date, nullable=True)
    court_date = Column(DateTime, nullable=True)
    outcome = Column(String(50), nullable=True)
    outcome_note = Column(Text, nullable=True)
    lawyer_id = Column(Integer, ForeignKey("lawyers.id"), nullable=True)
    is_archived = Column(Boolean, default=False)
    notes = Column(Text, default="")
    core_summary = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    lawyer = relationship("Lawyer", back_populates="cases")
    documents = relationship("CaseDocument", back_populates="case", cascade="all, delete-orphan")
    logs = relationship("CaseLog", back_populates="case", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="case", cascade="all, delete-orphan")


class CaseDocument(Base):
    __tablename__ = "case_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(50), default="")
    file_size = Column(Integer, default=0)
    ai_analysis_status = Column(String(50), default="pending")  # pending / processing / completed / failed
    ai_extracted_stage = Column(String(50), nullable=True)
    ai_extracted_parties = Column(Text, nullable=True)
    ai_extracted_deadline = Column(Date, nullable=True)
    ai_extracted_cause = Column(String(200), nullable=True)
    ai_extracted_court_date = Column(DateTime, nullable=True)
    ai_raw_response = Column(Text, nullable=True)
    ai_match_result = Column(Text, nullable=True)
    ai_progress = Column(String(200), default="")
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="documents")
    notifications = relationship("Notification", back_populates="document", cascade="all, delete-orphan")


class CaseLog(Base):
    __tablename__ = "case_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False)
    action = Column(String(100), nullable=False)
    old_value = Column(String(500), default="")
    new_value = Column(String(500), default="")
    note = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="logs")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=True)
    document_id = Column(Integer, ForeignKey("case_documents.id"), nullable=True)
    type = Column(String(50), nullable=False)
    message = Column(String(500), nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    case = relationship("Case", back_populates="notifications")
    document = relationship("CaseDocument", back_populates="notifications")
