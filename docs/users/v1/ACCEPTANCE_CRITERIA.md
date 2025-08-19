

## Scope

Defines the criteria by which features are considered complete and acceptable for release. Covers authentication, profile onboarding, taxonomy management, roles/RBAC, and catalog exposure.

---

## 1) Authentication & Session

- ✅ Requesting OTP:
    
    - Only valid E.164 phones accepted.
        
    - Cooldown enforced (configurable, e.g., 60s).
        
    - Per-phone/day and per-IP/hour rate limits applied.
        
    - New users created with status `pending_profile` and role `student`.
        
- ✅ Verify OTP:
    
    - Validates code and expires correctly (≤ 5 min TTL).
        
    - First successful verify must include `display_name`.
        
    - Access token issued (≤ 10 min TTL) and refresh cookie set with httpOnly+Secure.
        
    - Rotation logic tested; reuse revokes family.
        
- ✅ Refresh endpoint:
    
    - Returns 200 with new access and rotated refresh.
        
    - Detects reuse; revokes family; returns 409 on subsequent attempt.
        
- ✅ Logout:
    
    - Clears refresh cookie and revokes device family.
        
- ✅ Session introspection:
    
    - Returns current user, roles, profile completion, `is_new_user` flag.
        

---

## 2) Profile Completion

- ✅ Identity submission:
    
    - Accepts `national_id` + `date_of_birth`.
        
    - Rate limited (≤ 5 per 24h).
        
    - Calls external Identity API; retries with backoff; circuit breaker enforced.
        
    - Auto-fills `first_name`, `last_name`, `father_name`, `gender`.
        
    - Minor detection accurate (based on `AGE_THRESHOLD`).
        
- ✅ Education submission:
    
    - Grade validated within EducationalLevel min/max.
        
    - Study branch required only if `is_high_school=true`.
        
    - Olympiad selection limited to ≤ 3 unique, published only.
        
- ✅ Location submission:
    
    - Accepts valid province/city pair from taxonomy.
        
    - Normalizes free-text input where legacy data exists.
        
- ✅ Parent contact:
    
    - Required if minor; optional otherwise.
        
    - OTP send and verify workflow mirrors main OTP logic.
        
    - Verification updates profile completion state.
        
- ✅ Profile completion flag:
    
    - Set only when Identity verified, Education valid, Location provided, Parent verified (if required), and display_name set.
        

---

## 3) Taxonomies & Locations

- ✅ Educational Levels endpoint returns all levels; supports filtering, ordering.
    
- ✅ Study Branches endpoint returns only branches with high school levels; supports filtering by level.
    
- ✅ Olympiads endpoint returns published list by default; includes fixed `olympiad_degree`.
    
- ✅ Locations endpoint:
    
    - Default: returns list of states/provinces only.
        
    - `?all=true`: returns nested states with cities.
        
    - `?state=<slug|id>`: returns cities under specified state.
        
    - Search via `?q=` works across names.
        

---

## 4) Roles & RBAC

- ✅ All new users default to role `student`.
    
- ✅ Admins (`staff_admin` or higher) can assign/remove roles.
    
- ✅ Access to admin endpoints forbidden without correct role.
    
- ✅ Role changes audited.
    

---

## 5) Catalog Exposure Policy

- ✅ Policy probe endpoint returns mode and booleans (`can_view_details`, `can_purchase`).
    
- ✅ Default mode is `browse_only` (list visible, details/purchase restricted until profile completion).
    
- ✅ Admin can override via config.
    

---

## 6) Observability

- ✅ `/healthz` returns 200 when process alive.
    
- ✅ `/readyz` checks DB, Redis, SMS, Identity providers.
    
- ✅ Prometheus metrics exposed with otp, jwt, profile stats.
    
- ✅ Audit events written for: otp_sent, otp_verified, refresh_rotated, refresh_reuse_detected, logout, identity_submit, identity_verified, profile_completed, role_changed, parent_contact_verified.
    

---

## 7) Security & Privacy

- ✅ All refresh tokens stored and rotated; old tokens rejected.
    
- ✅ Sensitive fields (national_id, dob) encrypted at rest and never returned in responses.
    
- ✅ OTPs expire in 5 minutes and are invalidated after use.
    
- ✅ CSRF protection enforced for cookie-auth requests.
    
- ✅ CORS restricted to allowed Next.js origins with credentials.
    
- ✅ Secrets not committed in repo; loaded from env/secret store.
    

---

## 8) Failure & Fallbacks

- ✅ SMS provider failover works; user sees consistent response.
    
- ✅ Identity provider failures trigger deferred verification, not user lockout.
    
- ✅ Redis downtime handled by fail-closed for sensitive flows, conservative mode otherwise.
    
- ✅ DB degradation triggers safe read-only modes.
    

---

## 9) Non-Functional Criteria

- ✅ P99 OTP request latency < 2s.
    
- ✅ P99 OTP verify latency < 3s (excluding external provider delay).
    
- ✅ P99 refresh latency < 1s.
    
- ✅ System supports horizontal scaling; stateless API nodes.
    
- ✅ Coverage ≥ 85% for core modules (auth, profile, taxonomy).
    

---

## 10) Out of Scope / Deferred

- ❌ Email/password as primary login (optional only).
    
- ❌ Marketing consents; deferred to future.
    
- ❌ Multi-language error messages; English-only v1.