import os
import traceback
from PIL import Image
from sqlalchemy.orm import Session
from src.database import SessionLocal
from src.models import Doctor, DoctorStatus, Submission
from src.storage import storage
from src.art_engine.preprocessor import validate_photo_quality, preprocess_image
from src.art_engine.segmentation import extract_masks
from src.art_engine.sketch import render_pencil_sketch
from src.art_engine.density import create_shading_and_gradient_map
from src.art_engine.text_pool import build_text_pool
from src.art_engine.renderer import render_word_art_portrait
from src.art_engine.composer import composite_two_region_portrait, create_certificate_layout
from src.art_engine.art_config import OUTPUT_PORTRAIT_SIZE

def process_doctor_art_job(doctor_id: int) -> bool:
    """
    Background worker job: processes original doctor photo into high-resolution
    word-art portrait certificate with a sketch face and typographic word-art suit.
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
        print("[Step 1/8] Preprocessing photo...", flush=True)
        gray_np, color_np, resized_pil = preprocess_image(photo_bytes, target_size=(1600, 1600))

        # Pipeline Step 2: Two-Region Segmentation (Silhouette, Natural [face+hair], Clothing)
        print("[Step 2/8] Running segmentation (rembg / face detection)...", flush=True)
        silhouette_mask, natural_mask, clothing_mask = extract_masks(gray_np, color_np)

        # Pipeline Step 3: Shading Map & Sobel Gradient Field Generation
        print("[Step 3/8] Generating shading map & Sobel gradient field...", flush=True)
        shading_map, grad_x, grad_y = create_shading_and_gradient_map(gray_np, clothing_mask)

        # Pipeline Step 4: Build Text Pool from Doctor Biographical & Achievement Data
        print("[Step 4/8] Building text pool...", flush=True)
        text_pool = build_text_pool(
            name=doctor.name,
            years_experience=doctor.years_experience,
            specialization=doctor.specialization,
            achievements_text=doctor.achievements_text
        )

        # Pipeline Step 5: Render Typographic Word Art Suit/Clothing Body
        print("[Step 5/8] Rendering dense word art suit...", flush=True)
        word_art_body = render_word_art_portrait(
            mask_np=clothing_mask,
            density_map=shading_map,
            text_pool=text_pool,
            grad_x=grad_x,
            grad_y=grad_y,
            output_size=(1600, 1600),
            natural_mask=natural_mask,
            orig_gray=gray_np
        )

        # Pipeline Step 6: Render Clean Graphite Pencil Sketch Face
        print("[Step 6/8] Rendering pencil sketch face...", flush=True)
        sketch_face = render_pencil_sketch(
            gray_np=gray_np,
            mask_np=natural_mask,
            output_size=(1600, 1600)
        )

        # Pipeline Step 7: Two-Region Composite (Sketch Face over Word-Art Suit)
        print("[Step 7/7] Compositing transparent sketch face over word-art suit...", flush=True)
        portrait_img = composite_two_region_portrait(
            word_art_body=word_art_body,
            sketch_face=sketch_face,
            face_mask=natural_mask,
            output_size=OUTPUT_PORTRAIT_SIZE
        )

        # Save standalone transparent portrait to storage
        saved_art_path = storage.save_generated_art(portrait_img, doctor_id=doctor.id, format="PNG")

        # Update database records
        submission.generated_art_path = saved_art_path
        submission.error_message = None
        doctor.status = DoctorStatus.READY_FOR_REVIEW
        doctor.reupload_reason = None
        db.commit()

        print(f"[Worker] Success: Generated transparent word-art portrait for Doctor #{doctor_id} ({doctor.name}).")
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
                submission = db.query(Submission).filter(Submission.doctor_id == doctor_id).order_by(Submission.attempt_number.desc()).first()
                if submission:
                    submission.error_message = str(e)
                db.commit()
        except Exception:
            pass

        return False
    finally:
        db.close()
