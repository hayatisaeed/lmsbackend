# Auth & Sessions (Milestone M1)

> **Goal:** Implement unified OTP authentication, cookie-based refresh sessions, rotation with reuse detection, logout, and session introspection per `./docs/users/v1/*.md` (source of truth).

## 0) Scope (Endpoints)

- `POST /api/v1/auth/request-otp`
    
- `POST /api/v1/auth/verify-otp`
    
- `POST /api/v1/auth/refresh`
    
- `POST /api/v1/auth/logout`
    
- `GET /api/v1/auth/session`
    

## 1) Functional Requirements

1. **Unified OTP entry** (`request-otp`)
    
    - Accept `phone` (E.164). Create user if not exists with status **pending_profile** and default role **student**.
        
    - Enforce rate limits: per-phone/day, per-IP/hour; cooldown between sends; CAPTCHA/PoW hook after threshold.
        
    - Send OTP via primary SMS; auto‑failover to fallback provider.
        
    - Response: `{ is_new_user, cooldown_seconds, next_step_hint:"verify_otp" }`.
        
2. **Verify OTP** (`verify-otp`)
    
    - Accept `phone`, `code`, plus `display_name` (required on **first** success) and optional `email`.
        
    - On success: issue **access token** (short TTL) in body and set **refresh cookie** (httpOnly+Secure; `SameSite=Lax` or `None` if configured; `Path=/`; prefer `__Host-` prefix).
        
    - Return `{ access_token, access_expires_in, profile_completion, is_new_user }`.
        
    - Deny if OTP invalid/expired or throttled. Invalidate OTP after successful verify.
        
3. **Refresh** (`refresh`)
    
    - Cookie‑only. Validate refresh token (`iss/aud/exp/iat/jti`, family not revoked).
        
    - **Rotate** on each call: issue new refresh (new `jti`), set cookie; return new access.
        
    - **Reuse detection**: if an old/rotated token is seen again, revoke the **entire family** and respond accordingly.
        
4. **Logout** (`logout`)
    
    - Revoke the current device refresh **family** and clear cookie (expired Set‑Cookie).
        
    - Idempotent; repeated calls are OK.
        
5. **Session Introspection** (`session`)
    
    - Return `{ user {id, phone, display_name, email?, roles[] }, profile_completion, is_new_user }`.
        

## 2) Non‑Functional Requirements

- **Security**: PII never logged; request/response logs redact phone. Tokens validated strictly; short access TTL.
    
- **Observability**: Emit metrics (otp_send_total, otp_throttled_total, jwt_refresh_rotations_total, jwt_reuse_detected_total), structured logs, audit events.
    
- **OpenAPI**: Annotate endpoints; expose `/api/v1/schema` and `/api/v1/docs`.
    
- **CSRF**: Issue `mh_csrf` non‑httpOnly cookie; require `X‑CSRF‑Token` for cookie‑credentialed state‑changing endpoints.
    
- **Rate limiting**: Implement via Redis sliding windows; configurable thresholds from env.
    

## 3) Data & Models (Auth layer only)

- **User**: `id (UUID)`, `phone (unique E.164)`, `display_name`, `email?`, `password_hash?`, `roles[]`, `is_active`, `created_at`.
    
- **OTPCode**: `id`, `phone`, `code_hash`, `purpose='login'`, `expires_at`, `used_at?`, `send_channel='sms'`, `ip?`, `device_fingerprint?`.
    
- **RefreshSession**: `jti`, `user_id`, `issued_at`, `expires_at`, `rotated_from?`, `revoked_at?`, `user_agent?`, `ip?`, `family_id` (if used).
    

> PII fields like `national_id`/`date_of_birth` are out of scope here (Profile milestone).

## 4) Settings & ENV (must read from env)

- `JWT_ACCESS_TTL_SEC` (e.g., 600), `JWT_REFRESH_TTL_SEC` (e.g., 2592000)
    
- `JWT_ISSUER`, `JWT_AUDIENCE`, `JWT_ALG`, and keys (`JWT_PRIVATE_KEY`/`JWT_PUBLIC_KEY` or `JWT_SIGNING_KEY`)
    
