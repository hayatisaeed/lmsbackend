

> Principles: **/api/v1** versioning, JSON only, snake_case, standard error envelope `{error:{code,message,details?}, request_id}`. Access tokens in `Authorization: Bearer`, refresh in **httpOnly Secure cookie** managed by backend.

## 0) Conventions

- **Pagination**: `page`, `page_size` (default 20, max 100), `ordering` (e.g., `-created_at`).
    
- **Filtering/Search**: consistent query params (`q`, exact field filters).
    
- **Throttling**: Global 100/min/IP; OTP endpoints have dedicated limits.
    
- **Headers**: `X-Request-ID` accepted; `X-CSRF-Token` required for state‑changing cookie‑credentialed requests.
    

---

## 1) Auth & Session

### 1.1 Request OTP — Unified Entry

**POST** `/api/v1/auth/request-otp`

**Body**

```json
{ "phone": "+989914307462" }
```

**Behavior**

- Create minimal user if not exists (status `pending_profile`). Assign default role `student` for all new users; future role changes handled by admins.
    
- Enforce per‑phone/day & per‑IP/hour throttles, cooldown, CAPTCHA threshold.
    
- Send OTP via primary SMS provider; fallback on failure.
    

**Response: 200**

```json
{
  "is_new_user": true,
  "cooldown_seconds": 45,
  "next_step_hint": "verify_otp"
}
```

**Errors**: `400 invalid_phone`, `429 otp_throttled`, `503 sms_unavailable`.

---

### 1.2 Verify OTP — Issue Tokens & Collect Required Fields

**POST** `/api/v1/auth/verify-otp`

**Body**

```json
{
  "phone": "+989914307462",
  "code": "123456",
  "display_name": "John Doe",   // required at first success
  "email": "john@example.com"    // optional
}
```

**Behavior**

- Validate OTP; on first successful verify if `display_name` missing → **400**.
    
- Issue short‑lived **access_token** in body.
    
- Set long‑lived **refresh cookie** (httpOnly, Secure, SameSite=Lax; `__Host-` prefix) and rotate family on subsequent refreshes.
    
- Return `profile_completion` and `is_new_user`.
    

**Response: 200**

```json
{
  "access_token": "<JWT>",
  "access_expires_in": 600,
  "is_new_user": true,
  "profile_completion": {
    "identity": false,
    "education": false,
    "location": false,
    "parent": false,
    "percent_complete": 20
  }
}
```

**Errors**: `400 otp_invalid_payload`, `401 otp_invalid_or_expired`, `409 user_locked`, `429 otp_throttled`.

---

### 1.3 Refresh Access Token — Cookie Only

**POST** `/api/v1/auth/refresh`

**Cookies**: refresh token cookie only.

**Behavior**

- Validate refresh; **rotate** token (reuse detection ⇒ family revoke).
    
- Return new access token & set new refresh cookie.
    

**Response: 200**

```json
{ "access_token": "<JWT>", "access_expires_in": 600 }
```

**Errors**: `401 auth_invalid_refresh`, `419 auth_rotation_required`, `409 auth_family_revoked`.

---

### 1.4 Logout — Server‑Side

**POST** `/api/v1/auth/logout`

**Auth**: Access token (optional: refresh cookie).

**Behavior**

- Revoke refresh family for this device; clear cookie in response.
    

**Response: 204** (empty body; `Set‑Cookie` expired refresh).

---

### 1.5 Session Introspection

**GET** `/api/v1/auth/session`

**Auth**: Access token.

**Response: 200**

```json
{
  "user": {"id": "uuid", "phone": "+9899...", "display_name": "John Doe", "email": "john@example.com", "roles": ["student"]},
  "profile_completion": {"identity": false, "education": false, "location": false, "parent": false, "percent_complete": 20},
  "is_new_user": false
}
```

---

## 2) Profile & Onboarding

> Sensitive fields (national_id, date_of_birth) are **never returned**; they’re encrypted at rest.

### 2.1 Submit Identity

**POST** `/api/v1/profile/identity`

**Body**

```json
{ "national_id": "1234567890", "date_of_birth": "2006-09-01" }
```

**Behavior**

- Rate limit: **max 5 submissions per 24h per user**.
    
- Call identity API to populate `first_name`, `last_name`, `father_name`, `gender`.
    
- Set `IdentityInfo.verified=true` on success; compute minor status.
    

**Response: 202** (Accepted)

```json
{ "status": "verification_in_progress" }
```

(or **200** with `{"status":"verified"}` if synchronous).

**Errors**: `400 identity_invalid`, `429 identity_rate_limited`, `502 identity_provider_error`.

---

### 2.2 Submit Education

**POST** `/api/v1/profile/education`

**Body**

```json
{ "level": 3, "grade": 11, "study_branch": 1, "olympiad_ids": [1,2,3] }
```

**Rules**

- `grade` must be within `level.min_grade..max_grade`.
    
- `study_branch` required iff `level.is_high_school=true` and branch belongs to that level.
    
- `olympiad_ids` must be **published** and ≤ 3 unique.
    

**Response: 200**

```json
{ "ok": true }
```

**Errors**: `400 education_validation_error` (+ field details).

---

### 2.3 Submit Location

**POST** `/api/v1/profile/location`

**Body**

```json
{ "province": "Tehran", "city": "Tehran" }
```

**Response: 200** `{ "ok": true }`

---

### 2.4 Parent Contact (Minors Only)

**POST** `/api/v1/profile/parent`

**Body**

```json
{ "phone": "+98912...", "relation": "father" }
```

**Behavior**: Send parent OTP, create ParentContact (unverified).

**Response: 200** `{ "status": "otp_sent" }`

