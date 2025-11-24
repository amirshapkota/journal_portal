# Journal Settings Configuration

Journal settings are stored as a JSON object in the `Journal.settings` field. Below are the available configuration options:

## Review Settings

### `review_deadline_days` (integer)

- **Description**: Number of days given to reviewers to complete a review
- **Default**: 30
- **Usage**: When a reviewer is assigned to a submission, the due date is automatically calculated as `invited_at + review_deadline_days`
- **Example**:
  ```json
  {
    "review_deadline_days": 21
  }
  ```

## Revision Settings

### `default_revision_deadline_days` (integer)

- **Description**: Default number of days given to authors to submit revisions (used when editor doesn't specify a custom deadline)
- **Default**: 30
- **Usage**: When creating an editorial decision requiring revision, if no custom deadline is specified, the deadline is calculated as `decision_date + default_revision_deadline_days`
- **Example**:
  ```json
  {
    "default_revision_deadline_days": 45
  }
  ```

## Example Complete Settings Object

```json
{
  "review_deadline_days": 21,
  "default_revision_deadline_days": 45,
  "submission_guidelines": "Please follow APA format...",
  "word_count_limit": 8000,
  "allow_preprints": true
}
```

## Usage in Code

### Setting Review Deadline from Journal Settings

```python
# In ReviewAssignment model save method
journal = self.submission.journal
deadline_days = journal.settings.get('review_deadline_days', 30)
self.due_date = timezone.now() + timedelta(days=deadline_days)
```

### Setting Revision Deadline from Editorial Decision

```python
# In EditorialDecision form/serializer
if decision_type in ['MINOR_REVISION', 'MAJOR_REVISION']:
    if not revision_deadline:
        journal = submission.journal
        default_days = journal.settings.get('default_revision_deadline_days', 30)
        revision_deadline = timezone.now() + timedelta(days=default_days)
```

## Automatic Deadline Expiration

The system automatically checks for expired deadlines via:

1. **Management Command**: Run manually or via cron

   ```bash
   python manage.py check_expired_deadlines
   ```

2. **Celery Task**: Scheduled to run daily
   - Task: `reviews.check_expired_deadlines`
   - Checks all review assignments with status PENDING/ACCEPTED
   - Checks all revision rounds with status REQUESTED/IN_PROGRESS
   - Updates status to EXPIRED if past deadline
   - Sends notifications to relevant parties

## Statuses

### ReviewAssignment Statuses

- `PENDING`: Invitation sent, awaiting response
- `ACCEPTED`: Reviewer accepted the assignment
- `DECLINED`: Reviewer declined the assignment
- `COMPLETED`: Review submitted
- `EXPIRED`: Deadline passed without completion
- `CANCELLED`: Assignment cancelled by editor

### RevisionRound Statuses

- `REQUESTED`: Revision requested from author
- `IN_PROGRESS`: Author is working on revision
- `SUBMITTED`: Revised manuscript submitted
- `UNDER_REVIEW`: Revision under editorial review
- `APPROVED`: Revision approved
- `REJECTED`: Revision rejected
- `EXPIRED`: Deadline passed without submission (submission auto-rejected)
