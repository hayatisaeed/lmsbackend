# Auth + Profile + People foundation

## TL;DR

Phone‑only, OTP‑based **unified sign‑in** with **backend‑owned cookies**. Refresh lives in **httpOnly + Secure** cookie (one session per device); access token is short‑lived (header). **display_name is required** during first successful OTP verify (no auto‑gen). Parent verification is **required only for minors**. Courses visibility is **admin‑configurable** (default: browse allowed; purchases/view details restricted until profile complete).

---

## 1) Environment Configuration (12‑Factor)

> All config via environment variables; no secrets in code or images.

|Key|Purpose|Example / Notes|
|---|---|---|
|`APP_ENV`|Environment name|`local`, `staging`, `prod`|
|`APP_HOST_URL`|Public base URL|Used for CORS & cookie domain decisions|
|`ALLOWED_ORIGINS`|CORS allowlist|Comma‑sep list of Next.js origins|
|`COOKIE_SAMESITE`|Cookie attr|`Lax` (default) or `None` if cross‑site SSO is needed|
|`REFRESH_COOKIE_NAME`|Refresh cookie|Recommend `__Host-mh_rtk` (requires no Domain, Path=/)|
|`CSRF_COOKIE_NAME`|CSRF cookie|e.g., `mh_csrf` (non‑httpOnly)|
|`JWT_ISSUER` / `JWT_AUDIENCE`|JWT claims|Match frontend origin(s)|
|`JWT_ACCESS_TTL_SEC`|Access TTL|e.g., `600` (10 min)|
|`JWT_REFRESH_TTL_SEC`|Refresh TTL|e.g., `2592000` (30 days)|
|`JWT_ALG`|Signing algorithm|`HS256` or `RS256` (prefer asymmetric in prod)|
|`JWT_PRIVATE_KEY` / `JWT_PUBLIC_KEY`|Keys|If using RS256; store in KMS/Secrets Manager|
|`JWT_SIGNING_KEY`|Symmetric key|If using HS256; rotate regularly|
|`SESSION_MAX_DEVICES`|Max concurrent device sessions|e.g., `5` (enforced by refresh family tracking)|
|`OTP_LENGTH`|Digits|`6`|
|`OTP_TTL_SEC`|Code lifetime|`300` (5 min)|
|`OTP_COOLDOWN_SEC`|Min gap between sends per phone|e.g., `60`|
|`OTP_MAX_PER_24H_PER_PHONE`|Abuse cap|e.g., `5`|
|`OTP_MAX_PER_HOUR_PER_IP`|Abuse cap|e.g., `20`|
|`OTP_CAPTCHA_THRESHOLD`|After N sends, require CAPTCHA|e.g., `3`|
|`SMS_PROVIDER`|Primary SMS|`kavenegar`, `twilio`, etc.|
|`SMS_FALLBACK_PROVIDER`|Fallback SMS|Different vendor/route|
|`SMS_FROM_SENDER_ID`|Sender ID|As per provider|
|`IDENTITY_API_BASE_URL`|External identity lookup|Used by Identity step|
|`IDENTITY_API_TIMEOUT_MS`|HTTP timeout|e.g., `2500`|
|`DB_URL`|Database DSN|Postgres recommended|
|`REDIS_URL`|Cache/ratelimit/blocklist|Redis|
|`LOG_LEVEL`|Logging|`INFO` default|
|`SENTRY_DSN`|Error monitoring|Optional|
|`OTEL_EXPORTER_OTLP_ENDPOINT`|Traces/Metrics|Optional|
|`METRICS_PORT`|Prometheus exporter|e.g., `9000`|
|`DATA_ENCRYPTION_KEY`|Field‑level encryption|KMS‑backed; for National ID & DoB|
|`FEATURE_CATALOG_EXPOSURE_MODE`|Catalog visibility policy|`browse_only`, `locked`, `open` (see §4)|

> **Secrets**: Load via platform secrets (AWS SSM/Secrets Manager, GCP Secret Manager, Vault). Never commit.

---

## 2) Cookie & Token Strategy

- **Access Token**: Short‑lived JWT, returned in response body, stored **in memory** on the client, sent via `Authorization: Bearer`.
    
