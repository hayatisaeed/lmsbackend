# Catalog Exposure Policy (Milestone M4)

> **Goal:** Implement the policy probe and server-side guards that determine whether users (guest, logged-in incomplete, logged-in complete) can **view course lists**, **view course details**, and **purchase**. The policy is configurable and must be enforced consistently across endpoints.

## 0) Scope (Endpoints & Guards)

- `GET /api/v1/policy/catalog-exposure` — policy probe consumed by the Next.js app.
    
- **Guards** (hooks/middleware/services) used by future Catalog/Purchase endpoints to enforce the same policy server-side.
    

## 1) Functional Requirements

1. **Policy Modes** (from env/config; see `CONFIG_AND_RUNBOOKS.md`):
    
    - `browse_only` (default):
        
        - Guests & incomplete profiles: **can_list=true**, **can_view_details=false**, **can_purchase=false**.
            
        - Completed profiles: **can_list=true**, **can_view_details=true**, **can_purchase=true** (subject to payment-specific checks in Commerce).
            
    - `locked`:
        
        - Guests & incomplete profiles: **can_list=false**, **can_view_details=false**, **can_purchase=false**.
            
        - Completed profiles: **can_list=true**, **can_view_details=true**, **can_purchase=true**.
            
    - `open`:
        
        - Guests & incomplete profiles: **can_list=true**, **can_view_details=true**, **can_purchase=false**.
            
        - Completed profiles: **can_list=true**, **can_view_details=true**, **can_purchase=true**.
            
2. **Inputs to Policy Evaluation**
    
    - **Auth state** (guest vs logged-in) from access token.
        
    - **Profile completion** from `/profile/completion` domain service (not a direct HTTP call; use internal service util).
        
    - **Mode** from `FEATURE_CATALOG_EXPOSURE_MODE` env var.
        
3. **Policy Probe Endpoint**
    
    - Request: no body. Auth optional (if access token present, evaluate as logged-in user; otherwise treat as guest).
        
    - Response (200):
        
        ```json
        { "mode": "browse_only", "can_list": true, "can_view_details": false, "can_purchase": false }
        ```
        
    - Errors: none (always 200). On internal failure, return safe default based on mode and guest state.
        
4. **Server-side Guards**
    
    - Provide `policy.can_list(user)`, `policy.can_view_details(user)`, `policy.can_purchase(user)` helpers.
        
    - Add a **decorator/mixin** for viewsets: `@policy_required(action="view_details"|"purchase"|"list")` that returns standardized error envelope when blocked.
        
    - Error envelope for blocked actions: `403 { "error": { "code": "policy_restricted", "message": "Profile completion required to access this resource." }, "request_id": "..." }`.
        

## 2) Non-Functional Requirements

- **Config**: Read `FEATURE_CATALOG_EXPOSURE_MODE` from env with default `browse_only`.
    
- **Observability**: Emit `policy_probe_total{mode=...,state=guest|incomplete|complete}` and `policy_block_total{action=list|view|purchase}` metrics.
    
- **OpenAPI**: Document the probe endpoint and common `policy_restricted` error for guarded routes (as a reusable response component).
    

## 3) Data & Services

- **No new DB models.** Implement a small `policy` domain service that reads env + user profile completion (via existing service function) to produce booleans.
    
- **Caching** (optional): cache `profile_completion` for the current request lifecycle; do not introduce cross-request caches in this milestone.
    

## 4) Settings & ENV

- `FEATURE_CATALOG_EXPOSURE_MODE` ∈ {`browse_only`, `locked`, `open`}.
    

## 5) Error Envelope & Codes

- On guarded routes: `403 policy_restricted` with user-safe message.
    

## 6) Implementation Plan (suggested)

1. **Service**: `apps/users/services/policy.py` with pure functions computing booleans.
    
2. **Endpoint**: `PolicyView` (APIView) at `/api/v1/policy/catalog-exposure` using the service; optional auth.
    
3. **Guards**: decorator/mixin to enforce policy in future Catalog/Purchase views; integrate into a sample placeholder view (or tests) to prove behavior.
    
4. **OpenAPI**: Add schema for probe response; add reusable `PolicyRestricted` response component.
    
5. **Metrics & Logs**: Counters for probe calls and blocks.
    

## 7) Tests (pytest) — target ≥85% coverage for policy module

**Unit**

- Service logic returns correct booleans for all three modes and states (guest, incomplete, complete).
    

**API**

- Probe returns correct values for each mode with guest token absent, incomplete profile, complete profile.
    
- Error envelope appears when guard denies access (use a minimal stub route guarded by `policy_required`).
    

**Edge Cases**

- Internal errors (e.g., profile completion service raises) fallback to safe defaults per mode.
    

## 8) OpenAPI (drf-spectacular)

- Tag: `policy`
    
- Schema: `CatalogExposureResponse` with examples for each mode.
    
- Response component: `PolicyRestricted` (403) for reuse across protected endpoints.
    

## 9) Done Definition

- Probe endpoint works and is documented; returns deterministic booleans per mode and user state.
    
- Guard decorator/mixin available and tested, producing `403 policy_restricted` when appropriate.
    
- Metrics emitted; coverage ≥85% for policy code; lints/typing pass.
    

## 10) Out of Scope

- Actual Catalog/Courses endpoints (to be implemented in a different milestone).
    
- Payment/checkout logic (Commerce milestone).