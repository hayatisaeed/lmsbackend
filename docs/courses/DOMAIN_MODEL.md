
## 1. Core Entities

### Course

- **id** (UUID/Int)
    
- **name** (string)
    
- **description** (text)
    
- **banner_image** (file URL)
    
- **index_image** (file URL)
    
- **visibility** (enum: public | private)
    
- **access_mode** (enum: free | purchase)
    
- **created_at**, **updated_at**
    

### Exam

- **id**
    
- **title** (string)
    
- **description** (text)
    
- **status** (enum: draft | published | archived)
    
- **default_correct_score** (decimal)
    
- **default_wrong_score** (decimal, supports negative)
    
- **allow_negative_scoring** (bool)
    
- **duration_minutes** (int, optional default)
    
- **attempt_limit** (int, default 1)
    
- **auto_grade_if_all_mcq** (bool)
    
- **min_accept_score** (decimal)
    
- **total_score** (decimal, optional fixed; else computed)
    
- **accept_even_below_min** (bool)
    
- **show_score_if_passed** (bool)
    
- **show_score_if_failed** (bool)
    
- **hide_autograded_until_release** (bool)
    
- **created_by** (Admin/Teacher FK)
    
- **created_at**, **updated_at**
    

### ExamAssignment (Exam ↔ Course mapping)

- **id**
    
- **exam_id** (FK Exam)
    
- **course_id** (FK Course)
    
- **start_at** (datetime)
    
- **end_at** (datetime)
    
- **duration_override** (int, nullable)
    
- **reuse_last_user_result** (bool, default false)
    
- **created_at**
    

### Question

- **id**
    
- **exam_id** (FK Exam)
    
- **type** (enum: MCQ | TEXT | FILE | TEXT_OR_FILE)
    
- **title** (string)
    
- **body_richtext** (text/html)
    
- **order_index** (int)
    
- **assets** (list of QuestionFile FK)
    
- **correct_score** (decimal, nullable → inherit exam default)
    
- **wrong_score** (decimal, nullable → inherit exam default)
    
- **partial_scoring** (bool, default false)
    
- **answer_accepts_file_types** (enum: images_only | images+pdf)
    
- **answer_max_files** (int, default 1)
    
- **is_required** (bool)
    
- **created_at**, **updated_at**
    

### QuestionFile (assets)

- **id**
    
- **question_id** (FK Question)
    
- **title** (string, optional)
    
- **file** (file URL)
    

### MCQOption

- **id**
    
- **question_id** (FK Question)
    
- **text** (string)
    
- **is_correct** (bool)
    
- **order_index** (int)
    

### Attempt

- **id**
    
- **user_id** (FK User)
    
- **exam_id** (FK Exam)
    
- **course_id** (FK Course)
    
- **status** (enum: not_started | in_progress | submitted | graded | released | expired | void)
    
- **started_at** (datetime)
    
- **expires_at** (datetime)
    
- **submitted_at** (datetime)
    
- **final_score** (decimal)
    
- **is_passed** (bool)
    
- **autograded** (bool)
    
- **result_visibility_state** (enum: visible | hidden | pending)
    
- **time_spent_seconds** (int)
    
- **created_at**, **updated_at**
    

### Answer

- **id**
    
- **attempt_id** (FK Attempt)
    
- **question_id** (FK Question)
    
- **final_payload** (JSON):
    
    - MCQ → `selected_option_id`
        
    - TEXT → `text`
        
    - FILE → list of AnswerFile FK
        
    - TEXT_OR_FILE → either text or list of files
        
- **submitted_at**
    

### AnswerFile

- **id**
    
- **answer_id** (FK Answer)
    
- **file** (file URL; type image/pdf)
    
- **title** (optional)
    
- **uploaded_at**
    

### GradingItem

- **id**
    
- **answer_id** (FK Answer)
    
- **grader_id** (FK Teacher/Admin)
    
- **score_awarded** (decimal)
    
- **feedback** (text, optional)
    
- **status** (enum: pending | graded | confirmed)
    
- **graded_at**
    

### GraderAssignment

- **id**
    
- **exam_id** (FK Exam)
    
- **teacher_id** (FK Teacher)
    
- **scope** (enum: entire_exam | subset_questions | subset_attempts)
    
- **created_at**
    

---

## 2. Relationships (Simplified)

```
Course ──< ExamAssignment >── Exam
Exam ──< Question ──< MCQOption
      └──< QuestionFile
Exam ──< Attempt >── User
Attempt ──< Answer ──< AnswerFile
Answer ──< GradingItem >── Teacher
Exam ──< GraderAssignment >── Teacher
```

---

## 3. Validation Rules

- **Attempt per course per exam**: 1 (strict).
    
- **Exam scoring**: question score = override else exam default.
    
- **Negative marking**: allowed per exam, configurable.
    
- **MCQ**: only one option marked correct.
    
- **File answers**: enforce type/size; max files per question.
    
- **Auto-submit**: if `expires_at` passed, system auto-finalizes latest draft.
    
- **Results**: rejected students always see scores; passed students may not, depending on exam policy.
    
- **Reuse across courses**: new attempt always required (no result carry-over).
    

---

## 4. Domain Events (high-level)

- ExamPublished
    
- AttemptStarted
    
- AnswerSaved (auto-save)
    
- AttemptSubmitted
    
- AttemptAutoSubmitted
    
- AttemptGraded
    
- ResultReleased