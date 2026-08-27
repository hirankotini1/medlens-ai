# Security Architecture & Controls

**Nexus Pathology** implements multiple defensive layers to safeguard patient data privacy, enforce role-based access boundaries, and preserve clinical report integrity.

---

## 1. Authentication & Cryptographic Standards

* **Password & Security PIN Hashing:** All administrator passwords and patient access PINs are cryptographically hashed using **PBKDF2-HMAC-SHA256** with 100,000 iterations and high-entropy 16-byte random salts. Plaintext credentials are never stored in the database.
* **HMAC-Signed Bearer Session Tokens:** Successful authentication generates a signed session token encoding the user role (`admin` or `patient`), target subject, and an expiration timestamp (24 hours).
* **Token Verification Middleware:** Every protected API request is validated using `secrets.compare_digest` to prevent timing attacks.

---

## 2. Authorization & Insecure Direct Object Reference (IDOR) Defenses

* **Role-Based Access Control (RBAC):** Administrative endpoints (`/api/patients`, `POST /api/reports`, etc.) strictly enforce `role == 'admin'`. Unauthorized callers receive an immediate `403 Forbidden` response.
* **Patient Isolation:** Patient queries to `/api/reports?patient_id=X` or `/api/reports/{id}` verify that the requesting token's `patient_id` matches the targeted report. Attempting to access another patient's reports or prediction history returns `403 Forbidden`.

---

## 3. Database Security & Injection Defenses

* **Parameterized SQL Queries:** All database interactions across `database.py` use SQLite parameterized queries with `?` placeholders. String concatenation in SQL statements is completely eliminated, neutralizing SQL injection vectors.
* **Database File Isolation:** The SQLite database file (`pathology.db`) and backend Python source files are strictly excluded from the web static mount, preventing direct HTTP downloading.
* **Online Database Backups:** Implements an automated, non-blocking online backup routine (`backup_database()`) utilizing the SQLite Backup API.

---

## 4. Malaria Image Upload Hardening

The `/predict/malaria` endpoint enforces multi-stage security validation:
1. **Extension Check:** Permitted extensions are strictly limited to `.png`, `.jpg`, and `.jpeg`.
2. **MIME-Type Verification:** Validates that incoming `Content-Type` is an image MIME type.
3. **File Size Cap:** Enforces a hard maximum limit of **5 MB** (and minimum of 100 bytes) to prevent Denial-of-Service buffer exhaustion.
4. **OpenCV Memory Decoding:** Image contents are decoded directly from memory buffers using `cv2.imdecode`. Corrupt files or executable scripts renamed with image extensions fail decoding and are rejected with HTTP 400.
5. **Dimension Bounds:** Enforces image dimensions between $20\times20$ and $4096\times4096$ pixels.

---

## 5. Report Integrity & ML Decoupling

* **Immutability Guarantee:** Official laboratory reports in `lab_reports` cannot be modified or overwritten by machine-learning inferences.
* **Isolated Prediction Table:** Predictions are persisted exclusively to `ml_predictions`, ensuring that medical reports remain legally and clinically uncorrupted.
