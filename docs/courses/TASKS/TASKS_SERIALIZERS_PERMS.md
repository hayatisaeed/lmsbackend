

## Goal

Implement DRF **serializers** and **permissions** that enforce business rules for the Exams domain, aligned with DOMAIN_MODEL, SYSTEM_DESIGN, and ENDPOINTS_SPEC. No business logic leaks to views; validation and object‑level checks live here.

## Inputs / Refs

- DOMAIN_MODEL: `courses_exam_domain_model`
    
- SYSTEM_DESIGN: `courses_exam_system_design`
    
- ENDPOINTS_SPEC: `courses_exam_endpoints_spec`
    
- TEST_PLAN: `courses_exam_test_plan`
    

## Deliverables

- Serializer classes for: Exam, ExamAssignment, Question, MCQOption, QuestionFile, Attempt, Answer (+ per‑type payloads), AnswerFile, GradingItem, GraderAssignment.
    
- Permissions: `IsEnrolledInCourse`, `IsExamAdmin`, `IsGrader`, `IsAttemptOwner`, plus function‑level guards.
    
- Throttles for autosave.
    
- Error responses consistent with ENDPOINTS_SPEC (400/403/404/409/413).
    
- Unit/Integration tests covering validations and permission paths.
    

---

## Serializers (Responsibilities & Validation)

### 1) ExamSerializer (create/update)

**Validates**

- `status` transitions: allow `draft→published→archived`; **block edits** if `published` and any attempts exist (use `validate` with query to Attempts).
    
- Defaults/scoring: if `allow_negative_scoring=false` then `default_wrong_score >= 0`.
    
- Policy matrix:
    
    - `min_accept_score >= 0`.
        
    - When `total_score` provided, allow value ≥ 0 (actual total computed at grading; do not hard‑enforce equality in model layer for MVP).
        

**Read serializer**

- Expose effective read fields; include computed `questions_count` and computed `total_max_score` (sum of question effective scores), best‑effort.
    

### 2) ExamAssignmentSerializer

**Validates**

- Unique `(exam, course)`.
    
- Availability window: `start_at < end_at` (if `end_at` present).
    
- Duration resolution: `duration_override` must be positive if provided; otherwise Exam.duration must exist for attempts to start (attempt serializer double‑checks).
    

### 3) QuestionSerializer

**Validates**

- `type ∈ {MCQ, TEXT, FILE, TEXT_OR_FILE}`.
    
- `answer_max_files ≥ 1` when type allows files; reject files when type disallows.
    
- Score overrides: if set, apply same negative marking rules as Exam; else inherit.
    
- **On publish**: block create/update when Exam is `published` and attempts exist.
    

### 4) MCQOptionSerializer

**Validates**

- Enforce **single correct** per MCQ Question: on create/update ensure total `is_correct=True` count == 1 (query options + incoming flag). Reject if zero or >1.
    
- Require ≥2 options for a MCQ question (enforce at finalization or on publish of exam; provide validation error if fewer).
    

### 5) QuestionFileSerializer

**Validates**

