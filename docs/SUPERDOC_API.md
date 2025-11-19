# SuperDoc API Documentation

## Overview
Manual save workflow for document editing with SuperDoc. Comments and formatting are stored within the DOCX file itself (no Yjs/real-time collaboration needed).

## Base URL
```
/api/v1/submissions/documents/
```

---

## Endpoints

### 1. Create Document
**POST** `/api/v1/submissions/documents/`

Create a new document with optional initial DOCX file upload.

**Request Body (multipart/form-data):**
```json
{
  "submission": "uuid",
  "title": "Manuscript Draft",
  "document_type": "MANUSCRIPT",
  "description": "Initial draft",
  "file": <docx file>  // Optional
}
```

**Document Types:**
- `MANUSCRIPT`
- `SUPPLEMENTARY`
- `COVER_LETTER`
- `REVIEWER_RESPONSE`
- `REVISED_MANUSCRIPT`
- `FINAL_VERSION`

**Response (201 Created):**
```json
{
  "id": "document-uuid",
  "submission": "submission-uuid",
  "submission_title": "My Research Paper",
  "title": "Manuscript Draft",
  "document_type": "MANUSCRIPT",
  "description": "Initial draft",
  "file_name": "manuscript.docx",
  "file_size": 1234567,
  "file_url": "http://example.com/media/documents/2025/11/19/manuscript.docx",
  "created_by": "profile-uuid",
  "created_by_name": "John Doe",
  "last_edited_by": null,
  "last_edited_by_name": null,
  "last_edited_at": null,
  "created_at": "2025-11-19T10:00:00Z",
  "updated_at": "2025-11-19T10:00:00Z"
}
```

---

### 2. List Documents
**GET** `/api/v1/submissions/documents/`

List all documents the current user has access to.

**Response (200 OK):**
```json
[
  {
    "id": "document-uuid",
    "submission": "submission-uuid",
    "submission_title": "My Research Paper",
    "title": "Manuscript Draft",
    "document_type": "MANUSCRIPT",
    "file_url": "http://example.com/media/documents/...",
    "created_by_name": "John Doe",
    "last_edited_by_name": "Jane Reviewer",
    "last_edited_at": "2025-11-19T15:30:00Z",
    "created_at": "2025-11-19T10:00:00Z"
  }
]
```

---

### 3. Load Document
**GET** `/api/v1/submissions/documents/{id}/load/`

Load document for SuperDoc editor. Returns metadata and DOCX file URL.

**Response (200 OK):**
```json
{
  "id": "document-uuid",
  "title": "Manuscript Draft",
  "document_type": "MANUSCRIPT",
  "can_edit": true,
  "file_url": "http://example.com/media/documents/2025/11/19/manuscript.docx",
  "file_name": "manuscript.docx",
  "file_size": 1234567,
  "last_edited_by": {
    "id": "profile-uuid",
    "name": "Jane Reviewer"
  },
  "last_edited_at": "2025-11-19T15:30:00Z",
  "created_at": "2025-11-19T10:00:00Z",
  "updated_at": "2025-11-19T15:30:00Z"
}
```

**Permissions:**
- `can_edit: true` → Corresponding author, Journal editors
- `can_edit: false` → Co-authors, Reviewers (view/comment only)

---

### 4. Save Document (Manual Save)
**POST** `/api/v1/submissions/documents/{id}/save/`

Save the current DOCX file with all edits and comments embedded.

**Request (multipart/form-data):**
```
file: <docx blob exported from SuperDoc>
```

**Frontend Example:**
```javascript
const docxBlob = await editorRef.current.exportDocx();
const formData = new FormData();
formData.append('file', docxBlob, `${documentData.title}.docx`);

await instance.post(
  `/api/v1/submissions/documents/${documentId}/save/`,
  formData,
  { headers: { 'Content-Type': 'multipart/form-data' } }
);
```