- **Refresh Token**: Long‑lived JWT (or opaque ID mapped to server session) sent **only** as `Set‑Cookie` with attributes:
    
    - `httpOnly`, `Secure`, `Path=/`, `SameSite=Lax` (or `None` if truly cross‑site), ideally `__Host-` prefix (no `Domain`, `Path=/`).
        
    - **One refresh per device**: each browser/device gets its own refresh session (tracked by `jti`, with UA/IP metadata). Enforce `SESSION_MAX_DEVICES`.
        
    - **Rotation on every refresh**; reuse detection ⇒ revoke family.
        
- **CSRF** (for cookie‑credentialed requests):
    
    - Double‑submit cookie pattern: server issues non‑httpOnly `mh_csrf`. Client echoes in `X-CSRF-Token` for state‑changing requests that rely on cookies.
        
    - Access‑token‑only requests (Authorization header) are not subject to CSRF, but we still recommend CSRF cookie issuance for uniformity.
        

---

## 3) Feature Flags & Admin‑Configurable Policies

- `FEATURE_CATALOG_EXPOSURE_MODE` (default `browse_only`):
    
    - `browse_only`: unauth or incomplete profiles can see **course lists** but **cannot view details or purchase**.
        
    - `locked`: catalog hidden until profile completion.
        
    - `open`: full view allowed; purchases still restricted until profile completion.
        
- `FEATURE_REQUIRE_PARENT_FOR_MINORS` (default `true`): derived from DoB < age threshold (configurable, default 18).
    
- `FEATURE_OPTIONAL_PASSWORD` (default `true`): users may add password post‑OTP.
    
- `FEATURE_DYNAMIC_BRANCHES` (default `true`): Study branches are admin‑managed content.
    

---

## 4) Security Baselines (OWASP ASVS/Top‑10)

- **AuthN/Z**: Deny‑by‑default; DRF permissions by role; JWT `iss/aud/exp/iat/jti` validated; refresh family blocklist.
    
- **PII**: Field‑level encryption (National ID, DoB). Strict serializer filtering (never return encrypted fields). Redact in logs.
    
- **Transport**: HTTPS + HSTS; secure cookies only; CORS allowlist with `credentials=true`.
    
- **Abuse Controls**: OTP per‑phone/day & per‑IP/hour; cooldown; CAPTCHA after threshold; ASN/country throttling hooks.
    
- **Sessions**: Device‑scoped refresh; rotation; family revocation on logout, reuse or suspicious activity.
    
- **Supply Chain**: Pinned dependencies; pre‑commit (ruff/black/isort/bandit); SCA in CI.
    

---

## 5) Observability & SLOs

- **Health**: `/healthz` (process up), `/readyz` (DB/Redis/SMS/Identity reachable), `/metrics` (Prometheus).
    
- **Logs**: JSON structured; include `request_id`, `user_id`, `ip`, `ua`, `route`, `latency_ms`, `status`, and security events.
    
- **Traces**: OpenTelemetry middleware; span per request; external calls instrumented (SMS, Identity API).
    
- **Metrics** (key examples):
    
    - `otp_send_total{provider=,status=}`; `otp_send_latency_ms` histogram.
        
    - `otp_throttled_total`, `otp_invalid_total`, `otp_expired_total`.
        
    - `jwt_refresh_rotations_total`, `jwt_reuse_detected_total`.
        
    - `profile_completion_ratio`, `identity_attempts_per_user`.
        
    - `catalog_blocked_views_total`, `purchases_blocked_total` (policy impact).
        
- **SLOs**:
    
    - OTP delivery success ≥ **98%** 5‑min rolling.
        
    - Auth API P95 < **300 ms** (excluding SMS latency).
        
    - Refresh rotation reuse rate < **0.1%** of total refreshes.
        
- **Alerts** (examples):
    
    - OTP failure rate > 3% for 10 min.
        
    - Redis unavailable or connection pool saturation.
        
    - Identity API error rate > 5%.
        
    - JWT reuse detected spikes.
        

---

## 6) Runbooks

### 6.1 OTP Delivery Incident

