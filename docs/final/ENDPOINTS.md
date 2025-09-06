# Endpoints

All endpoints are versioned under `/api/v1` and accept/return JSON. Errors follow `{ "error": {"code", "message", "details?"}, "request_id" }`.

## Conventions

- **Pagination**: `page`, `page_size` (default 20, max 100), `ordering`
- **Auth**: Access token in `Authorization: Bearer`; refresh in httpOnly Secure cookie
- **CSRF**: `X-CSRF-Token` required for cookie-auth POST/PUT/PATCH/DELETE

## 1. Auth & Session

### Request OTP
`POST /api/v1/auth/request-otp`
```json
{ "phone": "+989914307462" }
```
Responses include `is_new_user` and cooldown seconds. Errors: `invalid_phone`, `otp_throttled`.

### Verify OTP
`POST /api/v1/auth/verify-otp`
```json
{
  "phone": "+989914307462",
  "code": "123456",
  "display_name": "John Doe",
  "email": "john@example.com"
}
```
Returns `access_token`, `profile_completion` object and sets refresh cookie. Errors: `otp_invalid_or_expired`, `user_locked`.

### Refresh Access Token
`POST /api/v1/auth/refresh`
- Cookie only
- Rotates refresh token; on reuse family revoked
- Errors: `auth_invalid_refresh`, `auth_family_revoked`

### Logout
`POST /api/v1/auth/logout`
- Clears refresh cookie and revokes family

### Session Introspection
`GET /api/v1/auth/session`
- Returns current user, roles, profile completion and `is_new_user`

## 2. Profile

Endpoints require valid access token.

- `POST /api/v1/profile/identity` – submit `national_id` + `date_of_birth`; rate limited 5/24h
- `POST /api/v1/profile/education` – submit `level`, `grade`, optional `study_branch`, `olympiads[]`
- `POST /api/v1/profile/location` – submit `province_id` & `city_id`
- `POST /api/v1/profile/parent` – request parent OTP when minor
- `POST /api/v1/profile/parent/verify` – verify parent OTP

## 3. Taxonomies

| Method & Path | Description |
| --- | --- |
| `GET /api/v1/educational-levels` | List levels; filter/order supported |
| `GET /api/v1/study-branches` | Filter by `level` where `is_high_school=true` |
| `GET /api/v1/olympiads` | Returns published olympiads |
| `GET /api/v1/locations` | Provinces; `?all=true` nested; `?state=<slug|id>` cities |

## 4. People & RBAC

Admin-only endpoints (`staff_admin` or higher):
- `GET /api/v1/people/users` – query users (`q`, `role`, `is_profile_complete`)
- `PATCH /api/v1/people/users/{id}/roles` – assign roles

## 5. Policy

- `GET /api/v1/policy/catalog-exposure`
```json
{ "mode": "browse_only", "can_view_details": false, "can_purchase": false }
```

## 6. Ops & Documentation

- `GET /api/v1/healthz`
- `GET /api/v1/readyz`
- `GET /api/v1/metrics`
- `GET /api/v1/schema`
- `GET /api/v1/docs`

## Error Codes (non-exhaustive)

`invalid_phone`, `otp_throttled`, `otp_invalid_or_expired`, `auth_invalid_refresh`, `auth_family_revoked`, `identity_provider_error`, `forbidden_insufficient_role`

Further entity rules are described in [DOMAIN_MODEL](DOMAIN_MODEL.md). Security requirements for tokens and cookies are in [SECURITY](SECURITY.md).
