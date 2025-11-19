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

Save the current DOCX file with all edits and comments embedded. **This REPLACES the existing file** - it does NOT create a version.

**When to use:**
- Author making edits and saving progress
- Reviewer adding comments and saving
- Any intermediate saves during editing

**Note:** The old DOCX file is automatically deleted and replaced with the new one.

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

### 5. Create Version (Submission/Revision)
**POST** `/api/v1/submissions/documents/{id}/create-version/`

Create a new version snapshot of the document. This should be called when the author submits the manuscript or a revision.

**When to use:**
- ✅ Author submits manuscript for initial review
- ✅ Author submits revision after reviewer feedback
- ❌ NOT for regular saves during editing

**Request Body:**
```json
{
  "change_summary": "Initial submission" // or "Revision based on reviewer comments"
}
```

**Frontend Example:**
```javascript
// When author clicks "Submit for Review"
await instance.post(
  `/api/v1/submissions/documents/${documentId}/create-version/`,
  { change_summary: "Initial submission for review" }
);
```

**Response (201 Created):**
```json
{
  "status": "created",
  "message": "Version 1 created successfully",
  "version": {
    "id": "version-uuid",
    "version_number": 1,
    "change_summary": "Initial submission",
    "file_name": "manuscript.docx",
    "file_size": 1245678,
    "created_by": "John Doe",
    "created_at": "2025-11-19T16:30:00Z"
  }
}
```

**Version History Example:**
```
Version 1: Initial submission (2025-11-19)
Version 2: Revision after first review (2025-12-05)
Version 3: Revision after second review (2025-12-20)
```

---

### 6. Download Document
**GET** `/api/v1/submissions/documents/{id}/download/`

Download the current DOCX file.

**Response:** File download with proper headers
```
Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document
Content-Disposition: attachment; filename="manuscript.docx"
```

---

### 7. Get Document Metadata
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

### 8. Delete Document
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

### Complete Submission & Review Workflow

```javascript
// ========================================
// STEP 1: Author creates document and uploads initial DOCX
// ========================================
const formData = new FormData();
formData.append('submission', submissionId);
formData.append('title', 'Manuscript');
formData.append('document_type', 'MANUSCRIPT');
formData.append('file', docxFile);

const createResponse = await instance.post('/api/v1/submissions/documents/', formData);
const documentId = createResponse.data.id;

// ========================================
// STEP 2: Author edits in SuperDoc and saves progress (multiple times)
// ========================================
// Load document
const loadResponse = await instance.get(`/api/v1/submissions/documents/${documentId}/load/`);
// SuperDoc loads loadResponse.data.file_url

// Author makes changes...
// Author clicks Save button
const docxBlob1 = await editorRef.current.exportDocx();
const saveFormData1 = new FormData();
saveFormData1.append('file', docxBlob1, 'manuscript.docx');
await instance.post(`/api/v1/submissions/documents/${documentId}/save/`, saveFormData1);
// Old DOCX deleted, new one replaces it

// Author continues editing...
// Author saves again
const docxBlob2 = await editorRef.current.exportDocx();
const saveFormData2 = new FormData();
saveFormData2.append('file', docxBlob2, 'manuscript.docx');
await instance.post(`/api/v1/submissions/documents/${documentId}/save/`, saveFormData2);
// Previous DOCX deleted, newest one replaces it

// ========================================
// STEP 3: Author submits manuscript for review
// ========================================
// Create Version 1 snapshot
await instance.post(`/api/v1/submissions/documents/${documentId}/create-version/`, {
  change_summary: 'Initial submission for review'
});
// Version 1 created with snapshot of current DOCX
// Submission status updated to "SUBMITTED"

// ========================================
// STEP 4: Reviewer opens document and adds comments
// ========================================
const reviewerLoadResponse = await instance.get(`/api/v1/submissions/documents/${documentId}/load/`);
// SuperDoc loads DOCX (can_edit: false for reviewers, but can comment)

// Reviewer adds comments in SuperDoc...
// Reviewer saves (comments embedded in DOCX)
const reviewerBlob = await editorRef.current.exportDocx();
const reviewerFormData = new FormData();
reviewerFormData.append('file', reviewerBlob, 'manuscript.docx');
await instance.post(`/api/v1/submissions/documents/${documentId}/save/`, reviewerFormData);
// DOCX now contains reviewer comments

// ========================================
// STEP 5: Author views reviewer comments and makes revisions
// ========================================
const authorLoadResponse = await instance.get(`/api/v1/submissions/documents/${documentId}/load/`);
// SuperDoc displays DOCX with all reviewer comments

// Author addresses comments and makes revisions...
// Author saves progress multiple times
const revisionBlob1 = await editorRef.current.exportDocx();
const revisionFormData1 = new FormData();
revisionFormData1.append('file', revisionBlob1, 'manuscript_revised.docx');
await instance.post(`/api/v1/submissions/documents/${documentId}/save/`, revisionFormData1);

// Author continues revising...
const revisionBlob2 = await editorRef.current.exportDocx();
const revisionFormData2 = new FormData();
revisionFormData2.append('file', revisionBlob2, 'manuscript_revised.docx');
await instance.post(`/api/v1/submissions/documents/${documentId}/save/`, revisionFormData2);

// ========================================
// STEP 6: Author submits revision
// ========================================
// Create Version 2 snapshot
await instance.post(`/api/v1/submissions/documents/${documentId}/create-version/`, {
  change_summary: 'Revision addressing reviewer comments'
});
// Version 2 created with snapshot
// Submission status updated to "REVISED"

// ========================================
// RESULT: Version History
// ========================================
// Version 1: Initial submission (snapshot from Step 3)
// Version 2: First revision (snapshot from Step 6)
// Current working file: Latest saved DOCX (can continue editing)
```

### Key Points

1. **Regular Saves** (`/save/`):
   - Replaces the DOCX file
   - Old file is deleted
   - No version created
   - Use for: progress saves, adding comments, any edits

2. **Create Version** (`/create-version/`):
   - Creates a snapshot in DocumentVersion table
   - Current file remains as working copy
   - Use ONLY when: submitting for review, submitting revision

3. **File Lifecycle**:
   ```
   Upload → Save → Save → Save → [Submit] Create Version 1
                                     ↓
                           Document continues as working copy
                                     ↓
                           Save → Save → Save → [Submit Revision] Create Version 2
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
