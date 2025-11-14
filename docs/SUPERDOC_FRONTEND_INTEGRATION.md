# SuperDoc Frontend Integration Guide

This guide shows how to integrate SuperDoc with the Django backend for document editing.

## Installation

```bash
npm install superdoc
```

## Basic Integration

### 1. Initialize SuperDoc Editor

```javascript
import { SuperDoc } from 'superdoc';

// Fetch document data from backend
async function loadDocument(documentId, token) {
  const response = await fetch(
    `/api/v1/submissions/documents/${documentId}/load/`,
    {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }
  );
  
  const docData = await response.json();
  return docData;
}

// Initialize SuperDoc
async function initializeEditor(documentId, token) {
  const docData = await loadDocument(documentId, token);
  
  const superdoc = new SuperDoc({
    selector: '#editor-container',
    document: docData.file_url,  // Original DOCX file URL
    documentMode: docData.can_edit ? 'editing' : 'viewing',
    user: {
      name: currentUser.name,
      email: currentUser.email,
      color: '#' + Math.floor(Math.random()*16777215).toString(16) // Random color
    },
    onReady: () => {
      console.log('SuperDoc loaded successfully');
      
      // Load existing Yjs state if available
      if (docData.yjs_state) {
        loadYjsState(superdoc, docData.yjs_state);
      }
      
      // Setup auto-save
      setupAutoSave(superdoc, documentId, token);
    },
    onChange: (content) => {
      console.log('Document changed');
      // SuperDoc handles this internally with Yjs
    }
  });
  
  return superdoc;
}
```

### 2. Load Existing Yjs State

```javascript
function loadYjsState(superdoc, yjsStateBase64) {
  // Decode base64 to binary
  const yjsState = Uint8Array.from(atob(yjsStateBase64), c => c.charCodeAt(0));
  
  // Apply state to SuperDoc's Yjs document
  // Note: This is a simplified example. SuperDoc's API may differ.
  // Check SuperDoc documentation for exact method.
  if (superdoc.applyUpdate) {
    superdoc.applyUpdate(yjsState);
  }
}
```

### 3. Auto-Save Yjs State

```javascript
function setupAutoSave(superdoc, documentId, token) {
  let saveTimeout;
  
  // Listen for document changes
  superdoc.on('update', (update) => {
    // Debounce saves (wait 2 seconds after last change)
    clearTimeout(saveTimeout);
    
    saveTimeout = setTimeout(async () => {
      await saveYjsState(superdoc, documentId, token);
    }, 2000);
  });
  
  // Save on window unload
  window.addEventListener('beforeunload', () => {
    saveYjsState(superdoc, documentId, token);
  });
}

async function saveYjsState(superdoc, documentId, token) {
  try {
    // Get current Yjs state from SuperDoc
    // Note: Check SuperDoc's actual API for getting state
    const yjsState = superdoc.getUpdate(); // This method name may vary
    
    // Convert to base64
    const yjsStateBase64 = btoa(
      String.fromCharCode(...new Uint8Array(yjsState))
    );
    
    // Save to backend
    const response = await fetch(
      `/api/v1/submissions/documents/${documentId}/save-state/`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          yjs_state: yjsStateBase64
        })
      }
    );
    
    const data = await response.json();
    console.log('State saved:', data.last_edited_at);
  } catch (error) {
    console.error('Error saving state:', error);
  }
}
```

### 4. Export Document to DOCX

```javascript
async function exportDocument(superdoc, documentId, token) {
  try {
    // Export from SuperDoc
    const docxBlob = await superdoc.exportDocx();
    
    // Upload to backend
    const formData = new FormData();
    formData.append('file', docxBlob, 'document.docx');
    
    const response = await fetch(
      `/api/v1/submissions/documents/${documentId}/export/`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      }
    );
    
    const data = await response.json();
    console.log('Document exported:', data.file_url);
    
    return data.file_url;
  } catch (error) {
    console.error('Error exporting document:', error);
  }
}
```

### 5. Upload New DOCX File

