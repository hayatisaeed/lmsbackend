
## Goal

Bootstrap the **`courses`** Django app (Exams domain) in our monorepo with DRF, JWT, Celery, and object storage wired—ready for models/endpoints in the next tasks.

## Inputs / Refs

- DOMAIN_MODEL: `courses_exam_domain_model`
    
- SYSTEM_DESIGN: `courses_exam_system_design`
    
- ENDPOINTS_SPEC: `courses_exam_endpoints_spec`
    
- Auth service (JWT) already exists in repo.
    

## Deliverables

- New Django app `courses/` added to project, URLs mounted at `/api/v1/courses/`.
    
- Dependencies installed; settings updated for DRF, SimpleJWT, django-filter, drf-spectacular, django-storages, Celery/Redis.
    
- Base project scaffolding: app module layout, empty routers, health/readiness endpoints, OpenAPI generation enabled.
    
- CI: tests and lint run successfully (even with empty app tests).
    
- Minimal README note on how to run server, worker, and docs.
    

## Constraints

- 12‑Factor: all config via env; **no secrets in repo**.
    
- Storage: S3/MinIO via `django-storages` (signed or gated access later).
    
- Timezone: UTC in backend; ISO‑8601 timestamps in APIs.
    
- No WebSockets in MVP.
    

## Steps

### 1) Dependencies

Add (or confirm) these packages to the project:

- `djangorestframework`, `djangorestframework-simplejwt`, `django-filter`, `drf-spectacular`
    
- `django-storages`, `boto3`
    
- `celery`, `redis`
    
- Dev tooling already used: `ruff`, `black`, `isort`, `pytest`, `factory_boy`, `pytest-django`
    

### 2) Create App Skeleton

- New Django app: `courses/`
    
    - `apps.py`, `__init__.py`
        
    - `urls.py` (root for this app)
        
    - `views.py` (temporary: health/readiness)
        
    - `permissions.py`, `serializers.py` (empty stubs)
        
    - `admin.py` (empty), `migrations/` (init)
        
    - `tasks.py` (Celery stub)
        
- Add `courses` to `INSTALLED_APPS`.
    

### 3) Project Settings (extend existing settings)

- **DRF defaults**: authentication (SimpleJWT), pagination, filtering (`django-filter`), throttling (basic), exception handler.
    
- **SimpleJWT**: token lifetimes via env.
    
- **Spectacular**: `SPECTACULAR_SETTINGS` with title “Courses/Exams API”, serve schema at `/api/schema/` and UI at `/api/docs/`.
    
- **CORS**: allow our SPA origins (env-controlled).
    
- **Storage**: configure `DEFAULT_FILE_STORAGE` for S3/MinIO via env (see ENV section).
    
- **Celery**: broker/backend from env; autodiscover tasks.
    

### 4) URL Wiring

- Project `config/urls.py`: include `path("api/v1/courses/", include("courses.urls"))`.
    
- In `courses/urls.py`: mount:
    
    - `health/` → liveness
        
    - `readiness/` → DB + storage + broker check
        
    - (Router placeholder for future endpoints)
        

### 5) Celery Bootstrap

- Ensure `celery.py` entry in project root (if not present) and `__init__.py` loads app.
    
- Verify worker launch with autodiscover (no-op tasks pass).
    

### 6) Storage Smoke Checks

- Add a tiny internal readiness check that attempts a signed URL generation or bucket head (non-blocking, fail-soft with warning).
    

### 7) OpenAPI Exposure

- Expose schema and Swagger/Redoc via drf-spectacular at project level.
    
- Confirm `/api/docs/` loads and lists the placeholder endpoints.
    

### 8) CI / Tooling

- Ensure `pre-commit` hooks run ruff/black/isort.
    
- Add a trivial test for `health/` to keep CI green.
    
- Update coverage config to include `courses/*`.
    

## Environment Variables (baseline)

```
DJANGO_SETTINGS_MODULE=...                # existing
SECRET_KEY=...                            # existing
DEBUG=false                               # per env
ALLOWED_HOSTS=api.example.com,localhost   # comma-separated

# DRF/JWT
JWT_ACCESS_LIFETIME_MIN=30
JWT_REFRESH_LIFETIME_DAYS=7

# CORS
CORS_ALLOWED_ORIGINS=https://app.example.com,https://admin.example.com

# Celery/Redis
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
CELERY_TASK_ALWAYS_EAGER=false            # true for local quick runs

# Storage (S3/MinIO)
DEFAULT_FILE_STORAGE=storages.backends.s3boto3.S3Boto3Storage
AWS_STORAGE_BUCKET_NAME=mentorhub-assets
AWS_S3_ENDPOINT_URL=http://minio:9000       # MinIO local, omit for AWS
AWS_ACCESS_KEY_ID=xxxx
AWS_SECRET_ACCESS_KEY=xxxx
AWS_S3_REGION_NAME=us-east-1
AWS_QUERYSTRING_AUTH=true                   # signed URLs
MAX_UPLOAD_SIZE_MB=10                       # MVP cap
ALLOWED_ANSWER_MIME=image/png,image/jpeg,application/pdf
```

## Verification (Done Criteria)

- `/api/v1/courses/health/` returns 200.
    
- `/api/v1/courses/readiness/` returns 200 and reports DB + Celery broker reachable; storage check warns or passes.
    
- `/api/docs/` renders with the Courses tag visible (even with placeholder endpoints).
    
- Celery worker starts and logs task autodiscovery for `courses`.
    
- Minimal test: health endpoint test passes in CI; linters pass.
    

## Rollback / Notes

- Changes are additive; to rollback, remove `courses/` app registration and URL include.
    
- No data model created in this task; migrations unaffected.
    

## Next Tasks

- `TASKS_MODELS.md` → implement DOMAIN_MODEL entities.
    
- `TASKS_SERIALIZERS_PERMS.md` → validations and permissions.
    
- `TASKS_API_EXAMS.md` & `TASKS_API_ATTEMPTS.md` → authoring and attempt flows.
    
- `TASKS_FILES.md`, `TASKS_CELERY.md`, `TASKS_GRADING.md`, `TASKS_TESTS.md`.
    

If you want, I can draft **TASKS_MODELS.md** in the same concise format next.