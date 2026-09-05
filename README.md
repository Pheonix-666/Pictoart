# PICTOART — Doctor Pencil Sketch Certificate Generator

> High-resolution graphite pencil sketch portrait & certificate generation system.  
> Converts a doctor's portrait photo into an artistic pencil sketch certificate at scale for pharma recognition programs.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.10+ · FastAPI · Uvicorn |
| **Database** | SQLite (development) · PostgreSQL (production) |
| **Image Engine** | OpenCV · Pillow · NumPy |
| **Background Jobs** | ThreadPoolExecutor (dev) · Redis Queue / RQ (production) |
| **Templates** | Jinja2 + Vanilla CSS |
| **Auth** | bcrypt + JWT session cookies |

---

## Project Structure

```
PICTOART/
├── main.py                     # FastAPI application entry point
├── cli.py                      # Admin CLI tool (create-admin, worker, import, export)
├── process_sample.py           # Quick CLI script to run and test a photo
├── debug_masks.py              # Debug utility to inspect masks and sketch output
├── sample_doctors.csv          # Sample CSV for bulk doctor import
├── sample_doctor_photo.jpg     # Sample test portrait photo
├── .env.example                # Environment variable configuration template
├── pyproject.toml              # Dependencies and project metadata
├── src/
│   ├── config.py               # App settings (Pydantic Settings)
│   ├── database.py             # SQLAlchemy engine & session factory
│   ├── models.py               # Database models (Doctor, Submission, AdminUser, AuditLog)
│   ├── schemas.py              # Pydantic request/response schemas
│   ├── storage.py              # Local / S3-compatible file storage manager
│   ├── art_engine/
│   │   ├── art_config.py       # Tunable constants for sketch lines, shading, & canvas
│   │   ├── preprocessor.py     # Image validation & preprocessing
│   │   ├── segmentation.py     # Face detection & subject silhouette segmentation
│   │   ├── sketch.py           # Multi-scale DoG pencil line & graphite shading engine
│   │   └── composer.py         # 300 DPI honorary presentation certificate layout
│   ├── worker/
│   │   ├── jobs.py             # Background sketch generation pipeline
│   │   └── queue.py            # Asynchronous job queue manager
│   ├── routers/
│   │   ├── auth.py             # Admin authentication, hashing, & audit logs
│   │   ├── public.py           # Doctor upload form & direct redirect routes
│   │   └── admin.py            # Admin review dashboard, import, and bulk export
│   ├── templates/              # Jinja2 HTML templates
│   └── static/                 # CSS & client-side assets
├── storage/                    # Uploads & generated outputs (.gitignore managed)
│   ├── originals/              # Original uploaded photos
│   ├── generated/              # Rendered 300 DPI sketch certificates
│   └── exports/                # Bulk exported ZIP archives
└── tests/
    ├── test_api.py             # API route tests
    └── test_core.py            # Core engine, segmentation, & sketch unit tests
```

---

## Quick Start

### 1. Install dependencies

```bash
pip install -e .
```

### 2. Configure environment

Copy `.env.example` to `.env`:

```bash
copy .env.example .env
```

### 3. Create Admin Account

```bash
python cli.py create-admin --email admin@pictoart.com --password admin123
```

### 4. Start the Application

```bash
python main.py
# or
uvicorn main:app --reload
```

The application will be available at: `http://localhost:8000`

---

## Key URLs

- **Doctor Upload Form**: `http://localhost:8000/upload` (automatically opens the active form)
- **Direct Token Form**: `http://localhost:8000/upload/{token}`
- **Admin Dashboard**: `http://localhost:8000/admin/doctors`
- **Admin Login**: `http://localhost:8000/admin/login`

---

## Running Tests

Run the full pytest suite:

```bash
pytest tests/ -v
```

---

## CLI Commands

```bash
# Create admin user
python cli.py create-admin --email admin@pictoart.com --password YourPassword

# Import doctor CSV
python cli.py import-csv sample_doctors.csv

# Run Redis Queue worker (when WORKER_MODE=rq)
python cli.py run-worker

# Export approved certificates to ZIP
python cli.py export-zip --status approved

# View system statistics
python cli.py stats
```