```javascript
async function uploadDocx(file, documentId, token) {
  try {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(
      `/api/v1/submissions/documents/${documentId}/upload/`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      }
    );
    
    const data = await response.json();
    console.log('File uploaded:', data.file_url);
    
    // Reload SuperDoc with new file
    window.location.reload(); // Or re-initialize SuperDoc
  } catch (error) {
    console.error('Error uploading file:', error);
  }
}
```

## Complete React Component Example

```jsx
import React, { useEffect, useRef, useState } from 'react';
import { SuperDoc } from 'superdoc';
import { useAuth } from './hooks/useAuth'; // Your auth hook

function DocumentEditor({ documentId }) {
  const editorRef = useRef(null);
  const superdocRef = useRef(null);
  const { token, user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [canEdit, setCanEdit] = useState(false);

  useEffect(() => {
    async function initEditor() {
      try {
        // Load document data
        const response = await fetch(
          `/api/v1/submissions/documents/${documentId}/load/`,
          {
            headers: { 'Authorization': `Bearer ${token}` }
          }
        );
        
        const docData = await response.json();
        setCanEdit(docData.can_edit);

        // Initialize SuperDoc
        const superdoc = new SuperDoc({
          selector: editorRef.current,
          document: docData.file_url,
          documentMode: docData.can_edit ? 'editing' : 'viewing',
          user: {
            name: user.name,
            email: user.email,
            color: user.color
          },
          onReady: () => {
            // Load existing state
            if (docData.yjs_state) {
              const yjsState = Uint8Array.from(
                atob(docData.yjs_state), 
                c => c.charCodeAt(0)
              );
              superdoc.applyUpdate(yjsState);
            }

            // Setup auto-save
            let saveTimeout;
            superdoc.on('update', (update) => {
              clearTimeout(saveTimeout);
              saveTimeout = setTimeout(() => saveState(superdoc), 2000);
            });

            setLoading(false);
          }
        });

        superdocRef.current = superdoc;
      } catch (error) {
        console.error('Error initializing editor:', error);
      }
    }

    initEditor();

    // Cleanup
    return () => {
      if (superdocRef.current) {
        saveState(superdocRef.current); // Final save
        superdocRef.current.destroy();
      }
    };
  }, [documentId, token]);

  async function saveState(superdoc) {
    const yjsState = superdoc.getUpdate();
    const yjsStateBase64 = btoa(
      String.fromCharCode(...new Uint8Array(yjsState))
    );

    await fetch(
      `/api/v1/submissions/documents/${documentId}/save-state/`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ yjs_state: yjsStateBase64 })
      }
    );
  }

  async function handleExport() {
    const docxBlob = await superdocRef.current.exportDocx();
    
    const formData = new FormData();
    formData.append('file', docxBlob, 'document.docx');
    
    const response = await fetch(
      `/api/v1/submissions/documents/${documentId}/export/`,
      {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      }
    );
    
    const data = await response.json();
    alert(`Document exported: ${data.file_url}`);
  }

  if (loading) {
    return <div>Loading editor...</div>;
  }

  return (
    <div className="document-editor">
      <div className="toolbar">
        {canEdit && (
          <button onClick={handleExport}>
            Export to DOCX
          </button>
        )}
      </div>
      <div ref={editorRef} id="editor-container" />
    </div>
  );
}

export default DocumentEditor;
```

## API Endpoints

### Load Document
```
GET /api/v1/submissions/documents/{id}/load/
Authorization: Bearer {token}

Response:
{
  "id": "uuid",
  "title": "Manuscript Title",
  "document_type": "MANUSCRIPT",
  "can_edit": true,
  "file_url": "https://example.com/media/documents/2024/11/14/file.docx",
  "file_name": "manuscript.docx",
  "file_size": 45678,
  "yjs_state": "base64-encoded-binary-state",
  "last_edited_at": "2024-11-14T10:30:00Z",
  "last_edited_by": {
    "id": "uuid",
    "name": "John Doe"
  }
}
```

### Save Yjs State
```
POST /api/v1/submissions/documents/{id}/save-state/
Authorization: Bearer {token}
Content-Type: application/json

{
  "yjs_state": "base64-encoded-binary-state"
}

Response:
{
  "status": "saved",
  "last_edited_at": "2024-11-14T10:35:00Z"
}
```

