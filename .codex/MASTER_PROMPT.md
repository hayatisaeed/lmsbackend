

> **Role:** You are CodeX, a coding agent implementing a production‑grade Django + DRF backend. Follow this prompt strictly. The documents in `./docs/users/v1/` are the single source of truth. The folder `./shitcode/` is a read‑only _reference_ for naming/structure only — **never copy logic** from it.

---

## 0) Project Context

- **Product:** MentorHub — backend API for a Next.js site that manages students, teachers, mentors, and staff admins; sells courses and packages.
    
- **Auth model:** Phone‑only unified sign‑in (register/login merged) using OTP. On first successful verify, **display_name is required**, `email` optional, `password` optional.
    
- **Sessions:** Short‑lived **access JWT** in headers; long‑lived **refresh token** in **httpOnly+Secure cookie**, rotated on every refresh with reuse detection and family revocation.
    
- **Onboarding:** Profile completion gate: Identity → Education → Location → Parent (minors only). Default policy lets users **browse catalog lists** but blocks **details/purchases** until completion; policy is admin‑configurable.
    
- **RBAC:** All new users start with role `student`. Admins can assign additional roles (`teacher`, `mentor`, `staff_admin`, `superadmin`).
    

---

## 1) Source of Truth (read these first)

Located under `./docs/users/v1/`:

1. `CONFIG_AND_RUNBOOKS.md`
    
2. `DOMAIN_MODEL.md`
    
3. `ENDPOINTS_SPEC.md`
    
4. `SYSTEM_DESIGN.md`
    
5. `ACCEPTANCE_CRITERIA.md`
    
6. `README.md`
    

> If any conflict arises, prefer `ENDPOINTS_SPEC.md` for routes/IO, `DOMAIN_MODEL.md` for data rules, and `CONFIG_AND_RUNBOOKS.md` for cookies/rate limits.

---

## 2) Guardrails & Non‑negotiables

- **Versioning:** All public endpoints under `/api/v1`.
    
- **Cookies:** Refresh token must be set/cleared by server with attributes: `httpOnly`, `Secure`, `Path=/`, `SameSite=Lax` (or `None` if configured), ideally using `__Host-` prefix (no Domain). Add CSRF cookie (non‑httpOnly) and enforce `X-CSRF-Token` for cookie‑credentialed state‑changing requests.
    
- **Rate limits:** OTP send per‑phone/day, per‑IP/hour, and cooldown between sends; Identity submissions ≤ 5/24h.
    
- **PII:** Encrypt `national_id` and `date_of_birth` at rest. Never return these fields in responses. Mask PII in logs.
    
- **RBAC:** Deny‑by‑default. New users get role `student` automatically. Admin endpoints require `staff_admin`+.
    
- **Locations:** Implement multi‑mode endpoint as specified: default states list; `?all=true` nested; `?state=<slug|id>` cities; `?q=` search.
    
- **OpenAPI:** Use **drf‑spectacular**. Expose `/api/v1/schema` and `/api/v1/docs`.
    
- **Observability:** Add `/healthz`, `/readyz`, `/metrics`; structured JSON logs; request IDs.
    
- **Error envelope:** Always `{ "error": { "code": "...", "message": "...", "details": {...}? }, "request_id": "..." }` on non‑2xx.
    
- **Shitcode policy:** The `./shitcode/` directory is **reference only** (naming idioms, serializers patterns). **Do not** import from or copy logic/data models verbatim. CI will fail if you import from it.
    

---

## 3) Milestones (execute one at a time)

### M1: AUTH_P0

**Endpoints:**

- POST `/api/v1/auth/request-otp`
    
- POST `/api/v1/auth/verify-otp`
    
- POST `/api/v1/auth/refresh`
    
- POST `/api/v1/auth/logout`
    
- GET `/api/v1/auth/session`
    

**Requirements:**

- Create user if not exists (`pending_profile`, role `student`).
    
- Enforce OTP throttles (per phone/day, per IP/hour) + cooldown; CAPTCHA hook.
    
- Verify-OTP requires `display_name` on first success; return `access_token`, `access_expires_in`, `profile_completion`, `is_new_user`; set refresh cookie.
    
- Refresh rotates tokens; reuse → revoke family; logout revokes current family and clears cookie.
    
- CSRF cookie issuance.
    
- Metrics and audit events for otp/refresh/logout.
    

### M2: PROFILE_P0

**Endpoints:**

- POST `/api/v1/profile/identity`
    
- POST `/api/v1/profile/education`
    
- POST `/api/v1/profile/location`
    
- POST `/api/v1/profile/parent`
    
- POST `/api/v1/profile/parent/verify`
    
