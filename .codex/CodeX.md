# TL;DR

Set up a clean monorepo, drop my specs into `./docs/<app>/v1/`, add your legacy sample in `./shitcode/` (read‑only), and give CodeX a **single “master prompt”** that: (1) points to the docs, (2) enumerates prioritized tasks, (3) defines acceptance gates (tests, lint, OpenAPI, cookies, rate limits), and (4) explains how to use the “shitcode” folder as reference—not source. Then run CodeX against one milestone at a time (Auth P0 → Profile P0 → Taxonomy → Policy probe → RBAC).

Below is a practical, copy‑pasteable startup plan.

---

# 1) Repo layout (top-level)

```
mentorhub-api/
├─ apps/
│  └─ users/                # first app CodeX will touch (auth+profile+people)
├─ shitcode/                # legacy sample: read-only reference
├─ docs/
│  ├─ users/
│  │  └─ v1/
│  │     ├─ CONFIG_AND_RUNBOOKS.md
│  │     ├─ DOMAIN_MODEL.md
│  │     ├─ ENDPOINTS_SPEC.md
│  │     ├─ SYSTEM_DESIGN.md
│  │     ├─ ACCEPTANCE_CRITERIA.md
│  │     └─ README.md
│  └─ shared/
│     └─ CODING_STANDARDS.md  # optional (lint/ruff/black/pytest rules)
├─ .codex/
│  ├─ MASTER_PROMPT.md
│  ├─ TASKS_AUTH_P0.md
│  ├─ TASKS_PROFILE_P0.md
│  ├─ TASKS_TAXONOMY_P0.md
│  ├─ TASKS_POLICY_P0.md
│  └─ TASKS_RBAC_P0.md
├─ pyproject.toml            # ruff/black/isort/pytest tooling (CodeX will need)
├─ requirements.txt
├─ docker-compose.yml
└─ README.md
```

> Put the canvas docs I wrote into `./docs/users/v1/` exactly as you described.  
> The “shitcode” folder is only a **reference corpus** for CodeX (naming, serializers, etc.), **not** code to reuse.

---

# 2) Master prompt for CodeX (what it must know)

Create `.codex/MASTER_PROMPT.md` with:

**Context**

- Project: MentorHub API (Django + DRF).
    
- Use docs in `./docs/users/v1/*.md` as the **source of truth**.
    
- Use `./shitcode/` only to infer style (serializers/permissions naming), never to copy logic _as is_.
    

**Global requirements**

- API versioning `/api/v1`.
    
- Phone‑only unified OTP auth; `display_name` required at first verify; email optional; password optional.
    
- Refresh token in **httpOnly+Secure cookie**; access token in header; CSRF via double‑submit cookie.
    
- Rate limits: OTP per phone/day & per IP/hour; cooldown; identity submissions 5/24h.
    
- RBAC: default role `student`; admins change later.
    
- Locations endpoint modes (`default`, `?all=true`, `?state=slug|id`).
    
- OpenAPI via drf‑spectacular; Spectacular views exposed.
    
- Security: PII encryption for national_id & dob; redact in logs.
    

**Acceptance gates (for every task)**

- Unit/API tests pass (pytest); coverage ≥ 85% on changed modules.
    
- Ruff/black/isort clean; mypy (or pyright) passes.
    
- OpenAPI updates present; `/schema` renders.
    
- Cookie attributes set correctly; refresh rotation & reuse detection tested.
    
- Throttling works; error envelope `{error:{code,message,details?}, request_id}`.
    
- Endpoints match `ENDPOINTS_SPEC.md` strictly.
    

**Priorities / Milestones**

1. **AUTH_P0** → endpoints: `/auth/request-otp`, `/auth/verify-otp`, `/auth/refresh`, `/auth/logout`, `/auth/session`; cookies; rotation; rate limits.
    
2. **PROFILE_P0** → `/profile/identity`, `/education`, `/location`, `/parent`, `/parent/verify`; minors only for parent requirement.
    
3. **TAXONOMY_P0** → educational-levels, study-branches, olympiads, **locations** multi-mode.
    
4. **POLICY_P0** → `/policy/catalog-exposure`.
    
5. **RBAC_P0** → default role `student`; admin role endpoints to assign roles.
    

---

# 3) Split tasks for CodeX (one file per milestone)

For each TASKS_*.md (example: `.codex/TASKS_AUTH_P0.md`):

**Objective**

- Implement endpoints as per `ENDPOINTS_SPEC.md` and cookie/token strategy from `CONFIG_AND_RUNBOOKS.md`.
    

**Deliverables**

- Views/viewsets, serializers, permissions, urls routing under `apps/users/`.
    
- Token utils: refresh rotation, family revoke, blocklist in Redis.
    
- Rate limiting: OTP sends per phone/day and IP/hour; cooldown.
    
- Tests: auth unit + API tests; cookie attribute assertions; rotation/reuse tests.
    
