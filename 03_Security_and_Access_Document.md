# Security & Access Document
## Project: Doctor Word-Art Certificate Generator

**Version:** 1.0
**Date:** August 12, 2026

---

## 1. Purpose

This system handles personal data for 20,000 individuals (doctors) — names, contact info, photos, and professional achievement details. This document defines how access is controlled and data is protected, kept intentionally practical for a solo/small dev team to actually implement and maintain.

---

## 2. Data Being Handled

| Data type | Sensitivity | Notes |
|---|---|---|
| Doctor's name | Low-Medium | Public-facing on the certificate anyway |
| Contact info (phone/email) | Medium | Used only to deliver the unique link; not published |
| Photo | Medium | Personal biometric-adjacent data; used only to generate art |
| Achievement/bio text | Low | Provided by the doctor themselves for the certificate |
| Generated art file | Low | Derived, non-reversible to raw photo in terms of exact likeness recovery, but still tied to identity |

**No payment data, medical records, or sensitive health information is collected by this system.**

---

## 3. Access Model

### 3.1 Doctor access (unsecured-by-design, scoped)
- Each doctor accesses their **own record only**, via a unique, non-guessable link (long random token, e.g. UUID v4).
- No login/password for doctors — the link itself is the credential.
- The link only grants access to **that doctor's own submission form** — not to any other doctor's data, and not to any admin function.
- Links should **expire or be invalidated** after successful submission + approval, to prevent stale links being reused or shared.

### 3.2 Admin access (authenticated, role-based)
- Vendor staff log in via **email + password** (hashed, never stored in plaintext — use bcrypt/argon2).
- Recommend adding a simple role split even in v1:
  - **Admin** — full access (import lists, manage users, export data, approve/reject).
  - **Reviewer** — can view/approve/reject submissions but not import lists or manage other admin accounts.
- All admin routes require an authenticated session (session cookie or JWT) — no admin functionality should be reachable without login.
- Use HTTPS everywhere — no exceptions, even in early testing (free certs via Let's Encrypt).

---

## 4. Data Protection Practices

1. **Encryption in transit:** all traffic over HTTPS (TLS). No exceptions for the doctor upload link either — it carries a photo and personal data.
2. **Encryption at rest:** enable at-rest encryption on the database and file storage bucket (both Postgres-managed-hosting and Cloudflare R2/S3 support this by default).
3. **Least privilege:** the web app's database/storage credentials should only have the permissions they actually need (read/write to specific tables/buckets) — not full admin credentials to the infrastructure.
4. **Secrets management:** database passwords, storage keys, and session secret keys stored in environment variables / a secrets manager — never committed to code or version control.
5. **Input validation:** photo uploads restricted by file type (JPEG/PNG only) and size limit (e.g. max 10MB) to prevent abuse; text fields sanitized to prevent injection into the database or rendered output.
6. **Rate limiting:** basic rate limiting on the public upload endpoint to prevent abuse/scraping of doctor tokens (e.g. limit attempts per IP per minute).
7. **Audit trail:** log key admin actions (approve, reject, export, delete) with timestamp + admin user — useful for accountability given this is client (pharma vendor) data.

---

## 5. Data Retention & Deletion

- Define upfront with the client: **how long doctor photos/data are retained after certificates are printed and delivered.**
- Recommended default: retain generated art + minimal record (name, status) for a defined period (e.g. 90 days) for reprint/dispute purposes, then purge raw photos and full contact data unless the client needs them retained longer.
- Provide an admin action to **delete a specific doctor's data** on request (relevant if a doctor asks to be removed — reasonable practice even without a specific regulatory mandate, since this involves personal photos).

---

## 6. Backup & Recovery

- Automated daily backups of the database (doctor records + status) — most managed Postgres providers (Railway, Supabase, Neon) offer this by default on free/low tiers.
- File storage (originals + generated art) should live in a provider with built-in redundancy (Cloudflare R2/S3-compatible) rather than only on a single VPS disk, so a server failure doesn't lose 20,000 doctors' work.

---

## 7. Threats Specifically Relevant to This Project

| Threat | Why it matters here | Mitigation |
|---|---|---|
| Unique upload links leaked/guessed | Someone could upload a fake photo/text under a doctor's name | Use long random tokens (128-bit+), invalidate after use, don't expose tokens in logs |
| Admin credentials compromised | Full access to 20,000 people's personal data + photos | Strong password policy, consider 2FA for admin login even in v1 if feasible |
| Bulk scraping of generated certificates | Competing vendor or unrelated party downloading all doctor photos/art | Admin bulk-export requires authentication; public routes never list or expose other doctors' files |
| Photo storage exposed publicly by misconfiguration | Common cloud mistake (public S3/R2 buckets) | Explicitly set storage buckets to private; serve files only through authenticated app routes, not direct public URLs |

---

## 8. Recommendation for Vendor Company

Before going live with real doctor data, get **written confirmation from the pharma client** on:
- Who legally owns the collected data (vendor vs. pharma company).
- Data retention duration expected.
- Any regulatory/compliance requirements specific to doctors' personal data in the relevant country (this varies by jurisdiction — worth a quick check since doctors' professional data can carry different handling expectations than general consumer data).