**POST** `/api/v1/profile/parent/verify`

```json
{ "code": "123456" }
```

**Response: 200** `{ "verified": true }`

**Errors**: `400 parent_invalid`, `401 parent_otp_invalid`, `410 parent_otp_expired`.

---

### 2.5 Get Profile & Completion

**GET** `/api/v1/profile`  
**GET** `/api/v1/profile/completion`

**Response: 200**

```json
{
  "identity": {"verified": true},
  "education": {"level": 3, "grade": 11, "study_branch": 1, "olympiad_count": 2},
  "location": {"province": "Tehran", "city": "Tehran"},
  "parent": {"required": false, "verified": false},
  "percent_complete": 80
}
```

---

## 3) Taxonomy & Reference Data

### 3.1 Educational Levels

**GET** `/api/v1/educational-levels`

**Query**: `?q=`, `?ordering=name`

**Response: 200** list of levels.

### 3.2 Study Branches

**GET** `/api/v1/study-branches`

**Query**: `?level=<id>` (required to scope branches), `?active=true`

**Response: 200** list; only branches with `level.is_high_school=true` returned.

### 3.3 Olympiads

**GET** `/api/v1/olympiads`

**Query**: `?published=true` (default true) | `false` for admin views.

**Response: 200** list; each item includes static `olympiad_degree (1..5)`.

### 3.4 Locations (States/Provinces & Cities)

**GET** `/api/v1/locations`

**Modes (by query):**

- **Default (no query)** → list all **states/provinces** only (shallow):
    
    - Fields: `id`, `name`, `slug`, `cities_count`.
        
- `?all=true` → list **full nested** tree of states with their cities:
    
    - Item: `{ id, name, slug, cities: [{ id, name, slug }] }`.
        
- `?state=<slug|id>` (alias: `?province=`) → list **cities under the specified state** only:
    
    - Response: array of `{ id, name, slug }`.
        
- `?q=` → case‑insensitive search across state and city names (works with any mode; scopes results accordingly).
    

**Examples**

- **Default**
    

```json
[
  {"id": 1, "name": "Tehran", "slug": "tehran", "cities_count": 16},
  {"id": 2, "name": "Isfahan", "slug": "isfahan", "cities_count": 12}
]
```

- **Cities under a state**: `/api/v1/locations?state=tehran`
    

```json
[
  {"id": 101, "name": "Tehran", "slug": "tehran-city"},
  {"id": 102, "name": "Rey", "slug": "rey"},
  {"id": 103, "name": "Shemiranat", "slug": "shemiranat"}
]
```

- **Full nested**: `/api/v1/locations?all=true` (truncated)
    

```json
[
  {"id": 1, "name": "Tehran", "slug": "tehran", "cities": [{"id":101,"name":"Tehran"}, {"id":102,"name":"Rey"}]},
  {"id": 2, "name": "Isfahan", "slug": "isfahan", "cities": [{"id":201,"name":"Isfahan"}]}
]
```

**Notes**

- Slugs are lowercase, ASCII, hyphen‑separated; ids are stable integers.
    
- Profile submission (`/profile/location`) SHOULD send `province_id` and `city_id` to avoid typos; API still accepts names for backward compatibility (will be normalized server‑side).
    

## 4) People & RBAC (Foundation)

### 4.1 Users (Admin)

**GET** `/api/v1/people/users`

**Auth**: `staff_admin` or higher.

**Query**: `?q=`, `?role=teacher|mentor|student`, `?is_profile_complete=true|false`

**Response: 200** paginated list.

**PATCH** `/api/v1/people/users/{id}/roles`

```json
{ "roles": ["teacher", "mentor"] }
```

**Response: 200** updated user roles.

---

## 5) Catalog Exposure Policy (Guard)

> Behavior enforced across catalog endpoints (defined in separate Catalog spec). This API provides a **policy probe** to let the frontend know what to show.

**GET** `/api/v1/policy/catalog-exposure`  
**Response: 200**

```json
{ "mode": "browse_only", "can_view_details": false, "can_purchase": false }
```

---

## 6) Ops & Docs

- **GET** `/api/v1/healthz` — liveness
    
- **GET** `/api/v1/readyz` — readiness (DB/Redis/SMS/Identity checks)
    
- **GET** `/api/v1/metrics` — Prometheus
    
- **GET** `/api/v1/schema` — OpenAPI JSON
    
- **GET** `/api/v1/docs` — Swagger/Redoc
    

---

## 7) Error Codes (non‑exhaustive)

- `invalid_phone`, `otp_throttled`, `otp_invalid_or_expired`
    
- `auth_invalid_refresh`, `auth_rotation_required`, `auth_family_revoked`
    
- `identity_rate_limited`, `identity_provider_error`
    
- `education_validation_error`, `parent_otp_invalid`, `parent_otp_expired`
    
- `forbidden_insufficient_role`
    

---

## 8) Acceptance Hooks per Endpoint (QA Pointers)

- Ensure OTP request throttles fire at configured thresholds and that cooldown values are correctly communicated to the client.
    
- Verify that the Verify‑OTP endpoint enforces `display_name` at first success and sets refresh cookie attributes correctly.
    
- Confirm that refresh requests rotate tokens and detect reuse; when reuse is detected, revoke the family and return 409 thereafter.
    
- Validate that profile completion logic reflects the minor rule and blocks or permits actions as appropriate.
    
- Check that taxonomy endpoints filter correctly by publication status and level flags as specified.
    

---

## 9) Deprecations / Compatibility

- Legacy paths (`/api/users/...`) respond with `308 Permanent Redirect` to `/api/v1/...` for a deprecation window (configurable); disable after cutover.