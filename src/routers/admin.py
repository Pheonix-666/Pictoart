import csv
import html as html_module
import io
import os
import re
import secrets
import zipfile
from datetime import datetime
from typing import Optional, List


def _sanitize(value: str | None, max_len: int = 500) -> str | None:
    """Strip HTML tags, trim whitespace, enforce max length."""
    if not value:
        return None
    clean = html_module.unescape(re.sub(r"<[^>]+>", "", value)).strip()
    return clean[:max_len] if clean else None
from fastapi import APIRouter, Depends, HTTPException, Request, Form, UploadFile, File, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from src.config import settings
from src.database import get_db
from src.models import Doctor, DoctorStatus, Submission, AdminUser, AdminRole, AuditLog
from src.storage import storage
from src.routers.auth import (
    verify_password,
    create_access_token,
    get_current_admin_user,
    require_admin,
    log_audit_action
)
from src.worker.queue import enqueue_art_generation_job

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory="src/templates")

@router.get("/login", response_class=HTMLResponse)
def get_login_page(request: Request):
    return templates.TemplateResponse("admin_login.html", {"request": request})

@router.post("/login")
def process_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    admin = db.query(AdminUser).filter(AdminUser.email == email.strip().lower()).first()
    if not admin or not verify_password(password, admin.password_hash):
        return templates.TemplateResponse(
            "admin_login.html",
            {"request": request, "error_message": "Invalid email or password."},
            status_code=400
        )

    token = create_access_token({"sub": admin.email, "role": admin.role.value})
    log_audit_action(db, admin, "login", details=f"Admin logged in from {request.client.host if request.client else 'unknown'}")

    response = RedirectResponse(url="/admin/doctors", status_code=303)
    response.set_cookie(key="admin_session", value=token, httponly=True, max_age=86400)
    return response

@router.get("/logout")
def process_logout(request: Request, db: Session = Depends(get_db)):
    admin = get_current_admin_user(request, db)
    if admin:
        log_audit_action(db, admin, "logout")
    response = RedirectResponse(url="/admin/login", status_code=303)
    response.delete_cookie("admin_session")
    return response

@router.get("/doctors", response_class=HTMLResponse)
def list_doctors(
    request: Request,
    q: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin)
):
    query = db.query(Doctor)

    if q:
        search_term = f"%{q.strip()}%"
        query = query.filter((Doctor.name.ilike(search_term)) | (Doctor.contact.ilike(search_term)))

    if status_filter and status_filter.lower() != "all":
        query = query.filter(Doctor.status == status_filter.lower())

    doctors = query.order_by(Doctor.id.desc()).all()

    # Status counts summary
    all_count = db.query(Doctor).count()
    counts = {
        "all": all_count,
        "not_submitted": db.query(Doctor).filter(Doctor.status == DoctorStatus.NOT_SUBMITTED).count(),
        "submitted": db.query(Doctor).filter(Doctor.status == DoctorStatus.SUBMITTED).count(),
        "processing": db.query(Doctor).filter(Doctor.status == DoctorStatus.PROCESSING).count(),
        "ready_for_review": db.query(Doctor).filter(Doctor.status == DoctorStatus.READY_FOR_REVIEW).count(),
        "approved": db.query(Doctor).filter(Doctor.status == DoctorStatus.APPROVED).count(),
        "needs_reupload": db.query(Doctor).filter(Doctor.status == DoctorStatus.NEEDS_REUPLOAD).count(),
    }

    return templates.TemplateResponse(
        "admin_dashboard.html",
        {
            "request": request,
            "admin": admin,
            "doctors": doctors,
            "counts": counts,
            "q": q or "",
            "current_status": status_filter or "all",
            "base_url": settings.BASE_URL
        }
    )

@router.get("/import", response_class=HTMLResponse)
def get_import_page(request: Request, admin: AdminUser = Depends(require_admin)):
    return templates.TemplateResponse("admin_import.html", {"request": request, "admin": admin})

