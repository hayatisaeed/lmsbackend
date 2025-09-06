# Overview

MentorHub API v1 powers the identity, profile and people services for the MentorHub educational platform. It enables phone-only onboarding with policy-driven catalog exposure and role-based access control.

## Goals

- Simplify authentication with OTP-based sign-in.
- Collect verified profile data to unlock course discovery and purchase.
- Provide admin tools to manage users, roles and educational taxonomies.

## Glossary

| Term | Description |
| --- | --- |
| **OTP** | One-time password sent via SMS for authentication |
| **Refresh Session** | Server-tracked device session tied to a refresh token |
| **Identity API** | External service used to verify national ID and date of birth |
| **Catalog Exposure** | Policy controlling whether users can view course details or purchase |
| **Minor** | User below configurable `AGE_THRESHOLD` requiring parent verification |

## User Roles

- `student` – default for all new users.
- `teacher` – can create instructional content.
- `mentor` – assists students in learning paths.
- `staff_admin` – manages users, taxonomies and policies.
- `superadmin` – full administrative access.

## User Journey

```
Request OTP -> Verify OTP & set display_name ->
Identity & profile completion ->
Explore catalog -> Purchase when allowed
```

## Risks & Mitigations

- **OTP abuse:** rate limits, cooldowns and CAPTCHA thresholds.
- **Identity provider outage:** deferred verification with retry queue.
- **Token theft:** httpOnly refresh cookies, rotation and family revocation.

For detailed system interactions see [SYSTEM_DESIGN](SYSTEM_DESIGN.md) and [ENDPOINTS](ENDPOINTS.md).
