# Copyediting and Production Workflow API Documentation

## Overview

This document provides comprehensive documentation for the Copyediting and Production workflow APIs. These endpoints manage the post-acceptance stages of manuscript processing, from copyediting through publication.

## Workflow Stages

1. **ACCEPTED** → Submission accepted by editorial decision
2. **COPYEDITING** → Copyeditor assigned and working on manuscript
3. **IN_PRODUCTION** → Production assistant creating galley files
4. **SCHEDULED** → Publication scheduled with metadata
5. **PUBLISHED** → Article published and publicly available

---

## Copyediting Workflow APIs

### Base URL

`/api/v1/submissions/copyediting/`

---

### Copyediting Assignments

#### List Copyediting Assignments

```
GET /api/v1/submissions/copyediting/assignments/
```

**Query Parameters:**

- `submission` (UUID): Filter by submission ID
- `copyeditor` (UUID): Filter by copyeditor profile ID
- `status`: Filter by status (PENDING, IN_PROGRESS, COMPLETED, CANCELLED)
- `assigned_by` (UUID): Filter by assigning editor
- `search`: Search in submission title and copyeditor name
- `ordering`: Sort by assigned_at, due_date, status

**Response:**

```json
{
  "count": 10,
  "results": [
    {
      "id": "uuid",
      "submission_id": "uuid",
      "submission_title": "Research Article Title",
      "copyeditor": {
        "id": "uuid",
        "user": {
          "email": "copyeditor@example.com",
          "first_name": "John",
          "last_name": "Doe"
        }
      },
      "status": "IN_PROGRESS",
      "status_display": "In Progress",
      "assigned_at": "2024-01-15T10:00:00Z",
      "due_date": "2024-02-15T10:00:00Z",
      "is_overdue": false,
      "completed_at": null
    }
  ]
}
```

#### Create Copyediting Assignment

```
POST /api/v1/submissions/copyediting/assignments/
```

**Request Body:**

```json
{
  "submission": "uuid",
  "copyeditor_id": "uuid",
  "due_date": "2024-02-15T10:00:00Z",
  "instructions": "Please focus on grammar and formatting consistency."
}
```

**Response:** 201 Created

```json
{
  "id": "uuid",
  "submission": "uuid",
  "submission_title": "Research Article Title",
  "copyeditor": {...},
  "assigned_by": {...},
  "status": "PENDING",
  "assigned_at": "2024-01-15T10:00:00Z",
  "due_date": "2024-02-15T10:00:00Z",
  "instructions": "Please focus on grammar and formatting consistency.",
  "is_overdue": false
}
```

**Notes:**

- Automatically moves submission status to COPYEDITING
- Validates copyeditor has COPY_EDITOR role
- Due date must be in the future

#### Get Copyediting Assignment

```
GET /api/v1/submissions/copyediting/assignments/{id}/
```

#### Update Copyediting Assignment

```
PATCH /api/v1/submissions/copyediting/assignments/{id}/
```

**Request Body (partial):**

```json
{
  "status": "IN_PROGRESS",
  "instructions": "Updated instructions"
}
```

#### Start Copyediting

```
POST /api/v1/submissions/copyediting/assignments/{id}/start/
```

**Response:** 200 OK (Assignment with status IN_PROGRESS)

#### Complete Copyediting

```
POST /api/v1/submissions/copyediting/assignments/{id}/complete/
```

**Request Body:**

```json
{
  "completion_notes": "All edits completed. Ready for author review."
}
```

**Response:** 200 OK (Assignment with status COMPLETED)

#### Get Assignment Files

```
GET /api/v1/submissions/copyediting/assignments/{id}/files/
```

#### Get Assignment Discussions

```
GET /api/v1/submissions/copyediting/assignments/{id}/discussions/
```

#### Get Assignment Participants

```
GET /api/v1/submissions/copyediting/assignments/{id}/participants/
```

**Response:**

```json
{
  "copyeditor": {...},
  "assigned_by": {...},
  "author": {...}
}
```

---

