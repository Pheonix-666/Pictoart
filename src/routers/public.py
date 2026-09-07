import html
import os
import re
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session
from src.config import settings
from src.database import get_db
from src.models import Doctor, DoctorStatus, Submission
from src.storage import storage
from src.art_engine.preprocessor import validate_photo_quality
from src.worker.queue import enqueue_art_generation_job

router = APIRouter()
templates = Jinja2Templates(directory="src/templates")
limiter = Limiter(key_func=get_remote_address)

# ── Sanitisation helpers (TICKET-032) ─────────────────────────────────────────

def _sanitize_text(value: str | None, max_len: int = 500) -> str | None:
    """Strip HTML tags, trim whitespace, enforce max length."""
    if not value:
        return None
    stripped = html.unescape(re.sub(r"<[^>]+>", "", value))
    stripped = stripped.strip()
    return stripped[:max_len] if stripped else None

def _sanitize_name(value: str, max_len: int = 255) -> str:
    """Strip HTML, collapse whitespace, enforce max length for doctor names."""
    clean = html.unescape(re.sub(r"<[^>]+>", "", value))
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean[:max_len]


# ── Self-service entry point — generates a fresh token and redirects ───────────

@router.get("/upload/", response_class=HTMLResponse)
def create_upload_session(request: Request, db: Session = Depends(get_db)):
    """Visit /upload/ to get a brand-new personal upload link."""
    token = uuid.uuid4().hex
    doctor = Doctor(name="Pending", unique_token=token)
    db.add(doctor)
    db.commit()
    return RedirectResponse(url=f"/upload/{token}", status_code=303)


# ── Doctor upload form (GET) ───────────────────────────────────────────────────

@router.get("/upload/{token}", response_class=HTMLResponse)
def get_upload_form(token: str, request: Request, db: Session = Depends(get_db)):
    doctor = db.query(Doctor).filter(Doctor.unique_token == token).first()
    if not doctor:
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "title": "Link Invalid",
             "message": "The certificate upload link is invalid or has expired."},
            status_code=404
        )

    # Already approved — block re-use (TICKET-035)
    if doctor.status == DoctorStatus.APPROVED:
        return templates.TemplateResponse(
            "confirmation.html",
            {"request": request, "doctor": doctor, "already_approved": True,
             "message": "Your certificate has already been approved and finalised. Thank you!"}
        )

    # Re-upload screen (TICKET-010)
    if doctor.status == DoctorStatus.NEEDS_REUPLOAD:
        return templates.TemplateResponse("reupload.html", {"request": request, "doctor": doctor})

    # In-progress — skip re-submission
    if doctor.status in [DoctorStatus.SUBMITTED, DoctorStatus.PROCESSING, DoctorStatus.READY_FOR_REVIEW]:
        return RedirectResponse(url=f"/upload/{token}/confirmation", status_code=303)

    return templates.TemplateResponse("upload_form.html", {"request": request, "doctor": doctor})


# ── Doctor upload form (POST) — rate limited to 5 req/min per IP ──────────────

@router.post("/upload/{token}")
@limiter.limit("5/minute")   # TICKET-031 — rate limiting
async def submit_upload_form(
    token: str,
    request: Request,
    name: str = Form(...),
    years_experience: int = Form(None),
    specialization: str = Form(None),
    achievements_text: str = Form(None),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    doctor = db.query(Doctor).filter(Doctor.unique_token == token).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Invalid token")

    if doctor.status == DoctorStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Certificate already approved")

    # ── Input sanitization (TICKET-032) ─────────────────────────────────────
    clean_name = _sanitize_name(name)
    if not clean_name:
        return templates.TemplateResponse(
            "upload_form.html",
            {"request": request, "doctor": doctor, "error_message": "Name is required."},
            status_code=400
        )
    clean_specialization = _sanitize_text(specialization, max_len=255)
    clean_achievements   = _sanitize_text(achievements_text, max_len=500)

    # ── Photo validation ─────────────────────────────────────────────────────
    photo_bytes = await photo.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(photo_bytes) > max_bytes:
        return templates.TemplateResponse(
            "upload_form.html",
            {"request": request, "doctor": doctor,
             "error_message": f"Photo exceeds the {settings.MAX_UPLOAD_SIZE_MB} MB size limit."},
            status_code=400
        )

    # File-type whitelist check
    ext = os.path.splitext(photo.filename or "")[-1].lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
        return templates.TemplateResponse(
            "upload_form.html",
            {"request": request, "doctor": doctor,
             "error_message": "Only JPEG, PNG, or WebP photos are accepted."},
            status_code=400
        )

    is_valid, err_msg, _face_detected, (_w, _h) = validate_photo_quality(photo_bytes)
    if not is_valid:
        return templates.TemplateResponse(
            "upload_form.html",
            {"request": request, "doctor": doctor, "error_message": err_msg},
            status_code=400
        )

    # ── Persist doctor info ───────────────────────────────────────────────────
    doctor.name              = clean_name
    doctor.years_experience  = years_experience
    doctor.specialization    = clean_specialization
    doctor.achievements_text = clean_achievements
    doctor.status            = DoctorStatus.SUBMITTED

    saved_photo_path = storage.save_original_photo(photo_bytes, doctor.id, photo.filename or "photo.jpg")

    prev_count = db.query(Submission).filter(Submission.doctor_id == doctor.id).count()
    submission = Submission(
        doctor_id=doctor.id,
        original_photo_path=saved_photo_path,
        attempt_number=prev_count + 1
    )
    db.add(submission)
    db.commit()

    # ── Enqueue background art-generation job ─────────────────────────────────
    enqueue_art_generation_job(doctor.id)
    return RedirectResponse(url=f"/upload/{token}/confirmation", status_code=303)


# ── Confirmation page ─────────────────────────────────────────────────────────

@router.get("/upload/{token}/confirmation", response_class=HTMLResponse)
def get_confirmation_page(token: str, request: Request, db: Session = Depends(get_db)):
    doctor = db.query(Doctor).filter(Doctor.unique_token == token).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Invalid token")
    return templates.TemplateResponse("confirmation.html", {"request": request, "doctor": doctor})


# ── Status API (polled by JS on confirmation page) ────────────────────────────

@router.get("/upload/{token}/status")
def get_submission_status(token: str, db: Session = Depends(get_db)):
    doctor = db.query(Doctor).filter(Doctor.unique_token == token).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Invalid token")
    return {"status": doctor.status.value, "name": doctor.name,
            "reupload_reason": doctor.reupload_reason}
