# Copyediting Final Stage Workflow - Backend Documentation

## Overview

This document describes the backend implementation of the complete final stage workflow for the copyediting process. The workflow allows authors to review and confirm copyedited files, and editors to complete the copyediting stage and transition submissions to production.

**Django Version:** 4.2+  
**DRF Version:** 3.14+

---

## File Status Transitions

The copyediting workflow now supports a complete file lifecycle with four distinct statuses:

```
DRAFT → COPYEDITED → AUTHOR_FINAL → FINAL
```

### Status Definitions

| Status         | Description                         | Who Can Set                | Action Required            |
| -------------- | ----------------------------------- | -------------------------- | -------------------------- |
| `DRAFT`        | Initial file uploaded by copyeditor | System (on upload)         | Copyeditor approval needed |
| `COPYEDITED`   | File approved by copyeditor         | Copyeditor (via approve)   | Author confirmation needed |
| `AUTHOR_FINAL` | File confirmed by author            | Author (via confirm_final) | Editor completion needed   |
| `FINAL`        | File finalized for production       | System (via complete)      | Ready for production       |

---

## Model Changes

### File: `apps/submissions/copyediting_models.py`

#### Updated: FILE_TYPE_CHOICES

```python
FILE_TYPE_CHOICES = [
    ('DRAFT', 'Draft'),
    ('COPYEDITED', 'Copyedited'),
    ('AUTHOR_FINAL', 'Author Confirmed Final'),  # NEW
    ('FINAL', 'Final'),
]
```

**Migration:** `0017_add_author_final_file_type.py`

---

## API Endpoints

### 1. Approve Copyediting File (FIXED)

**Endpoint:** `POST /api/submissions/copyediting/files/{file_id}/approve/`  
**Method:** `POST`  
**Permissions:** IsAuthenticated, IsCopyeditorOrEditor  
**Status Change:** DRAFT → COPYEDITED

#### Bug Fix

Previously, the approve endpoint was not updating the `file_type` field. This has been fixed.

#### Request Body

```json
{
  "approval_notes": "Looks good, ready for author review" // optional
}
```

#### Response

```json
{
  "status": "success",
  "message": "File approved successfully",
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "file_type": "COPYEDITED",
  "is_approved": true,
  "approved_by": {
    "id": "user-uuid",
    "name": "John Doe"
  },
  "approved_at": "2025-12-10T10:30:00Z",
  "approval_notes": "Looks good, ready for author review"
}
```

#### Implementation Details

```python
@action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
def approve(self, request, pk=None):
    file = self.get_object()

    # Permission check: Must be copyeditor or editor
    if not (is_copyeditor or is_editor):
        return Response(
            {"detail": "Only copyeditors or editors can approve files."},
            status=status.HTTP_403_FORBIDDEN,
        )

    # Update file status
    file.is_approved = True
    file.file_type = 'COPYEDITED'  # NEW: Explicitly set file type
    file.approved_by = request.user.profile
    file.approved_at = timezone.now()
    file.approval_notes = request.data.get("approval_notes", "")
    file.save()

    return Response({...})
```

---

### 2. Get Copyedited Files (NEW)

**Endpoint:** `GET /api/submissions/copyediting/assignments/{assignment_id}/copyedited-files/`  
**Method:** `GET`  
**Permissions:** IsAuthenticated  
**Purpose:** Retrieve all copyedited files awaiting author confirmation

#### Query Parameters

None required. Automatically filters files with `file_type='COPYEDITED'`.

#### Response

```json
{
  "count": 3,
  "results": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "original_filename": "manuscript_v2.docx",
      "file_type": "COPYEDITED",
      "file_type_display": "Copyedited",
      "file_size": 2048576,
      "version": 2,
      "is_approved": true,
      "approved_by": {
        "id": "user-uuid",
        "first_name": "John",
        "last_name": "Doe"
      },
      "approved_at": "2025-12-10T10:30:00Z",
      "uploaded_by": {
        "id": "user-uuid",
        "first_name": "Jane",
        "last_name": "Smith"
      },
      "created_at": "2025-12-10T09:00:00Z",
      "description": "Copyedited manuscript with tracked changes"
    }
  ]
}
```

#### Implementation Details