**Response (200 OK):**
```json
{
  "status": "saved",
  "message": "Document saved successfully",
  "document": {
    "id": "document-uuid",
    "title": "Manuscript Draft",
    "file_url": "http://example.com/media/documents/2025/11/19/manuscript_updated.docx",
    "file_name": "manuscript.docx",
    "file_size": 1245678,
    "last_edited_by": "profile-uuid",
    "last_edited_by_name": "Jane Reviewer",
    "last_edited_at": "2025-11-19T16:00:00Z"
  }
}
```

---

### 5. Download Document
**GET** `/api/v1/submissions/documents/{id}/download/`

Download the current DOCX file.

**Response:** File download with proper headers
```
Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document
Content-Disposition: attachment; filename="manuscript.docx"
```

---

### 6. Get Document Metadata
**GET** `/api/v1/submissions/documents/{id}/`

Get document metadata without loading for editor.

**Response (200 OK):**
```json
{
  "id": "document-uuid",
  "submission": "submission-uuid",
  "submission_title": "My Research Paper",
  "title": "Manuscript Draft",
  "document_type": "MANUSCRIPT",
  "description": "Initial draft",
  "file_name": "manuscript.docx",
  "file_size": 1234567,
  "file_url": "http://example.com/media/documents/...",
  "created_by": "profile-uuid",
  "created_by_name": "John Doe",
  "last_edited_by": "profile-uuid",
  "last_edited_by_name": "Jane Reviewer",
  "last_edited_at": "2025-11-19T15:30:00Z",
  "created_at": "2025-11-19T10:00:00Z",
  "updated_at": "2025-11-19T15:30:00Z"
}
```

---

### 7. Delete Document
**DELETE** `/api/v1/submissions/documents/{id}/`

Delete a document permanently.

**Permissions:** Corresponding author, Journal editors, Admin only

**Response (204 No Content):** Empty response on success

---

## Access Permissions

| User Role | View | Comment | Edit | Delete |
|-----------|------|---------|------|--------|
| Corresponding Author | ✅ | ✅ | ✅ | ✅ |
| Co-author | ✅ | ✅ | ❌ | ❌ |
| Reviewer | ✅ | ✅ | ❌ | ❌ |
| Journal Editor | ✅ | ✅ | ✅ | ✅ |
| Admin/Staff | ✅ | ✅ | ✅ | ✅ |

---

## Workflow Example

### Author Uploads → Reviewer Comments → Author Revises

```javascript
// 1. Author creates document with DOCX file
const formData = new FormData();
formData.append('submission', submissionId);
formData.append('title', 'Manuscript');
formData.append('document_type', 'MANUSCRIPT');
formData.append('file', docxFile);

const createResponse = await instance.post('/api/v1/submissions/documents/', formData);
const documentId = createResponse.data.id;

// 2. Reviewer opens document in SuperDoc
const loadResponse = await instance.get(`/api/v1/submissions/documents/${documentId}/load/`);
// SuperDoc loads loadResponse.data.file_url
// Reviewer adds comments in SuperDoc UI

// 3. Reviewer saves (comments embedded in DOCX)
const docxBlob = await editorRef.current.exportDocx();
const saveFormData = new FormData();
saveFormData.append('file', docxBlob, 'manuscript.docx');

await instance.post(`/api/v1/submissions/documents/${documentId}/save/`, saveFormData);

// 4. Author opens and sees all reviewer comments
const authorLoadResponse = await instance.get(`/api/v1/submissions/documents/${documentId}/load/`);
// SuperDoc displays DOCX with all comments intact

// 5. Author makes revisions and saves
const revisedBlob = await editorRef.current.exportDocx();
const revisedFormData = new FormData();
revisedFormData.append('file', revisedBlob, 'manuscript_revised.docx');

await instance.post(`/api/v1/submissions/documents/${documentId}/save/`, revisedFormData);
```

---

## Error Responses

### 403 Forbidden
```json
{
  "error": "You do not have permission to edit this document"
}
```

### 400 Bad Request
```json
{
  "error": "File must be a .docx file"
}
```

### 404 Not Found
```json
{
  "error": "No file available for download"
}
```
