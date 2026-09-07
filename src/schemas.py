from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from src.models import DoctorStatus, AdminRole

class DoctorBase(BaseModel):
    name: str
    contact: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    place: Optional[str] = None
    years_experience: Optional[int] = None
    specialization: Optional[str] = None
    achievements_text: Optional[str] = None

class DoctorCreate(DoctorBase):
    pass

class DoctorSubmissionUpdate(BaseModel):
    name: str
    state: Optional[str] = None
    district: Optional[str] = None
    place: Optional[str] = None

class DoctorOut(DoctorBase):
    id: int
    unique_token: str
    status: DoctorStatus
    reupload_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class SubmissionOut(BaseModel):
    id: int
    doctor_id: int
    original_photo_path: str
    generated_art_path: Optional[str] = None
    attempt_number: int
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class CSVImportRow(BaseModel):
    name: str
    contact: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    place: Optional[str] = None
    years_experience: Optional[int] = None
    specialization: Optional[str] = None
    achievements_text: Optional[str] = None

class CSVImportResult(BaseModel):
    total_rows: int
    imported_count: int
    failed_count: int
    errors: List[str]

class AdminUserCreate(BaseModel):
    email: str
    password: str
    role: AdminRole = AdminRole.ADMIN

class AdminUserOut(BaseModel):
    id: int
    email: str
    role: AdminRole
    created_at: datetime

    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    email: str
    password: str

class ReuploadRequest(BaseModel):
    reason: str

class AuditLogOut(BaseModel):
    id: int
    admin_id: Optional[int] = None
    admin_email: Optional[str] = None
    action: str
    target_doctor_id: Optional[int] = None
    details: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