### Copyediting Files

#### List Copyediting Files

```
GET /api/v1/submissions/copyediting/files/
```

**Query Parameters:**

- `assignment` (UUID): Filter by assignment ID
- `submission` (UUID): Filter by submission ID
- `file_type`: Filter by type (DRAFT, COPYEDITED, FINAL)
- `is_approved`: Filter by approval status
- `search`: Search in filename and description

**Response:**

```json
{
  "count": 5,
  "results": [
    {
      "id": "uuid",
      "assignment": "uuid",
      "submission": "uuid",
      "file_type": "COPYEDITED",
      "file_type_display": "Copyedited File",
      "file": "/media/copyediting/2024/01/15/manuscript_edited.docx",
      "file_url": "https://example.com/media/copyediting/2024/01/15/manuscript_edited.docx",
      "original_filename": "manuscript_edited.docx",
      "file_size": 1024000,
      "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "version": 1,
      "description": "Initial copyedited version",
      "uploaded_by": {...},
      "is_approved": false,
      "approved_by": null,
      "approved_at": null,
      "created_at": "2024-01-20T14:30:00Z"
    }
  ]
}
```

#### Upload Copyediting File

```
POST /api/v1/submissions/copyediting/files/
Content-Type: multipart/form-data
```

**Form Data:**

```
assignment: uuid
submission: uuid
file_type: COPYEDITED
file: [file upload]
description: "Copyedited version with tracked changes"
```

**Response:** 201 Created

#### Approve Copyediting File

```
POST /api/v1/submissions/copyediting/files/{id}/approve/
```

**Response:** 200 OK (File with is_approved=true)

---

### Copyediting Discussions

#### List Copyediting Discussions

```
GET /api/v1/submissions/copyediting/discussions/
```

**Query Parameters:**

- `assignment` (UUID): Filter by assignment ID
- `submission` (UUID): Filter by submission ID
- `status`: Filter by status (OPEN, CLOSED)
- `started_by` (UUID): Filter by discussion starter
- `search`: Search in subject

**Response:**

```json
{
  "count": 3,
  "results": [
    {
      "id": "uuid",
      "subject": "Query about methodology section",
      "status": "OPEN",
      "status_display": "Open",
      "started_by": {...},
      "message_count": 5,
      "last_message_at": "2024-01-25T16:45:00Z",
      "created_at": "2024-01-22T10:00:00Z",
      "updated_at": "2024-01-25T16:45:00Z"
    }
  ]
}
```

#### Create Copyediting Discussion

```
POST /api/v1/submissions/copyediting/discussions/
```

**Request Body:**

```json
{
  "assignment": "uuid",
  "submission": "uuid",
  "subject": "Query about methodology section",
  "participant_ids": ["uuid1", "uuid2"]
}
```

**Response:** 201 Created

#### Get Copyediting Discussion

```
GET /api/v1/submissions/copyediting/discussions/{id}/
```

**Response:**

```json
{
  "id": "uuid",
  "assignment": "uuid",
  "submission": "uuid",
  "subject": "Query about methodology section",
  "status": "OPEN",
  "started_by": {...},
  "participants": [{...}, {...}],
  "messages": [
    {
      "id": "uuid",
      "author": {...},
      "message": "<p>I have a question about the methodology...</p>",
      "has_attachments": false,
      "attachments": [],
      "created_at": "2024-01-22T10:00:00Z"
    }
  ],
  "message_count": 5,
  "last_message": {
    "author": "John Doe",
    "message": "Thank you for clarifying...",
    "created_at": "2024-01-25T16:45:00Z"
  }
}
```

#### Add Message to Discussion

```
POST /api/v1/submissions/copyediting/discussions/{id}/add_message/
```

**Request Body:**

```json
{
  "message": "<p>Here is my response to your query...</p>"
}
```

**Response:** 201 Created (Message object)

#### Close Discussion

```
POST /api/v1/submissions/copyediting/discussions/{id}/close/
```

**Response:** 200 OK

#### Reopen Discussion

