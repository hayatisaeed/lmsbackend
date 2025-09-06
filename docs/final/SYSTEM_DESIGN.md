# System Design

MentorHub API v1 is a Django + DRF service with PostgreSQL for persistence and Redis for rate limiting and session tracking. External SMS and Identity providers are integrated for OTP delivery and national ID verification.

## Architecture
```
+---------------------------+            +-----------------------------+
|        Next.js FE         |            |  Admin (Backoffice UI)      |
+-------------+-------------+            +---------------+-------------+
              |   HTTPS (JWT access, refresh cookie)
              v
+---------------------------------------------------------------+
|                     MentorHub API (Django)                    |
|  Auth & Session  |  Profile  |  People/RBAC  |  Policy Probe |
+---------+---------+----------+---------------+---------------+
          |                    |               |
          v                    v               v
+---------+---------+  +-------+------+  +----+----------------+
|    Postgres        |  |    Redis     |  | External Services  |
|  Users, Profile,   |  | Rate limits, |  |  SMS (primary+fb)  |
|  Taxonomies, OTP,  |  | Refresh BL   |  |  Identity API      |
|  Refresh Sessions  |  | Caches       |  +--------------------+
+--------------------+  +--------------+
```

## Data Flow Highlights

1. **Unified OTP Sign-In**
```
Client -> POST /auth/request-otp
API -> SMS provider
Client -> POST /auth/verify-otp (display_name required on first success)
API -> issues access token, sets refresh cookie
```

2. **Refresh Rotation & Reuse Detection**
```
Client -> POST /auth/refresh (refresh cookie)
API -> rotate token, revoke family on reuse
```

3. **Minor Parent Verification**
```
API computes minor flag from IdentityInfo
Client -> POST /profile/parent & /profile/parent/verify
API -> marks ParentContact verified
```

## Components

- **Auth Service** – handles OTP, refresh rotation, CSRF, session introspection.
- **Profile Service** – identity, education, location and parent flows.
- **People & RBAC** – role assignment and admin protections.
- **Policy Service** – exposes catalog exposure mode to frontend.
- **Observability** – healthz/readyz endpoints, metrics and structured logs.

Security and privacy controls are detailed in [SECURITY](SECURITY.md).
