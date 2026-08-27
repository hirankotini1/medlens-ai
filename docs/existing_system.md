# Existing System vs. Proposed System

---

## 1. Existing System Analysis

In conventional small-to-medium diagnostic laboratories and clinic setups, laboratory reporting and pathology management typically exhibit the following characteristics:

| Dimension | Existing System | Limitations |
|---|---|---|
| **Record Keeping** | Physical paper slips, Excel sheets, or local Word templates. | High risk of record loss, duplication, transcription errors, and lack of searchability. |
| **Patient Access** | In-person physical collection or unencrypted email attachments. | Inconvenient for patients; risk of email interception or misdirected sensitive health records. |
| **Diagnostic Support** | Purely manual inspection of parameter numbers against reference charts. | Increased cognitive load during high-throughput sample processing; subtle multi-parameter patterns may be overlooked. |
| **Data Integrity** | Reports can be casually edited or overwritten without audit tracking. | Lack of version control; no historical trail of revisions or amendments. |
| **Security & Privacy** | Minimal access control; shared generic login credentials or unauthenticated URLs. | Vulnerable to unauthorized access, cross-patient data exposure, and SQL injection vulnerabilities. |

---

## 2. Proposed System (Nexus Pathology)

**Nexus Pathology** introduces an integrated, secure, and structured web architecture that addresses these limitations:

```
+-----------------------------------------------------------------------------+
|                           NEXUS PATHOLOGY PLATFORM                          |
+-----------------------------------------------------------------------------+
|  1. Centralized SQLite Database with Parameterized Queries                  |
|  2. Role-Based Access Control (Admin / Staff vs. Patient Portal)             |
|  3. Structured Clinical Reporting with Reference Ranges & Dynamic Flags      |
|  4. Decoupled Experimental ML Decision Support (5 Specialized Pipelines)     |
|  5. Cryptographic PBKDF2 Hashing & Signed HMAC Bearer Session Tokens         |
|  6. Immutable ML Prediction Audit Logging & Online Database Backups          |
+-----------------------------------------------------------------------------+
```

### Key Comparative Advantages

| Feature | Existing Conventional System | Proposed Nexus Pathology Platform |
|---|---|---|
| **Data Storage** | Dispersed files / Flat sheets | Centralized relational SQLite DB with foreign key constraints |
| **Patient Privacy** | Unsecured / Publicly reachable | Isolated patient session tokens (IDOR prevention) |
| **Input Validation** | Ad-hoc / Free-form text | Strict Pydantic schemas validating physiological ranges |
| **Decision Support** | None / External disconnected tools | Built-in, decoupled ML decision-support pipelines |
| **Report Decoupling** | N/A | Official lab findings are strictly immutable by ML analysis |
| **Audit Trail** | None | Independent `ml_predictions` audit table with input snapshots |
| **Image Analysis** | Manual microscopy inspection only | Integrated OpenCV feature extractor + Gradient Boosting for Malaria |
| **Print Capability** | Basic print without formatting | Dedicated `@media print` layout formatting official pathology sheets |
