# Runbooks & Configuration

This guide covers environment configuration and operational playbooks for MentorHub API v1.

## Environment Variables

| Key | Purpose |
| --- | --- |
| `APP_ENV` | Environment name (`local`, `staging`, `prod`) |
| `APP_HOST_URL` | Public base URL used for CORS and cookies |
| `ALLOWED_ORIGINS` | Comma-separated Next.js origins for CORS |
| `REFRESH_COOKIE_NAME` | Name of refresh cookie (e.g. `__Host-mh_rtk`) |
| `CSRF_COOKIE_NAME` | Non-httpOnly CSRF cookie (e.g. `mh_csrf`) |
| `JWT_ACCESS_TTL_SEC` | Access token lifetime (default 600) |
| `JWT_REFRESH_TTL_SEC` | Refresh token lifetime (e.g. 2592000) |
| `SESSION_MAX_DEVICES` | Max concurrent device sessions per user |
| `OTP_TTL_SEC` | OTP validity in seconds (default 300) |
| `OTP_COOLDOWN_SEC` | Minimum gap between OTP sends |
| `IDENTITY_API_BASE_URL` | External identity lookup endpoint |
| `REDIS_URL` | Redis DSN for rate limiting and token blocklist |
| `DB_URL` | Postgres DSN |
| `DATA_ENCRYPTION_KEY` | Key for encrypting `national_id` and `date_of_birth` |
| `FEATURE_CATALOG_EXPOSURE_MODE` | `browse_only`, `locked`, or `open` |

All secrets should be stored in a managed secret store and injected as environment variables.

## Operational Playbooks

### OTP Provider Outage
1. Detect elevated `sms_unavailable` errors.
2. Switch to `SMS_FALLBACK_PROVIDER` and notify stakeholders.
3. Record incident and restore primary when healthy.

### Redis Down
1. Enter conservative mode: deny OTP sends beyond minimal threshold; pause refresh rotation with strict reuse detection.
2. Restore Redis and re-enable normal policies.

### JWT Key Rotation
1. Add new signing key with `kid`; start signing new tokens while accepting old.
2. After full refresh TTL, retire old key and monitor 401/419 errors.

### Token Compromise / Reuse Detected
1. Revoke refresh family for affected user.
2. Expire refresh cookie and force re-authentication.
3. Audit event `refresh_reuse_detected` emitted.

### Identity API Outage
1. Mark identity verification as deferred; queue retries with backoff.
2. Inform users of delay without exposing sensitive data.
3. Resume processing when provider recovers.

## Startup Checklist

1. Set required environment variables.
2. `/healthz` returns 200; `/readyz` confirms DB, Redis, SMS and Identity reachability.
3. OTP request → verify → refresh rotation works end-to-end.
4. Confirm `FEATURE_CATALOG_EXPOSURE_MODE` behaves as configured.

Refer to [SECURITY](SECURITY.md) for token and PII handling guidelines.