@router.post("/import")
async def process_csv_import(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin)
):
    if not file.filename.endswith(".csv"):
        return templates.TemplateResponse(
            "admin_import.html",
            {"request": request, "admin": admin, "error_message": "File must be a CSV file."},
            status_code=400
        )

    content = await file.read()
    try:
        csv_text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        csv_text = content.decode("latin-1")

    reader = csv.DictReader(io.StringIO(csv_text))
    imported_count = 0
    errors = []

    new_doctors = []
    for idx, row in enumerate(reader, start=1):
        name = row.get("name") or row.get("Name") or row.get("doctor_name")
        if not name or not name.strip():
            errors.append(f"Row #{idx}: Missing required 'name' field.")
            continue

        contact = row.get("contact") or row.get("Contact") or row.get("phone") or row.get("email")
        state = row.get("state") or row.get("State")
        district = row.get("district") or row.get("District")
        place = row.get("place") or row.get("Place") or row.get("city") or row.get("City")

        token = secrets.token_urlsafe(24) # Secure 128-bit+ unique token

        doctor = Doctor(
            name=_sanitize(name, 255) or name.strip()[:255],
            contact=_sanitize(contact, 255) if contact else None,
            unique_token=token,
            state=_sanitize(state, 255) if state else None,
            district=_sanitize(district, 255) if district else None,
            place=_sanitize(place, 255) if place else None,
            status=DoctorStatus.NOT_SUBMITTED
        )
        db.add(doctor)
        new_doctors.append(doctor)
        imported_count += 1

    db.commit()
    log_audit_action(db, admin, "import_csv", details=f"Imported {imported_count} doctors from {file.filename}")

    return templates.TemplateResponse(
        "admin_import.html",
        {
            "request": request,
            "admin": admin,
            "success_message": f"Successfully imported {imported_count} doctors!",
            "imported_count": imported_count,
            "errors": errors,
            "imported_doctors": new_doctors,
            "base_url": settings.BASE_URL
        }
    )

@router.get("/export-links")
def export_unique_links(db: Session = Depends(get_db), admin: AdminUser = Depends(require_admin)):
    doctors = db.query(Doctor).order_by(Doctor.id.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Name", "Contact", "Status", "Unique Upload Link"])

    for d in doctors:
        link = f"{settings.BASE_URL}/upload/{d.unique_token}"
        writer.writerow([d.id, d.name, d.contact or "", d.status.value, link])

    output.seek(0)
    log_audit_action(db, admin, "export_links", details=f"Exported links for {len(doctors)} doctors")

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=doctor_links_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
    )

@router.get("/doctor/{doctor_id}", response_class=HTMLResponse)
def get_doctor_detail(doctor_id: int, request: Request, db: Session = Depends(get_db), admin: AdminUser = Depends(require_admin)):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    submission = db.query(Submission).filter(Submission.doctor_id == doctor_id).order_by(Submission.attempt_number.desc()).first()

    return templates.TemplateResponse(
        "admin_detail.html",
        {
            "request": request,
            "admin": admin,
            "doctor": doctor,
            "submission": submission
        }
    )

@router.post("/doctor/{doctor_id}/approve")
def approve_doctor_art(doctor_id: int, db: Session = Depends(get_db), admin: AdminUser = Depends(require_admin)):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    doctor.status = DoctorStatus.APPROVED
    doctor.reupload_reason = None
    db.commit()

    log_audit_action(db, admin, "approve", target_doctor_id=doctor_id, details=f"Approved portrait for Dr. {doctor.name}")
    return RedirectResponse(url=f"/admin/doctor/{doctor_id}", status_code=303)

@router.post("/doctor/{doctor_id}/reject")
def reject_doctor_art(
    doctor_id: int,
    reason: str = Form(...),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin)
):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    doctor.status = DoctorStatus.NEEDS_REUPLOAD
    doctor.reupload_reason = reason.strip()
    db.commit()

    log_audit_action(db, admin, "request_reupload", target_doctor_id=doctor_id, details=f"Requested re-upload: {reason.strip()}")
    return RedirectResponse(url=f"/admin/doctor/{doctor_id}", status_code=303)

@router.post("/doctor/{doctor_id}/regenerate")
def regenerate_doctor_art(doctor_id: int, db: Session = Depends(get_db), admin: AdminUser = Depends(require_admin)):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    enqueue_art_generation_job(doctor_id)
    log_audit_action(db, admin, "regenerate", target_doctor_id=doctor_id, details=f"Triggered art regeneration for Dr. {doctor.name}")
    return RedirectResponse(url=f"/admin/doctor/{doctor_id}", status_code=303)

