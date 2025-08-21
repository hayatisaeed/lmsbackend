

## 1. Scope

Covers functionality, integration, security, and performance for **Exams** domain: authoring, attempts, autosave, grading, result visibility, file uploads.

---

## 2. Test Categories

### 2.1 Unit Tests

- **Exam Model**
    
    - Default score/negative marking inheritance.
        
    - Lock after publish.
        
- **Question Model**
    
    - Type validation (MCQ single correct only).
        
    - Max files enforcement.
        
- **Attempt Model**
    
    - One attempt per exam per course.
        
    - Expiration logic (duration override, default duration).
        
- **Answer Validation**
    
    - MCQ only one correct selected.
        
    - Text answers required if configured.
        
    - File type (image/pdf) + size.
        

### 2.2 API/Integration Tests

- **Active Exams Listing**
    
    - Student enrolled vs not enrolled.
        
    - Exam within availability window vs expired.
        
- **Start Attempt**
    
    - Creates attempt with `started_at`, `expires_at`.
        
    - Prevent duplicate attempts.
        
- **Auto-Save**
    
    - Draft updates accepted, limited rate.
        
    - Conflict resolution with versioning.
        
- **Submit Attempt**
    
    - Snapshot of final answers saved.
        
    - Prevent resubmission.
        
- **Auto-Submit Timeout**
    
    - Celery worker submits expired attempts.
        
    - Last saved draft promoted to final.
        
- **File Uploads**

    - Accept image/pdf.

    - Reject other formats, oversized files.

    - Delete draft answer files only when attempt in progress; enforce ownership, URL match, and idempotency.
        
- **Grading**
    
    - Auto-grading correct for MCQ.
        
    - Manual grading applies score + feedback.
        
    - Override MCQ by teacher.
        
- **Result Visibility**
    
    - Rejected students always see scores.
        
    - Passed students may/may not depending on config.
        
    - Hidden until release → students see pending.
        
- **Reuse Across Courses**
    
    - Same exam mapped to 2 courses requires 2 attempts.
        
    - Ensure no score carry-over.
        

### 2.3 Security Tests

- Auth required for all endpoints.
    
- Object-level permissions:
    
    - Students can access only their attempts/answers.
        
    - Teachers can grade only assigned exams.
        
    - Admins full access.
        
- Invalid/missing JWT rejected.
    
- Rate limiting for autosave endpoint.
    
- Files: path traversal, MIME spoofing.
    

### 2.4 Performance Tests

- Load test: 1000 concurrent students starting attempts.
    
- Autosave under load → latency <200ms p95.
    
- File uploads stress test (images + pdf).
    
- Celery auto-submit worker scales with 10k active attempts.
    

### 2.5 Regression Tests

- Publish → lock exam; no edits after attempts exist.
    
- Course visibility: exam visible only if course joined.
    
- Attempt expiration edge cases (DST, timezone shifts).
    

---

## 3. Acceptance Criteria (Sample)

1. A student cannot start more than one attempt per exam per course.
    
2. Exam lock prevents adding/removing questions once published.
    
3. Autosave stores latest draft and survives refresh.
    
4. Auto-submit finalizes attempt if student runs out of time.
    
5. Auto-grading produces correct total for MCQ-only exam.
    
6. Teachers can override MCQ grading manually.
    
7. Result release by Admin only, respects visibility policy.
    
8. Rejected students always see score breakdown.
    
9. File uploads accept only valid types; reject others.
    
10. Students in Course A cannot see exams from Course B.
    

---

## 4. Tools & Setup

- **Pytest + Factory Boy** for unit/integration.
    
- **DRF test client** for API tests.
    
- **Locust/JMeter** for load/performance.
    
- **pre-commit hooks** (lint, black, ruff).
    
- **CI/CD**: automated tests on push.
    

---

## 5. Risks & Mitigation

- **Race conditions** in autosave/submit → versioning + idempotency.
    
- **File storage corruption** → checksum validation.
    
- **Celery failure** → monitoring + retries.
    
- **Policy misconfig** → test matrix for visibility scenarios.
    

---

## 6. Out of Scope (Phase 1)

- Multiple attempts with score aggregation.
    
- Proctoring, device/IP logging.
    
- Rich rubric-based grading.
    

---

## 7. Summary

This plan ensures coverage from unit up to performance and security, with clear acceptance criteria aligned to DOMAIN_MODEL, SYSTEM_DESIGN, and ENDPOINTS_SPEC.