### Upload DOCX
```
POST /api/v1/submissions/documents/{id}/upload/
Authorization: Bearer {token}
Content-Type: multipart/form-data

file: [binary DOCX file]

Response:
{
  "status": "uploaded",
  "file_name": "manuscript.docx",
  "file_size": 45678,
  "file_url": "https://example.com/media/documents/2024/11/14/file.docx"
}
```

### Export DOCX
```
POST /api/v1/submissions/documents/{id}/export/
Authorization: Bearer {token}
Content-Type: multipart/form-data

file: [binary DOCX file from SuperDoc]

Response:
{
  "status": "exported",
  "file_name": "manuscript.docx",
  "file_url": "https://example.com/media/documents/2024/11/14/file.docx"
}
```

### Download DOCX
```
GET /api/v1/submissions/documents/{id}/download/
Authorization: Bearer {token}

Response: Binary DOCX file
Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document
Content-Disposition: attachment; filename="manuscript.docx"
```

## Features Provided by SuperDoc

### ✅ Version History
- All versions stored in Yjs CRDT state
- View any previous version
- Compare versions
- Restore previous versions
- All automatic!

### ✅ Comments & Tracked Changes
- Add comments anywhere in document
- Reply to comments
- Resolve/unresolve comments
- Track insertions/deletions
- Accept/reject changes
- All stored in Yjs state!

### ✅ Collaborative Features
- User awareness (who's viewing)
- Real-time cursor positions
- User selections highlighted
- Conflict-free merging
- Offline editing support

### ✅ Word Compatibility
- Native DOCX rendering
- Preserve Word formatting
- Export to DOCX with all changes
- Import from DOCX

## Workflow Example

### Author Workflow:
1. **Upload Document**
   ```javascript
   // Create new document
   const formData = new FormData();
   formData.append('submission', submissionId);
   formData.append('title', 'My Manuscript');
   formData.append('document_type', 'MANUSCRIPT');
   formData.append('file', docxFile);
   
   await fetch('/api/v1/submissions/documents/', {
     method: 'POST',
     headers: { 'Authorization': `Bearer ${token}` },
     body: formData
   });
   ```

2. **Edit in SuperDoc**
   - Open editor
   - Make changes
   - Auto-save handles persistence

3. **Export Final Version**
   ```javascript
   await exportDocument(superdoc, documentId, token);
   ```

### Reviewer Workflow:
1. **Open Document** (read-only or comment mode)
   ```javascript
   const docData = await loadDocument(documentId, token);
   // docData.can_edit = false (view + comment only)
   ```

2. **Add Comments**
   - Select text in SuperDoc
   - Add comment
   - Comment stored in Yjs state

3. **Author Sees Comments**
   - SuperDoc shows all comments
   - Author can reply or resolve
   - All synced via Yjs state

### Editor Workflow:
1. **Review Document** (full edit access)
   - View tracked changes
   - Accept/reject changes
   - Add final edits

2. **Finalize**
   ```javascript
   // Export final version
   await exportDocument(superdoc, documentId, token);
   ```

## Important Notes

1. **No WebSocket** - We're NOT using real-time collaboration
   - Users edit one at a time
   - Yjs state persists document state between sessions
   - No simultaneous editing needed

2. **SuperDoc Handles Everything**
   - Version history via Yjs
   - Comments via Yjs
   - Tracked changes via Yjs
   - Backend just stores binary state

3. **Binary State**
   - Yjs state is binary (not JSON)
   - Base64 encode for HTTP transport
   - Store as BinaryField in Django

4. **Check SuperDoc Docs**
   - Method names may differ from examples
   - Refer to official SuperDoc documentation
   - API may change between versions

## Troubleshooting

### State Not Persisting
- Check auto-save is triggered
- Verify base64 encoding/decoding
- Check token authorization

### Comments Not Showing
- Ensure Yjs state is loaded
- Check SuperDoc module configuration
- Verify comment module is enabled

### Export Issues
- Ensure SuperDoc has latest changes
- Check DOCX export permissions
- Verify file upload size limits

## Summary

This simplified integration:
- ✅ No complex backend logic
- ✅ SuperDoc handles features
- ✅ Simple state persistence
- ✅ Easy to maintain
- ✅ Full Word compatibility
