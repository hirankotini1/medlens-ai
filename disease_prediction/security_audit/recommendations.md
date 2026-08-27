# Security Hardening & Production Deployment Recommendations

This document details the architectural and security recommendations for moving the **Nexus Pathology Diagnostic Platform** from a local academic / demo environment to staging and potential clinical pilot environments.

---

## 1. Authentication & Identity Management

| Priority | Area | Recommendation | Implementation Strategy |
|:---:|---|---|---|
| **High** | Multi-Factor Authentication (MFA) | Require TOTP or SMS OTP for lab technicians & pathologists. | Integrate `pyotp` or OAuth2/OIDC identity providers (e.g. Keycloak, Auth0). |
| **High** | Patient Identity Verification | Require registered mobile number OTP or government-issued health ID linkage. | Implement SMS gateway verification for patient portal logins. |
| **Medium** | Session Invalidation | Implement token revocation / blacklist stored in Redis. | Add token jti (JWT ID) checking on every request. |

---

## 2. Infrastructure & Network Hardening

| Priority | Area | Recommendation | Implementation Strategy |
|:---:|---|---|---|
| **Critical** | TLS / HTTPS Termination | Enforce TLS 1.3 encryption for all data-in-transit. | Deploy behind Nginx / Cloudflare reverse proxy with HSTS enabled. |
| **High** | Rate Limiting & DoS Protection | Limit login attempts and prediction invocations per IP. | Use `slowapi` middleware or Nginx `limit_req_zone` (e.g., max 10 requests/sec). |
| **High** | Dedicated Database Engine | Migrate from SQLite to PostgreSQL with encrypted storage (TDE). | Replace SQLite with PostgreSQL connection pool (SQLAlchemy + asyncpg). |
| **Medium** | Static Asset Segregation | Serve frontend assets from dedicated CDN / Nginx instance. | Decouple FastAPI backend to API-only server (`api.domain.com`). |

---

## 3. Clinical & Medical AI Governance

| Priority | Area | Recommendation | Implementation Strategy |
|:---:|---|---|---|
| **Critical** | Medical Device Regulation | Adhere to Software as a Medical Device (SaMD) / FDA / CE-IVD guidelines. | Maintain human-in-the-loop validation; ML predictions must never trigger autonomous medical actions. |
| **High** | Data Drift Monitoring | Continuously monitor demographic and clinical feature shifts. | Implement Evidently AI or Prometheus metrics to log feature distributions over time. |
| **High** | Model Explainability | Provide SHAP / LIME feature attribution scores for every tabular prediction. | Add local SHAP waterfall plots in the clinician portal to show why a risk level was calculated. |

---

## 4. Compliance & HIPAA / GDPR Readiness

Before handling real patient identifying health information (PHI):
1. **HIPAA Security Rule**: Encrypt all data at rest (AES-256) and in transit (TLS 1.3). Execute Business Associate Agreements (BAAs) with hosting providers.
2. **Access Control Auditing**: Implement immutable audit logs capturing every user view, report generation, and prediction inspection with timestamp and user ID.
3. **Data Anonymization / De-identification**: Strip direct identifiers (Name, phone, email, SSN/Aadhaar) prior to running automated machine learning pipelines or research exports.
