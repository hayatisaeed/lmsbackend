

## Overview

MentorHub is a backend API service for managing students, teachers, mentors, and staff admins in an educational platform. It powers a Next.js frontend and provides OTP‑based phone authentication, profile onboarding, taxonomy management (educational levels, study branches, olympiads, locations), and role‑based access control. Catalog exposure and purchases are controlled via profile completion status and policy settings.

---

## Features

- **Unified OTP Login/Register** — Phone-only authentication; users always registered as `student` initially.
    
- **Refresh Token in Secure Cookies** — httpOnly, Secure, rotated per device; short‑lived access tokens in headers.
    
- **Profile Onboarding** — Identity verification via external API, education history, location, and parent verification for minors.
    
- **Taxonomies** — Admin‑managed educational levels, branches, olympiads, and locations with nested states/cities.
    
- **Role Management** — Admins can promote users from student to teacher, mentor, or staff roles.
    
- **Catalog Policy** — Browse allowed by default; details/purchases gated by profile completion, configurable by admins.
    
- **Observability** — Health checks, Prometheus metrics, audit logs, tracing.
    

---

## Tech Stack

- **Backend**: Django + Django REST Framework
    
- **Database**: PostgreSQL (RDS or self‑hosted)
    
- **Cache/Rate Limit**: Redis
    
- **Frontend**: Next.js (separate repo)
    
- **External Services**: SMS provider (primary + fallback), Identity API for national ID verification
    
- **Containerization**: Docker & Docker Compose (local), K8s-ready for production
    

---

## Local Development

### Requirements

- Docker + Docker Compose
    
- Python 3.11+
    

### Setup

```bash
git clone <repo-url>
cd mentorhub-api
cp .env.example .env
docker compose up --build
```

- API available at `http://localhost:8000/api/v1`
    
- Next.js frontend (if linked) at `http://localhost:3000`
    

### Default Services

- Postgres: `localhost:5432`
    
- Redis: `localhost:6379`
    
- Mailhog/SMS mock: `http://localhost:8025`
    

### Running Tests

```bash
docker compose run --rm api pytest --maxfail=1 --disable-warnings -q
```

---

## Deployment

- Staging and production use environment variables for configuration.
    
- CI/CD pipeline builds Docker images, runs tests, applies migrations, and deploys.
    
- Blue‑green or canary release strategies recommended.
    

---

## API Documentation

- OpenAPI schema: `/api/v1/schema`
    
- Swagger/Redoc UI: `/api/v1/docs`
    

---

## Key Endpoints

- **Auth**: `/api/v1/auth/request-otp`, `/api/v1/auth/verify-otp`, `/api/v1/auth/refresh`, `/api/v1/auth/logout`
    
- **Profile**: `/api/v1/profile/identity`, `/api/v1/profile/education`, `/api/v1/profile/location`, `/api/v1/profile/parent`
    
- **Taxonomies**: `/api/v1/educational-levels`, `/api/v1/study-branches`, `/api/v1/olympiads`, `/api/v1/locations`
    
- **Policy**: `/api/v1/policy/catalog-exposure`
    
- **People (Admin)**: `/api/v1/people/users`, `/api/v1/people/users/{id}/roles`
    

---

## Security Notes

- All refresh tokens are httpOnly, Secure cookies; rotation enforced.
    
- Sensitive PII (national_id, dob) encrypted at rest and never returned.
    
- OTPs expire after 5 minutes and single use only.
    
- CSRF token required for cookie‑based state‑changing requests.
    
- CORS restricted to Next.js frontend origins.
    

---

## Observability & Monitoring

- Health: `/healthz`, `/readyz`
    
- Metrics: `/metrics` (Prometheus format)
    
- Tracing: OpenTelemetry spans for API + external calls
    
- Logs: Structured JSON with request_id; PII masked
    

---

## Roadmap (Next Steps)

- Add consent management (privacy, marketing).
    
- Extend catalog endpoints (courses, packages).
    
- Multi‑language support for errors/messages.
    
- Admin dashboards for analytics.
    

---

## License

[Proprietary] — Internal use only.