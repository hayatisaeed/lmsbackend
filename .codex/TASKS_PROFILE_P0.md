# Profile & Onboarding (Milestone M2)

> **Goal:** Implement profile onboarding flows and validations per `./docs/users/v1/*.md`: Identity (with external API), Education (levels/branches/olympiads), Location, and Parent contact (minors only). Respect all domain rules and acceptance criteria.

## 0) Scope (Endpoints)

- `POST /api/v1/profile/identity`
    
- `POST /api/v1/profile/education`
    
- `POST /api/v1/profile/location`
    
- `POST /api/v1/profile/parent`
    
- `POST /api/v1/profile/parent/verify`
    
- `GET /api/v1/profile`
    
- `GET /api/v1/profile/completion`
    

**Dependencies** (read-only):

- Taxonomies: `EducationalLevel`, `StudyBranch`, `Olympiad` (published only for selection).
    
- Locations: states/provinces & cities (provided by TAXONOMY_P0 endpoint; profile uses IDs/names).
    

## 1) Functional Requirements

1. **Identity Submission** (`POST /profile/identity`)
    
    - Accepts: `national_id` (string), `date_of_birth` (YYYY-MM-DD).
        
    - **Rate limit**: max **5 submissions per 24h** per user.
        
    - **External Identity API** call:
        
        - Short timeout (≈2.5s), 2–3 retries with jitter, circuit breaker.
            
        - On success, **auto‑fill** fields: `first_name`, `last_name`, `father_name`, `gender`.
            
        - Use returned `father_name` to **pre‑fill ParentContact** UI (optional for adults).
            
    - **Encryption**: store `national_id` and `date_of_birth` with field‑level encryption.
        
    - **Verification**: set `verified=true` when provider confirms; compute `minor_required = (today - DoB) < AGE_THRESHOLD`.
        
    - Responses:
        
        - `202 {"status":"verification_in_progress"}` for async, or `200 {"status":"verified"}` if sync.
            
        - Errors: `400 identity_invalid`, `429 identity_rate_limited`, `502 identity_provider_error`.
            
2. **Education Submission** (`POST /profile/education`)
    
    - Accepts: `level` (id), `grade` (int), `study_branch` (id, optional), `olympiad_ids` (list[int], optional).
        
    - **Rules**:
        
        - `grade` must be within `EducationalLevel.min_grade..max_grade`.
            
        - If `EducationalLevel.is_high_school=true`, `study_branch` is **required** and must belong to that level.
            
        - `olympiad_ids` must be **published**, **unique**, and **≤ 3** total.
            
        - `olympiad_degree` is **not user input**; it is a static field on each Olympiad record.
            
    - Response: `200 {"ok": true}` or `400 education_validation_error` with field details.
        
3. **Location Submission** (`POST /profile/location`)
    
    - Accepts: `province_id` and `city_id` (preferred) **or** normalized names (`province`, `city`) for backward compatibility.
        
    - Validate that `city` belongs to the given `province`.
        
    - Response: `200 {"ok": true}`; errors include `400 location_invalid`.
        
4. **Parent Contact (Minors Only)**
    
    - `POST /profile/parent` accepts `{ phone, relation }` and **sends parent OTP**; creates (or updates) ParentContact with `verified=false`.
        
    - `POST /profile/parent/verify` accepts `{ code }` and marks ParentContact `verified=true` if correct.
        
    - Parent contact is **required only if minor**; optional for adults (we may still pre‑fill father’s name from Identity and keep as optional record).
        
    - Errors: `400 parent_invalid`, `401 parent_otp_invalid`, `410 parent_otp_expired`.
        
5. **Profile Retrieval & Completion**
    
    - `GET /profile` returns non‑sensitive profile view (never returns encrypted fields).
        
    - `GET /profile/completion` returns `{ identity, education, location, parent, percent_complete }` with minor logic applied.
        
    - `is_profile_complete` becomes true when: Identity verified, Education valid, Location present, Parent verified if minor, and `display_name` set.
        

## 2) Non‑Functional Requirements

- **Security**: Never serialize `national_id` or `date_of_birth`. Redact PII in logs.
    
