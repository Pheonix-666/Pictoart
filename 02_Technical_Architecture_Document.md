# Technical Architecture Document
## Project: Doctor Word-Art Certificate Generator

**Version:** 1.0
**Date:** August 12, 2026

---

## 1. Architecture Overview

A simple, self-hostable web application with three moving parts: a **web app** (upload form + admin dashboard), a **background worker** (does the actual image processing), and **storage** (files + database). Kept intentionally minimal so one developer can build and maintain it.

```
                        ┌─────────────────────┐
   Doctor's phone  ───▶ │   Web App (FastAPI)  │ ◀─── Admin dashboard
   (unique link)        │  - upload endpoint    │      (staff browser)
                        │  - admin API          │
                        └──────────┬───────────┘
                                   │
                     writes job    │    reads status
                                   ▼
                        ┌─────────────────────┐
                        │   PostgreSQL DB      │
                        │  doctors, jobs,      │
                        │  status, file paths  │
                        └──────────┬───────────┘
                                   │
                          job queued│
                                   ▼
                        ┌─────────────────────┐
                        │  Redis Queue (RQ)    │
                        └──────────┬───────────┘
                                   │
                                   ▼
                        ┌─────────────────────┐
                        │  Background Worker    │
                        │  - OpenCV face/edge   │
                        │    detection          │
                        │  - word-density map    │
                        │  - text placement      │
                        │    render (Pillow)     │
                        └──────────┬───────────┘
                                   │
                                   ▼
                        ┌─────────────────────┐
                        │  File Storage         │
                        │  (Cloudflare R2 / disk)│
                        │  originals + outputs   │
                        └─────────────────────┘
```

---

## 2. Recommended Stack

| Layer | Choice | Why |
|---|---|---|
| Backend/API | **Python + FastAPI** | Simple, fast to build, great docs, same language as the image pipeline (no context-switching) |
| Image processing | **OpenCV + Pillow + NumPy** | Industry-standard, free, well-documented, does exactly what's needed (edge/contour detection, masking, rendering text) |
| Background jobs | **Redis + RQ (Redis Queue)** | Much simpler than Celery for a solo dev, handles "process this doctor's photo" jobs reliably with retries |
| Database | **PostgreSQL** | Handles 20k+ rows easily, free tier available on Railway/Supabase/Neon |
| File storage | **Cloudflare R2** (or local disk if self-hosting on a VPS) | Free egress, cheap storage, S3-compatible API |
| Doctor-facing frontend | **Plain HTML + Tailwind CSS** (server-rendered via FastAPI/Jinja2) | No build step, loads instantly on any doctor's phone, minimal maintenance |
| Admin dashboard | **Simple React (or just server-rendered HTML w/ HTMX)** | Recommend HTMX + Jinja2 for a solo dev — avoids running/maintaining a separate frontend build pipeline |
| Hosting | **A single VPS** (Hetzner/DigitalOcean, ~$6–12/mo) running the web app + worker, or Railway/Render if you prefer managed | Predictable cost, enough power for batch image processing, simple to reason about |

This stack deliberately avoids anything requiring a paid AI API — the art generation is 100% deterministic image processing.

---

## 3. Core Components

### 3.1 Web App (FastAPI)
- **Public routes:** `/upload/{unique_token}` — doctor-facing upload form and submit handler.
- **Admin routes:** `/admin/*` — protected by login, CSV import, dashboard, preview, approve/reject, bulk export.
- **API routes:** internal endpoints used by the dashboard (list doctors, get status, trigger regenerate).

### 3.2 Database Schema (simplified)

**`doctors`**
- `id` (PK)
- `name`
- `contact` (phone/email)
- `unique_token`
- `years_experience`, `achievements_text`, `specialization` (free text fields)
- `status` (enum: not_submitted, submitted, processing, ready_for_review, approved, needs_reupload)
- `created_at`, `updated_at`

**`submissions`**
- `id` (PK)
- `doctor_id` (FK)
- `original_photo_path`
- `generated_art_path`
- `attempt_number`
- `created_at`

**`admin_users`**
- `id`, `email`, `password_hash`, `role`

### 3.3 Background Worker
Picks up jobs from the Redis queue, one per doctor submission:
1. Load original photo.
2. Run face/contour detection (OpenCV) to get a clean silhouette/shape mask.
3. Build a density map from the photo (darker regions = denser text).
4. Place the doctor's name/achievement text repeatedly along that density map (word-cloud-style placement algorithm) to fill the silhouette.
5. Composite onto the certificate template (background, borders, logos as needed).
6. Render at print resolution (300 DPI equivalent) and save to storage.
7. Update doctor status to `ready_for_review`.

### 3.4 File Storage
- Two buckets/folders: `originals/` (raw doctor uploads) and `generated/` (final art).
- Files named by `doctor_id` for predictable bulk export.

---

## 4. Processing Pipeline Detail (the actual "art engine")

This is the core IP of the project — a **text-density portrait generator**:

1. **Preprocessing:** resize/normalize the uploaded photo, convert to grayscale.
2. **Silhouette/shape extraction:** use OpenCV contour or face-landmark detection to isolate the subject from the background (or ask doctors to upload against a plain background to simplify this step for v1).
3. **Density mapping:** convert grayscale intensity into a "how much text should go here" map — darker areas (hair, eyebrows, shadows) get denser text, lighter areas (cheeks, forehead) get sparser text.
4. **Text pool generation:** build the pool of words to place, drawn from: name, years of experience, achievements, specialization, repeated/varied in size and rotation for visual richness (this mirrors the reference sample's style).
5. **Placement algorithm:** iteratively place words following the density map (similar approach to Python's `word_cloud` library, adapted to use a custom photo-derived mask instead of a generic shape).
6. **Rendering:** compose the final image with consistent branding (borders, vendor/pharma logos) via Pillow.
7. **Export:** save as print-ready high-res PNG/PDF.

---

## 5. Scaling Considerations for 20,000 Images

- Processing is **queued and asynchronous** — doctors upload independently over days/weeks, so there's no need to process all 20k at once.
- A single worker process can handle this comfortably; if turnaround time matters, run **multiple worker processes** in parallel (RQ supports this natively) — a modest VPS can run 2–4 workers.
- Estimate: if generation takes ~30–60 seconds per image, 4 parallel workers process ~20,000 images in roughly 2–4 days of continuous processing — comfortably within a typical order timeline.
- Storage: 20,000 original + generated high-res images will land in the tens of GB range — well within affordable object storage tiers.

---

## 6. Environments

- **Local dev:** SQLite substitute for Postgres optional, local Redis, local file storage — keeps early development free and simple.
- **Staging:** small VPS or free-tier managed services, used to test the full doctor-submission flow before going live.
- **Production:** VPS (or managed Postgres/Redis) sized to handle concurrent uploads + background processing.

---

## 7. Key Technical Risks

| Risk | Mitigation |
|---|---|
| Poor-quality doctor photos break the silhouette extraction | Add client-side guidance + basic validation (min resolution, face-detection check before accepting upload) |
| Processing bottleneck at scale | Async queue + horizontally scalable workers; process is embarrassingly parallel (each doctor independent) |
| Doctors abandon upload halfway | Save partial text data as soon as entered; only photo/final submit is required to complete |
| Inconsistent output quality across styles of photos (background clutter, lighting) | v1 constraint: request plain-background, front-facing photos; consider adding automatic background removal as a v1.1 enhancement |