- OpenAPI annotations; add `/healthz`, `/readyz`, `/docs`, `/schema`.
    

**Constraints**

- No breaking from docs; no reuse of “shitcode” logic verbatim.
    
- Use ruff/black/isort; typing hints; pytest + factory_boy.
    

**Done when**

- All acceptance gates pass and endpoints behave per spec.
    

> Create similar TASKS files for Profile, Taxonomy, Policy, RBAC with their specific endpoints and checks.

---

# 4) How to “start” CodeX on this repo (operator steps)

1. **Prepare environment**
    
    - Ensure `requirements.txt`, `pyproject.toml` (ruff/black/isort/pytest), and `docker-compose.yml` exist.
        
    - Create **empty app skeleton** under `apps/users/` so CodeX has a target path.
        
2. **Seed the knowledge**
    
    - Place all spec files in `./docs/users/v1/`.
        
    - Place sample legacy project in `./shitcode/`.
        
3. **Point CodeX to MASTER_PROMPT**
    
    - In your CodeX UI/CLI, select the repo root and set `.codex/MASTER_PROMPT.md` as the **project brief**.
        
    - Add `.codex/TASKS_AUTH_P0.md` as the **first work item**.
        
4. **Run CodeX in milestone mode**
    
    - Ask CodeX to **only** implement AUTH_P0.
        
    - On completion, run: `pytest -q` and linting; review the OpenAPI at `/api/v1/docs`.
        
    - If green, proceed to `.codex/TASKS_PROFILE_P0.md`, and so on.
        
5. **Guardrails**
    
    - Make `shitcode/` read‑only using a pre-commit hook or CI check so generated code can’t import from it.
        
    - Add CI job that fails if any module imports from `shitcode`.
        
6. **Review loop**
    
    - After each milestone, validate against `ACCEPTANCE_CRITERIA.md`.
        
    - If gaps exist, open a new `.codex/TASKS_PATCH_<milestone>.md` with crisp steps.
        

---

# 5) Mapping of docs → CodeX artifacts

- `CONFIG_AND_RUNBOOKS.md` → env vars, cookie attrs, rate limits, runbooks → **CodeX should wire settings & middleware**.
    
- `DOMAIN_MODEL.md` → models/relations/validations → **serializers + DB schema**.
    
- `ENDPOINTS_SPEC.md` → **views/urls + tests**.
    
- `SYSTEM_DESIGN.md` → infra glue (Redis, health, metrics).
    
- `ACCEPTANCE_CRITERIA.md` → CI gates & test expectations.
    
- `README.md` → dev instructions (unchanged by CodeX).
    

---

# 6) “shitcode” usage policy (teach CodeX)

Add this note at the top of `.codex/MASTER_PROMPT.md`:

> **Legacy sample policy**  
> The `./shitcode/` directory is a _reference_ for naming conventions and DRF idioms only. Do **not** copy its logic or database schema. Prefer implementations that match the v1 specs in `./docs/users/v1/`. Any direct imports from `shitcode` must be rejected by CI.

---

# 7) CI/QA harness (so CodeX can finish autonomously)

- **Pre-commit**: ruff, black, isort, bandit.
    
- **CI jobs** (GitHub Actions/GitLab CI):
    
    1. Lint/type: ruff + mypy.
        
    2. Unit/API tests with coverage report; enforce ≥ 85%.
        
    3. Spec check: fail if OpenAPI missing endpoints from `ENDPOINTS_SPEC.md`.
        
    4. Policy check: fail if any import path references `shitcode/`.
        
    5. Security check: bandit (informational, but fail on high).
        

_(If you want, I can drop a ready-to-use CI YAML and pre‑commit config in a follow-up.)_

---

# 8) First work order for CodeX (you can paste this)

**Work item:** Implement **AUTH_P0** per `./docs/users/v1/*`.

**Key points to satisfy:**

- `/api/v1/auth/request-otp` (unified): create user if needed, default role `student`, OTP throttles, cooldown.
    
- `/api/v1/auth/verify-otp`: require `display_name` on first success; set refresh cookie (httpOnly+Secure); return access token + profile status + `is_new_user`.
    
- `/api/v1/auth/refresh`: rotate refresh; reuse → family revoke.
    
- `/api/v1/auth/logout`: clear cookie; revoke family.
    
- `/api/v1/auth/session`: return user + roles + profile completion.
    
- CSRF cookie issuance for cookie‑credentialed flows.
    
- Metrics & logs for OTP send/verify, rotation, reuse.
    
- Tests for cookie attrs, rotation, throttling, and error envelope.
    

---

## NEXT ACTIONS

1. Create the `.codex/` folder and add **MASTER_PROMPT.md** + **TASKS_AUTH_P0.md** (I can generate both now if you like).
    
2. Move the canvas docs into `./docs/users/v1/` (done on your side).
    
3. Copy your legacy project into `./shitcode/` (read-only).
    
4. Kick off CodeX with AUTH_P0, review the PR, then proceed milestone by milestone.