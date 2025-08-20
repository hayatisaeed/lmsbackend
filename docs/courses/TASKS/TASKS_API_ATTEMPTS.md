

## Goal

Implement **student attempt lifecycle** endpoints per ENDPOINTS_SPEC: list active exams, start attempt, (optional) autosave answer, submit, get attempt status, and view results with policy enforcement.

## Inputs / Refs

- DOMAIN_MODEL: `courses_exam_domain_model`
    
- SYSTEM_DESIGN: `courses_exam_system_design`
    
- ENDPOINTS_SPEC: `courses_exam_endpoints_spec`
    
- TEST_PLAN: `courses_exam_test_plan`
    
- SERIALIZERS/PERMS: `courses_exam_tasks_serializers_perms`
    

## Deliverables

- DRF class-based views + routers for:
    
    - `GET /my/active-exams/`
        
    - `POST /{course_id}/exams/{exam_id}/attempts/start/`
        
    - `GET /exams/attempts/{attempt_id}/`
        
    - `PUT /exams/attempts/{attempt_id}/answers/{question_id}/autosave/` (optional MVP)
        
    - `POST /exams/attempts/{attempt_id}/submit/`
        
    - `GET /exams/attempts/{attempt_id}/result/`
        
- Server-side time enforcement and auto-submit hook.
    
- OpenAPI docs with examples and error schemas.
    

---

## Endpoint Specs & Logic

### 1) List Active Exams (dashboard)

**GET** `/api/v1/courses/my/active-exams/`

- **Perms**: Authenticated student; filter to courses the user joined.
    
- **Logic**:
    
    - Query ExamAssignments for courses where user is a member and `now` within `[start_at, end_at]` (or no end).
        
    - Join with existing Attempt (if any) to show `started`, `attempt_status`, `expires_at`.
        
    - Return exam card fields: `exam_id, course_id, title, start_at, end_at, started, attempt_status, expires_at_if_started`.
        

### 2) Start Attempt

**POST** `/api/v1/courses/{course_id}/exams/{exam_id}/attempts/start/`

- **Perms**: `IsEnrolledInCourse` + `IsAttemptOwner` (implicit).
    
- **Validations**:
    
    - `now` within assignment window; reject otherwise (403).
        
    - Enforce **one attempt per (user, exam, course)**; if exists, return 409 + existing attempt info.
        
    - Resolve duration: `duration_override` or `exam.duration_minutes`; if none → 400.
        
- **Actions**:
    
    - Create `Attempt(status=in_progress)`, set `started_at=server_now`, `expires_at=started_at + duration`.
        
    - Pre-create empty `Answer` rows for each question (optional; or lazy create on first save).
        
    - Return attempt info + **exam structure** (questions, options, assets).
        

### 3) Get Attempt Detail

**GET** `/api/v1/courses/exams/attempts/{attempt_id}/`

- **Perms**: `IsAttemptOwner`.
    
- **Logic**:
    
    - Return attempt fields + remaining time computed server-side.
        
    - Include current **draft snapshot** if autosave enabled (optional), otherwise only final answers if submitted.
        

### 4) Auto-Save Answer (optional MVP)

**PUT** `/api/v1/courses/exams/attempts/{attempt_id}/answers/{question_id}/autosave/`

- **Perms**: `IsAttemptOwner` + attempt `status=in_progress` and `now < expires_at`.
    
- **Validations**: via `AnswerAutoSaveSerializer` (type rules, version, file caps, mime/size).
    
- **Throttling**: 5 req / 10s per user per attempt.
    
- **Actions**:
    
    - Update draft storage (either a JSON column on Answer or a separate DraftAnswer table); bump `auto_save_version`.
        
    - Respond with `{version, saved_at}`.
        

### 5) Submit Attempt

**POST** `/api/v1/courses/exams/attempts/{attempt_id}/submit/`

- **Perms**: `IsAttemptOwner`.
    
- **Validations**:
    
    - If `now >= expires_at`, first **auto-submit** then return current status.
        
    - Ensure required answers exist and conform.
        
- **Actions**:
    
    - Snapshot drafts → `final_payload`; set `submitted_at`; set `status=submitted`.
        
    - If exam is **MCQ-only** and `auto_grade_if_all_mcq=true`, run auto-grader immediately:
        
        - Compute per-question score with inheritance rules.
            
        - Sum to `final_score`; compute `is_passed` via exam policy.
            
        - Mark `autograded=true`; set `status=graded` but keep **visibility** per policy (may be hidden until admin release).
            

### 6) View Result

**GET** `/api/v1/courses/exams/attempts/{attempt_id}/result/`

- **Perms**: `IsAttemptOwner`.
    
- **Logic**:
    
    - Use policy engine to decide response shape (hidden vs visible; rejected always see scores).
        
    - Include per-question feedback if available (from GradingItem).
        

---

## Auto-Submit on Timeout (Server)

- Implement a Celery task that periodically scans `Attempt` where `status=in_progress AND expires_at <= now()` and performs submit logic.
    
- Idempotent: re-running on an already-submitted attempt is a no-op.
    
- Log audit events: `AttemptAutoSubmitted`.
    

---

## Serialization

- Use: AttemptStartSerializer, AttemptDetailSerializer, AnswerAutoSaveSerializer, AttemptSubmitSerializer, ResultSerializer.
    
- For exam structure, include: questions (id, type, title, body, assets, options), effective scoring (optional), and any per-question constraints.
    

---

## Permissions & Guards

- `IsEnrolledInCourse` on list + start.
    
- `IsAttemptOwner` for all attempt-specific routes.
    
- Server-side time check on every write (autosave/submit).
    

---

## OpenAPI

- Add `extend_schema` with request/response examples from ENDPOINTS_SPEC.
    
- Tag endpoints under `Attempts`.
    

---

## Tests

- Active exams list filters by membership and window.
    
- Start attempt creates record, sets `expires_at`, prevents duplicates.
    
- Autosave obeys throttle and type rules.
    
- Submit validates required answers and snapshots drafts.
    
- Timeout path auto-submits.
    
- Result visibility policies enforced (rejected see scores; hidden until release shows pending).
    

---

## Done Criteria

1. All attempt endpoints implemented and routed under `/api/v1/courses/...`.
    
2. Strict permission checks and server-time enforcement.
    
3. Auto-submit worker operational and idempotent.
    
4. OpenAPI shows accurate schemas and examples.
    
5. Tests from this task pass in CI.