# Email Template Gap And Mapping

## Phase 1 Audit Summary

### Inventory: `EmailTemplate.TEMPLATE_TYPES`

Existing core templates already covered account verification, review invites/reminders/submission, editorial decisions, revision rounds, copyediting lifecycle, production lifecycle, and publication scheduling.

### Inventory: Seeded HTML template files

`templates/emails/` already contained review, decision, revision, copyediting, production, and publication templates. Add-on files were missing for dedicated submission-level acknowledgement/correction/review-start semantics and review/copyediting assignment variants.

### Inventory: Trigger points that enqueue notifications

- `apps/reviews/views.py`: review assignment create/accept/decline/cancel; review create; editorial decision create.
- `apps/submissions/views/views.py`: submission `submit` and `update_status`.
- `apps/submissions/views/workflow/views.py`: copyediting assignment/file transitions, production assignment/file transitions, publication scheduling.

## Requested Item Mapping

| Requested item                                    | Mapping template type                           | Status |
| ------------------------------------------------- | ----------------------------------------------- | ------ |
| Submission: First Acknowledgement                 | `SUBMISSION_FIRST_ACKNOWLEDGEMENT`              | New    |
| Submission: Pre Review and Correction             | `SUBMISSION_PRE_REVIEW_CORRECTION`              | New    |
| Submission: Review                                | `SUBMISSION_REVIEW_STARTED`                     | New    |
| Submission: Review Correction                     | `REVISION_REQUEST` / `REVISION_REQUESTED`       | Reused |
| Submission: Accept                                | `DECISION_ACCEPT` / `EDITORIAL_DECISION_ACCEPT` | Reused |
| Submission: Reject                                | `DECISION_REJECT` / `EDITORIAL_DECISION_REJECT` | Reused |
| Submission: Copy Editing                          | `COPYEDITING_ASSIGNED` / `COPYEDITING_STARTED`  | Reused |
| Submission: Discussion                            | `SUBMISSION_COPYEDITING_DISCUSSION`             | New    |
| Submission: Production                            | `PRODUCTION_ASSIGNED` / `PRODUCTION_STARTED`    | Reused |
| Submission: Proofreading                          | `SUBMISSION_PRODUCTION_PROOFREADING`            | New    |
| Submission: Final Publication                     | `PUBLICATION_PUBLISHED`                         | Reused |
| Submission: Editorial Assignment (Section Editor) | `EDITORIAL_ASSIGNMENT_SECTION_EDITOR`           | New    |
| Submission: Editorial Assignment (Guest Editor)   | `EDITORIAL_ASSIGNMENT_GUEST_EDITOR`             | New    |
| Review: Editorial Assignment                      | `REVIEW_EDITORIAL_ASSIGNMENT`                   | New    |
| Review: Article Review Request                    | `REVIEW_ARTICLE_REQUEST`                        | New    |
| Review: Reminding email                           | `REVIEW_REMINDER`                               | Reused |
| Review: Unable to Review                          | `REVIEW_UNABLE_TO_REVIEW`                       | New    |
| Review: Request for Review Cancelled              | `REVIEW_REQUEST_CANCELLED`                      | New    |
| Review: Editor Decision                           | `REVIEW_EDITOR_DECISION_NOTICE`                 | New    |
| Copyediting: Editorial Assignment                 | `COPYEDITING_EDITORIAL_ASSIGNMENT`              | New    |
| Copyediting: Copyediting Request                  | `COPYEDITING_REQUEST`                           | New    |

## Existing vs New Template Matrix

### Reused templates

- `REVISION_REQUEST`, `REVISION_REQUESTED`, `REVISION_SUBMITTED`, `REVISION_APPROVED`, `REVISION_REJECTED`
- `DECISION_ACCEPT`, `DECISION_REJECT`, `DECISION_MINOR_REVISION`, `DECISION_MAJOR_REVISION`
- `EDITORIAL_DECISION_ACCEPT`, `EDITORIAL_DECISION_REJECT`
- `REVIEW_INVITATION`, `REVIEW_REMINDER`, `REVIEW_SUBMITTED`
- `COPYEDITING_ASSIGNED`, `COPYEDITING_STARTED`, `COPYEDITING_COMPLETED`, `COPYEDITING_FILE_READY`
- `PRODUCTION_ASSIGNED`, `PRODUCTION_STARTED`, `PRODUCTION_COMPLETED`, `GALLEY_PUBLISHED`
- `PUBLICATION_SCHEDULED`, `PUBLICATION_PUBLISHED`, `PUBLICATION_CANCELLED`