- `REFRESH_COOKIE_NAME` (recommend `__Host-mh_rtk`), `CSRF_COOKIE_NAME` (`mh_csrf`), `COOKIE_SAMESITE`
    
- `OTP_LENGTH` (6), `OTP_TTL_SEC` (300), `OTP_COOLDOWN_SEC` (60)
    
- `OTP_MAX_PER_24H_PER_PHONE` (5), `OTP_MAX_PER_HOUR_PER_IP` (20), `OTP_CAPTCHA_THRESHOLD` (3)
    
- `SMS_PROVIDER`, `SMS_FALLBACK_PROVIDER`, `SMS_FROM_SENDER_ID`
    
- `REDIS_URL`, `APP_HOST_URL`, `ALLOWED_ORIGINS`
    

## 5) Redis Keys (suggested)

- Rate limits: `otp:phone:{E164}` with counters/TTL; `otp:ip:{IP}`
    
- Cooldown: `otp:cooldown:{E164}` TTL
    
- Refresh blocklist/family: `rf:revoked:{jti}`; `rf:family:{user_id}:{family_id}` (set of active jtis)
    

## 6) Error Envelope & Codes

Always return non‑2xx errors as:

```json
{ "error": { "code": "<machine_code>", "message": "<safe_message>", "details": {"field": ["msg"]}? }, "request_id": "..." }
```

**Common codes:**

- `invalid_phone`, `otp_throttled`, `otp_invalid_or_expired`
    
- `auth_invalid_refresh`, `auth_rotation_required`, `auth_family_revoked`
    

## 7) Implementation Plan (suggested sequence)

1. **Scaffold** `apps/users/` with DRF routers, settings, urls under `/api/v1`.
    
2. **Models & migrations**: `OTPCode`, `RefreshSession` (and minimal `User` if not present yet in repo).
    
3. **Services**: OTP generator/validator, SMS sender (primary/fallback), refresh manager (rotation, reuse detection), rate limiter.
    
4. **Views/Serializers**: Implement each endpoint using the service layer; validate inputs; set cookies.
    
5. **Middleware**: Request ID injection; CSRF helper for cookie‑credentialed requests; exception handler to standardize error envelope.
    
6. **OpenAPI**: Add drf‑spectacular, tags, components, error schema.
    
7. **Observability**: Metrics counters/histograms; audit events on OTP send/verify, refresh, reuse, logout.
    

## 8) Tests (pytest) — must cover ≥85%

**Unit**

- OTP code lifecycle: generate → TTL → invalid after use.
    
- Rate limiter: per phone/day, per IP/hour, cooldown; boundary tests.
    
- Refresh manager: rotation, reuse detection → family revoke.
    

**API**

- `request-otp`: new user → `is_new_user=true`; existing user; throttle (429) and cooldown in response.
    
- `verify-otp`: missing `display_name` on first success → 400; success sets cookie with flags; invalid/expired code → 401.
    
- `refresh`: rotates cookie; using old token later → 409 with family revoked.
    
- `logout`: clears cookie; subsequent refresh fails.
    
- `session`: returns roles `["student"]` for new user and correct profile flags.
    

**Security**

- Cookie attributes asserted: `httpOnly`, `Secure`, `Path=/`, `SameSite` configured; no Domain when using `__Host-`.
    
- Ensure PII is not present in logs or responses.
    

## 9) OpenAPI (drf‑spectacular)

- Tag: `auth`
    
- Components: `AccessTokenResponse`, `SessionResponse`, `ErrorEnvelope`
    
- Document cookies via `Set-Cookie` response headers; include examples matching `ENDPOINTS_SPEC.md`.
    

## 10) Done Definition

- All acceptance gates in MASTER_PROMPT §5 pass.
    
- Endpoints behave **exactly** as in `ENDPOINTS_SPEC.md`.
    
- CI green with coverage ≥ 85% for `apps/users/auth/*` modules.
    
- Manual curl checks confirm cookie rotation/reuse behavior and error codes.
    

## 11) Out of Scope (for this milestone)

- Identity, Education, Location, Parent endpoints (handled in PROFILE_P0).
    
- Admin role assignment endpoints (RBAC_P0).
    
- Catalog/policy endpoints (POLICY_P0).