# SuperDoc Integration - Simplified Architecture

## Understanding SuperDoc

After analyzing SuperDoc's documentation and architecture, here's what SuperDoc actually does:

### ✅ SuperDoc Handles EVERYTHING Frontend:
1. **Document Editing** - Full DOCX editing in browser
2. **Version History** - Via Yjs CRDT (Conflict-free Replicated Data Type)
3. **Comments & Tracked Changes** - Built into the editor
4. **User Awareness** - Cursors, selections, presence
5. **Conflict Resolution** - Automatic via CRDT
6. **Offline Support** - Edit offline, sync when online
7. **Real-time Collaboration** - Via Yjs + WebSocket

### 🔌 Backend Responsibilities ("Bring Your Own Backend"):
1. **Store Yjs document state** - Binary data (not complex version objects!)
2. **WebSocket server** - For real-time sync between users
3. **Authentication** - Who can access which document
4. **Auto-save hook** - Periodic save of document state
5. **DOCX upload/download** - Initial file and export

## What We DON'T Need

❌ **Comment Model** - SuperDoc handles comments  
❌ **DocumentVersion Model** - SuperDoc handles versions via Yjs  
❌ **Complex Serializers** - Just binary state storage  
❌ **Permission Classes for Editing** - SuperDoc handles UI permissions  
❌ **DOCX Conversion Utilities** - SuperDoc does this in browser  
❌ **python-docx** - Not needed!

## What We DO Need

### Minimal Django Backend:

```python
# apps/submissions/models.py

class Document(models.Model):
    """
    Minimal document model for SuperDoc integration.
    SuperDoc handles everything else (versions, comments, editing).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE)
    
    # Metadata
    title = models.CharField(max_length=255)
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES)
    created_by = models.ForeignKey(Profile, on_delete=models.CASCADE)
    
    # SuperDoc state (Yjs binary data)
    yjs_state = models.BinaryField(null=True, blank=True)
    yjs_state_vector = models.BinaryField(null=True, blank=True)
    
    # Original file
    original_file = models.FileField(upload_to='documents/%Y/%m/%d/')
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_edited_at = models.DateTimeField(null=True, blank=True)
    last_edited_by = models.ForeignKey(
        Profile, 
        null=True, 
        on_delete=models.SET_NULL,
        related_name='last_edited_documents'
    )
```

### API Endpoints (Simple):

```python
# apps/submissions/views.py

class DocumentViewSet(viewsets.ModelViewSet):
    """
    Minimal document API for SuperDoc.
    """
    
    @action(detail=True, methods=['get'])
    def load(self, request, pk=None):
        """
        Load document for SuperDoc editor.
        Returns original DOCX file + Yjs state if exists.
        """
        document = self.get_object()
        
        return Response({
            'id': str(document.id),
            'title': document.title,
            'file_url': request.build_absolute_uri(document.original_file.url),
            'yjs_state': document.yjs_state,  # Binary Yjs state
            'yjs_state_vector': document.yjs_state_vector,
            'last_edited_at': document.last_edited_at,
            'last_edited_by': document.last_edited_by.display_name if document.last_edited_by else None,
        })
    
    @action(detail=True, methods=['post'])
    def save_state(self, request, pk=None):
        """
        Save Yjs state from SuperDoc.
        Called by collaboration backend auto-save.
        """
        document = self.get_object()
        
        # Save binary Yjs state
        document.yjs_state = request.data.get('yjs_state')
        document.yjs_state_vector = request.data.get('yjs_state_vector')
        document.last_edited_at = timezone.now()
        document.last_edited_by = request.user.profile
        document.save()
        
        return Response({'status': 'saved'})
    
    @action(detail=True, methods=['post'])
    def export(self, request, pk=None):
        """
        Export current document state to DOCX.
        SuperDoc provides the DOCX file from frontend.
        """
        document = self.get_object()
        
        # Frontend sends the exported DOCX blob
        docx_file = request.FILES.get('file')
        
        # Save as new version or update original
        document.original_file = docx_file
        document.save()
        
        return Response({'status': 'exported'})
```

### WebSocket Collaboration Server:

```python
# apps/collaboration/server.py

from superdoc_yjs_collaboration import CollaborationBuilder

collaboration = CollaborationBuilder() \
    .withName('Journal Portal Collaboration') \
    .withDebounce(2000) \
    .onAuthenticate(authenticate_user) \
    .onLoad(load_document_state) \
    .onAutoSave(save_document_state) \
    .build()

async def authenticate_user(token, request):
    """Verify JWT token and check document access."""
    user = verify_jwt(token)
    document_id = request.params['documentId']
    
    # Check if user can access this document's submission
    document = Document.objects.get(id=document_id)
    submission = document.submission
    
    # Check access (author, reviewer, editor)
    if not user.can_access_submission(submission):
        raise PermissionDenied()
    
    return {'id': user.id, 'name': user.profile.display_name}

async def load_document_state(document_id):
    """Load Yjs binary state for collaboration."""
    document = Document.objects.get(id=document_id)
    return document.yjs_state or b''

async def save_document_state(document_id, yjs_state):
    """Auto-save Yjs state every 2 seconds."""
    document = Document.objects.get(id=document_id)
    document.yjs_state = yjs_state
    document.last_edited_at = timezone.now()
    document.save()
```