```
POST /api/v1/submissions/copyediting/discussions/{id}/reopen/
```

**Response:** 200 OK

---

## Production Workflow APIs

### Base URL

`/api/v1/submissions/production/`

---

### Production Assignments

#### List Production Assignments

```
GET /api/v1/submissions/production/assignments/
```

**Query Parameters:**

- `submission` (UUID): Filter by submission ID
- `production_assistant` (UUID): Filter by production assistant profile ID
- `status`: Filter by status (PENDING, IN_PROGRESS, COMPLETED, CANCELLED)
- `assigned_by` (UUID): Filter by assigning editor
- `search`: Search in submission title and production assistant name
- `ordering`: Sort by assigned_at, due_date, status

**Response:** Similar structure to copyediting assignments

#### Create Production Assignment

```
POST /api/v1/submissions/production/assignments/
```

**Request Body:**

```json
{
  "submission": "uuid",
  "production_assistant_id": "uuid",
  "due_date": "2024-03-15T10:00:00Z",
  "instructions": "Please create PDF and HTML galleys."
}
```

**Response:** 201 Created

**Notes:**

- Automatically moves submission status to IN_PRODUCTION
- Validates production assistant has LAYOUT_EDITOR or PRODUCTION_EDITOR role

#### Action Endpoints

- `POST /api/v1/submissions/production/assignments/{id}/start/`
- `POST /api/v1/submissions/production/assignments/{id}/complete/`
- `GET /api/v1/submissions/production/assignments/{id}/files/`
- `GET /api/v1/submissions/production/assignments/{id}/discussions/`
- `GET /api/v1/submissions/production/assignments/{id}/participants/`

---

### Production Files (Galleys)

#### List Production Files

```
GET /api/v1/submissions/production/files/
```

**Query Parameters:**

- `assignment` (UUID): Filter by assignment ID
- `submission` (UUID): Filter by submission ID
- `file_type`: Filter by type (PRODUCTION_READY, GALLEY)
- `galley_format`: Filter by format (PDF, HTML, XML, EPUB, MOBI, OTHER)
- `is_published`: Filter by publication status
- `is_approved`: Filter by approval status
- `search`: Search in filename, label, and description

**Response:**

```json
{
  "count": 3,
  "results": [
    {
      "id": "uuid",
      "assignment": "uuid",
      "submission": "uuid",
      "file_type": "GALLEY",
      "file_type_display": "Galley File",
      "galley_format": "PDF",
      "galley_format_display": "PDF",
      "file": "/media/production/2024/02/15/article.pdf",
      "file_url": "https://example.com/media/production/2024/02/15/article.pdf",
      "original_filename": "article.pdf",
      "file_size": 2048000,
      "mime_type": "application/pdf",
      "label": "PDF",
      "version": 1,
      "description": "Final PDF galley for publication",
      "uploaded_by": {...},
      "is_published": false,
      "published_at": null,
      "is_approved": true,
      "approved_by": {...},
      "approved_at": "2024-02-20T12:00:00Z",
      "created_at": "2024-02-15T14:30:00Z"
    }
  ]
}
```

#### Upload Production File (Galley)

```
POST /api/v1/submissions/production/files/
Content-Type: multipart/form-data
```

**Form Data:**

```
assignment: uuid
submission: uuid
file_type: GALLEY
galley_format: PDF
label: PDF
file: [file upload]
description: "Final PDF galley"
```

**Response:** 201 Created

#### Approve Production File

```
POST /api/v1/submissions/production/files/{id}/approve/
```

**Response:** 200 OK

#### Publish Galley File

```
POST /api/v1/submissions/production/files/{id}/publish/
```

**Response:** 200 OK

**Notes:**

- File must be approved before it can be published
- Published galleys are publicly accessible

---

### Production Discussions

Similar endpoints to copyediting discussions:

