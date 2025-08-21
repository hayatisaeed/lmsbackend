## Goal

Implement the core data models for the Courses service covering exams and attempts.

## Inputs / Refs

- DOMAIN_MODEL.md (source of truth)
- SYSTEM_DESIGN.md (secondary)

## Deliverables

- Django models for:
  - `Course`
  - `Exam`
  - `ExamAssignment` (bridge between Course and Exam)
  - `Question` and `MCQOption`
  - `QuestionFile`
  - `Attempt`
  - `Answer` and `AnswerFile`
  - `GradingItem`
  - `GraderAssignment`
- Initial migration generating the schema above.
- Tests exercising relationships and constraints (e.g. unique attempt per user/exam/course).

## Constraints

- Mirror field names and enums from `DOMAIN_MODEL.md`; if other docs conflict, the domain model wins.
- Use UUID primary keys.
- Enforce unique attempt per `(user, exam, course)`.
- Keep files as URL fields for now; upload handling comes later.

## Acceptance

- `pytest -q` passes with coverage for new models.
- Migration file `0001_initial.py` exists under `apps/courses/migrations`.
