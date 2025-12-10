# Copyediting File Save Workflow

## Overview

The copyediting file save implementation follows the same pattern as **SuperDoc** with a **manual save workflow** that replaces existing files rather than creating new versions on each save.

## Key Concepts

### Manual Save vs Version Creation

**Manual Save** (Intermediate saves):

- Used during the editing process
- Replaces the existing file
- Does NOT create a new version
- Updates `last_edited_by` and `last_edited_at` timestamps
- Old file is automatically deleted from storage

**Version Creation** (Major milestones):

- Used when work is complete or needs to be snapshotted
- Creates a NEW `CopyeditingFile` record
- Increments version number
- Keeps both old and new files

## Implementation Details

### Model Changes

Added to `CopyeditingFile` model:

```python
last_edited_by = models.ForeignKey(
    'users.Profile',
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name='last_edited_copyediting_files',
    help_text="Last person to edit this file"
)
last_edited_at = models.DateTimeField(null=True, blank=True)
```

### API Endpoints

#### 1. Load File for Editing

**GET** `/api/v1/submissions/copyediting/files/{id}/load/`

Returns file metadata and download URL for loading in editor (e.g., SuperDoc).

Response:

```json
{
  "id": "uuid",
  "assignment_id": "uuid",
  "submission_id": "uuid",
  "file_type": "DRAFT",
  "file_type_display": "Draft File",
  "original_filename": "manuscript.docx",
  "description": "Initial draft from submission",
  "version": 1,
  "is_approved": false,
  "file_url": "http://localhost:8000/media/copyediting/2025/12/10/manuscript.docx",
  "file_size": 28163,
  "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "last_edited_by": {
    "id": "uuid",
    "name": "John Doe",
    "email": "john@example.com"
  },
  "last_edited_at": "2025-12-10T10:30:00Z",
  "created_at": "2025-12-10T09:00:00Z",
  "updated_at": "2025-12-10T10:30:00Z"
}
```

#### 2. Save File (Manual Save)

**POST** `/api/v1/submissions/copyediting/files/{id}/save/`

Saves the file by **replacing** the existing one. Does NOT create a new version.

Request (multipart/form-data):

```
file: <binary file data>
```

Response:

```json
{
  "status": "saved",
  "message": "File saved successfully",
  "file": {
    // Full file object with updated fields
  }
}
```

**What happens:**

1. Old file path is stored
2. New file replaces the old one in the database
3. `file_size`, `mime_type`, `original_filename` are updated
4. `last_edited_by` is set to current user
5. `last_edited_at` is set to now
6. Old file is deleted from disk

#### 3. Download File

**GET** `/api/v1/submissions/copyediting/files/{id}/download/`

Downloads the current file.

Response: Binary file with appropriate content-type and Content-Disposition headers.

## Workflow Examples

### Example 1: Copyeditor Working on a Document

```
1. Assignment starts -> INITIAL_DRAFT file created from submission
2. Copyeditor loads file: GET /files/{id}/load/
3. Copyeditor edits in SuperDoc
4. Copyeditor saves progress: POST /files/{id}/save/ (replaces file)
5. Copyeditor continues editing
6. Copyeditor saves again: POST /files/{id}/save/ (replaces file again)
7. Copyeditor completes work
8. System creates COPYEDITED version: POST /files/ with file_type='COPYEDITED'
```

### Example 2: Author Reviewing Copyedited Version

```
1. Author loads copyedited file: GET /files/{id}/load/
2. Author reviews in SuperDoc (read-only or with suggestions)
3. Author approves: POST /files/{id}/approve/
4. System creates FINAL version: POST /files/ with file_type='FINAL'
```

## Comparison with SuperDoc

| Feature              | SuperDoc           | Copyediting Files          |
| -------------------- | ------------------ | -------------------------- |
| Load endpoint        | `/load/`           | `/load/`                   |
| Save endpoint        | `/save/`           | `/save/`                   |
| Download endpoint    | `/download/`       | `/download/`               |
| Version creation     | `/create-version/` | Create new CopyeditingFile |
| File replacement     | Yes                | Yes                        |
| Last edited tracking | Yes                | Yes                        |
| Old file deletion    | Yes                | Yes                        |
| Comments in file     | Yes (DOCX native)  | Yes (DOCX native)          |

## File Types in Copyediting Workflow

```python
FILE_TYPE_CHOICES = [
    ('INITIAL_DRAFT', 'Initial Draft'),    # Created on assignment start
    ('COPYEDITED_VERSION', 'Copyedited'),  # After copyeditor completes
    ('AUTHOR_CHANGES', 'Author Changes'),  # If author makes changes
    ('FINAL_VERSION', 'Final Version'),    # Approved final version
]
```

Each type represents a **milestone**, not an intermediate save.

## Best Practices

1. **Use `/save/` for intermediate work** - Don't create new file records for every save
2. **Create new file records for milestones** - When work stage changes (DRAFT → COPYEDITED)
3. **Track who last edited** - Always set `last_edited_by` on save
4. **Clean up old files** - Old files are auto-deleted on replacement
5. **Version numbers** - Increment when creating NEW file records, not on save

## Migration Applied

- **0016_add_edit_tracking_to_copyediting_files.py**
  - Added `last_edited_by` field
  - Added `last_edited_at` field

## Testing

Test the endpoints:

```bash
# Load file
GET http://localhost:8000/api/v1/submissions/copyediting/files/{id}/load/

# Save file (with actual file upload)
POST http://localhost:8000/api/v1/submissions/copyediting/files/{id}/save/
Content-Type: multipart/form-data
file: <upload your .docx file>

# Download file
GET http://localhost:8000/api/v1/submissions/copyediting/files/{id}/download/
```

## Security & Permissions

All endpoints use `WorkflowPermissions`:

- Journal staff can access all files for their journals
- Copyeditors can access files in their assignments
- Assignment participants can access files
- Authors can view (read-only) files in their submissions

The `/save/` endpoint requires edit permission (checked by `WorkflowPermissions`).