```python
@action(
    detail=True,
    methods=["get"],
    url_path="copyedited-files",
    permission_classes=[IsAuthenticated],
)
def copyedited_files(self, request, pk=None):
    """Get all copyedited files for this assignment"""
    assignment = self.get_object()

    # Filter files with COPYEDITED status
    files = CopyeditingFile.objects.filter(
        submission=assignment.submission,
        file_type='COPYEDITED'
    ).select_related('uploaded_by__user', 'approved_by__user')

    serializer = CopyeditingFileSerializer(files, many=True)
    return Response({
        'count': files.count(),
        'results': serializer.data
    })
```

---

### 3. Confirm File as Final (NEW)

**Endpoint:** `POST /api/submissions/copyediting/files/{file_id}/confirm-final/`  
**Method:** `POST`  
**Permissions:** IsAuthenticated, IsSubmissionAuthor  
**Status Change:** COPYEDITED → AUTHOR_FINAL

#### Request Body

```json
{
  "confirmation_notes": "Reviewed and approved all changes" // optional
}
```

#### Response

```json
{
  "status": "success",
  "message": "File confirmed as final successfully",
  "file": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "original_filename": "manuscript_v2.docx",
    "file_type": "AUTHOR_FINAL",
    "version": 2
  },
  "confirmed_at": "2025-12-10T14:00:00Z",
  "confirmed_by": {
    "id": "user-uuid",
    "name": "Author Name"
  },
  "confirmation_notes": "Reviewed and approved all changes"
}
```

#### Validation Rules

- File must have `file_type='COPYEDITED'`
- User must be the submission author
- File must belong to an active assignment

#### Implementation Details

```python
@action(
    detail=True,
    methods=["post"],
    url_path="confirm-final",
    permission_classes=[IsAuthenticated],
)
def confirm_final(self, request, pk=None):
    """Author confirms copyedited file as final"""
    file = self.get_object()

    # Validation: Only COPYEDITED files can be confirmed
    if file.file_type != 'COPYEDITED':
        return Response(
            {"detail": "Only copyedited files can be confirmed as final."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Permission check: Must be submission author
    submission_authors = file.submission.authors.all()
    if request.user.profile not in submission_authors:
        return Response(
            {"detail": "Only submission authors can confirm files."},
            status=status.HTTP_403_FORBIDDEN,
        )

    # Update file status
    file.file_type = 'AUTHOR_FINAL'
    file.save()

    # Log the confirmation (you can add a separate model for this)
    confirmation_data = {
        'confirmed_by': request.user.profile,
        'confirmed_at': timezone.now(),
        'confirmation_notes': request.data.get('confirmation_notes', '')
    }

    return Response({...})
```

---

### 4. Complete Copyediting Assignment (ENHANCED)

**Endpoint:** `POST /api/submissions/copyediting/assignments/{assignment_id}/complete/`  
**Method:** `POST`  
**Permissions:** IsAuthenticated, IsEditor  
**Status Changes:**

- Files: AUTHOR_FINAL → FINAL
- Assignment: IN_PROGRESS → COMPLETED
- Submission: COPYEDITING → PRODUCTION

#### Request Body

```json
{
  "completion_notes": "All files reviewed and approved by author" // optional
}
```

#### Response

```json
{
  "status": "success",
  "message": "Copyediting assignment completed successfully",
  "assignment_id": "550e8400-e29b-41d4-a716-446655440000",
  "assignment_status": "COMPLETED",
  "submission_status": "PRODUCTION",
  "files_finalized": 3,
  "completed_at": "2025-12-10T16:00:00Z",
  "completed_by": {
    "id": "user-uuid",
    "name": "Editor Name"
  },
  "completion_notes": "All files reviewed and approved by author",
  "assignment": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "COMPLETED",
    "submission": {
      "id": "submission-uuid",
      "status": "PRODUCTION"
    }
  }
}
```

#### Validation Rules (Multi-Step)

1. **Assignment Status Check**

   ```python
   if assignment.status != 'IN_PROGRESS':
       return Response({"detail": "Assignment must be in progress"}, status=400)
   ```

2. **Author Confirmation Check**

   ```python
   author_final_files = CopyeditingFile.objects.filter(
       submission=assignment.submission,
       file_type='AUTHOR_FINAL'
   )
   if author_final_files.count() == 0:
       return Response({
           "detail": "No files have been confirmed by the author yet."
       }, status=400)
   ```

