
## TL;DR

Service-oriented Django + DRF API with Redis for rate limiting & token/session support, Postgres for persistence, and external SMS + Identity providers. Phone‑only, OTP‑based **unified sign‑in** with **backend‑owned refresh cookies** (one refresh per device) and short‑lived access tokens in headers. Profile completion gates (identity → education → location → parent-for-minors) drive access. Catalog exposure is policy‑driven and admin‑configurable.

---

## 1) High-Level Architecture

```
+---------------------------+            +-----------------------------+
|        Next.js FE         |            |  Admin (Ops/Backoffice UI)  |
| - SPA/SSR pages           |            | - Roles/Users/Taxonomies    |
| - Stores access in memory |            | - Policy toggles            |
+-------------+-------------+            +---------------+-------------+
              |  HTTPS (JWT access in header, refresh cookie auto-sent)
              v
+-------------+--------------------------------------------------------+
|                        MentorHub API (Django + DRF)                  |
|  - Auth & Session (OTP, refresh rotation, CSRF)                      |
|  - Profile & Onboarding (identity/education/location/parent)         |
|  - People & RBAC (roles & permissions)                               |
|  - Policy Service (catalog exposure)                                 |
|  - Observability (logs/metrics/traces)                               |
+-------------+---------------------+----------------+-----------------+
              |                     |                |
              |                     |                |
              v                     v                v
+-------------+-------------+  +----+---------+  +---+----------------+
|    Postgres (RDS)        |  |  Redis       |  | External Providers |
| - Users, Profile, Taxo.  |  | - Rate limit |  | - SMS (primary+fb) |
| - OTP/Audit/RefreshSess. |  | - Token BL   |  | - Identity API     |
+--------------------------+  | - Caches     |  +---------------------+
                              +--------------+
```

**Key responsibilities**

- **DRF API**: Enforces RBAC, profile gates, and policy controls.
    
- **Postgres**: Source of truth for users, profile, sessions, audit log, taxonomies (levels, branches, olympiads).
    
- **Redis**: Sliding‑window rate limiting, OTP counters, refresh blocklist/families, lightweight caches.
    
- **Providers**: SMS (primary + fallback), Identity verification service.
    

---

## 2) Component Breakdown

1. **Auth Service**
    
    - Unified OTP entry (`request-otp`), verify flow (collects `display_name`, optional `email` on first success), access/refresh issuance, refresh rotation, logout (family revoke), session introspection.
        
    - CSRF double‑submit cookie for cookie‑credentialed requests.
        
    - Device session tracking: one refresh per device, capped by policy (`SESSION_MAX_DEVICES`).
        
2. **Profile Service**
    
    - IdentityInfo: encrypted national_id & DoB, external verification, attempt rate limiting (5/24h), minor status derivation.
        
    - Education: level/grade validation, high‑school branch requirement, olympiad M2M (≤3, unique, published only).
        
    - Location: province/city.
        
    - ParentContact: OTP verification required **only for minors**.
        
3. **People & RBAC**
    
    - Role assignment (student default; teacher, mentor, staff_admin, superadmin).
        
    - Deny‑by‑default permission checks; staff_admin endpoints protected.
        
4. **Policy Service**
    
    - Catalog exposure: modes `browse_only` (default), `locked`, `open`. Frontend probes `/policy/catalog-exposure` to shape UI.
        
5. **Observability**
    
    - Health/readiness endpoints, structured JSON logs, Prometheus metrics, OpenTelemetry tracing.
        

---

## 3) Data Storage & Indexing

- **Postgres**
    
    - `users`: PK UUID; unique index on phone (E.164), optional unique on email.
        
    - `refresh_sessions`: index on `user_id`, `revoked_at is null`, `expires_at`; store `jti`, UA, IP, chain (`rotated_from`).
        
    - `otp_codes`: `phone`, `expires_at`, `used_at`; minimal retention.
        
    - `identity_info`: encrypted columns; index on `user_id`.
        
    - `educational_profile`: composite unique `(user_id)`; FK to level/branch.
        
    - `olympiads`: indexed by `published`, include static `olympiad_degree`.
        
    - `audit_events`: append‑only; index by `actor_id`, `created_at`, `type`.
        
