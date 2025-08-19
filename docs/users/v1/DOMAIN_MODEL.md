

> Reflects your confirmed decisions:  
> • Phone‑only unified sign‑in; display_name & email are set at verification (password optional).  
> • Olympiad degree is a fixed attribute of the Olympiad (not per user selection). Max 3 olympiads per user.  
> • Study branches are **dynamic** (admin-managed) and tied to educational levels that have `is_high_school = true`.  
> • Parent contact is **required only for minors** (derived from DoB).  
> • One refresh session per device; pending registrations preserved for analytics when display_name step is not completed.  
> • Catalog exposure is configurable; default is **browse allowed**, but details & purchase restricted until profile completion.

---

## 1) Core Aggregates & Entities

### 1.1 User (Aggregate Root)

**Purpose:** Primary account identified by phone; holds roles & session state.

**Fields**

- `id: UUID` — internal PK.
    
- `phone: Phone[E.164, unique]` — primary login identifier.
    
- `display_name: str` — **required at first successful verify** (enforced by flow; not auto‑generated).
    
- `email: Email?` — optional; unique when present.
    
- `password_hash: str?` — optional (user may add later).
    
- `roles: Set[Role]` — default: `{student}`; others: `teacher`, `mentor`, `staff_admin`, `superadmin`.
    
- `is_active: bool` — soft disable flag.
    
- `is_profile_complete: bool` — derived & cached.
    
- `created_at, updated_at`
    

**Derived / Computed**

- `age_years` (from IdentityInfo DoB)
    
- `requires_parent_contact = age_years < AGE_THRESHOLD` (configurable, default 18)
    
- `is_new_user` — true for first successful OTP verify until first session introspection.
    

**Invariants**

- `phone` immutable (number change handled via verified change flow).
    
- `display_name` must be non‑empty before granting non‑guest capabilities.
    

---

### 1.2 AuthArtifacts

**Purpose:** Support OTP, sessions, and auditability.

**OTPCode**

- `id: UUID`
    
- `phone: Phone`
    
- `code_hash: str`
    
- `purpose: Enum('login')`
    
- `expires_at: datetime`
    
- `used_at: datetime?`
    
- `send_channel: Enum('sms')`
    
- `ip: inet?`, `device_fingerprint: str?`
    

**RefreshSession** (per device)

- `jti: UUID` — refresh token ID
    
- `user_id: UUID`
    
- `issued_at: datetime`, `expires_at: datetime`
    
- `rotated_from: UUID?` — chain for family
    
- `revoked_at: datetime?` — family revocation supported
    
- `user_agent: str?`, `ip: inet?`
    

**Constraints**

- One **active** refresh per device; enforce `SESSION_MAX_DEVICES` per user.
    

---

### 1.3 Profile (sub‑aggregates)

**IdentityInfo**

- `user_id: UUID`
    
- `national_id: str(Encrypted)` — sensitive; field‑level encryption.
    
- `date_of_birth: date(Encrypted)` — sensitive.
    
- `first_name: str?`, `last_name: str?`, `father_name: str?`, `gender: Enum?`
    
- `verified: bool` — result of external identity lookup.
    
- `submission_count: int` — attempts in current 24h window.
    
- `last_attempt_at: datetime`
    

**EducationalLevel**

- `id: int`
    
- `name: str` (e.g., Elementary, Middle, High School)
    
- `min_grade: int`, `max_grade: int`
    
- `is_high_school: bool`
    

**StudyBranch** (dynamic, admin‑managed)

- `id: int`
    
- `level: FK(EducationalLevel)` — must reference a level with `is_high_school = true`.
    
- `name: str` (e.g., Mathematics, Experimental, Humanities)
    
- `is_active: bool`
    

**Olympiad**

- `id: int`
    
- `name: str`
    
- `olympiad_degree: int (1..5)` — **fixed attribute of the Olympiad** (certificate validity rank).
    
- `published: bool`
    

**EducationalProfile**

- `user_id: UUID`
    
- `level: FK(EducationalLevel)` (required)
    
- `grade: int` (required; **must be within** `level.min_grade..max_grade`)
    
- `study_branch: FK(StudyBranch)?` — **required iff** `level.is_high_school = true`.
    
- `olympiads: M2M[Olympiad]` — **max 3 unique** olympiads per user; duplicates not allowed.
    

**Location**

- `user_id: UUID`
    
- `province: str`
    
- `city: str`
    

**ParentContact** (minors only)

- `user_id: UUID`
    
- `phone: Phone`
    
- `relation: Enum('father','mother','guardian')`
    
