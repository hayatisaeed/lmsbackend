
## 1) Purpose

This file tells CodeX **how to behave** on the `courses` app:

- Where to find the source of truth (`./docs/courses/`)
    
- How to consume task specs (`./docs/courses/TASKS/`)
    
- How to turn the specs into a working Django/DRF service that passes acceptance gates.
    

---

## 2) Source of Truth & Boundaries

- **Specs live at** `./docs/courses/`:
    
    - `DOMAIN_MODEL.md`
        
    - `SYSTEM_DESIGN.md`
        
    - `ENDPOINTS_SPEC.md`
        
    - `TEST_PLAN.md`
        
    - `README.md` (if present)
        
- **Tasks live at** `./docs/courses/TASKS/`:
    
    - `TASKS_BOOTSTRAP.md`
        
    - `TASKS_MODELS.md`
        
    - `TASKS_SERIALIZERS_PERMS.md`
        
    - `TASKS_API_EXAMS.md`
        
    - `TASKS_API_ATTEMPTS.md`
        
    - (`TASKS_FILES.md`, `TASKS_GRADING.md` if included later)
        
- **Legacy `shitcode/` dir** is **reference only** (naming/idioms). Do **not** copy logic or schema.
    
- **Public API prefix** is `/api/v1/courses`.
    

---

## 3) If repo has no `courses/` app yet → run TASKS_BOOTSTRAP first

Before any models exist, scaffold the app using `TASKS_BOOTSTRAP.md`.

**BOOTSTRAP Deliverables:**

- Create `apps/courses/` Django app.
    
- Wire URLs under `/api/v1/courses/`.
    
- DRF + SimpleJWT + drf-spectacular ready.
    
- Health endpoints (`/api/v1/healthz`, `/api/v1/readyz`).
    
- Minimal OpenAPI schema served at `/api/v1/docs`.
    

Acceptance:

- `python manage.py runserver` starts.
    
- `/api/v1/courses/` base route resolves.
    
- `/api/v1/docs` renders empty schema.
    

---

## 4) Milestone Order for CodeX

1. **TASKS_BOOTSTRAP** — scaffold app, wire configs.
    
2. **TASKS_MODELS** — implement domain models (Exam, Question, Attempt, Answer, etc.).
    
3. **TASKS_SERIALIZERS_PERMS** — serializers, validators, permissions.
    
4. **TASKS_API_EXAMS** — authoring endpoints (exams, questions, publish).
    
5. **TASKS_API_ATTEMPTS** — student endpoints (start attempt, submit, result).
    
6. **TASKS_FILES** (optional) — file uploads (images/PDF).
    
7. **TASKS_GRADING** (optional) — auto-grading + teacher grading workflow.
    

Always complete **one milestone at a time**, merging only when acceptance criteria pass.

---

## 5) Global Implementation Rules

- **Attempts:** one attempt per `(user, exam, course)`. Auto-submit on timeout.
    
- **Scoring:** defaults from exam; overrides at question level. Negative marking configurable.
    
- **MCQ:** single correct option in MVP.
    
- **Visibility:** rejected users always see scores; passed may be hidden. Admin controls release.
    
- **Files (if enabled):** image/PDF only, type/size validated, stored via `django-storages`.
    
- **Permissions:** `IsEnrolledInCourse`, `IsAttemptOwner`, `IsExamAdmin`, `IsGrader`. Deny-by-default.
    
- **Transactions:** use atomic blocks for submit and grading.
    
- **Observability:** `/healthz`, `/readyz`, structured logs, request IDs.
    

---

## 6) Pull Request Expectations

Each milestone PR must include:

- Code under `apps/courses/` (models, serializers, views, urls, perms).
    
- Migrations (complete, reversible).
    
- Tests (pytest + factory_boy) with ≥85% coverage for new code.
    
- Updated OpenAPI visible at `/api/v1/docs`.
    
- Short changelog in PR body (endpoints, behaviors).
    

---

## 7) How to react if only docs exist

If CodeX finds only `./docs/courses/` and no app code:

1. Run `TASKS_BOOTSTRAP.md` → scaffold `courses` app.
    
2. Open PR: **"Bootstrap Courses app (TASKS_BOOTSTRAP)"**.
    
3. After merge, proceed with `TASKS_MODELS.md`.
    

---

## 8) Do / Don’t

**Do:**

- Follow specs in `./docs/courses/`.
    
- Validate file uploads (image/PDF only).
    
- Enforce one attempt rule and server-side timers.
    
- Use DRF routers + drf-spectacular annotations.
    

**Don’t:**

- Copy anything from `shitcode/`.
    
- Trust client clocks for timing.
    
- Expose hidden results when config forbids.
    

---

## 9) Quick Start (human operator cheat-sheet)

- Start with **“Run TASKS_BOOTSTRAP.md for Courses app”**.
    
- When merged, run **“Implement TASKS_MODELS.md”**.
    
- Continue milestone by milestone.
    

---

## 10) Contact Points

At the end of each milestone, CodeX must report:

- Endpoints added.
    
- Migration files created.
    
- Test counts & coverage.
    
- Schema diff summary.
    
- Any TODOs/deferred features.
    

---

Would you like me to also generate a **TASKS_INDEX.md** for `./docs/courses/TASKS/` so CodeX knows the execution order explicitly, just like we did for users?