- GET `/api/v1/profile`
    
- GET `/api/v1/profile/completion`
    

**Rules:**

- Identity: `national_id` + `date_of_birth` → external Identity API; auto‑fill `first_name`, `last_name`, `father_name`, `gender`; 5/24h limit; minors detected by `AGE_THRESHOLD`.
    
- Parent required only for minors; OTP flow mirrors main OTP.
    
- Education: grade within level range; branch required if level.is_high_school; ≤ 3 unique olympiads (published only).
    

### M3: TAXONOMY_P0

**Endpoints:**

- GET `/api/v1/educational-levels`
    
- GET `/api/v1/study-branches?level=<id>`
    
- GET `/api/v1/olympiads?published=true`
    
- GET `/api/v1/locations[?all=true|?state=<slug|id>][&q=]`
    

### M4: POLICY_P0

**Endpoint:** GET `/api/v1/policy/catalog-exposure`

- Implement modes per config: `browse_only` (default), `locked`, `open`.
    

### M5: RBAC_P0

**Endpoints:**

- GET `/api/v1/people/users`
    
- PATCH `/api/v1/people/users/{id}/roles`
    
- Permissions: `staff_admin` required.
    

---

## 4) Deliverables per Milestone

- **Code:** Django apps under `apps/users/` (views/viewsets, serializers, models, permissions, urls, services/utils). No code in `shitcode/` may be imported.
    
- **Migrations:** Complete and reversible.
    
- **Tests:** `pytest` unit + API tests with `factory_boy`. Assertions for cookie attributes, token rotation/reuse, throttling, validators, and error envelopes.
    
- **OpenAPI:** drf‑spectacular schema updated; endpoints visible in `/api/v1/docs`.
    
- **Observability:** health/readiness/metrics wired; audit events emitted.
    

---

## 5) Acceptance Gates (must all pass)

1. **Tests:** All tests green; coverage ≥ 85% for changed packages.
    
2. **Lint/Format/Types:** ruff, black, isort, and mypy (or pyright) pass.
    
3. **Spec Conformance:** Endpoints, request/response bodies match `ENDPOINTS_SPEC.md` exactly.
    
4. **Security:** Refresh cookie attributes set; rotation + reuse detection proven by tests; encrypted PII never serialized.
    
5. **Rate Limits:** OTP and identity submission limits enforced; 429 surfaced with correct `error.code`.
    
6. **Docs:** OpenAPI schema present; README unchanged except where paths must be updated.
    

---

## 6) Implementation Priorities & Style

- **Style:** DRF ViewSets + Routers unless a simple APIView is more appropriate; serializers handle validation; `django-filter` for filtering; pagination consistent.
    
- **Config:** All values via env (see `CONFIG_AND_RUNBOOKS.md`); **never** hardcode secrets.
    
- **Logging:** Structured JSON with `request_id`; **no PII**.
    
- **Errors:** Prefer explicit `ValidationError` details mapped into the standard error envelope.
    
- **Transactions:** Use atomic blocks for multi‑write operations (e.g., refresh rotation).
    

---

## 7) Integration Details

- **Redis:** Use for rate limiting counters and refresh blocklist/families. Keys like `otp:phone:{E164}`, `otp:ip:{IP}`, `rf:revoked:{jti}`.
    
- **Identity API:** Short timeout, 2–3 retries with jitter, circuit breaker; auto‑fill identity + father name; parent verification still required only for minors.
    
- **SMS:** Primary + fallback; idempotent send per phone/time window.
    

---

## 8) Prohibited Sources & Shortcuts

- Do **not** copy models, serializers, permissions, or views from `shitcode/`.
    
- Do **not** bypass rotation/reuse detection.
    
- Do **not** store access tokens in cookies or localStorage.
    
- Do **not** expose encrypted PII fields in any responses.
    

---

## 9) Deliverable Format (per milestone)

Submit a PR that includes:

- Code changes with migrations.
    
- New/updated tests.
    
- Updated OpenAPI (auto‑generated) and any settings/env samples.
    
- Short `CHANGELOG.md` entry in the PR body summarizing endpoints and notable behaviors.
    

---

## 10) Kickoff Task (AUTH_P0)

Implement **AUTH_P0** exactly as specified above. After completion, run:

- `pytest -q` (must pass, coverage ≥ 85% for auth modules)
    
- `ruff check . && black --check . && isort --check-only .`
    
- Verify `/api/v1/docs` renders the five auth endpoints.
    
- Manual curl checks for cookie attributes and rotation/reuse behavior.
    

> When AUTH_P0 is accepted, proceed to PROFILE_P0 and repeat the same acceptance gates.