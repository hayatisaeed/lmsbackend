# Security

MentorHub API v1 follows OWASP best practices with strict token and cookie handling.

## Token & Session Lifecycle

- **Access Token**: short-lived JWT (default 10 min) returned in responses; stored in memory on the client.
- **Refresh Token**: long-lived JWT or opaque ID sent only as `Set-Cookie` with attributes `httpOnly`, `Secure`, `Path=/`, `SameSite=Lax`. One refresh session per device and rotated on every refresh. Reuse revokes the entire family.
- **Session Introspection** endpoint reports current session and `is_new_user` flag.

## CSRF & CORS

- Double-submit cookie pattern: server issues non-httpOnly CSRF cookie `mh_csrf`; clients echo value in `X-CSRF-Token` header for state-changing requests using cookies.
- CORS restricted via `ALLOWED_ORIGINS`; credentials allowed only for approved Next.js domains.

## Rate Limiting & Abuse Controls

- OTP request throttles: per-phone/day and per-IP/hour plus cooldown; CAPTCHA after threshold.
- Global API limit: 100 req/min/IP by default.

## PII Protection

- `national_id` and `date_of_birth` stored with field-level encryption (key from `DATA_ENCRYPTION_KEY`).
- Sensitive fields never returned in responses and redacted from logs.

## Transport & Storage

- HTTPS enforced with HSTS.
- Secrets supplied via environment variables or secret manager; never committed to repo.
- Logs emitted in structured JSON including `request_id` and audit events (`otp_sent`, `refresh_reuse_detected`, etc.).

## Baseline Policies

- Deny-by-default authorization using DRF permissions and role checks.
- Default catalog mode `browse_only`; details/purchases restricted until profile complete.
- Data retention: OTP artifacts ≤30 days, audit logs ≥180 days.

Operational mitigations and incident playbooks are covered in [RUNBOOKS](RUNBOOKS.md).