- **Redis**
    
    - Keys for rate limits: `otp:phone:{E164}`, `otp:ip:{IP}` with TTLs.
        
    - Token family/blocklist: `rf:family:{user}:{family_id}`, `rf:revoked:{jti}`.
        
    - Short‑term caches: taxonomy lists with low TTL.
        

---

## 4) Authentication & Session Lifecycle

- **Access token**: Short TTL (e.g., 10 min). Sent only in Authorization header; not persisted by server.
    
- **Refresh token**: Long TTL (e.g., 30 days). **httpOnly + Secure** cookie (prefer `__Host-` prefix). Rotated on every refresh.
    
- **Rotation & Reuse detection**
    
    - Each refresh has `jti` and belongs to a **family**. On refresh: issue new token, store new `jti`, mark previous as rotated. If a rotated/old token is observed, **revoke the entire family** and require OTP re‑auth.
        
- **Device sessions**
    
    - One active refresh per device; cap total devices per user. If cap exceeded, revoke oldest session (LRU by `issued_at`).
        
- **Logout**
    
    - Revokes the current device family; clears cookie.
        

---

## 5) Cookies, CSRF & CORS

- **Refresh cookie**: httpOnly, Secure, SameSite=Lax (or `None` for cross‑site), `Path=/`, no `Domain` (use `__Host-` pattern when feasible).
    
- **CSRF**: Non‑httpOnly CSRF cookie issued; client mirrors value in `X‑CSRF‑Token` for state‑changing requests where cookies are used.
    
- **CORS**: Strict allowlist for Next.js origins; `credentials=true`; headers allow Authorization and CSRF header.
    

---

## 6) Profile Completion Gate

- Gate is computed from: Identity (verified), Education (valid), Location (present), Parent (verified if minor), and `display_name` present.
    
- Gate result is exposed in session payload and `/profile/completion`.
    
- **Policy enforcement**
    
    - Guard middleware/checks annotate requests with `profile_complete` and `minor_requires_parent` flags.
        
    - Purchase/booking routes hard‑require completion.
        
    - Catalog exposure per `Policy Service` (see §2.4) controls list/details visibility.
        

---

## 7) Rate Limiting & Abuse Prevention

- **OTP sends**: per‑phone/day (e.g., 5), per‑IP/hour (e.g., 20), cooldown between sends (e.g., 60s). After threshold, require CAPTCHA/PoW.
    
- **OTP verify**: lockouts on repeated failures; sliding window counters.
    
- **Identity submissions**: 5/24h per user; backoff on provider failures.
    
- **WAF hooks**: ASN/country throttle, IP reputation list.
    

---

## 8) External Integrations

- **SMS**
    
    - Primary + Fallback providers; provider health tracked; automatic failover when error rate exceeds threshold.
        
    - Idempotent send (request key per phone/time window) to avoid duplicate SMS.
        
- **Identity API**
    
    - Short timeouts (2.5s), 2–3 retries with jitter, circuit breaker.
        
    - If provider is down, queue verification for retry (deferred state) and update user with non‑blocking status.
        

---

## 9) Observability

- **Health**: `/healthz` (process up), `/readyz` (DB/Redis/SMS/Identity checks).
    
- **Metrics** (examples): otp_send_total, otp_send_latency_ms, otp_throttled_total, jwt_refresh_rotations_total, jwt_reuse_detected_total, profile_completion_ratio, catalog_blocked_views_total.
    
- **Logs**: JSON with request_id, route, user_id, ip, ua, latency_ms, status; redact PII; dedicated security/audit events.
    
- **Tracing**: OpenTelemetry spans for request; include SMS and Identity calls.
    

---

## 10) Scalability & Availability

- **Stateless API**: Horizontal scaling behind a load balancer; sticky sessions not required (refresh in cookie; state in DB/Redis).
    
- **DB**: Read replicas (for reporting/analytics) and primary for writes; connection pooling.
    
- **Redis**: Highly available (sentinel/managed); memory sizing for rate limits and token state.
    
- **Throughput assumptions** (tune per environment):
    
    - Peak OTP requests: short bursts around campaigns; 95th percentile within rate limits.
        
    - Refresh traffic: 5–10× access traffic over a day due to rotation on active users.
        

---

## 11) Failure Modes & Fallbacks