- `GET /api/v1/submissions/production/discussions/`
- `POST /api/v1/submissions/production/discussions/`
- `GET /api/v1/submissions/production/discussions/{id}/`
- `POST /api/v1/submissions/production/discussions/{id}/add_message/`
- `POST /api/v1/submissions/production/discussions/{id}/close/`
- `POST /api/v1/submissions/production/discussions/{id}/reopen/`

---

### Publication Schedules

#### List Publication Schedules

```
GET /api/v1/submissions/production/schedules/
```

**Query Parameters:**

- `submission` (UUID): Filter by submission ID
- `status`: Filter by status (SCHEDULED, PUBLISHED, CANCELLED)
- `year`: Filter by publication year
- `volume`: Filter by volume
- `issue`: Filter by issue
- `search`: Search in submission title and DOI
- `ordering`: Sort by scheduled_date, published_date, created_at

**Response:**

```json
{
  "count": 10,
  "results": [
    {
      "id": "uuid",
      "submission": "uuid",
      "submission_title": "Research Article Title",
      "status": "SCHEDULED",
      "status_display": "Scheduled",
      "scheduled_date": "2024-04-01T00:00:00Z",
      "published_date": null,
      "volume": "10",
      "issue": "2",
      "year": 2024,
      "doi": "10.1234/journal.v10i2.123",
      "pages": "45-67",
      "scheduled_by": {...},
      "created_at": "2024-03-01T10:00:00Z"
    }
  ]
}
```

#### Schedule Publication

```
POST /api/v1/submissions/production/schedules/
```

**Request Body:**

```json
{
  "submission": "uuid",
  "scheduled_date": "2024-04-01T00:00:00Z",
  "volume": "10",
  "issue": "2",
  "year": 2024,
  "doi": "10.1234/journal.v10i2.123",
  "pages": "45-67"
}
```

**Response:** 201 Created

**Notes:**

- Automatically moves submission status to SCHEDULED
- Scheduled date must be in the future

#### Get Publication Schedule

```
GET /api/v1/submissions/production/schedules/{id}/
```

#### Update Publication Schedule

```
PATCH /api/v1/submissions/production/schedules/{id}/
```

**Request Body (partial):**

```json
{
  "scheduled_date": "2024-04-15T00:00:00Z",
  "doi": "10.1234/journal.v10i2.123"
}
```

#### Publish Now

```
POST /api/v1/submissions/production/schedules/{id}/publish_now/
```

**Response:** 200 OK

**Notes:**

- Immediately publishes the submission
- Updates submission status to PUBLISHED
- Sets published_date to current timestamp

#### Cancel Publication

```
POST /api/v1/submissions/production/schedules/{id}/cancel/
```

**Response:** 200 OK

**Notes:**

- Cannot cancel already published submissions
- Reverts submission status to IN_PRODUCTION

---

## Permissions

All workflow endpoints use `WorkflowPermissions`:

- **Superusers/Staff**: Full access to all operations
- **Journal Staff**: Can manage workflow for their journal's submissions
- **Copyeditors**: Can manage their assigned copyediting tasks
- **Production Assistants**: Can manage their assigned production tasks
- **Authors**: Read-only access to their submission's workflow, can add messages to discussions

---

## Status Transitions

### Submission Status Flow

```
ACCEPTED (Editorial Decision)
    ↓
COPYEDITING (Copyeditor Assigned)
    ↓
IN_PRODUCTION (Production Assistant Assigned)
    ↓
SCHEDULED (Publication Scheduled)
    ↓
PUBLISHED (Article Published)
```

### Assignment Status Flow

```
PENDING (Just Assigned)
    ↓
IN_PROGRESS (Work Started)
    ↓
COMPLETED (Work Finished)

CANCELLED (Assignment Cancelled)
```

### Discussion Status Flow

```
OPEN (Active Discussion)
    ↓
CLOSED (Discussion Resolved)
    ↓
OPEN (Reopened if needed)
```

---

## Error Responses

### 400 Bad Request

```json
{
  "detail": "Error message describing the validation issue"
}
```

### 401 Unauthorized

