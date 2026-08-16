# Feature Ticket List
## Project: Doctor Word-Art Certificate Generator

**Version:** 1.0
**Date:** August 12, 2026

Organized by build phase. Each ticket is scoped to be independently buildable/testable — a practical order for a solo developer to work through.

---

## Phase 0 — Project Setup

- **TICKET-001:** Set up FastAPI project skeleton, environment config, and local dev environment (Postgres, Redis running locally).
- **TICKET-002:** Set up database schema/migrations for `doctors`, `submissions`, `admin_users`.
- **TICKET-003:** Set up file storage integration (Cloudflare R2 or local disk abstraction) with a simple upload/download interface.
- **TICKET-004:** Set up background worker skeleton (RQ) with a test job to confirm the queue pipeline works end-to-end.

## Phase 1 — Doctor Upload Flow

- **TICKET-005:** Build unique token generation logic tied to doctor records.
- **TICKET-006:** Build public upload page UI (Screen 1: form + photo upload, mobile-first).
- **TICKET-007:** Build client-side validation (file type/size/resolution, required fields).
- **TICKET-008:** Build submit endpoint — saves doctor's text fields + original photo, updates status to `submitted`, queues generation job.
- **TICKET-009:** Build confirmation screen (Screen 2).
- **TICKET-010:** Build re-upload flow (Screen 3) — detect `needs_reupload` status and show correct UI.

## Phase 2 — Art Generation Engine (core IP)

- **TICKET-011:** Implement photo preprocessing (resize, normalize, grayscale conversion).
- **TICKET-012:** Implement silhouette/contour extraction from photo (OpenCV).
- **TICKET-013:** Implement density map generation from grayscale intensity.
- **TICKET-014:** Implement text-pool builder (assemble words/phrases from doctor's name, experience, achievements).
- **TICKET-015:** Implement word-placement algorithm following the density map (adapt/extend word-cloud placement logic to a custom photo-derived mask).
- **TICKET-016:** Implement final composition — overlay onto certificate template with branding, borders, caption area (Pillow).
- **TICKET-017:** Implement high-resolution export (print-ready PNG/PDF, confirm DPI/dimensions with client).
- **TICKET-018:** Wire the full pipeline into the background worker — on job pickup, run steps 011–017, update doctor status to `ready_for_review`, handle failures with retry logic.
- **TICKET-019:** Add basic photo quality pre-check (e.g. face-detection confidence threshold) to catch bad uploads before they hit the full pipeline.

## Phase 3 — Admin Dashboard

- **TICKET-020:** Build admin login/authentication (email + password, hashed, session/JWT).
- **TICKET-021:** Build role-based access (Admin vs Reviewer) if implementing in v1.
- **TICKET-022:** Build CSV import flow — parse, preview, confirm, bulk-create doctor records + tokens (Screen 3).
- **TICKET-023:** Build exportable list of `name + unique link` for staff to send out manually.
- **TICKET-024:** Build doctor list/table view with filter, search, status badges (Screen 2).
- **TICKET-025:** Build doctor detail/review screen — side-by-side original photo vs. generated art (Screen 4).
- **TICKET-026:** Build Approve / Request re-upload / Regenerate actions on the detail screen.
- **TICKET-027:** Build bulk-select + bulk-approve on the list view.
- **TICKET-028:** Build bulk export flow — filter by status, confirm count, download ZIP of print-ready files named by doctor ID (Screen 5).
- **TICKET-029:** Build admin action audit log (who approved/rejected/exported what, and when).

## Phase 4 — Security & Hardening

- **TICKET-030:** Enforce HTTPS across all routes (public + admin), set up TLS certs (Let's Encrypt).
- **TICKET-031:** Add rate limiting on the public upload endpoint.
- **TICKET-032:** Add input sanitization on all text fields (achievement text, name, etc.).
- **TICKET-033:** Set storage buckets to private; serve files only through authenticated app routes.
- **TICKET-034:** Set up automated daily database backups.
- **TICKET-035:** Implement token invalidation after successful approval (prevent stale link reuse).
- **TICKET-036:** Implement data deletion action (remove a specific doctor's data on request).

## Phase 5 — QA & Launch Readiness

- **TICKET-037:** End-to-end test: import 10 sample doctors → each submits → review → approve → bulk export, confirm output quality.
- **TICKET-038:** Load-test the generation pipeline with parallel workers to estimate real throughput for 20,000 images.
- **TICKET-039:** Confirm print-ready output specs (dimensions, DPI, color profile) against an actual physical print sample.
- **TICKET-040:** Write a short internal runbook for vendor staff (how to import, send links, review, export) — non-technical, screenshot-based.

---

## Suggested Build Order Priority

1. Phase 0 → 1 → 2 first (get one doctor's photo turning into art, end-to-end, before building the full admin dashboard).
2. Phase 3 once the core pipeline is proven on a handful of real sample photos.
3. Phase 4 before any real doctor data is collected.
4. Phase 5 right before the actual 20,000-doctor rollout begins.