## Frontend Integration

```javascript
// Load document in SuperDoc
import { SuperDoc } from 'superdoc';

// 1. Fetch document metadata
const response = await fetch(`/api/v1/submissions/documents/${docId}/load/`, {
  headers: { 'Authorization': `Bearer ${token}` }
});
const docData = await response.json();

// 2. Initialize SuperDoc
const superdoc = new SuperDoc({
  selector: '#editor',
  document: docData.file_url,  // Original DOCX file
  documentMode: 'editing',
  user: {
    name: currentUser.name,
    email: currentUser.email
  },
  modules: {
    collaboration: {
      url: 'wss://your-server.com/collaboration',
      token: jwtToken,
      params: {
        documentId: docId
      }
    }
  },
  onReady: () => {
    // SuperDoc loaded with DOCX
    console.log('Document ready');
  }
});

// 3. SuperDoc handles:
// - Version history (via Yjs)
// - Comments & tracked changes
// - Real-time collaboration
// - Conflict resolution
// - User cursors & presence

// 4. Export when done
async function exportDocument() {
  const docxBlob = await superdoc.exportDocx();
  
  const formData = new FormData();
  formData.append('file', docxBlob, 'document.docx');
  
  await fetch(`/api/v1/submissions/documents/${docId}/export/`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
    body: formData
  });
}
```

## Complete Workflow

### 1. Author Uploads DOCX
```
POST /submissions/{id}/upload_document/
→ Save original DOCX file
→ Create Document record
→ yjs_state is null (no edits yet)
```

### 2. Reviewer Opens Document
```
Frontend:
1. GET /documents/{id}/load/
2. Initialize SuperDoc with DOCX URL
3. SuperDoc loads DOCX in browser
4. Connect to WebSocket collaboration server
5. SuperDoc shows document, comments UI, version history

Backend (WebSocket):
1. Authenticate user via JWT
2. Check if user can access this submission
3. Load yjs_state for this document
4. Send state to SuperDoc
5. SuperDoc syncs with other users (if any)
```

### 3. Multiple Users Collaborate
```
Frontend (All automatic by SuperDoc):
- User A types → Yjs updates → WebSocket → All users see change
- User B adds comment → Stored in Yjs → All users see it
- User C accepts tracked change → Updated in Yjs → All users see it
- Conflict resolution automatic (CRDT)

Backend (WebSocket):
- Receives Yjs updates via WebSocket
- Broadcasts to all connected users
- Auto-saves yjs_state every 2 seconds
```

### 4. Author Revises Based on Comments
```
Frontend:
- Author sees all comments in SuperDoc
- Makes changes directly in editor
- Resolves comments in SuperDoc UI
- All tracked automatically by Yjs

Backend:
- Just saves yjs_state periodically
- No manual comment/version tracking needed!
```

### 5. Export Final Version
```
Frontend:
- Click "Export to DOCX"
- SuperDoc generates DOCX with all changes
- Upload via /documents/{id}/export/

Backend:
- Save new DOCX file
- Original file updated or versioned
```

## What This Gives You

### ✅ All SuperDoc Features:
- Real-time collaboration
- Comments & tracked changes
- Version history
- Conflict resolution
- User presence/cursors
- Offline editing
- Perfect DOCX compatibility

### ✅ Simple Django Backend:
- Document metadata storage
- Binary Yjs state storage
- WebSocket collaboration server
- Permission control
- DOCX file storage

### ✅ No Complex Code:
- No Comment model
- No DocumentVersion model
- No conversion utilities
- No complex serializers
- Just simple state storage!

## Dependencies

```bash
# Backend
pip install channels  # For Django WebSockets
pip install channels-redis  # For WebSocket scaling
npm install @superdoc-dev/superdoc-yjs-collaboration  # Node collaboration server

# Frontend
npm install superdoc
```

## Summary

**Old Approach (Over-engineered):**
- 15+ API endpoints
- Comment model with location tracking
- DocumentVersion model with diffs
- DOCX conversion utilities
- Complex serializers
- python-docx dependency
- Manual version/comment management

**New Approach (Correct):**
- 3 simple endpoints (load, save_state, export)
- Binary Yjs state storage
- WebSocket collaboration server (50 lines)
- SuperDoc handles ALL features
- Clean, simple, maintainable

**This is the RIGHT way to integrate SuperDoc!** 🎉