```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden

```json
{
  "detail": "You do not have permission to perform this action."
}
```

### 404 Not Found

```json
{
  "detail": "Not found."
}
```

---

## Frontend Integration Guide

### Copyediting Workflow

1. When editorial decision is ACCEPT, show "Assign Copyeditor" button
2. Assign copyeditor using POST `/copyediting/assignments/`
3. Display copyediting interface with tabs:
   - **Draft Files**: List files from submission
   - **Copyedited Files**: Upload and manage edited files
   - **Discussions**: Communication threads
   - **Participants**: Show copyeditor, editor, author
4. Copyeditor can start/complete assignment
5. When complete, enable "Move to Production" button

### Production Workflow

1. Assign production assistant using POST `/production/assignments/`
2. Display production interface with tabs:
   - **Production Ready Files**: Copyedited files
   - **Galleys**: Upload and manage galley files (PDF, HTML, etc.)
   - **Discussions**: Communication threads
   - **Participants**: Show production assistant, editor, author
3. Production assistant uploads galleys
4. Editor approves galleys
5. When ready, enable "Schedule Publication" button

### Publication Scheduling

1. Create publication schedule using POST `/production/schedules/`
2. Provide publication metadata (volume, issue, year, DOI, pages)
3. Schedule can be updated before publication
4. Publish immediately or wait for scheduled date
5. Once published, submission status changes to PUBLISHED

---

## Example Workflow Sequence

### Complete Copyediting to Production Flow

```javascript
// 1. Editorial decision is ACCEPT
POST /api/v1/reviews/decisions/
{
  "submission": "sub-uuid",
  "decision_type": "ACCEPT",
  "decision_letter": "..."
}
// Submission status → ACCEPTED

// 2. Assign copyeditor
POST /api/v1/submissions/copyediting/assignments/
{
  "submission": "sub-uuid",
  "copyeditor_id": "copyeditor-uuid",
  "due_date": "2024-02-15T10:00:00Z"
}
// Submission status → COPYEDITING

// 3. Copyeditor uploads edited files
POST /api/v1/submissions/copyediting/files/
{
  "assignment": "assignment-uuid",
  "file_type": "COPYEDITED",
  "file": [file]
}

// 4. Complete copyediting
POST /api/v1/submissions/copyediting/assignments/{id}/complete/
{
  "completion_notes": "All edits completed"
}

// 5. Assign production assistant
POST /api/v1/submissions/production/assignments/
{
  "submission": "sub-uuid",
  "production_assistant_id": "prod-uuid",
  "due_date": "2024-03-15T10:00:00Z"
}
// Submission status → IN_PRODUCTION

// 6. Upload galley files
POST /api/v1/submissions/production/files/
{
  "assignment": "prod-assignment-uuid",
  "file_type": "GALLEY",
  "galley_format": "PDF",
  "label": "PDF",
  "file": [pdf-file]
}

// 7. Approve galley
POST /api/v1/submissions/production/files/{id}/approve/

// 8. Schedule publication
POST /api/v1/submissions/production/schedules/
{
  "submission": "sub-uuid",
  "scheduled_date": "2024-04-01T00:00:00Z",
  "volume": "10",
  "issue": "2",
  "year": 2024
}
// Submission status → SCHEDULED

// 9. Publish
POST /api/v1/submissions/production/schedules/{id}/publish_now/
// Submission status → PUBLISHED
```

---

## Testing

Run migrations and test the endpoints:

```bash
# Generate migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create test users with appropriate roles
python create_test_users.py

# Test endpoints using curl or Postman
curl -X GET http://localhost:8000/api/v1/submissions/copyediting/assignments/ \
  -H "Authorization: Bearer <token>"
```

---

## Notes

- All file uploads support multipart/form-data
- All timestamps are in ISO 8601 format (UTC)
- All UUIDs should be in standard UUID format
- File size limits apply as configured in settings
- Supported file types for galleys: PDF, HTML, XML, EPUB, MOBI, and other formats
- Discussion messages support HTML content
- All endpoints support pagination (default page size: 20)
- drf-spectacular integration provides auto-generated OpenAPI schema
