
## Goal

Implement **exam authoring & management** endpoints per ENDPOINTS_SPEC: create/list/update/publish exams, manage questions/options/files, and map exams to courses.

## Inputs / Refs

- DOMAIN_MODEL: `courses_exam_domain_model`
    
- SYSTEM_DESIGN: `courses_exam_system_design`
    
- ENDPOINTS_SPEC: `courses_exam_endpoints_spec`
    
- TEST_PLAN: `courses_exam_test_plan`
    
- SERIALIZERS/PERMS: `courses_exam_tasks_serializers_perms`
    

## Deliverables

- DRF views (class-based) + routers for:
    
    - Exams CRUD + publish action
        
    - Questions CRUD
        
    - MCQ options creation
        
    - Question asset upload
        
    - Exam → Course assignment
        
- OpenAPI (drf-spectacular) documented for each endpoint
    
- Tests covering authoring and mapping
    

---

## Endpoints to Implement

### 1) Exams

- **POST** `/api/v1/courses/exams/` → Create exam (Admin/Teacher via `IsExamAdmin`)
    
- **GET** `/api/v1/courses/exams/` → List exams (filters: `status`, `created_by`)
    
- **GET** `/api/v1/courses/exams/{exam_id}/` → Retrieve exam
    
- **PATCH** `/api/v1/courses/exams/{exam_id}/` → Update (respect publish lock)
    
- **POST** `/api/v1/courses/exams/{exam_id}/publish/` → Publish (lock if attempts exist); response includes computed totals
    

**Validation**

- Status transitions allowed: `draft→published→archived`; deny edits on published if attempts exist.
    
- Negative marking rules from ExamSerializer.
    

### 2) Questions

- **POST** `/api/v1/courses/exams/{exam_id}/questions/` → Create question
    
- **PATCH** `/api/v1/courses/questions/{question_id}/` → Update
    
- **DELETE** `/api/v1/courses/questions/{question_id}/` → Delete (only when exam is draft/no attempts)
    

**Validation**

- Enforce type constraints; score overrides; file acceptance options; order_index required.
    

### 3) MCQ Options

- **POST** `/api/v1/courses/questions/{question_id}/options/` → Bulk or single create
    

**Validation**

- Exactly one `is_correct=True` overall; ensure ≥2 options for MCQ.
    

### 4) Question Assets

- **POST** `/api/v1/courses/questions/{question_id}/files/` → Upload image asset (multipart)
    
- **DELETE** `/api/v1/courses/question-files/{file_id}/` → Remove asset (draft only)
    

**Validation**

- Images only; size limit from env; shared globally (no course scoping).
    

### 5) Assign Exam to Course

- **POST** `/api/v1/courses/exams/{exam_id}/assign-to-course/`
    
- **GET** `/api/v1/courses/exams/{exam_id}/assignments/` → list mappings
    

**Validation**

- Unique `(exam, course)`; valid window (`start_at < end_at` if provided); duration override positive.
    

---

## Views & Routing

- Use DRF **APIView** or **GenericAPIView + mixins** (keep simple; ViewSets optional but not required in MVP).
    
- Namespace: `courses.exams`, tag all routes with `"Exams"` for OpenAPI.
    
- Add `DefaultRouter` if ViewSets are chosen; otherwise explicit `path()`.
    

---

## Permissions

- Exams & questions endpoints → `IsExamAdmin`.
    
- Assignment endpoints → `IsExamAdmin` with check that admin/teacher has rights for the target course (simple rule: admins always; course teachers only for their courses).
    

---

## Serialization

- Use serializers from `TASKS_SERIALIZERS_PERMS.md`.
    
- For publish action, return:
    

```json
{
  "status": "published",
  "exam_id": 123,
  "questions_count": 20,
  "total_max_score": 100
}
```

---

## OpenAPI / Schema

- Annotate request/response and error schemas for each endpoint via drf-spectacular `extend_schema`.
    
- Group under tags: `Exams`, `Questions`, `ExamAssignments`.
    

---

## Tests

- **Create/Update Exam**: ok + negative marking validation; lock after publish.
    
- **Create Question (MCQ/TEXT/FILE/TEXT_OR_FILE)**: type/score/file rules enforced.
    
- **MCQ Options**: second `is_correct=True` rejected; <2 options rejected on publish.
    
- **Question Assets**: non-image rejected; delete blocked after publish with attempts.
    
- **Exam Assignment**: unique pair, invalid window rejected.
    

---

## Done Criteria

1. All endpoints exist and wired under `/api/v1/courses/...`.
    
2. Permissions enforced; non-admins cannot modify exams.
    
3. Publish action locks content per rules.
    
4. OpenAPI shows all routes with accurate schemas.
    
5. Tests pass for the above scenarios in CI.
    

---

## Notes

- Keep endpoints **idempotent** where appropriate (e.g., re-publishing returns same state).
    
- Avoid nested writes that complicate transactions; create questions and options in separate calls to simplify locking rules.