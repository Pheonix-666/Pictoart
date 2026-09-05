import os
import traceback
from sqlalchemy.orm import Session
from src.database import SessionLocal
from src.models import Doctor, DoctorStatus, Submission
from src.storage import storage
from src.art_engine.preprocessor import validate_photo_quality, preprocess_image
from src.art_engine.segmentation import extract_masks
from src.art_engine.sketch import render_pencil_sketch, render_full_sketch_portrait
from src.art_engine.composer import create_certificate_layout


def process_doctor_art_job(doctor_id: int) -> bool:
    """
    Background worker job: processes original doctor photo into a high-resolution
    artistic graphite pencil sketch portrait certificate.
    """
    db: Session = SessionLocal()
    try:
        doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
        if not doctor:
            print(f"[Worker] Error: Doctor #{doctor_id} not found.")
            return False

        submission = db.query(Submission).filter(
            Submission.doctor_id == doctor_id
        ).order_by(Submission.attempt_number.desc()).first()

        if not submission or not submission.original_photo_path:
            print(f"[Worker] Error: No submission or photo path found for Doctor #{doctor_id}.")
            doctor.status = DoctorStatus.NEEDS_REUPLOAD
            doctor.reupload_reason = "No photo file found."
            db.commit()
            return False

        # Set status to processing
        doctor.status = DoctorStatus.PROCESSING
        db.commit()

        photo_path = storage.get_full_path(submission.original_photo_path)
        if not os.path.exists(photo_path):
            doctor.status = DoctorStatus.NEEDS_REUPLOAD
            doctor.reupload_reason = "Original photo file missing from storage."
            db.commit()
            return False

        with open(photo_path, "rb") as f:
            photo_bytes = f.read()

        # Quality Pre-check (Ticket-019)
        is_valid, err_msg, face_detected, res = validate_photo_quality(photo_bytes)
        if not is_valid:
            doctor.status = DoctorStatus.NEEDS_REUPLOAD
            doctor.reupload_reason = f"Photo quality check failed: {err_msg}"
            submission.error_message = err_msg
            db.commit()
            return False

        # Pipeline Step 1: Preprocessing
        print("[Step 1/4] Preprocessing photo...", flush=True)
        gray_np, color_np, resized_pil = preprocess_image(photo_bytes, target_size=(1200, 1200))

        # Pipeline Step 2: Subject Silhouette & Feature Segmentation
        print("[Step 2/4] Running subject segmentation...", flush=True)
        silhouette_mask, natural_mask, clothing_mask = extract_masks(gray_np, color_np)

        # Pipeline Step 3: Render Full Pencil Sketch Portrait
        print("[Step 3/4] Rendering artistic graphite pencil sketch portrait...", flush=True)
        portrait_img = render_pencil_sketch(
            gray_np=gray_np,
            mask_np=silhouette_mask,
            output_size=(1600, 1600)
        )

        # Pipeline Step 4: Presentation Layout Composition & High-Res Export
        print("[Step 4/4] Creating certificate presentation layout...", flush=True)
        cert_img = create_certificate_layout(
            portrait_img=portrait_img,
            doctor_name=doctor.name,
            specialization=doctor.specialization,
            years_experience=doctor.years_experience,
            achievements_text=doctor.achievements_text,
            cert_size=(2400, 3200)
        )

        # Save generated art to storage
        saved_art_path = storage.save_generated_art(cert_img, doctor_id=doctor.id, format="PNG")

        # Update database records
        submission.generated_art_path = saved_art_path
        submission.error_message = None
        doctor.status = DoctorStatus.READY_FOR_REVIEW
        doctor.reupload_reason = None
        db.commit()

        print(f"[Worker] Success: Generated pencil sketch certificate for Doctor #{doctor_id} ({doctor.name}).")
        return True

    except Exception as e:
        db.rollback()
        err_trace = traceback.format_exc()
        print(f"[Worker] Exception processing Doctor #{doctor_id}:\n{err_trace}")

        try:
            doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
            if doctor:
                doctor.status = DoctorStatus.NEEDS_REUPLOAD
                doctor.reupload_reason = f"Processing error: {str(e)}"
                submission = db.query(Submission).filter(
                    Submission.doctor_id == doctor_id
                ).order_by(Submission.attempt_number.desc()).first()
                if submission:
                    submission.error_message = str(e)
                db.commit()
        except Exception:
            pass

        return False
    finally:
        db.close()
