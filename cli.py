"""
PICTOART CLI -- Admin utility tool for Doctor Pencil Sketch Certificate Generator.

Usage:
  python cli.py create-admin --email admin@vendor.com --password Secret123
  python cli.py run-worker
  python cli.py import-csv doctors.csv
  python cli.py export-zip [--status approved]
  python cli.py stats
"""
import sys
import argparse
import csv
import io
import os
import secrets
import zipfile
from datetime import datetime

# Set stdout to UTF-8 on Windows to avoid codec errors
if sys.platform == "win32":
    import io as _io
    sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def create_admin(email: str, password: str, role: str = "admin"):
    """Create a new admin user account."""
    from src.database import SessionLocal, Base, engine
    from src.models import AdminUser, AdminRole
    from src.routers.auth import hash_password

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(AdminUser).filter(AdminUser.email == email.strip().lower()).first()
        if existing:
            print(f"❌ Admin with email '{email}' already exists.")
            return

        admin_role = AdminRole.ADMIN if role.lower() == "admin" else AdminRole.REVIEWER
        admin = AdminUser(
            email=email.strip().lower(),
            password_hash=hash_password(password),
            role=admin_role
        )
        db.add(admin)
        db.commit()
        print(f"✅ Admin account created: {email} (role: {admin_role.value})")
    finally:
        db.close()


def run_worker():
    """Start the Redis Queue (RQ) worker process for background art generation jobs."""
    from src.config import settings
    print(f"🚀 Starting PICTOART background worker (mode: {settings.WORKER_MODE})...")
    if settings.WORKER_MODE.lower() == "rq":
        try:
            from redis import Redis
            from rq import Worker, Queue
            redis_conn = Redis.from_url(settings.REDIS_URL)
            q = Queue("art_jobs", connection=redis_conn)
            w = Worker([q], connection=redis_conn)
            print(f"📡 Connected to Redis at {settings.REDIS_URL}. Worker listening on 'art_jobs' queue...")
            w.work()
        except Exception as e:
            print(f"❌ Worker error: {str(e)}")
    else:
        print("ℹ️  Worker mode is 'threaded'. Jobs run automatically in background threads when the server is running.")
        print("   To use Redis Queue, set WORKER_MODE=rq in your .env file.")


def import_csv(filepath: str):
    """Import doctors from a CSV file."""
    from src.database import SessionLocal, Base, engine
    from src.models import Doctor, DoctorStatus

    Base.metadata.create_all(bind=engine)

    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return

    db = SessionLocal()
    imported_count = 0
    errors = []

    try:
        with open(filepath, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader, start=1):
                name = row.get("name") or row.get("Name")
                if not name or not name.strip():
                    errors.append(f"Row #{idx}: Missing 'name' field.")
                    continue

                contact = row.get("contact") or row.get("phone") or row.get("email")
                years_exp = row.get("years_experience") or row.get("experience")
                years_exp_val = int(years_exp) if years_exp and str(years_exp).strip().isdigit() else None
                specialization = row.get("specialization") or row.get("speciality")
                achievements = row.get("achievements_text") or row.get("achievements")

                token = secrets.token_urlsafe(24)
                doctor = Doctor(
                    name=name.strip(),
                    contact=contact.strip() if contact else None,
                    unique_token=token,
                    years_experience=years_exp_val,
                    specialization=specialization.strip() if specialization else None,
                    achievements_text=achievements.strip() if achievements else None,
                    status=DoctorStatus.NOT_SUBMITTED
                )
                db.add(doctor)
                imported_count += 1

        db.commit()
        print(f"✅ Imported {imported_count} doctors from '{filepath}'.")
        if errors:
            print(f"⚠️  {len(errors)} rows skipped:")
            for err in errors:
                print(f"   {err}")
    finally:
        db.close()


def export_zip(status_filter: str = "approved"):
    """Export all approved (or filtered) doctor certificates as a ZIP file."""
    from src.config import settings
    from src.database import SessionLocal
    from src.models import Doctor, DoctorStatus, Submission
    from src.storage import storage

    db = SessionLocal()
    try:
        query = db.query(Doctor)
        if status_filter != "all":
            query = query.filter(Doctor.status == status_filter.lower())
        doctors = query.all()

        if not doctors:
            print(f"No doctors found with status '{status_filter}'.")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_zip = os.path.join(settings.STORAGE_DIR, "exports", f"certificates_{timestamp}.zip")
        exported_count = 0

        with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            for doctor in doctors:
                submission = db.query(Submission).filter(
                    Submission.doctor_id == doctor.id,
                    Submission.generated_art_path.isnot(None)
                ).order_by(Submission.attempt_number.desc()).first()

                if submission and submission.generated_art_path:
                    full_path = storage.get_full_path(submission.generated_art_path)
                    if os.path.exists(full_path):
                        safe_name = "".join(c for c in doctor.name if c.isalnum() or c in (" ", "_", "-")).strip()
                        zf.write(full_path, arcname=f"Certificate_Doc_{doctor.id}_{safe_name}.png")
                        exported_count += 1

        print(f"✅ Exported {exported_count} certificates to: {output_zip}")
    finally:
        db.close()


def show_stats():
    """Print database status summary."""
    from src.database import SessionLocal, Base, engine
    from src.models import Doctor, DoctorStatus

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        total = db.query(Doctor).count()
        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("  ✨ PICTOART — Certificate System Stats")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"  Total Doctors          : {total}")
        for status in DoctorStatus:
            count = db.query(Doctor).filter(Doctor.status == status).count()
            label = status.value.replace("_", " ").title().ljust(25)
            bar = "█" * min(count, 30)
            print(f"  {label}: {count:5d}  {bar}")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="cli.py", description="PICTOART Admin CLI")
    subparsers = parser.add_subparsers(dest="command")

    # create-admin
    p_admin = subparsers.add_parser("create-admin", help="Create an admin user")
    p_admin.add_argument("--email", required=True)
    p_admin.add_argument("--password", required=True)
    p_admin.add_argument("--role", default="admin", choices=["admin", "reviewer"])

    # run-worker
    subparsers.add_parser("run-worker", help="Start the background RQ worker")

    # import-csv
    p_import = subparsers.add_parser("import-csv", help="Import doctors from a CSV file")
    p_import.add_argument("filepath", help="Path to the CSV file")

    # export-zip
    p_export = subparsers.add_parser("export-zip", help="Export certificates as ZIP")
    p_export.add_argument("--status", default="approved", help="Status filter (default: approved)")

    # stats
    subparsers.add_parser("stats", help="Show database stats")

    args = parser.parse_args()

    if args.command == "create-admin":
        create_admin(args.email, args.password, args.role)
    elif args.command == "run-worker":
        run_worker()
    elif args.command == "import-csv":
        import_csv(args.filepath)
    elif args.command == "export-zip":
        export_zip(args.status)
    elif args.command == "stats":
        show_stats()
    else:
        parser.print_help()