- File type by header sniff (image/*), optional PDF only when question `answer_accepts_file_types` includes pdf for ANSWER files; for **question assets**, images only (MVP). Size ≤ `MAX_UPLOAD_SIZE_MB`.
    

### 6) AttemptStartSerializer (input/output)

**Validates**

- Student course membership via `IsEnrolledInCourse`.
    
- Availability: now ∈ [start_at, end_at].
    
- Enforce **one attempt per (user, exam, course)** (DB unique + clean, surface as 409).
    
- Compute `expires_at = started_at + (duration_override or exam.duration_minutes)`; error if none available.
    

### 7) AttemptDetailSerializer (read)

- Returns attempt status, `expires_at`, exam structure (read‑only subset: questions, options, assets), and any existing **draft snapshot** (if we keep it transient on the attempt or derived from answer drafts store; MVP may omit drafts if PM disables autosave).
    

### 8) AnswerAutoSaveSerializer (optional MVP)

**Validates**

- Per question type payload:
    
    - MCQ: `selected_option_id` must belong to question.
        
    - TEXT: non‑empty string within size limit.
        
    - FILE: uploaded file IDs belong to current user’s unfinalized attempt; max files ≤ `answer_max_files`; mime ∈ {image/jpeg, image/png, application/pdf} depending on config.
        
    - TEXT_OR_FILE: at least one of text or files present.
        
- **Versioning**: require `version` int; last‑write‑wins if `version` >= server version, else 409 with server version echo.
    
- **Rate limit hint**: rely on DRF throttle (see Throttling below).
    

### 9) AttemptSubmitSerializer

**Validates**

- Attempt must be `in_progress` and **before** `expires_at`. If not, perform auto‑submit path (promote last draft) then return 409 or success depending on policy.
    
- For each question, ensure required answer present and conforms to type rules; promote draft payloads to **final_payload**. Set `submitted_at`.
    

### 10) ResultSerializer (student view)

- Apply **Result Policy Engine**: if hidden → `{ "status":"pending_release" }`; if rejected → always include score; if passed and `show_score_if_passed=false` → omit `final_score` but show `is_passed=true`.
    
- Optional per‑question feedback when graded.
    

### 11) GradingItemSerializer

**Validates**

- `score_awarded` within [0, question.correct_score] unless negative marking/override permits (<0 allowed when exam allows negatives).
    
- Only assigned graders or course teachers with `IsGrader` may grade.
    

### 12) AnswerFileSerializer (upload)

**Validates**

- MIME & size; link to `Answer` only for attempts owned by user and not yet submitted.
    

### 13) GraderAssignmentSerializer

**Validates**

- Uniqueness `(exam, teacher, scope)`.
    
- Teacher existence and role.
    

---

## Permissions (Classes & Usage)

### `IsEnrolledInCourse`

- **Object permission** ensuring `request.user` is a member of `course_id` in path/query before allowing: list active exams, start attempt, read attempt, upload answer files.
    

### `IsExamAdmin`

- Admins (and optionally course owners) can create/update exams, questions, assignments, publish, and manage graders.
    

### `IsGrader`

- User is assigned grader for given exam (or is course teacher if allowed). Required for grading endpoints and grading queues.
    

### `IsAttemptOwner`

- Student can access/modify only their own attempts/answers.
    

### Compositions

- Authoring endpoints → `IsExamAdmin`.
    
- Student attempt endpoints → `IsEnrolledInCourse` & `IsAttemptOwner`.
    
- Grading endpoints → `IsGrader` (and possibly `IsExamAdmin` for finalize/release when admin‑only per spec).
    

---

## Throttling & Limits

- **Autosave endpoint**: Scoped rate limit e.g., `5 req / 10s` per user per attempt; return 429 with retry‑after.
    
- **File uploads**: Size limit via settings; reject with 413.
    

---

## Error Shape (examples)

- **400**: `{ "detail": "Invalid payload for TEXT_OR_FILE: provide text or files" }`
    
- **403**: `{ "detail": "You are not enrolled in this course" }`
    
- **404**: `{ "detail": "Attempt not found" }`
    
- **409**: `{ "detail": "Attempt already exists for this exam and course" }`
    
- **413**: `{ "detail": "File too large. Max 10MB" }`
    

---

## Tests (What to implement now)

- Exam publish lock prevents Question edits when attempts exist.
    
- MCQ: exactly one correct; creating second correct → 400.
    
- Assignment: invalid windows rejected; unique (exam,course) enforced.
    
- Attempt start: not enrolled → 403; outside window → 403; missing duration → 400; duplicate → 409.
    
- Autosave: type‑mismatch rejected; rate limit hit returns 429; version conflict returns 409 and server version.
    
- Submit: promotes last draft; missing required answer → 400; after expiry → auto‑submit then reject further changes.
    
- Result policy: rejected always sees scores; passed hidden when configured; hidden until release → pending.
    
- Grading: non‑grader → 403; override MCQ allowed; score bounds enforced with negative marking rules.
    

---

## Done Criteria

1. All serializers and permissions implemented with validations above.
    
2. Endpoints use these classes and return error shapes per spec.
    
3. Throttling active for autosave; file validators enforce type/size.
    
4. Tests from this file pass in CI.
    
5. OpenAPI (drf‑spectacular) reflects request/response schemas and error examples for these endpoints.
    

---

## Notes

- Keep serializers thin but authoritative; complex business checks (e.g., option counts on publish) can be triggered in `Exam.publish` action serializer.
    
- Centralize policy evaluation in a small utility and call it from `ResultSerializer` to avoid duplication.