- **SMS outage**: auto‑failover to fallback; if all fail, return accepted with cooldown message and telemetry; prevent repeated sends.
    
- **Redis down**: switch to conservative mode (deny extra OTP, allow minimal existing sessions) or fail closed for sensitive routes; alert immediately.
    
- **Identity API down**: mark identity as pending; requeue; throttle submissions; inform user.
    
- **DB degraded**: protect writes (shed catalog traffic first), enforce read‑only mode if necessary; keep health signals accurate.
    

---

## 12) Security & Privacy Controls

- Field‑level encryption for `national_id` and `date_of_birth`; keys in KMS; envelope encryption pattern.
    
- Secrets via platform secret stores; no secrets in repo or images.
    
- JWT `iss/aud/exp/iat/jti` validation; clock skew tolerance small (≤ 60s).
    
- Least privilege roles; deny by default; admin actions fully audited.
    
- PII minimization in responses and logs; masking of phone/IDs.
    
- Data retention: OTP ≤ 30 days; audit ≥ 180 days; identity submissions per local law.
    

---

## 13) Versioning & Compatibility

- Public API under `/api/v1`.
    
- Legacy paths return 308 to v1 for a deprecation window; toggle off after cutover.
    
- Contract changes documented in OpenAPI with `x‑deprecation‑since` metadata.
    

---

## 14) Environments & Release Flow

- **Local**: Docker Compose (API, Postgres, Redis, Mailhog/SMS mock); seed taxonomies.
    
- **Staging**: Mirrors prod; SMS sandbox route; identity API sandbox.
    
- **Prod**: Blue‑green or canary; DB migrations zero‑downtime (expand→backfill→contract).
    
- **CI/CD**: Lint/type/test/coverage gates; SCA; image build; migration dry‑run; smoke tests.
    

---

## 15) Key Sequences (ASCII)

### 15.1 Unified OTP Sign‑In

```
Client -> API: POST /auth/request-otp {phone}
API -> SMS: send OTP (throttled, cooldown)
API -> Client: 200 {is_new_user, cooldown_seconds}

Client -> API: POST /auth/verify-otp {phone, code, display_name?, email?}
API: validate OTP; if first success and display_name missing -> 400
API: issue access (body), set refresh cookie (httpOnly, Secure), create RefreshSession
API -> Client: 200 {access_token, access_expires_in, profile_completion, is_new_user}
```

### 15.2 Refresh Rotation & Reuse Detection

```
Client -> API: POST /auth/refresh  (cookie only)
API: validate refresh (jti, family, not revoked)
API: issue new refresh (new jti), set cookie; return new access
If old refresh seen again -> revoke family; next refresh -> 409
```

### 15.3 Minor Parent Verification (with Identity API Auto-fill)

```
API: after identity verify, compute minor flag (DoB < threshold)
Client -> API: POST /profile/parent {phone, relation}
API -> SMS: send parent OTP
Client -> API: POST /profile/parent/verify {code}
API: mark ParentContact.verified = true; update profile_completion
```

### 15.4 Catalog Exposure Probe

```
Client -> API: GET /policy/catalog-exposure
API: read FEATURE_CATALOG_EXPOSURE_MODE + user profile state
API -> Client: {mode, can_view_details, can_purchase}
```

---

## 16) Risks & Mitigations

- **OTP abuse / SIM farms**: enforce per‑IP & per‑phone limits, cooldown, CAPTCHA/PoW, ASN blocks, anomaly alerts.
    
- **Token theft**: httpOnly refresh, rotation & reuse detection, family revocation, short access TTL.
    
- **Identity provider coupling**: circuit breaker, retries with backoff, deferred verification mode.
    
- **Data sensitivity**: encryption at rest, redaction, access audits, least‑privilege admin.
    

---

## 17) Open Items / Decisions Needed

- Final `AGE_THRESHOLD` (default 18).
    
- Province/City as free text vs referential taxonomy.
    
- Max concurrent devices per user (`SESSION_MAX_DEVICES`).
    
- CAPTCHA provider and activation thresholds.
    

---

## 18) Next Actions

1. Approve session/device cap and eviction policy.
    
2. Confirm catalog exposure default (keep `browse_only`).
    
3. Lock identity API contract (fields, error model, sandbox URL).
    
4. Validate observability dashboards & alert thresholds.