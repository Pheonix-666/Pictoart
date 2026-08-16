# Product Requirements Document (PRD)
## Project: Doctor Word-Art Certificate Generator

**Client:** Pharma photo-frame/certificate vendor company
**Prepared for:** Internal dev use
**Version:** 1.0
**Date:** August 12, 2026

---

## 1. Background

The vendor company produces physical photo-frames with printed certificates for pharma companies to gift to doctors. A new order requires **20,000 customized certificates**, each featuring a **word-cloud style typographic portrait** of the individual doctor — a portrait made entirely out of text (their name, years of experience, specializations, achievements, patient stats, etc.) shaped into their likeness — instead of a plain photo.

Doing this manually per doctor is not feasible at this scale. The project is to build software that automates conversion of a doctor's photo + biographical text into this art style, ready for print.

---

## 2. Problem Statement

- 20,000 doctors, each with a unique photo and unique achievement text, need a personalized word-art portrait generated and prepared for certificate printing.
- The vendor company does not have the photos in hand — each doctor holds their own photo.
- Manual design (like the reference sample) is too slow and expensive at this volume.
- Output must be print-ready (high resolution) and visually consistent in template/branding across all 20,000 certificates.

---

## 3. Goals

1. Let each doctor submit their own photo + details without the vendor manually collecting/organizing 20,000 files.
2. Automatically generate a word-cloud portrait for each doctor using their photo (for the shape/likeness) and their text (name, years of experience, achievements, specialization) as the "ink."
3. Give the vendor's staff a dashboard to track submissions, preview outputs, approve/regenerate, and bulk-export print-ready files.
4. Keep the whole system operable by a small/solo dev team with minimal ongoing cost.

## 4. Non-Goals (out of scope for v1)

- Multiple art style templates (v1 ships with **one** template, per stakeholder decision).
- AI-generated (diffusion-model) art — this is a deterministic text-density portrait, not generative AI.
- Doctor-side account creation/login system (unique links replace this).
- Physical printing/frame assembly — software ends at producing a print-ready file.

---

## 5. Users & Roles

| Role | Who | What they do |
|---|---|---|
| **Doctor** (submitter) | The individual doctor being featured | Opens their unique link, uploads a photo, confirms/edits their name & achievement text, submits |
| **Vendor Admin/Staff** | Vendor company employees | Uploads the master doctor list, generates/sends unique links, monitors submission status, previews generated art, approves or requests re-upload, bulk-downloads final print files |
| **System** | The software itself | Generates unique links, runs the word-art generation pipeline, stores files, tracks status |

---

## 6. User Flow

### Doctor flow
1. Doctor receives a unique link via WhatsApp/email (sent manually by vendor staff, exported from the dashboard).
2. Opens link → sees a simple page pre-filled with their name (editable) and empty fields for: years of experience, key achievements/specializations, optional patient/education stats.
3. Uploads one clear front-facing photo (with live preview + basic guidance: "well-lit, front-facing, plain background works best").
4. Submits. Sees a confirmation screen ("Your certificate is being prepared").

### Admin flow
1. Admin logs into the dashboard.
2. Bulk-imports the doctor master list (name + phone/email, via CSV upload) — system generates a unique upload link per doctor.
3. Exports the list of links to send out (or system can trigger WhatsApp/email sending, if integrated later).
4. Dashboard shows live status per doctor: **Not submitted / Submitted / Processing / Ready for review / Approved / Needs re-upload**.
5. Admin previews generated art per doctor; can approve or flag for re-upload (e.g., blurry photo).
6. Once approved, certificate is queued for the print-ready export.
7. Admin can bulk-download all approved, print-ready files (e.g., as a ZIP or triggered batch export).

---

## 7. Functional Requirements

1. **Bulk doctor import** — CSV upload with name, contact, and any pre-known bio fields.
2. **Unique link generation** — one secure, non-guessable link per doctor tied to their record.
3. **Doctor-facing upload form** — mobile-friendly, photo upload + text fields, client-side validation (file type/size, required fields).
4. **Word-art generation pipeline** — takes photo + text, outputs a high-resolution word-cloud portrait matching the reference template style.
5. **Status tracking** — every doctor record has a visible state throughout the pipeline.
6. **Admin review dashboard** — searchable/filterable list, per-doctor preview, approve/reject/regenerate actions.
7. **Bulk export** — approved, print-ready files downloadable in bulk, named predictably (e.g., by doctor ID/name) for the print team.
8. **Re-upload handling** — if a photo is rejected (poor quality/wrong photo), doctor can be sent a fresh link to resubmit without losing their original text data.

---

## 8. Non-Functional Requirements

- **Scale:** must reliably handle 20,000 doctor records and photo uploads without manual bottlenecks.
- **Print quality:** final output must be high-resolution (300 DPI equivalent) and suitable for physical printing at certificate size.
- **Performance:** individual art generation should complete within a couple of minutes per doctor, processed in the background so it doesn't block uploads.
- **Reliability:** no doctor's submission should be lost; failed generations should be retryable.
- **Cost:** system should run on free/low-cost infrastructure (see Technical Architecture doc).
- **Simplicity:** built and maintainable by a solo/small developer, minimal moving parts.

---

## 9. Success Criteria

- All 20,000 doctors are able to self-submit via their link without vendor staff manually handling files.
- Admin can process the full batch to "approved & exported" state without needing custom one-off scripts per doctor.
- Generated art visually matches the quality/style of the reference sample.
- Vendor can go from "doctor submitted" to "print-ready file" with a handful of clicks, not manual design work.

---

## 10. Open Questions (to confirm with client before build)

- Exact certificate print dimensions (needed to fix output resolution/aspect ratio).
- Branding elements required on the certificate beyond the word-art (logos, borders, pharma company name)?
- How will links actually be distributed to doctors — WhatsApp Business API, email, or manual copy-paste by vendor staff?
- Who owns/hosts the doctors' personal data (photos, names) after the project — data retention expectations?