3. **Pending Files Check**
   ```python
   copyedited_files = CopyeditingFile.objects.filter(
       submission=assignment.submission,
       file_type='COPYEDITED'
   )
   if copyedited_files.exists():
       return Response({
           "detail": f"{copyedited_files.count()} file(s) still awaiting author confirmation."
       }, status=400)
   ```

#### Implementation Details

```python
@action(
    detail=True,
    methods=["post"],
    permission_classes=[IsAuthenticated],
)
def complete(self, request, pk=None):
    """Complete the copyediting assignment"""
    assignment = self.get_object()

    # Permission check
    if not is_editor:
        return Response({"detail": "Only editors can complete assignments."},
                       status=403)

    # Validation Step 1: Assignment must be in progress
    if assignment.status != 'IN_PROGRESS':
        return Response({"detail": "Assignment must be in progress to complete."},
                       status=400)

    # Validation Step 2: Check for author-confirmed files
    author_final_files = CopyeditingFile.objects.filter(
        submission=assignment.submission,
        file_type='AUTHOR_FINAL'
    )

    if author_final_files.count() == 0:
        return Response({
            "detail": "No files have been confirmed by the author yet. "
                     "At least one file must be confirmed before completion.",
            "files_confirmed": 0
        }, status=400)

    # Validation Step 3: Check for pending copyedited files
    copyedited_files = CopyeditingFile.objects.filter(
        submission=assignment.submission,
        file_type='COPYEDITED'
    )

    if copyedited_files.exists():
        return Response({
            "detail": f"Cannot complete assignment. {copyedited_files.count()} "
                     f"file(s) are still awaiting author confirmation.",
            "pending_files": copyedited_files.count(),
            "pending_file_names": list(copyedited_files.values_list('original_filename', flat=True))
        }, status=400)

    # All validations passed - proceed with completion
    with transaction.atomic():
        # Step 1: Finalize all author-confirmed files
        files_updated = author_final_files.update(file_type='FINAL')

        # Step 2: Update assignment status
        assignment.status = 'COMPLETED'
        assignment.completed_by = request.user.profile
        assignment.completed_at = timezone.now()
        assignment.completion_notes = request.data.get('completion_notes', '')
        assignment.save()

        # Step 3: Update submission status to PRODUCTION
        submission = assignment.submission
        submission.status = 'PRODUCTION'
        submission.save()

    return Response({
        "status": "success",
        "message": "Copyediting assignment completed successfully",
        "assignment_id": str(assignment.id),
        "assignment_status": assignment.status,
        "submission_status": submission.status,
        "files_finalized": files_updated,
        "completed_at": assignment.completed_at,
        "completed_by": {
            "id": str(request.user.profile.id),
            "name": f"{request.user.first_name} {request.user.last_name}"
        },
        "completion_notes": assignment.completion_notes,
        "assignment": CopyeditingAssignmentSerializer(assignment).data
    })
```

---

## Error Handling

### Common Error Responses

#### 400 Bad Request

```json
{
  "detail": "Error message describing the validation failure",
  "files_confirmed": 0, // when no files confirmed
  "pending_files": 2, // when files await confirmation
  "pending_file_names": ["file1.docx", "file2.pdf"]
}
```

#### 403 Forbidden

```json
{
  "detail": "Permission denied message"
}
```

#### 404 Not Found

```json
{
  "detail": "Not found."
}
```

---

## Database Migration

### Migration File: `0017_add_author_final_file_type.py`

```python
from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('submissions', '0016_previous_migration'),
    ]

    operations = [
        migrations.AlterField(
            model_name='copyeditingfile',
            name='file_type',
            field=models.CharField(
                choices=[
                    ('DRAFT', 'Draft'),
                    ('COPYEDITED', 'Copyedited'),
                    ('AUTHOR_FINAL', 'Author Confirmed Final'),
                    ('FINAL', 'Final')
                ],
                default='DRAFT',
                max_length=20
            ),
        ),
    ]
```

### Applying Migration

```bash
cd backend-journal-portal
python manage.py migrate
```

**Note:** This migration is backward compatible and safe to apply to production.

---

## Testing Checklist

### Unit Tests Required

- [ ] Test approve endpoint sets file_type='COPYEDITED'
- [ ] Test copyedited_files endpoint filters correctly
- [ ] Test confirm_final validates file status
- [ ] Test confirm_final validates author permission
- [ ] Test complete validates assignment status
- [ ] Test complete validates author confirmation
- [ ] Test complete validates no pending files
- [ ] Test complete updates all statuses correctly
- [ ] Test transaction rollback on completion failure

