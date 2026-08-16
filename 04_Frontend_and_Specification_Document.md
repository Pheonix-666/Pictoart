# Frontend & Specification Document
## Project: Doctor Word-Art Certificate Generator

**Version:** 1.0
**Date:** August 12, 2026

---

## 1. Scope

Two distinct frontend surfaces:
1. **Doctor Upload Page** — public, mobile-first, one doctor at a time, accessed via unique link.
2. **Admin Dashboard** — internal, desktop-first, used by vendor staff to manage the full batch of 20,000 doctors.

---

## 2. Doctor Upload Page

### 2.1 Design principles
- Must work well on a phone (most doctors will open this from a WhatsApp link on mobile).
- Minimal friction — under 2 minutes to complete.
- No account creation, no app download.
- Clear, reassuring copy (this is for a professional certificate — should feel credible, not spammy).

### 2.2 Screens/States

**Screen 1 — Welcome & Form**
- Vendor/pharma branding header (logo).
- Pre-filled name field (editable, since names can have typos in the source list).
- Fields:
  - Years of experience (number)
  - Specialization (text)
  - Key achievements / recognitions (multi-line text, with a short helper: "These will appear as part of your artwork — e.g. patients treated, awards, certifications")
  - Photo upload (camera or gallery picker)
- Photo upload area shows a live preview + guidance text: *"For best results: front-facing, well-lit, plain background."*
- Primary CTA: **Submit**

**Screen 2 — Confirmation**
- "Thank you, Dr. [Name] — your certificate artwork is being prepared."
- No further action needed; doctor can close the page.

**Screen 3 — Re-upload (only shown if admin flags an issue)**
- Same link, but the page detects `needs_reupload` status and shows: "We need a clearer photo to prepare your certificate" + upload field only (text fields retained from before).

### 2.3 Validation rules
- Photo: required, JPEG/PNG, max 10MB, minimum resolution check (e.g. 600×600px) client-side before upload.
- Name: required, pre-filled but editable.
- Years of experience: optional but recommended, numeric.
- Achievements text: optional but recommended, reasonable max length (e.g. 500 characters) to keep the art layout readable.

---

## 3. Admin Dashboard

### 3.1 Design principles
- Built for volume — staff will be scanning/acting on hundreds of records per session.
- Table-first UI (not card-heavy) so status is scannable at a glance.
- Every bulk action (import, export) clearly confirms scope before executing (e.g. "This will export 342 approved certificates").

### 3.2 Screens

**Screen 1 — Login**
- Email + password. Simple, no public sign-up (accounts created manually by the primary admin).

**Screen 2 — Doctor List (main view)**
- Table columns: Name, Contact, Status, Date Submitted, Actions.
- Filter/search by name, status (Not submitted / Submitted / Processing / Ready for review / Approved / Needs re-upload).
- Bulk actions: select multiple rows → bulk-approve, bulk-export.
- "Import doctors" button → CSV upload flow (Screen 3).
- "Export approved" button → bulk download flow (Screen 5).

**Screen 3 — Import Doctors**
- CSV upload (template provided for download: `name, contact, [optional pre-known fields]`).
- Preview parsed rows before confirming import.
- On confirm: system creates doctor records + unique tokens, shows a downloadable list of `name + link` pairs for staff to send out manually (or via WhatsApp/email integration, if added later).

**Screen 4 — Doctor Detail / Review**
- Opened by clicking a row in the doctor list.
- Shows: submitted photo (original), submitted text fields, generated art preview (side-by-side).
- Actions: **Approve** / **Request re-upload** (with optional note, e.g. "photo too blurry") / **Regenerate** (re-run the pipeline without needing a new photo, e.g. after a template tweak).

**Screen 5 — Bulk Export**
- Select status filter (typically "Approved") → confirm count → download as ZIP of print-ready files, named by doctor ID/name for the print team.

### 3.3 Status indicators (visual language)
- Not submitted — gray
- Submitted / Processing — blue (in progress)
- Ready for review — yellow (needs admin action)
- Approved — green
- Needs re-upload — red

---

## 4. Visual/Brand Specification

- Doctor upload page and generated certificate should carry consistent vendor/pharma branding — confirm exact logo placement, color palette, and certificate dimensions with the client before finalizing templates (flagged also in the PRD's open questions).
- Generated art template: single style for v1, matching the reference sample's structure — portrait silhouette filled with text, with a dedicated caption area below for name/title/years-of-experience in clean typography (not part of the word-cloud itself, for legibility).

---

## 5. Accessibility & Usability Notes

- Upload form should be usable with basic screen readers (proper labels on all fields).
- Sufficient color contrast on status badges in the admin dashboard (don't rely on color alone — pair with text labels, already reflected in Screen 2 above).
- Support both camera capture and gallery/file picker on mobile photo upload.

---

## 6. Out of Scope for Frontend v1

- Doctor-side accounts/login.
- Multi-language support (confirm with client if needed for a future version).
- In-browser editing/cropping of the uploaded photo (v1 relies on guidance text + validation, not an editing tool).
