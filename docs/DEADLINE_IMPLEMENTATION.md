# Deadline Implementation for Review Assignments and Revisions

## Overview

This implementation adds automatic deadline tracking and expiration for:

1. **Review Assignments** - Deadlines for reviewers to complete their reviews
2. **Revision Rounds** - Deadlines for authors to submit revised manuscripts

## Features

### 1. Review Assignment Deadlines

#### Deadline Calculation

- Deadlines are automatically calculated when a reviewer is assigned
- Uses journal-specific settings: `review_deadline_days` (default: 30 days)
- Can be manually set by editor when creating assignment

#### Status Flow

- `PENDING` → `ACCEPTED` → `COMPLETED` (normal flow)
- `PENDING` → `EXPIRED` (if deadline passes without acceptance)
- `ACCEPTED` → `EXPIRED` (if deadline passes without review submission)

#### Configuration

Set in Journal settings JSON:

```json
{
  "review_deadline_days": 21
}
```

### 2. Revision Round Deadlines

#### Deadline Configuration

- **Primary Source**: Set by editor in `EditorialDecision.revision_deadline` field
- **Fallback**: Uses `RevisionRound.deadline` if specified
- **Default**: 30 days from decision date if not specified

#### Status Flow

- `REQUESTED` → `IN_PROGRESS` → `SUBMITTED` → `APPROVED` (normal flow)
- `REQUESTED` → `EXPIRED` → Submission auto-rejected
- `IN_PROGRESS` → `EXPIRED` → Submission auto-rejected

## Implementation Details

### Database Changes

#### ReviewAssignment Model

- Added `EXPIRED` status to `STATUS_CHOICES`
- Modified `save()` method to use journal-specific deadline
- Added `check_and_update_expired()` method

#### RevisionRound Model

- Added `EXPIRED` status to `STATUS_CHOICES`
- Modified `is_overdue()` to check REQUESTED/IN_PROGRESS statuses
- Added `check_and_update_expired()` method
- Auto-rejects submission when revision expires

### Automatic Expiration Checking

#### Management Command

```bash
# Check and update expired items (production use)
python manage.py check_expired_deadlines

# Dry run (preview without making changes)
python manage.py check_expired_deadlines --dry-run
```

#### Celery Tasks

Two periodic tasks are available:

1. **check_expired_deadlines** - Runs daily to expire overdue items

   ```python
   from apps.reviews.tasks import check_expired_deadlines
   result = check_expired_deadlines.delay()
   ```

2. **send_deadline_reminders** - Sends reminders 3 days before deadline
   ```python
   from apps.reviews.tasks import send_deadline_reminders
   result = send_deadline_reminders.delay()
   ```

#### Celery Beat Schedule (recommended)

```python
# In settings.py
CELERY_BEAT_SCHEDULE = {
    'check-expired-deadlines-daily': {
        'task': 'reviews.check_expired_deadlines',
        'schedule': crontab(hour=0, minute=0),  # Daily at midnight
    },
    'send-deadline-reminders-daily': {
        'task': 'reviews.send_deadline_reminders',
        'schedule': crontab(hour=9, minute=0),  # Daily at 9 AM
    },
}
```

### API Endpoints

#### Manual Expiration Check (Admin Only)

```
POST /api/v1/reviews/assignments/check_expired/
POST /api/v1/reviews/revisions/check_expired/
```

Response:

```json
{
  "status": "success",
  "message": "Checked and updated 5 expired assignments",
  "expired_count": 5
}
```

### Serializer Updates

#### EditorialDecisionCreateSerializer

- Validates `revision_deadline` is required for revision decisions
- Uses deadline in revision round creation

#### RevisionRoundCreateSerializer

- Uses `EditorialDecision.revision_deadline` if not provided
- Falls back to 30-day default if neither specified

## Usage Examples

### 1. Setting Review Deadline in Journal Settings

```python
journal = Journal.objects.get(short_name='JRNL')
journal.settings['review_deadline_days'] = 14  # 2 weeks
journal.save()
```

### 2. Creating Editorial Decision with Revision Deadline

