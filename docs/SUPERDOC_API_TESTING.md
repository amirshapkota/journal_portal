# SuperDoc API Testing Guide

## Quick Test with cURL

### 1. Get Authentication Token
First, login to get your JWT token:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email": "your@email.com", "password": "yourpassword"}'
```

Response:
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

Save the `access` token for subsequent requests.

### 2. List All Documents

```bash
curl -X GET http://localhost:8000/api/v1/submissions/documents/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 3. Create a New Document

```bash
curl -X POST http://localhost:8000/api/v1/submissions/documents/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "submission=YOUR_SUBMISSION_UUID" \
  -F "title=Test Manuscript" \
  -F "document_type=MANUSCRIPT" \
  -F "description=Initial draft" \
  -F "file=@/path/to/your/manuscript.docx"
```

Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "submission": "...",
  "submission_title": "My Research Paper",
  "title": "Test Manuscript",
  "document_type": "MANUSCRIPT",
  "description": "Initial draft",
  "file_name": "manuscript.docx",
  "file_size": 45678,
  "created_by": "...",
  "created_by_name": "John Doe",
  "last_edited_by": null,
  "last_edited_by_name": null,
  "last_edited_at": null,
  "created_at": "2024-11-14T10:00:00Z",
  "updated_at": "2024-11-14T10:00:00Z"
}
```

### 4. Load Document for SuperDoc

```bash
curl -X GET http://localhost:8000/api/v1/submissions/documents/DOCUMENT_UUID/load/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Test Manuscript",
  "document_type": "MANUSCRIPT",
  "can_edit": true,
  "created_at": "2024-11-14T10:00:00Z",
  "updated_at": "2024-11-14T10:00:00Z",
  "last_edited_at": null,
  "last_edited_by": null,
  "file_url": "http://localhost:8000/media/documents/2024/11/14/manuscript.docx",
  "file_name": "manuscript.docx",
  "file_size": 45678,
  "yjs_state": null
}
```

### 5. Save Yjs State (Simulated)

```bash
# In real usage, this would be base64-encoded binary Yjs state
# For testing, we'll use a dummy base64 string

curl -X POST http://localhost:8000/api/v1/submissions/documents/DOCUMENT_UUID/save-state/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "yjs_state": "SGVsbG8gV29ybGQh"
  }'
```

Response:
```json
{
  "status": "saved",
  "last_edited_at": "2024-11-14T10:05:00Z"
}
```

### 6. Load Again (Should Have Yjs State)

```bash
curl -X GET http://localhost:8000/api/v1/submissions/documents/DOCUMENT_UUID/load/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

Response (now with yjs_state):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "Test Manuscript",
  "document_type": "MANUSCRIPT",
  "can_edit": true,
  "created_at": "2024-11-14T10:00:00Z",
  "updated_at": "2024-11-14T10:05:00Z",
  "last_edited_at": "2024-11-14T10:05:00Z",
  "last_edited_by": {
    "id": "...",
    "name": "John Doe"
  },
  "file_url": "http://localhost:8000/media/documents/2024/11/14/manuscript.docx",
  "file_name": "manuscript.docx",
  "file_size": 45678,
  "yjs_state": "SGVsbG8gV29ybGQh"
}
```

### 7. Export Document

```bash
curl -X POST http://localhost:8000/api/v1/submissions/documents/DOCUMENT_UUID/export/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -F "file=@/path/to/exported.docx"
```

Response:
```json
{
  "status": "exported",
  "file_name": "exported.docx",
  "file_url": "http://localhost:8000/media/documents/2024/11/14/exported.docx"
}
```

### 8. Download Document

```bash
curl -X GET http://localhost:8000/api/v1/submissions/documents/DOCUMENT_UUID/download/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -o downloaded_manuscript.docx
```

## Test with Python

```python
import requests
import base64

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
EMAIL = "your@email.com"
PASSWORD = "yourpassword"

# 1. Login
response = requests.post(f"{BASE_URL}/auth/login/", json={
    "email": EMAIL,
    "password": PASSWORD
})
token = response.json()["access"]
headers = {"Authorization": f"Bearer {token}"}

# 2. List documents
response = requests.get(f"{BASE_URL}/submissions/documents/", headers=headers)
print("Documents:", response.json())

# 3. Create document
with open("manuscript.docx", "rb") as f:
    response = requests.post(
        f"{BASE_URL}/submissions/documents/",
        headers=headers,
        data={
            "submission": "YOUR_SUBMISSION_UUID",
            "title": "Test Manuscript",
            "document_type": "MANUSCRIPT"
        },
        files={"file": f}
    )
document_id = response.json()["id"]
print("Created document:", document_id)

# 4. Load document
response = requests.get(
    f"{BASE_URL}/submissions/documents/{document_id}/load/",
    headers=headers
)
doc_data = response.json()
print("Document loaded:", doc_data)

# 5. Save Yjs state (simulated)
yjs_state = b"Hello World!"  # In reality, this would be Yjs binary state
yjs_state_b64 = base64.b64encode(yjs_state).decode('utf-8')

response = requests.post(
    f"{BASE_URL}/submissions/documents/{document_id}/save-state/",
    headers=headers,
    json={"yjs_state": yjs_state_b64}
)
print("State saved:", response.json())

