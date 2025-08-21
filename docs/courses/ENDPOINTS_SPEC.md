

Base URL: `/api/v1/courses/`

---

## 1. Student-Facing Endpoints

### 1.1 List Active Exams

**GET** `/my/active-exams/`

- **Auth**: Bearer (student)
    
- **Params**: optional `course_id`
    
- **Response**:
    

```json
[
  {
    "exam_id": 12,
    "course_id": 3,
    "title": "Math Level Exam",
    "start_at": "2025-09-01T10:00:00Z",
    "end_at": "2025-09-03T10:00:00Z",
    "started": true,
    "attempt_status": "in_progress",
    "expires_at": "2025-09-01T11:00:00Z"
  }
]
```

- **Errors**: 403 (not enrolled), 404 (course not found)
    

### 1.2 Start Attempt

**POST** `/{course_id}/exams/{exam_id}/attempts/start/`

- **Auth**: Bearer (student)
    
- **Body**: none
    
- **Response**:
    

```json
{
  "attempt_id": 55,
  "started_at": "2025-09-01T10:00:00Z",
  "expires_at": "2025-09-01T11:00:00Z",
  "exam_structure": { ... },
  "drafts": {}
}
```

- **Errors**: 409 (attempt already exists), 403 (outside window)
    

### 1.3 Get Attempt Detail

**GET** `/exams/attempts/{attempt_id}/`

- **Response**:
    

```json
{
  "attempt_id": 55,
  "status": "in_progress",
  "started_at": "2025-09-01T10:00:00Z",
  "expires_at": "2025-09-01T11:00:00Z",
  "exam_structure": { ... },
  "drafts": { "q1": {"text": "partial answer"} }
}
```

### 1.4 Auto-Save Answer (Optional)

**PUT** `/exams/attempts/{attempt_id}/answers/{question_id}/autosave/`

- **Body**: varies by question type
    

```json
{
  "version": 3,
  "text": "drafted text"
}
```

- **Response**:
    

```json
{ "version": 3, "saved_at": "2025-09-01T10:15:00Z" }
```

- **Errors**: 400 (invalid input), 413 (file too large)
    

### 1.5 Submit Attempt

**POST** `/exams/attempts/{attempt_id}/submit/`

- **Body**: `{ "confirm": true }`
    
- **Response**:
    

```json
{ "status": "submitted", "submitted_at": "2025-09-01T10:45:00Z" }
```

- **Errors**: 409 (already submitted), 403 (expired)
    

### 1.6 View Result

**GET** `/exams/attempts/{attempt_id}/result/`

- **Response** (visible):
    

```json
{
  "final_score": 72,
  "is_passed": true,
  "feedback": [
    { "question_id": 1, "score": 5, "comment": "Good." },
    { "question_id": 2, "score": 3, "comment": "Needs work." }
  ]
}
```

- **Response** (hidden):
    

```json
{ "status": "pending_release" }
```

---

## 2. Exam Authoring (Admin/Teacher)

### 2.1 Manage Exams

- **POST** `/exams/` → create exam (title, defaults, policies)
    
- **GET** `/exams/` → list exams (filters: status, creator)
    
- **GET/PATCH** `/exams/{exam_id}/` → view/update exam
    
- **POST** `/exams/{exam_id}/publish/` → lock + publish
    

### 2.2 Manage Questions

- **POST** `/exams/{exam_id}/questions/` → add question
    
- **PATCH** `/questions/{question_id}/` → update question
    
- **DELETE** `/questions/{question_id}/` → delete (if draft)
    
- **POST** `/questions/{question_id}/options/` → add MCQ options
    
- **POST** `/questions/{question_id}/files/` → upload asset
    

### 2.3 Assign Exam to Course

**POST** `/exams/{exam_id}/assign-to-course/`

- **Body**:
    

```json
{
  "course_id": 3,
  "start_at": "2025-09-01T10:00:00Z",
  "end_at": "2025-09-03T10:00:00Z",
  "duration_override": 90,
  "reuse_last_user_result": false
}
```

### 2.4 Grader Assignment

**POST** `/exams/{exam_id}/graders/assign/`

- **Body**: `{ "teacher_id": 7, "scope": "entire_exam" }`
    

---

## 3. Grading (Teacher/Admin)

### 3.1 Grading Queue

**GET** `/exams/{exam_id}/grading-queue/`

- **Response**:
    

```json
[
  { "attempt_id": 55, "user_id": 101, "status": "submitted" },
  { "attempt_id": 56, "user_id": 102, "status": "submitted" }
]
```

### 3.2 Grade Answer

**POST** `/answers/{answer_id}/grade/`

- **Body**:
    

```json
{
  "score_awarded": 4,
  "feedback": "Detailed feedback here"
}
```

- **Response**:
    

```json
{ "status": "graded", "graded_at": "2025-09-01T12:00:00Z" }
```

### 3.3 Finalize Attempt

**POST** `/attempts/{attempt_id}/finalize/`

- Marks attempt as fully graded, calculates total score.
    

### 3.4 Release Results

- **POST** `/attempts/{attempt_id}/release/`
    
- **POST** `/exams/{exam_id}/results/release-bulk/`
    

---

## 4. File Handling

### 4.1 Upload Answer File

**POST** `/files/upload/answer/`

- **Body**: multipart (image/pdf)
    
- **Response**:
    

```json
{ "file_id": 901, "url": "/files/901" }
```

### 4.2 Upload Question Asset

**POST** `/files/upload/question-asset/`

### 4.3 Get File

**GET** `/files/{file_id}`

- Auth-based streaming / signed URL

### 4.4 Delete Draft Answer File

**DELETE** `/files/upload/answer/`

- **Body**:

```json
{ "file_id": "901", "url": "/files/draft/901" }
```

- **Responses**: `204 No Content`


---

## 5. Errors & Status Codes

- **400**: validation error (bad input, wrong type)
    
- **401**: invalid/missing token
    
- **403**: permission denied (not enrolled, not assigned grader)
    
- **404**: not found (exam, attempt, question)
    
- **409**: conflict (already submitted, attempt exists)
    
- **413**: payload too large (file)
    

---

## 6. Notes

- All responses wrapped in JSON.
    
- Pagination for list endpoints (exams, grading queue).
    
- Timestamps in ISO8601 UTC.
    
- Strict object-level permissions: students only see their attempts, teachers only grade assigned exams, admins full access.
    

---

This ENDPOINTS_SPEC captures student flows (attempts, autosave, submit, results), authoring flows (exams, questions, assignments), grading, and file management, aligned with the DOMAIN_MODEL and SYSTEM_DESIGN.