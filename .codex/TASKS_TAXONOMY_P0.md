# Taxonomies (Milestone M3)

> **Goal:** Implement taxonomy services (Educational Levels, Study Branches, Olympiads, Locations) that power Profile onboarding and dropdowns in the frontend. Ensure validations align with `DOMAIN_MODEL.md` and endpoints match `ENDPOINTS_SPEC.md`.

## 0) Scope (Endpoints)

- `GET /api/v1/educational-levels`
    
- `GET /api/v1/study-branches?level=<id>`
    
- `GET /api/v1/olympiads?published=true`
    
- `GET /api/v1/locations[?all=true|?state=<slug|id>][&q=]`
    

**Admin endpoints** (for `staff_admin`+ only):

- `POST /api/v1/educational-levels`
    
- `PATCH /api/v1/educational-levels/{id}`
    
- `POST /api/v1/study-branches`
    
- `PATCH /api/v1/study-branches/{id}`
    
- `POST /api/v1/olympiads`
    
- `PATCH /api/v1/olympiads/{id}`
    
- `POST /api/v1/locations`
    
- `PATCH /api/v1/locations/{id}`
    

## 1) Functional Requirements

1. **Educational Levels**
    
    - Fields: `id`, `name`, `min_grade`, `max_grade`, `is_high_school` (bool).
        
    - Validation: `min_grade <= max_grade`.
        
    - Public GET: list all active levels.
        
2. **Study Branches**
    
    - Fields: `id`, `name`, `level_id`, `is_active`.
        
    - Validation: `level.is_high_school = true` if branches exist.
        
    - Public GET: filterable by `level=<id>`.
        
3. **Olympiads**
    
    - Fields: `id`, `name`, `olympiad_degree` (static int), `published: bool`.
        
    - Validation: degree is fixed, not editable by users.
        
    - Public GET: only `published=true` returned to students.
        
4. **Locations**
    
    - Hierarchy: `Province` (state) → `City`.
        
    - Public GET modes:
        
        - Default: list all provinces (no nested cities).
            
        - `?all=true`: nested provinces with their cities.
            
        - `?state=<slug|id>`: list only cities under a given province.
            
        - `?q=term`: search provinces/cities by name (case-insensitive).
            
5. **Admin CRUD**
    
    - Only `staff_admin`+ can create/update levels, branches, olympiads, and locations.
        
    - All changes audited (`taxonomy_created`, `taxonomy_updated`).
        

## 2) Non‑Functional Requirements

- **Caching**: Use Redis for read‑heavy queries (taxonomy lists). TTL ≈ 1h, invalidated on updates.
    
- **OpenAPI**: Document all endpoints with examples (nested vs flat locations, published olympiads).
    
- **Error Envelope**: Use standard `{error:{code,message,details?}, request_id}`.
    
- **RBAC**: Read‑only endpoints public; write endpoints require `staff_admin`.
    
- **Observability**: Metrics for cache hits/misses, admin mutations.
    

## 3) Data & Models

- **EducationalLevel**: `id`, `name`, `min_grade`, `max_grade`, `is_high_school`, `is_active`, timestamps.
    
- **StudyBranch**: `id`, `level_id`, `name`, `is_active`, timestamps.
    
- **Olympiad**: `id`, `name`, `olympiad_degree` (static int), `published`, timestamps.
    
- **Province**: `id`, `name`, `slug`, timestamps.
    
- **City**: `id`, `province_id`, `name`, `slug`, timestamps.
    

## 4) Validation Rules

- Branch must belong to a `level` with `is_high_school=true`.
    
- Olympiad degree cannot be changed once created.
    
- Cities must belong to an existing province.
    
- Names unique within parent scope (e.g., city names unique within province).
    

## 5) Settings & ENV

- `CACHE_TTL_TAXONOMY` (default 3600s)
    
- `MAX_OLYMPIADS_PER_USER` (default 3; enforced at profile level, not taxonomy)
    

## 6) Tests (pytest) — target ≥85% coverage

**Unit**

- Level validation (min_grade <= max_grade).
    
- Branch only allowed for high school levels.
    
- Olympiad degree immutability.
    
- City must belong to province.
    

**API**

- GET educational levels: returns only active.
    
- GET study branches filtered by level.
    
- GET olympiads: only published visible.
    
- GET locations: default, `?all=true`, `?state=<id>`, `?q=`.
    
- Admin CRUD: create/update by staff_admin; forbidden for student.
    
- Caching behavior: cache populated on first call, invalidated on update.
    

**Security**

- RBAC enforced: staff_admin only for mutations.
    
- Audit events logged for create/update.
    

## 7) OpenAPI (drf‑spectacular)

- Tags: `taxonomy`, `admin-taxonomy`.
    
- Components: `EducationalLevel`, `StudyBranch`, `Olympiad`, `Location`, `Province`, `City`.
    
- Examples for nested location queries.
    

## 8) Observability & Metrics

- `taxonomy_cache_hits_total`, `taxonomy_cache_misses_total`.
    
- `taxonomy_admin_mutations_total{type=level|branch|olympiad|location}`.
    

## 9) Done Definition

- All acceptance gates in MASTER_PROMPT §5 pass for taxonomy modules.
    
- Endpoints behave exactly as in `ENDPOINTS_SPEC.md`.
    
- Coverage ≥ 85%; OpenAPI includes all taxonomy endpoints with examples.
    
- Redis caching functional; cache invalidation proven in tests.
    

## 10) Out of Scope (this milestone)

- Auth endpoints (AUTH_P0).
    
- Profile onboarding flows (PROFILE_P0).
    
- Policy service (POLICY_P0).
    
- RBAC role assignments (RBAC_P0).