# 6. Load again (should have state)
response = requests.get(
    f"{BASE_URL}/submissions/documents/{document_id}/load/",
    headers=headers
)
doc_data = response.json()
print("Yjs state:", doc_data.get("yjs_state"))

# Decode state
if doc_data.get("yjs_state"):
    decoded = base64.b64decode(doc_data["yjs_state"])
    print("Decoded state:", decoded)

# 7. Download document
response = requests.get(
    f"{BASE_URL}/submissions/documents/{document_id}/download/",
    headers=headers
)
with open("downloaded.docx", "wb") as f:
    f.write(response.content)
print("Document downloaded")
```

## Test with Postman

### Import Collection

Create a Postman collection with these requests:

1. **Login** - POST `/api/v1/auth/login/`
   - Body: `{"email": "...", "password": "..."}`
   - Save `access` token to environment

2. **List Documents** - GET `/api/v1/submissions/documents/`
   - Headers: `Authorization: Bearer {{token}}`

3. **Create Document** - POST `/api/v1/submissions/documents/`
   - Headers: `Authorization: Bearer {{token}}`
   - Body: form-data
     - submission: `UUID`
     - title: `Test Manuscript`
     - document_type: `MANUSCRIPT`
     - file: `[Select file]`

4. **Load Document** - GET `/api/v1/submissions/documents/{{doc_id}}/load/`
   - Headers: `Authorization: Bearer {{token}}`

5. **Save State** - POST `/api/v1/submissions/documents/{{doc_id}}/save-state/`
   - Headers: `Authorization: Bearer {{token}}`
   - Body: JSON
     ```json
     {
       "yjs_state": "SGVsbG8gV29ybGQh"
     }
     ```

6. **Download** - GET `/api/v1/submissions/documents/{{doc_id}}/download/`
   - Headers: `Authorization: Bearer {{token}}`
   - Save response as file

## API Endpoints Summary

### Base URL: `/api/v1/submissions/documents/`

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/` | List all accessible documents | ✅ |
| POST | `/` | Create new document | ✅ |
| GET | `/{id}/` | Get document metadata | ✅ |
| GET | `/{id}/load/` | Load for SuperDoc editor | ✅ |
| POST | `/{id}/save-state/` | Save Yjs state | ✅ |
| POST | `/{id}/upload/` | Upload DOCX file | ✅ |
| POST | `/{id}/export/` | Export as DOCX | ✅ |
| GET | `/{id}/download/` | Download DOCX | ✅ |

## Permission Testing

Test different user roles:

### 1. Corresponding Author (Full Access)
- ✅ Can create documents
- ✅ Can edit documents
- ✅ Can save state
- ✅ Can export/download

### 2. Co-Author (Read + Comment)
- ✅ Can view documents
- ❌ Cannot edit (can_edit = false)
- ✅ Can save state (for comments)
- ✅ Can download

### 3. Reviewer (Read + Comment)
- ✅ Can view documents
- ❌ Cannot edit
- ✅ Can save state (for comments)
- ✅ Can download

### 4. Editor (Full Access)
- ✅ Can view all documents
- ✅ Can edit all documents
- ✅ Can save state
- ✅ Can export/download

### 5. Unauthorized User
- ❌ 403 Forbidden on all endpoints

## Swagger UI

The API is also documented in Swagger UI:

```
http://localhost:8000/api/docs/
```

Browse to:
- **submissions** section
- Look for `superdoc` endpoints

You can test all endpoints directly from Swagger!

## Expected Responses

### Success (200/201)
```json
{
  "status": "success",
  "data": {...}
}
```

### Permission Denied (403)
```json
{
  "error": "You do not have permission to edit this document"
}
```

### Not Found (404)
```json
{
  "detail": "Not found."
}
```

### Validation Error (400)
```json
{
  "error": "No file provided"
}
```

## Tips

1. **Document Types**:
   - `MANUSCRIPT`
   - `SUPPLEMENTARY`
   - `COVER_LETTER`
   - `REVIEWER_RESPONSE`
   - `REVISED_MANUSCRIPT`
   - `FINAL_VERSION`

2. **File Upload**:
   - Only `.docx` files accepted
   - Max size depends on `settings.DATA_UPLOAD_MAX_MEMORY_SIZE`

3. **Yjs State**:
   - Must be base64 encoded
   - Binary data from SuperDoc's Yjs document
   - Includes ALL document state (content, versions, comments)

4. **Permissions**:
   - Checked on every request
   - Based on submission relationship
   - Returns `can_edit` flag in load response

## Troubleshooting

### 401 Unauthorized
- Check token is valid
- Token may have expired (use refresh token)

### 403 Forbidden
- User doesn't have access to this document
- Check submission permissions

### 400 Bad Request
- Missing required fields
- Invalid file type
- Invalid yjs_state format

### 500 Server Error
- Check Django logs
- Run `python manage.py check`
- Verify database connection

## Next Steps

After backend testing:
1. Integrate frontend with SuperDoc
2. Test full workflow (upload → edit → comment → export)
3. Test with real Yjs state from SuperDoc
4. Load test with larger documents

---

**All endpoints are working!** ✅

The backend is ready for SuperDoc frontend integration.