```python
from datetime import timedelta
from django.utils import timezone

decision = EditorialDecision.objects.create(
    submission=submission,
    decision_type='MAJOR_REVISION',
    decided_by=editor_profile,
    decision_letter="Please revise...",
    revision_deadline=timezone.now() + timedelta(days=60)  # 60 days
)
```

### 3. Manually Checking Single Assignment

```python
assignment = ReviewAssignment.objects.get(id=assignment_id)
if assignment.check_and_update_expired():
    print(f"Assignment {assignment.id} has expired")
```

### 4. Manually Checking Single Revision Round

```python
revision = RevisionRound.objects.get(id=revision_id)
if revision.check_and_update_expired():
    print(f"Revision {revision.id} has expired and submission rejected")
```

## Notifications

The system sends email notifications for:

1. **Review Assignment Expiration** - Notifies editor
2. **Revision Expiration** - Notifies author
3. **Deadline Reminders** (3 days before)
   - Review deadline reminder to reviewer
   - Revision deadline reminder to author

## Migration

Migration file: `apps/reviews/migrations/0008_alter_reviewassignment_status_and_more.py`

Applied changes:

- Added `EXPIRED` to ReviewAssignment.status choices
- Added `EXPIRED` to RevisionRound.status choices

## Testing

### Test Expired Review Assignment

```bash
# Create an assignment with past due date
from django.utils import timezone
from datetime import timedelta

assignment = ReviewAssignment.objects.create(
    submission=submission,
    reviewer=reviewer,
    assigned_by=editor,
    due_date=timezone.now() - timedelta(days=1),  # Yesterday
    status='ACCEPTED'
)

# Run check
python manage.py check_expired_deadlines

# Verify status changed to EXPIRED
assignment.refresh_from_db()
assert assignment.status == 'EXPIRED'
```

### Test Expired Revision

```bash
revision = RevisionRound.objects.create(
    submission=submission,
    editorial_decision=decision,
    round_number=1,
    deadline=timezone.now() - timedelta(days=1),  # Yesterday
    status='REQUESTED',
    revision_requirements="Please address..."
)

# Run check
python manage.py check_expired_deadlines

# Verify status changed to EXPIRED and submission rejected
revision.refresh_from_db()
assert revision.status == 'EXPIRED'
assert revision.submission.status == 'REJECTED'
```

## Monitoring

### Check for Overdue Items (without updating)

```python
# Overdue review assignments
overdue_reviews = ReviewAssignment.objects.filter(
    status__in=['PENDING', 'ACCEPTED'],
    due_date__lt=timezone.now()
).count()

# Overdue revisions
overdue_revisions = RevisionRound.objects.filter(
    status__in=['REQUESTED', 'IN_PROGRESS'],
    deadline__lt=timezone.now()
).count()
```

### Admin Dashboard Query

```python
# Get summary of deadlines
from django.db.models import Count, Q

summary = {
    'expired_assignments': ReviewAssignment.objects.filter(status='EXPIRED').count(),
    'overdue_not_expired': ReviewAssignment.objects.filter(
        status__in=['PENDING', 'ACCEPTED'],
        due_date__lt=timezone.now()
    ).count(),
    'expired_revisions': RevisionRound.objects.filter(status='EXPIRED').count(),
    'overdue_revisions': RevisionRound.objects.filter(
        status__in=['REQUESTED', 'IN_PROGRESS'],
        deadline__lt=timezone.now()
    ).count(),
}
```

## Best Practices

1. **Set Realistic Deadlines**: Configure journal-specific review deadlines based on field complexity
2. **Run Daily Checks**: Schedule the management command or Celery task to run daily
3. **Monitor Expiration Rate**: High expiration rates may indicate unrealistic deadlines
4. **Send Reminders**: Enable reminder notifications 3 days before deadline
5. **Editor Review**: Editors should review expired assignments and reassign if needed
6. **Grace Period**: Consider implementing a grace period before auto-rejection of submissions

## Future Enhancements

- [ ] Configurable grace period before expiration
- [ ] Automatic reviewer reassignment after expiration
- [ ] Deadline extension requests from reviewers/authors
- [ ] Dashboard widgets showing upcoming deadlines
- [ ] Deadline statistics and reporting
- [ ] Customizable reminder schedules
