import sys
import os
import shutil
import secrets
import csv
from src.database import SessionLocal, Base, engine
from src.models import Doctor, DoctorStatus, Submission
from src.storage import storage
from src.worker.jobs import process_doctor_art_job

# Ensure tables exist
Base.metadata.create_all(bind=engine)

# Allow overriding doctor name and photo via CLI: python process_sample.py "Dr. Rajesh Kumar" photo.jpg
DOCTOR_NAME = sys.argv[1] if len(sys.argv) > 1 else "Aman Sharma"
PHOTO_PATH  = sys.argv[2] if len(sys.argv) > 2 else "sample_doctor_photo.jpg"

db = SessionLocal()
try:
    # 1. Create or get Doctor record
    doctor = db.query(Doctor).filter(Doctor.name.like(f"%{DOCTOR_NAME}%")).first()
    if not doctor:
        doctor = Doctor(
            name=DOCTOR_NAME,
            contact="+91-9876543210",
            unique_token=secrets.token_urlsafe(24),
            years_experience=12,
            specialization="Neurology",
            achievements_text="1000+ Successful Surgeries, National Medical Excellence Award, Fellow of Neurology, AIIMS Gold Medalist",
            status=DoctorStatus.NOT_SUBMITTED
        )
        db.add(doctor)
        db.commit()
        db.refresh(doctor)
        print(f"[OK] Doctor record created: Dr. {doctor.name} (ID #{doctor.id})")
    else:
        print(f"[INFO] Found existing doctor record: Dr. {doctor.name} (ID #{doctor.id})")

    # 2. Read attached photo
    photo_path = PHOTO_PATH

    with open(photo_path, "rb") as f:
        photo_bytes = f.read()

    # 3. Save photo into storage
    saved_path = storage.save_original_photo(photo_bytes, doctor.id, "sample_doctor_photo.jpg")
    print(f"[DEBUG] saved_path={saved_path}, exists={os.path.exists(saved_path)}")

    # 4. Clear old submissions and create clean submission
    db.query(Submission).filter(Submission.doctor_id == doctor.id).delete()
    db.commit()

    submission = Submission(
        doctor_id=doctor.id,
        original_photo_path=saved_path,
        attempt_number=1
    )
    db.add(submission)
    doctor.status = DoctorStatus.SUBMITTED
    db.commit()

    print(f"[RUNNING] Running Art Generation Engine pipeline for Dr. {doctor.name}...")
    try:
        success = process_doctor_art_job(doctor.id)
    except Exception as e:
        import traceback
        traceback.print_exc()
        success = False

    if success:
        db.refresh(submission)
        generated_path = storage.get_full_path(submission.generated_art_path)
        print(f"[SUCCESS] Certificate generated at: {generated_path}")

        # Copy to artifacts directory for display if available
        artifact_dir = os.environ.get("ARTIFACT_DIR", r"C:\Users\ADMIN\.gemini\antigravity-ide\brain\6800def3-2f94-4502-9788-c5bcd697bbe2")
        if os.path.isdir(artifact_dir):
            artifact_dest = os.path.join(artifact_dir, "sample_certificate_output.png")
            shutil.copy(generated_path, artifact_dest)
            print(f"[COPIED] Copied to artifact location: {artifact_dest}")
    else:
        db.refresh(doctor)
        sub = db.query(Submission).filter(Submission.doctor_id == doctor.id).first()
        print(f"[FAILED] Status: {doctor.status}, Reason: {doctor.reupload_reason}, Submission Err: {sub.error_message if sub else 'None'}")

finally:
    db.close()