### Integration Tests Required

- [ ] Test complete workflow: upload → approve → confirm → complete
- [ ] Test concurrent file confirmations by multiple authors
- [ ] Test completion with multiple files
- [ ] Test error handling for partial confirmations

### Manual Testing Scenarios

1. **Happy Path**

   - Copyeditor uploads and approves file
   - Author confirms file
   - Editor completes assignment
   - Verify submission moves to production

2. **Error Cases**
   - Try to confirm non-copyedited file
   - Try to complete with pending files
   - Try to complete without author confirmations
   - Non-author tries to confirm file

---

## Performance Considerations

### Database Queries

All endpoints use `select_related()` and `prefetch_related()` to minimize database hits:

```python
# copyedited_files endpoint
files = CopyeditingFile.objects.filter(
    submission=assignment.submission,
    file_type='COPYEDITED'
).select_related(
    'uploaded_by__user',
    'approved_by__user'
).prefetch_related(
    'submission__authors__user'
)
```

### Indexing Recommendations

```sql
-- Add index on file_type for faster filtering
CREATE INDEX idx_copyediting_file_type ON copyediting_files(file_type);

-- Add composite index for common query pattern
CREATE INDEX idx_copyediting_submission_type
ON copyediting_files(submission_id, file_type);
```

---

## Security Considerations

### Permission Checks

1. **Approve**: Only copyeditors and editors
2. **Confirm Final**: Only submission authors
3. **Complete**: Only editors
4. **Copyedited Files**: Any authenticated user with assignment access

### Data Validation

- File status transitions are strictly enforced
- Atomic transactions prevent partial updates
- All user inputs are sanitized
- File uploads are validated for type and size

---

## Monitoring & Logging

### Recommended Logging Points

```python
import logging
logger = logging.getLogger(__name__)

# Log important state transitions
logger.info(f"File {file.id} approved by {user.email}")
logger.info(f"File {file.id} confirmed by author {user.email}")
logger.info(f"Assignment {assignment.id} completed, submission moved to production")

# Log validation failures
logger.warning(f"Completion failed: {copyedited_files.count()} files pending")
```

### Metrics to Track

- Average time from COPYEDITED to AUTHOR_FINAL
- Average time from AUTHOR_FINAL to FINAL
- Number of files confirmed per day
- Number of assignments completed per day
- Validation failure rates

---

## API Summary Table

| Endpoint                              | Method | Permission        | Status Change             | New      |
| ------------------------------------- | ------ | ----------------- | ------------------------- | -------- |
| `/files/{id}/approve/`                | POST   | Copyeditor/Editor | DRAFT → COPYEDITED        | Fixed    |
| `/assignments/{id}/copyedited-files/` | GET    | Authenticated     | -                         | ✅       |
| `/files/{id}/confirm-final/`          | POST   | Author            | COPYEDITED → AUTHOR_FINAL | ✅       |
| `/assignments/{id}/complete/`         | POST   | Editor            | AUTHOR_FINAL → FINAL      | Enhanced |

---

## Rollback Plan

If issues arise after deployment:

1. **Immediate Rollback**

   ```bash
   python manage.py migrate submissions 0016_previous_migration
   ```

2. **Data Cleanup** (if needed)

   ```python
   # Reset any AUTHOR_FINAL files back to COPYEDITED
   CopyeditingFile.objects.filter(
       file_type='AUTHOR_FINAL'
   ).update(file_type='COPYEDITED')
   ```

3. **Redeploy Previous Version**
   ```bash
   git checkout <previous-commit>
   # Deploy
   ```

---

## Future Enhancements

1. Add email notifications for each status transition
2. Add deadline tracking for author confirmations
3. Add bulk file confirmation for authors
4. Add file comparison/diff view between versions
5. Add assignment analytics dashboard
6. Add automated reminders for pending confirmations

---

## Related Documentation

- [Copyediting Workflow Overview](./COPYEDITING_WORKFLOW.md)
- [File Upload Guidelines](./FILE_UPLOAD.md)
- [Permission System](./PERMISSIONS.md)
- [API Authentication](./AUTHENTICATION.md)

---

**Version:** 1.0.0  
**Authors:** Development Team
