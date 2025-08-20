
## 1. High-Level Architecture

```
+----------------------+        +----------------------+        +----------------------+
|   Client (Web/App)  | <----> |    API Gateway /     | <----> |   Courses Service    |
| - Exam UI           |        | Django REST (DRF)   |        | (Exams, Questions,   |
| - Timer, Auto-Save  |        | + SimpleJWT          |        | Attempts, Grading)   |
+----------------------+        +----------------------+        +----------------------+
                                                              |
                                                              v
                                                  +-----------------------+
                                                  | File Storage (S3/MinIO|
                                                  |   for Q assets & Ans) |
                                                  +-----------------------+
                                                              |
                                                              v
                                                  +-----------------------+
                                                  | Background Workers    |
                                                  |  (Celery + Redis)     |
                                                  | - Auto-submit timeout |
                                                  | - Bulk grading/release|
                                                  +-----------------------+
```

## 2. Components

### 2.1 API Layer (Django DRF)

- **Auth**: JWT via existing Authentication Service.
    
- **Endpoints**: exams, questions, attempts, answers, grading, files.
    
- **Permissions**: `IsEnrolledInCourse`, `IsExamAdmin`, `IsGrader`, `IsStudent`.
    

### 2.2 Core Services

- **Exam Management**: create, edit, publish, lock after publish.
    
- **Question Management**: CRUD with assets, MCQ options.
    
- **Attempt Lifecycle**: start, autosave (if enabled), submit, auto-submit.
    
- **Answer Handling**: validation (text/file), finalization, linking files.
    
- **Grading Service**: auto-grade MCQ, manual grading by teachers, override.
    
- **Result Policy Engine**: evaluates visibility flags (show/hide score, release logic).
    
- **Reuse Policy Manager**: ensures new attempt per course mapping, no cross-course carry-over.
    

### 2.3 Background Jobs (Celery)

- **Auto-submit worker**: checks expired attempts, finalizes drafts.
    
- **Bulk result release**: batch release for autograded exams.
    
- **Notification hook (future)**: notify student/teacher on grading completion.
    

### 2.4 File Handling

- Store **question assets** and **answers** in object storage (S3/MinIO).
    
- Validate type (image/pdf) + size before save.
    
- Files referenced by DB IDs; access controlled by DRF endpoint or signed URLs.
    

### 2.5 Database

- Relational DB (Postgres/MySQL).
    
- Entities from DOMAIN_MODEL (Course, Exam, ExamAssignment, Question, Attempt, Answer, GradingItem, etc.).
    
- Strict foreign keys, cascade deletes disabled for audit safety.
    

---

## 3. Key Flows

### 3.1 Exam Authoring

1. **Admin/Teacher** creates Exam (defaults: score config, policies).
    
2. Add Questions (MCQ/Text/File/TextOrFile) with overrides.
    
3. Add MCQOptions (if type=MCQ).
    
4. Publish Exam → status locked; cannot edit if attempts exist.
    
5. Attach Exam to Course via ExamAssignment (start/end windows, duration, reuse policy).
    

### 3.2 Student Attempt Lifecycle

1. Student requests **Active Exams** for courses joined.
    
2. Start Attempt → record created with `started_at`, `expires_at`.
    
3. Student answers questions:
    
    - Text entered or File uploaded (validated, stored).
        
    - Optional Auto-Save → saves per question (limited rate).
        
4. Student submits attempt → final snapshot of answers.
    
5. If timeout occurs → Celery auto-submits last drafts.
    

### 3.3 Grading

- **Auto-grading** (MCQ-only exams): compute immediately, mark autograded.
    
- **Manual grading**:
    
    - Teacher sees Grading Queue.
        
    - Grades per answer (score + feedback).
        
    - Overrides allowed on MCQ.
        
- **Finalize attempt**: compute total score, set pass/fail.
    
- **Result release**: Admin (only) releases results if hidden.
    

### 3.4 Result Visibility

- **Rejected students** → always see scores.
    
- **Passed students** → may see or not, depending on `show_score_if_passed`.
    
- **Hidden until release** → no scores until Admin releases.
    

---

## 4. Integrations

- **Authentication Service**: Users and JWT auth.
    
- **File Storage**: for assets/answers (global sharing).
    
- **Celery/Redis**: job scheduling.
    
- **(Future)** Payment Service → enforce purchase-only access.
    

---

## 5. Non-Functional Requirements

- **Performance**: autosave latency <200ms for drafts; scale to thousands of concurrent attempts.
    
- **Consistency**: server authoritative for attempt timers.
    
- **Resilience**: auto-submit worker ensures no lost attempts.
    
- **Security**: object-level permissions, file type/size validation, JWT auth.
    
- **Auditability**: immutable logs for grading, result release, attempt lifecycle.
    

---

## 6. Open Questions (Future Phases)

- Multiple attempts with configurable result policy.
    
- Proctoring, anti-cheat measures.
    
- Rich rubric-based grading.
    
- Notifications (email/SMS) for grading completion.
    
- Export/analytics dashboards.
    

---

## 7. Deployment & Ops

- **Containerized** (Docker) + orchestration.
    
- **CI/CD** with migrations, tests, linting.
    
- **Monitoring**: metrics (attempts started, submissions, grading throughput).
    
- **Alerting**: failed auto-submits, grading SLA breaches.
    

---

## 8. Risks & Mitigations

- **Clock drift** → server-side time only.
    
- **File abuse** → strict type/size check.
    
- **Data loss** → auto-submit worker, transactional DB writes.
    
- **Exam edits after publish** → enforce lock; allow clone for updates.
    

---

## 9. Sequence Diagram (Student Attempt)

```
Student → API: GET active exams
API → DB: fetch ExamAssignments
Student → API: POST start_attempt
API → DB: create Attempt (started_at, expires_at)
API → Student: exam structure

Student → API: PUT autosave_answer (optional)
API → DB: update Answer draft

Student → API: POST submit_attempt
API → DB: finalize Answers, set submitted_at
API → Grading Service: auto-grade if eligible

[if timeout]
Celery Worker → DB: auto-submit attempt
Celery Worker → Grading Service: auto-grade
```

---

## 10. Summary

This system design ensures:

- **One attempt per course per exam**, with auto-submit safety.
    
- Flexible **scoring policies** (negative marking, overrides).
    
- **Manual + auto grading** with admin-controlled result release.
    
- **Scalable architecture**: DRF + Celery + Object Storage.
    
- **Secure by design**: auth, validation, locking after publish.
    

This sets the foundation for the Exams domain, ready to extend with purchase flow, proctoring, and advanced grading later.