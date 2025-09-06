# QA Criteria

Acceptance rules for MentorHub API v1 features and non-functional requirements.

## 1. Authentication & Session
- Only E.164 phone numbers accepted for OTP requests.
- Cooldown, per-phone/day and per-IP/hour rate limits enforced.
- First successful `verify-otp` must include `display_name`.
- Refresh endpoint rotates token; reuse revokes family and returns 409.
- Logout clears refresh cookie and revokes device family.

## 2. Profile Completion
- **Identity**: accepts `national_id` + `date_of_birth`; rate limited to 5 attempts/24h; populates names and gender via Identity API.
- **Education**: grade within level range; `study_branch` required if level is high school; ≤3 unique published olympiads.
- **Location**: province/city pair valid from taxonomy.
- **Parent Contact**: required and OTP-verified only for minors.
- Profile marked complete only when all sections and `display_name` present.

## 3. Taxonomies & Locations
- Educational levels endpoint filters and orders correctly.
- Study branches endpoint filters by level with `is_high_school=true`.
- Olympiads endpoint returns published items; degree is static attribute.
- Locations endpoint supports `?all=true`, `?state=<slug|id>` and search via `?q`.

## 4. Roles & RBAC
- New users default to role `student`.
- Admins (`staff_admin` or higher) can assign and remove roles.
- Admin endpoints reject requests without sufficient role and log audit events.

## 5. Catalog Exposure Policy
- `/policy/catalog-exposure` returns mode and booleans `can_view_details`, `can_purchase`.
- Default mode `browse_only`; admin override respected.

## 6. Observability
- `/healthz` returns 200 when process alive.
- `/readyz` verifies DB, Redis, SMS and Identity providers.
- Prometheus metrics expose OTP, JWT and profile stats.
- Audit events recorded for key actions (otp_sent, refresh_reuse_detected, profile_completed...).

## 7. Security & Privacy
- Refresh tokens stored/rotated; old tokens rejected.
- `national_id` and `date_of_birth` encrypted at rest and never returned.
- OTPs expire in ≤5 minutes and invalidated after use.
- CSRF protection enforced for cookie-auth requests.
- CORS restricted to approved origins.

## 8. Failure & Fallbacks
- SMS provider failover works; user receives consistent response.
- Identity provider failure triggers deferred verification, not lockout.
- Redis downtime handled by conservative mode with safe defaults.
- DB degradation triggers read-only modes.

## 9. Non-Functional
- P99 OTP request latency <2s; verify latency <3s; refresh latency <1s.
- Horizontal scalability with stateless API nodes.
- Test coverage ≥85% for auth, profile and taxonomy modules.

Validation rules per entity are listed in [DOMAIN_MODEL](DOMAIN_MODEL.md); endpoint behaviors are in [ENDPOINTS](ENDPOINTS.md).