- `verified: bool`, `verified_at: datetime?`
    

---

### 1.4 Taxonomy & Admin Content

- **Taxonomies**: `EducationalLevel`, `StudyBranch`, `Olympiad` are editable via Admin.
    
- **Publication**: `Olympiad.published` controls visibility; selection UI/API must filter by `published=true`.
    
- **Branch Lifecycle**: Branches can be created/retired; when inactivated, existing references remain valid but new assignments blocked.
    

---

## 2) Relationships Diagram (ASCII)

```
User (1) ──── (1) IdentityInfo
   │
   ├─ (1) ──── (1) EducationalProfile ── (M)── Olympiad
   │                 │                     (published=true)
   │                 └─ (0..1) StudyBranch ── (1) EducationalLevel
   │
   ├─ (1) ──── (1) Location
   │
   └─ (0..1) ─ (1) ParentContact  [required if minor]

User (1) ──── (M) RefreshSession (per device)
Phone ──────── (M) OTPCode (ephemeral)
```

---

## 3) Business Rules & Invariants

### Identity & Minor Determination

- `verified=true` only after successful external lookup using `national_id + date_of_birth`.
    
- Minor rule: `requires_parent_contact = (today - DoB) < AGE_THRESHOLD` (default 18 years; configurable).
    
- ParentContact **must be verified** for minors before `is_profile_complete` can become `true`.
    

### Education

- `grade ∈ [level.min_grade, level.max_grade]`.
    
- `study_branch` is **mandatory** iff `level.is_high_school = true`.
    
- `olympiads` selection constrained to `published=true`, **≤ 3**, **unique**.
    
- `olympiad_degree` is not user input; it’s inherent to each Olympiad entity.
    

### Profile Completion

A user is considered **profile‑complete** when all of the following hold:

1. `IdentityInfo.verified = true` and fields present.
    
2. `EducationalProfile.level & grade` valid; `study_branch` present when required; olympiads constraints satisfied.
    
3. `Location.province & city` present.
    
4. If minor: `ParentContact.verified = true`.
    
5. `display_name` present on User.
    

### Catalog Exposure Policy (configurable)

- See `FEATURE_CATALOG_EXPOSURE_MODE` in CONFIG doc: default allows list browsing; **course details & purchase** blocked for incomplete profiles.
    

---

## 4) Audit & Compliance

- **AuditEvent** (append‑only): `id, actor_id, type, target_type, target_id, context(json), ip, ua, created_at`.
    
    - Types include: `otp_sent`, `otp_verified`, `refresh_rotated`, `refresh_reuse_detected`, `logout`, `identity_submit`, `identity_verified`, `profile_completed`, `role_changed`, `parent_contact_verified`.
        
- **PII Handling**: `national_id` and `date_of_birth` encrypted at rest; never serialized back to clients.
    

---

## 5) Validation Matrix (Serializers/Domain Rules)

|Entity|Rule|
|---|---|
|User|`display_name` required at first verify; `email` unique if provided|
|OTPCode|6 digits; TTL=5m; per‑phone/day and per‑IP/hour throttles; cooldown enforced|
|IdentityInfo|5 submissions/24h rate limit; external API timeout & retry policy|
|EducationalProfile|grade within range; branch required for high school; max 3 unique olympiads; olympiads must be `published`|
|ParentContact|required & must be verified for minors only|

---

## 6) Deletion & Retention

- **Soft delete** users (status flags) for recoverability.
    
- Retention: OTP ≤ 30 days; Audit ≥ 180 days; Identity submissions as per legal requirements.
    
- Pending registrations (phone captured but display_name not set) retained for analytics with `status=pending_profile` and TTL policy (configurable).
    

---

## 7) Extensibility Notes

- Roles can be expanded with scopes (e.g., `catalog.manage`, `users.manage`).
    
- Add `Consent` entity for privacy and marketing.
    
- Support `Address` normalization if provinces/cities become taxonomies.
    

---

## 8) Edge Cases

- **Phone change**: require OTP verification on new phone; migrate sessions; audit event `phone_changed`.
    
- **Multiple devices**: cap by `SESSION_MAX_DEVICES`; oldest session revoked when cap exceeded.
    
- **Olympiad unpublish**: existing user links remain; future selection blocked.
    

---

## 9) Ready‑to‑Implement Checklist

-  Define AGE_THRESHOLD config.
    
-  Confirm province/city as free text vs taxonomy.
    
-  Approve audit event vocabulary.
    
-  Confirm maximum devices policy & eviction strategy.
    
-  Finalize error codes for validation failures.