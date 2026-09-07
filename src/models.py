import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from src.database import Base

def _now():
    return datetime.now(timezone.utc)

class DoctorStatus(str, enum.Enum):
    NOT_SUBMITTED = "not_submitted"
    SUBMITTED = "submitted"
    PROCESSING = "processing"
    READY_FOR_REVIEW = "ready_for_review"
    APPROVED = "approved"
    NEEDS_REUPLOAD = "needs_reupload"

class AdminRole(str, enum.Enum):
    ADMIN = "admin"
    REVIEWER = "reviewer"

class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    contact = Column(String(255), nullable=True)
    unique_token = Column(String(64), unique=True, index=True, nullable=False)
    years_experience = Column(Integer, nullable=True)
    specialization = Column(String(255), nullable=True)
    achievements_text = Column(Text, nullable=True)
    state = Column(String(255), nullable=True)
    district = Column(String(255), nullable=True)
    place = Column(String(255), nullable=True)
    status = Column(SQLEnum(DoctorStatus), default=DoctorStatus.NOT_SUBMITTED, nullable=False, index=True)
    reupload_reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)

    submissions = relationship("Submission", back_populates="doctor", cascade="all, delete-orphan")

class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False, index=True)
    original_photo_path = Column(String(512), nullable=False)
    generated_art_path = Column(String(512), nullable=True)
    attempt_number = Column(Integer, default=1, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)

    doctor = relationship("Doctor", back_populates="submissions")

class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(SQLEnum(AdminRole), default=AdminRole.ADMIN, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True)
    admin_email = Column(String(255), nullable=True)
    action = Column(String(100), nullable=False, index=True)
    target_doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="SET NULL"), nullable=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now, nullable=False)