- **Observability**: Metrics for identity submissions (success/failure), education validations, parent OTP sends/verifies; audit events for: `identity_submit`, `identity_verified`, `profile_completed`, `parent_contact_verified`.
    
- **OpenAPI**: Document request/response schemas; list all validation errors.
    
- **Error Envelope**: Use standard `{error:{code,message,details?}, request_id}` for all non‑2xx.
    

## 3) Data & Models (Profile domain)

- **IdentityInfo**: `user_id`, `national_id (Encrypted)`, `date_of_birth (Encrypted)`, `first_name?`, `last_name?`, `father_name?`, `gender?`, `verified: bool`, `submission_count`, `last_attempt_at`.
    
- **EducationalLevel**: `id`, `name`, `min_grade`, `max_grade`, `is_high_school`.
    
- **StudyBranch**: `id`, `level_id` (must reference level with `is_high_school=true`), `name`, `is_active`.
    
- **Olympiad**: `id`, `name`, `olympiad_degree (1..5)`, `published`.
    
- **EducationalProfile**: `user_id`, `level_id`, `grade`, `study_branch_id?`, `olympiads (M2M, max=3 unique)`.
    
- **Location**: `user_id`, `province_id`, `city_id` (or normalized names), integrity check city∈province.
    
- **ParentContact**: `user_id`, `phone`, `relation ('father'|'mother'|'guardian')`, `verified`, `verified_at`.
    

## 4) Validation Rules (Serializers)

- Identity: enforce per‑user 5/24h attempts; block if circuit open; validate formats; encrypt fields before save.
    
- Education: grade range; branch required iff high school; branch belongs to level; olympiads unique, ≤ 3, published only.
    
- Location: province+city must exist and be related; fallback normalization for names → IDs.
    
- Parent: phone is valid E.164; relation in choices; OTP flow mirrors main OTP with TTL and reuse rules.
    

## 5) External Identity API Integration

- Config via env: base URL, timeout, retries, circuit thresholds.
    
- Request payload: `{ national_id, date_of_birth }`.
    
- Expected response (example): `{ first_name, last_name, father_name, gender, verified }`.
    
- Map failures to `502 identity_provider_error`; timeouts obey retry+jitter; open circuit returns cached message for a short TTL.
    

## 6) Tests (pytest) — target ≥85% coverage for profile modules

**Unit**

- Identity submission limiter: 5/24h; sixth returns 429.
    
- Encryption: ensure raw `national_id`/`dob` never leak from serializers.
    
- Education: grade boundary tests; high‑school branch requirement; olympiad uniqueness and published constraint.
    
- Location: invalid province/city combos rejected; normalization from names to IDs works.
    
- Parent: OTP TTL and invalid code paths; verify success flips flag and timestamp.
    

**API**

- Identity: happy path (verified) and provider failure (502) with retries; circuit breaker behavior.
    
- Education: valid vs invalid payloads; error details in envelope.
    
- Location: province/city lookup via IDs; via names.
    
- Parent: minors required; adults optional; verify endpoint responses.
    
- Profile completion: evaluate percent and boolean flags across combinations (with/without minor).
    

**Security**

- No sensitive fields in any GET/POST response bodies.
    
- Audit events emitted for key actions.
    

## 7) OpenAPI (drf‑spectacular)

- Tags: `profile`, `taxonomy` (read references only), `identity`.
    
- Components for request/response models; error schemas; examples for minors vs adults.
    

## 8) Observability & Metrics

- `identity_submit_total{status=success|error}`; `identity_provider_latency_ms` histogram.
    
- `education_validation_errors_total{field=...}`.
    
- `parent_otp_send_total`, `parent_otp_verify_total{status=...}`.
    
- `profile_completed_total`.
    

## 9) Done Definition

- All acceptance gates in MASTER_PROMPT §5 pass for profile modules.
    
- Endpoints behave exactly as in `ENDPOINTS_SPEC.md`; minor logic enforced.
    
- Provider integration resilient (timeouts, retries, breaker) and observable.
    
- Coverage ≥ 85%; schema exposed at `/api/v1/docs` shows all profile endpoints.
    

## 10) Out of Scope (this milestone)

- Auth endpoints (handled in AUTH_P0).
    
- Catalog/policy endpoints (POLICY_P0).
    
- Admin role management (RBAC_P0).