@router.post("/bulk-approve")
def bulk_approve_doctors(
    doctor_ids_csv: str = Form("", alias="doctor_ids_csv"),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin)
):
    """Bulk approve doctors. Expects a hidden form field 'doctor_ids_csv' with
    comma-separated integer IDs collected by the dashboard JavaScript."""
    approved_count = 0
    if doctor_ids_csv.strip():
        for raw_id in doctor_ids_csv.split(","):
            try:
                d_id = int(raw_id.strip())
            except ValueError:
                continue
            doc = db.query(Doctor).filter(Doctor.id == d_id).first()
            if doc and doc.status in (
                DoctorStatus.READY_FOR_REVIEW,
                DoctorStatus.SUBMITTED,
            ):
                doc.status = DoctorStatus.APPROVED
                doc.reupload_reason = None
                approved_count += 1

    db.commit()
    log_audit_action(db, admin, "bulk_approve", details=f"Bulk approved {approved_count} doctors")
    return RedirectResponse(url="/admin/doctors?status_filter=approved", status_code=303)

@router.get("/bulk-export")
def bulk_export_zip(status_filter: str = "approved", db: Session = Depends(get_db), admin: AdminUser = Depends(require_admin)):
    query = db.query(Doctor)
    if status_filter != "all":
        query = query.filter(Doctor.status == status_filter.lower())
    doctors = query.all()

    zip_buffer = io.BytesIO()
    exported_count = 0

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for doctor in doctors:
            submission = db.query(Submission).filter(
                Submission.doctor_id == doctor.id,
                Submission.generated_art_path.isnot(None)
            ).order_by(Submission.attempt_number.desc()).first()

            if submission and submission.generated_art_path:
                full_path = storage.get_full_path(submission.generated_art_path)
                if os.path.exists(full_path):
                    safe_name = "".join(c for c in doctor.name if c.isalnum() or c in (" ", "_", "-")).strip()
                    arcname = f"Certificate_Doc_{doctor.id}_{safe_name}.png"
                    zip_file.write(full_path, arcname=arcname)
                    exported_count += 1

    zip_buffer.seek(0)
    log_audit_action(db, admin, "bulk_export", details=f"Bulk exported ZIP containing {exported_count} certificate files")

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=certificates_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"}
    )

@router.get("/audit-logs", response_class=HTMLResponse)
def view_audit_logs(request: Request, db: Session = Depends(get_db), admin: AdminUser = Depends(require_admin)):
    logs = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(200).all()
    return templates.TemplateResponse("admin_audit_logs.html", {"request": request, "admin": admin, "logs": logs})

# Secure File Serving (Ticket-033: Private Storage Buckets)
@router.get("/preview/original/{doctor_id}")
def serve_original_photo(doctor_id: int, db: Session = Depends(get_db), admin: AdminUser = Depends(require_admin)):
    submission = db.query(Submission).filter(Submission.doctor_id == doctor_id).order_by(Submission.attempt_number.desc()).first()
    if not submission or not submission.original_photo_path:
        raise HTTPException(status_code=404, detail="Photo not found")
    
    full_path = storage.get_full_path(submission.original_photo_path)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File missing on server")
        
    return FileResponse(full_path)

@router.get("/preview/art/{doctor_id}")
def serve_generated_art(doctor_id: int, db: Session = Depends(get_db), admin: AdminUser = Depends(require_admin)):
    submission = db.query(Submission).filter(Submission.doctor_id == doctor_id).order_by(Submission.attempt_number.desc()).first()
    if not submission or not submission.generated_art_path:
        raise HTTPException(status_code=404, detail="Generated art not found")

    full_path = storage.get_full_path(submission.generated_art_path)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File missing on server")

    return FileResponse(full_path)

@router.delete("/doctor/{doctor_id}")
def delete_doctor_record(doctor_id: int, db: Session = Depends(get_db), admin: AdminUser = Depends(require_admin)):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    # Delete storage files (Ticket-036)
    storage.delete_doctor_files(doctor_id)

    db.delete(doctor)
    db.commit()

    log_audit_action(db, admin, "delete_doctor", target_doctor_id=doctor_id, details=f"Permanently deleted Doctor #{doctor_id} and all associated files.")
    return {"success": True, "message": f"Deleted Doctor #{doctor_id} successfully."}