1. Check dashboard: `otp_send_total`, failure ratio, provider errors.
    
2. If failure rate > threshold, **switch to fallback** (`SMS_FALLBACK_PROVIDER`).
    
3. Increase `OTP_COOLDOWN_SEC` and enable CAPTCHA (if available) for new attempts.
    
4. Communicate status to frontend (banner/maintenance flag).
    
5. Post‑mortem: root cause, provider SLA credits, update routing rules.
    

### 6.2 JWT Key Rotation (RS256) / Signing Key Rotation (HS256)

1. Add new key with `kid` and start signing new tokens with it while accepting old.
    
2. Maintain dual‑verify for at least one full refresh TTL.
    
3. Invalidate old `kid` after overlap; monitor 401/419 errors.
    

### 6.3 Token Compromise / Reuse Detected

1. Revoke **refresh family** for affected `jti` and user.
    
2. Force logout: return `Set‑Cookie` expired for refresh.
    
3. Require OTP re‑auth; verify recent activity; optionally lock account temporarily.
    

### 6.4 Abuse / Mass OTP Attack

1. Tighten per‑IP & per‑phone limits; raise cooldown.
    
2. Enable CAPTCHA/PoW; block abusive ASNs/countries temporarily.
    
3. Notify stakeholders; keep audit of blocked attempts.
    

### 6.5 Identity API Outage / Degradation

1. Mark identity verification as **deferred**; queue retries with exponential backoff.
    
2. Inform users the step is delayed; do **not** expose sensitive data.
    
3. When restored, process queue; if consistent failure, open support ticket.
    

### 6.6 Redis Down (Rate limit / Blocklist)

1. Flip service to **conservative mode**: deny OTP send beyond minimal threshold; disable refresh rotation temporarily with strict reuse detection (if safe), or fail closed.
    
2. Restore Redis; re‑enable normal policies.
    

### 6.7 Database Migration Playbook

1. Blue‑green or zero‑downtime style: add nullable columns first; backfill; switch reads; remove old columns.
    
2. Run read‑only checks on `/readyz` before rollout.
    
3. Rollback plan ready (schema down migration tested).
    

### 6.8 Stale Pending Registrations Cleanup

- Users who requested OTP but **did not finish display_name step**: retain phone for analytics; mark `status=pending_profile` with `created_at`.
    
- Cron/periodic job: after N days (configurable), **soft‑delete** or archive.
    

---

## 7) Operational Policies

- **Data Retention**: OTP artifacts ≤ 30 days; audit logs ≥ 180 days; identity submissions (PII) retention per legal requirements.
    
- **Backups**: Daily snapshots (DB); restore test monthly.
    
- **Access Control**: Production DB read access only via bastion; audit every role change.
    
- **Admin Actions**: Role assignment, branch & olympiad management, policy toggles logged as audit events.
    

---

## 8) Startup & Smoke Checklist

1. Environment set with required variables (see §1).
    
2. `/healthz` = 200; `/readyz` = 200 (DB/Redis/SMS/Identity green).
    
3. Request OTP → Verify OTP → receive access token and refresh cookie.
    
4. Verify CSRF cookie present and `X‑CSRF‑Token` required for cookie‑credentialed POST/PUT/PATCH/DELETE.
    
5. Confirm policy flag `FEATURE_CATALOG_EXPOSURE_MODE` behavior end‑to‑end.
    

---

## 9) Governance & Compliance

- Maintain records of parental consent for minors; verifiable timestamps.
    
- PII encryption key lifecycle managed in KMS (rotation & access audit).
    
- Data export/delete workflows to be defined in Privacy spec (future doc).
    

---

## 10) Change Management

- Every policy/config change captured in **Config Changelog** (who, what, when, old→new).
    
- Versioned OpenAPI; deprecations announced 90 days in advance.
    

---

## 11) Next Steps

- Lock final CORS origins and cookie `SameSite` mode.
    
- Choose JWT algorithm (prefer RS256 in prod) and set up automated key rotation.
    
- Finalize OTP thresholds for your traffic profile (per‑market tuning).
    
- Approve SLOs & alert thresholds and wire dashboards.