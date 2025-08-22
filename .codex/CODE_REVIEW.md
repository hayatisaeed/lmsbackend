# CodeX Review Prompt

## Role

You are CodeX acting as a **senior code reviewer and advanced tester**.

## Objective

Scan the **entire codebase** (all apps, docs, and tasks) and produce a detailed **review report** highlighting potential conflicts, bugs, design inconsistencies, and risky patterns. Do **not** modify or generate new code. Only report.

## Inputs

* All source files under `./apps/`, `./docs/`, and `./config/`
* All design docs under `./docs/`
* Task specs under `./docs/**/TASKS/`

## Deliverable

* A single markdown file written to repo root named:

  ```
  CODE_REVIEW_REPORT.md
  ```
* This file must contain:

  1. **Conflict Scan** — mismatched field names, inconsistent model relations, endpoint/serializer mismatches.
  2. **Bug Risks** — unvalidated input, missing perms, timing/atomicity issues, missing constraints.
  3. **Design Gaps** — areas where implementation diverges from DOMAIN\_MODEL, SYSTEM\_DESIGN, or ENDPOINTS\_SPEC.
  4. **Testing Gaps** — missing or weak test coverage vs. TEST\_PLAN.
  5. **Security/Perf Red Flags** — e.g., unthrottled endpoints, unsafe file handling, N+1 queries.
* For each finding: include file path(s), snippet reference, **Impact**, and **Suggested Fix/Follow-up**.
* At the end: summary table of findings grouped by severity (High / Medium / Low).

## Rules

* Do not attempt to fix code; only review and comment.
* Assume latest migrations are applied; check models vs. serializers vs. views.
* Follow Django + DRF best practices, OWASP ASVS Top 10, and project conventions (12-Factor, DRF style).
* Be explicit when unsure (mark as "Needs Clarification").

## Acceptance

* `CODE_REVIEW_REPORT.md` exists in repo root.
* It contains at least one entry for each of the 5 sections.
* Findings reference real code/doc locations.
* Structured, readable, and actionable for engineers.

## Execution

1. Traverse full repo.
2. Compare implementation vs. docs.
3. Write findings to `CODE_REVIEW_REPORT.md`.
4. Stop. Do not change code.
