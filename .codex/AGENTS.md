#  Operating Guide for CodeX

## 1) Purpose

This file tells CodeX **how to behave** on this repo, **what to do first** when the repo has only docs, and **how to turn specifications into a working Django/DRF service** that passes our acceptance gates.

---

## 2) Source of Truth & Boundaries

- **Specs live at** `./docs/users/v1/` and are authoritative: `ENDPOINTS_SPEC.md`, `DOMAIN_MODEL.md`, `SYSTEM_DESIGN.md`, `CONFIG_AND_RUNBOOKS.md`, `ACCEPTANCE_CRITERIA.md`, `README.md`.
    
- **Legacy sample** at `./shitcode/` is **reference‑only** (naming & style). **Do not** import from or copy logic/schema verbatim. Treat it as read‑only.
    
- **Public API prefix** is `/api/v1`. Use DRF, drf‑spectacular, Redis, Postgres per specs.
    

---

## 3) If the repo has no Django project yet → run BOOTSTRAP_P0 first

The error you surfaced ("no real Django/DRF project structure") is expected before the initial scaffold exists. **Do not block.** Execute **BOOTSTRAP_P0** below, then proceed to `TASKS_AUTH_P0.md`.

### BOOTSTRAP_P0 — Deliverables

Create a minimal, production‑ready skeleton that the later milestones will extend.

**Project layout**

```
mentorhub-api/
├─ apps/
│  └─ users/                 # empty package now; filled by AUTH/PROFILE/TAXONOMY tasks
├─ config/                   # Django project settings & urls
├─ docker/                   # runtime assets (optional)
├─ scripts/                  # manage helpers (optional)
├─ .env.example
├─ docker-compose.yml
├─ requirements.txt
├─ pyproject.toml            # ruff/black/isort/mypy/pytest config
├─ manage.py
└─ README.md                 # keep, do not overwrite; add "How to run" if missing
```

**Skeleton requirements**

- Django project named **`config`** (settings module: `config.settings`), timezone/locale sane defaults.
    
- Installed apps: `rest_framework`, `drf_spectacular`, `apps.users` (empty for now), `django.contrib.admin`.
    
- DRF defaults: JSON only, pagination, exception handler wired to our error envelope.
    
- OpenAPI: `/api/v1/schema`, `/api/v1/docs` routes configured via drf‑spectacular.
    
- Health endpoints: `/api/v1/healthz`, `/api/v1/readyz` (stub readiness that will later check DB/Redis/SMS/Identity).
    
- CORS/CSRF: settings placeholders and env toggles (values from `CONFIG_AND_RUNBOOKS.md`).
    
- Redis & Postgres settings via env (even if not used yet).
    
- **No domain models yet** (AUTH_P0 will add them). Keep migrations enabled.
    

**Tooling**

- `pyproject.toml` with ruff/black/isort/mypy/pytest settings matching our standards.
    
- `requirements.txt` minimal: Django, djangorestframework, drf‑spectacular, psycopg, redis, python‑dotenv (and mypy/ruff/pytest as dev).
    
- `docker-compose.yml` with services: `api`, `db` (postgres), `redis`.
    

**CI hint** (optional in this step)

- Add placeholders for lint/test workflows; they can be refined later.
    

**Acceptance for BOOTSTRAP_P0**

- `python manage.py runserver` starts.
    
- `GET /api/v1/docs` renders an empty schema (no domain endpoints yet).
    
- Linting commands run with no fatal issues.
    

---

## 4) Milestone order for CodeX

1. **BOOTSTRAP_P0** (scaffold) → this file.
    
2. **AUTH_P0** — see `TASKS_AUTH_P0.md`.
    
3. **PROFILE_P0** — see `TASKS_PROFILE_P0.md`.
    
4. **TAXONOMY_P0** — see `TASKS_TAXONOMY_P0.md`.
    
5. **POLICY_P0** — see `TASKS_POLICY_P0.md`.
    
6. **RBAC_P0** — when added.
    

Always complete **one milestone at a time**, merging only when acceptance gates pass.

---

## 5) Global Implementation Rules (summarized)

- **Security‑first**: least privilege, validated inputs, CSRF for cookie‑credentialed writes, secret hygiene, PII minimization.
    
- **Sessions**: short‑lived access JWT in header; refresh token in **httpOnly+Secure cookie** set/cleared by backend; rotate every refresh; detect reuse and revoke family.
    
- **Phone‑only unified sign‑in**: `display_name` required on first verify; email optional; password optional.
    
- **Profile gates**: identity→education→location→parent(for minors). Default policy: list browse allowed; details/purchase gated until completion.
    
- **Locations endpoint**: default states, `?all=true` nested, `?state=<slug|id>` cities, `?q=` search.
    
- **Error envelope** (non‑2xx): `{error:{code,message,details?}, request_id}` for every API.
    
- **OpenAPI**: drf‑spectacular must reflect all endpoints as per `ENDPOINTS_SPEC.md`.
    

---

## 6) Pull Request Expectations (per milestone)

- Code under `apps/users/` (views/viewsets, serializers, models, permissions, urls, services/utils).
    
- Migrations included and reversible.
    
- Tests (pytest + factory_boy) with **≥85% coverage** on changed modules.
    
- Updated OpenAPI visible at `/api/v1/docs`.
    
- Metrics and audit events where specified.
    
- Changelog in PR description summarizing endpoints & behaviors.
    

---

## 7) How to react to missing code next time

If you detect that only docs exist (like the error you printed), **do this instead of failing**:

1. Create a new task/branch **`bootstrap/p0`**.
    
2. Implement **BOOTSTRAP_P0** as defined above.
    
3. Open a PR titled **"Bootstrap Django/DRF skeleton (BOOTSTRAP_P0)"**.
    
4. After merge, immediately pick up `TASKS_AUTH_P0.md`.
    

Include a short PR note: _“Scaffolded minimal Django/DRF project per AGENTS.md (BOOTSTRAP_P0). No domain endpoints yet. /api/v1/docs renders empty schema.”_

---

## 8) Do / Don’t

**Do**

- Follow `./docs/users/v1/` strictly; raise diffs if conflicts.
    
- Keep refresh cookie management server‑side; assert cookie attributes in tests.
    
- Use Redis for throttles and token family state.
    

**Don’t**

- Don’t import from `shitcode/`.
    
- Don’t store access tokens in cookies or localStorage.
    
- Don’t return encrypted PII in any response.
    

---

## 9) Quick Start (human operator cheat‑sheet)

- Create CodeX task: **“Run BOOTSTRAP_P0 from AGENTS.md”**.
    
- When green: create task **“Implement AUTH_P0 per TASKS_AUTH_P0.md”**.
    
- Repeat for PROFILE_P0, TAXONOMY_P0, POLICY_P0.
    

---

## 10) Contact Points (signals CodeX should emit)

- On completing a milestone, post a summary: endpoints added, tests count & coverage, schema diff summary, and any TODOs.
    
- On encountering provider or env gaps, propose placeholders and mocks aligned with `CONFIG_AND_RUNBOOKS.md`.