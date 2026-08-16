# PICTOART — Doctor Word-Art Certificate Generator

> Automated typographic portrait generation system for bulk pharma certificate production.  
> Converts a doctor's photo + bio text into a high-resolution word-art portrait certificate, at scale for 20,000 doctors.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.10+ · FastAPI · Uvicorn |
| Database | SQLite (dev) · PostgreSQL (production) |
| Image Engine | OpenCV · Pillow · NumPy |
| Background Jobs | ThreadPoolExecutor (dev) · Redis Queue / RQ (production) |
| Templates | Jinja2 + Vanilla HTML/CSS |
| Auth | bcrypt + JWT session cookies |

---

## Project Structure

```
PICTOART/
├── main.py                     # FastAPI app entry point
├── cli.py                      # Admin CLI tool
├── sample_doctors.csv          # Sample import data
├── .env.example                # Environment variable template
├── pyproject.toml              # Dependencies
├── src/
│   ├── config.py               # App settings (Pydantic Settings)
│   ├── database.py             # SQLAlchemy engine & session
│   ├── models.py               # DB models: Doctor, Submission, AdminUser, AuditLog
│   ├── schemas.py              # Pydantic request/response schemas
│   ├── storage.py              # File storage manager (local / S3-compatible)
│   ├── art_engine/
│   │   ├── preprocessor.py     # Image preprocessing & quality checks
│   │   ├── segmentation.py     # OpenCV silhouette extraction
│   │   ├── density.py          # Pixel density map generation
│   │   ├── text_pool.py        # Weighted word pool builder
│   │   ├── renderer.py         # Multi-scale word placement engine
│   │   └── composer.py         # Certificate template layout + 300 DPI export
│   ├── worker/
│   │   ├── jobs.py             # Background art generation pipeline
│   │   └── queue.py            # Queue manager (Thread / Redis Queue)
│   ├── routers/
│   │   ├── auth.py             # JWT auth, password hashing, audit logging
│   │   ├── public.py           # Doctor upload form endpoints
│   │   └── admin.py            # Full admin dashboard API
│   ├── templates/              # Jinja2 HTML templates
│   └── static/                 # CSS & JS assets
└── tests/
    └── test_core.py            # Core module test suite
```

---

## Quick Start

### 1. Install dependencies

```bash
pip install -e .
```

### 2. Configure environment

```bash
copy .env.example .env
# Edit .env with your settings (database URL, secret key, etc.)
```

### 3. Create the first admin user

```bash
python cli.py create-admin --email admin@yourvendor.com --password YourPassword123
```

### 4. Start the server

```bash
python main.py
# or
uvicorn main:app --reload
```

Access at: `http://localhost:8000`

---

## Admin Workflow

1. **Login** → `http://localhost:8000/admin/login`
2. **Import doctors** → Upload `sample_doctors.csv` or your own CSV via Admin Dashboard
3. **Export links** → Download CSV of unique upload links to send to doctors (WhatsApp / Email)
4. Doctors open their unique link, upload photo + bio details
5. Background worker generates word-art certificate automatically
6. **Review** generated art per doctor — Approve, Request Re-upload, or Regenerate
7. **Bulk Export** → Download all approved certificates as a ZIP archive

---

## Doctor-Facing Submission

Each doctor receives a unique link in format:
```
http://yourdomain.com/upload/<unique_token>
```

The link:
- Pre-fills their name
- Collects photo + bio fields
- Validates photo (min 600×600px, max 10MB, JPEG/PNG only)
- Shows a live preview before submission
- Displays a confirmation screen after submission

---

## CSV Import Format

```csv
name,contact,years_experience,specialization,achievements_text
Dr. Rajesh Kumar,+91-9876543210,22,Cardiology,"10000+ Patients Treated, FACC Fellow"
```

| Column | Required | Notes |
|---|---|---|
| name | Yes | Doctor's full name |
| contact | No | Phone or email for link delivery |
| years_experience | No | Numeric |
| specialization | No | e.g. Cardiology |
| achievements_text | No | Used as typographic art content |

---

## CLI Reference

```bash
python cli.py create-admin --email EMAIL --password PASS  # Create admin user
python cli.py import-csv doctors.csv                       # Bulk import from CSV
python cli.py export-zip --status approved                 # Export certificates ZIP
python cli.py run-worker                                   # Start Redis Queue worker
python cli.py stats                                        # Show database statistics
```

---

## Art Pipeline (Core Engine)

For each doctor submission, the background worker runs:

1. **Preprocessing** — resize, normalize, grayscale conversion
2. **Segmentation** — OpenCV silhouette / contour extraction from photo
3. **Density Mapping** — darker areas → denser/smaller text, lighter areas → sparse/larger text
4. **Text Pool Building** — weighted words from name, specialization, years, achievements
5. **Word Placement** — iterative placement following density map within silhouette mask
6. **Certificate Composition** — branding borders, header, caption block (Pillow)
7. **High-Res Export** — 300 DPI PNG (2400×3200px), print-ready

---

## Running Tests

```bash
python -m pytest tests/ -v
```

---

## Production Deployment

1. Set `DATABASE_URL=postgresql://...` in `.env`
2. Set `WORKER_MODE=rq` and ensure Redis is running
3. Run `python cli.py run-worker` in a separate process (or systemd service)
4. Deploy behind Nginx with TLS (Let's Encrypt)
5. Use Cloudflare R2 by setting `USE_S3_STORAGE=True` with R2 credentials in `.env`

> See `02_Technical_Architecture_Document.md` for full infrastructure and scaling notes.