### Newly added templates

- `SUBMISSION_FIRST_ACKNOWLEDGEMENT`
- `SUBMISSION_PRE_REVIEW_CORRECTION`
- `SUBMISSION_REVIEW_STARTED`
- `SUBMISSION_COPYEDITING_DISCUSSION`
- `SUBMISSION_PRODUCTION_PROOFREADING`
- `EDITORIAL_ASSIGNMENT_SECTION_EDITOR`
- `EDITORIAL_ASSIGNMENT_GUEST_EDITOR`
- `REVIEW_EDITORIAL_ASSIGNMENT`
- `REVIEW_ARTICLE_REQUEST`
- `REVIEW_UNABLE_TO_REVIEW`
- `REVIEW_REQUEST_CANCELLED`
- `REVIEW_EDITOR_DECISION_NOTICE`
- `COPYEDITING_EDITORIAL_ASSIGNMENT`
- `COPYEDITING_REQUEST`

## Trigger Point Mapping

| Trigger function/view action                  | Task(s)                                                                                                                                                                                                                                                 |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ReviewAssignmentViewSet.perform_create`      | `send_review_invitation_email`, `send_review_article_request_email`, `send_review_editorial_assignment_email`, `send_submission_review_started_email`, `send_editorial_assignment_section_editor_email`, `send_editorial_assignment_guest_editor_email` |
| `ReviewAssignmentViewSet.accept`              | `send_submission_review_started_email`                                                                                                                                                                                                                  |
| `ReviewAssignmentViewSet.decline`             | `send_review_unable_to_review_email`                                                                                                                                                                                                                    |
| `ReviewAssignmentViewSet.cancel`              | `send_review_request_cancelled_email`                                                                                                                                                                                                                   |
| `ReviewViewSet.perform_create`                | `send_review_submitted_email`                                                                                                                                                                                                                           |
| `EditorialDecisionViewSet.perform_create`     | `send_decision_letter_email`, `send_review_editor_decision_notice_email`                                                                                                                                                                                |
| `SubmissionViewSet.submit`                    | `send_submission_first_acknowledgement_email`, `send_submission_review_started_email`                                                                                                                                                                   |
| `SubmissionViewSet.update_status`             | `send_submission_pre_review_correction_email`, `send_submission_review_started_email`                                                                                                                                                                   |
| `CopyeditingAssignmentViewSet.perform_create` | `send_copyediting_assigned_email`, `send_copyediting_editorial_assignment_email`, `send_copyediting_request_email`                                                                                                                                      |
| `ProductionAssignmentViewSet.perform_create`  | `send_production_assigned_email`                                                                                                                                                                                                                        |
| `ProductionFileViewSet.publish`               | `send_galley_published_email`, `send_submission_production_proofreading_email`                                                                                                                                                                          |

## Recipient Matrix

| Template type                         | Recipient roles                |
| ------------------------------------- | ------------------------------ |
| `SUBMISSION_FIRST_ACKNOWLEDGEMENT`    | Author, Editor                 |
| `SUBMISSION_PRE_REVIEW_CORRECTION`    | Author                         |
| `SUBMISSION_REVIEW_STARTED`           | Author                         |
| `EDITORIAL_ASSIGNMENT_SECTION_EDITOR` | Section Editor                 |
| `EDITORIAL_ASSIGNMENT_GUEST_EDITOR`   | Guest Editor                   |
| `REVIEW_EDITORIAL_ASSIGNMENT`         | Section Editor, Author, Editor |
| `REVIEW_ARTICLE_REQUEST`              | Reviewer                       |
| `REVIEW_UNABLE_TO_REVIEW`             | Section Editor, Editor         |
| `REVIEW_REQUEST_CANCELLED`            | Section Editor, Author, Editor |
| `REVIEW_EDITOR_DECISION_NOTICE`       | Section Editor, Editor         |
| `COPYEDITING_EDITORIAL_ASSIGNMENT`    | Editor                         |
| `COPYEDITING_REQUEST`                 | Author, Copyeditor, Editor     |
| `SUBMISSION_PRODUCTION_PROOFREADING`  | Author                         |
