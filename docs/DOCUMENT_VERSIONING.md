# Document Versioning Strategy

## Overview
This document explains how document saves and versions work in the SuperDoc system.

## Two Types of Operations

### 1. Save Document (In-Place Update)
**Endpoint:** `POST /api/v1/submissions/documents/{id}/save/`

**What it does:**
- Replaces the existing DOCX file with a new one
- Automatically deletes the old DOCX file from storage
- Updates `last_edited_by` and `last_edited_at` metadata
- Does **NOT** create a version entry

**When to use:**
- ✅ Author saving progress while writing
- ✅ Reviewer adding comments
- ✅ Any intermediate saves during editing
- ✅ Collaborative editing (multiple people adding comments)

**Storage impact:**
- Only 1 DOCX file exists at a time (the current working copy)
- Old files are deleted to save storage space

---

### 2. Create Version (Snapshot)
**Endpoint:** `POST /api/v1/submissions/documents/{id}/create-version/`

**What it does:**
- Creates a permanent snapshot in the `DocumentVersion` table
- Copies the current DOCX file
- Assigns a version number (1, 2, 3, etc.)
- Stores metadata: version number, change summary, timestamp, creator
- Marks previous versions as `is_current=False`
- The working document remains editable

**When to use:**
- ✅ Author submits manuscript for initial review
- ✅ Author submits revision after receiving reviewer feedback
- ✅ Major milestones in the submission process

**Storage impact:**
- Each version is permanently stored
- Provides audit trail and history
- Allows reverting to previous versions if needed

---

## Workflow Timeline

```
Day 1: Author uploads manuscript.docx
       └─> Document created with original_file = manuscript.docx

Day 2: Author edits and saves
       └─> Save endpoint: manuscript.docx replaced (old deleted)

Day 3: Author edits more and saves
       └─> Save endpoint: manuscript.docx replaced (old deleted)

Day 4: Author submits for review
       └─> Create Version 1: Snapshot saved to DocumentVersion table
       └─> Document.original_file still = manuscript.docx (working copy)

Day 5: Reviewer adds comments and saves
       └─> Save endpoint: manuscript.docx replaced with commented version

Day 6: Reviewer adds more comments and saves
       └─> Save endpoint: manuscript.docx replaced

Day 10: Author views comments and revises, saves multiple times
        └─> Save endpoint: manuscript.docx replaced each time

Day 12: Author submits revision
        └─> Create Version 2: Snapshot saved to DocumentVersion table
        └─> Document.original_file still = manuscript.docx (working copy)

Day 15: Second round of review...
```

---

## Version History Example

After the above workflow, the system would have:

**DocumentVersion table:**
```
┌────────────────┬─────────────────────┬──────────────────────────┬────────────┐
│ Version Number │ Change Summary      │ Created At               │ File       │
├────────────────┼─────────────────────┼──────────────────────────┼────────────┤
│ 1              │ Initial submission  │ 2025-11-23 10:00:00      │ v1.docx    │
│ 2              │ First revision      │ 2025-11-25 14:30:00      │ v2.docx    │
└────────────────┴─────────────────────┴──────────────────────────┴────────────┘
```

**Document.original_file:**
```
Current working copy: manuscript.docx (latest saved version)
```

---

## Benefits of This Approach

### Storage Efficiency
- Working document is always replaced (only 1 copy)
- Versions only created at important milestones
- Reduces storage costs compared to saving every edit

### Clear Audit Trail
- Version numbers mark submission milestones
- Easy to see: "What was submitted for review?"
- Can compare Version 1 vs Version 2 to see changes

### Flexibility
- Authors can edit freely without creating versions
- Reviewers can add/update comments without versions
- Only intentional submissions create permanent records

---

## Database Schema

### Document Model
```python
class Document(models.Model):
    id = UUIDField
    submission = ForeignKey(Submission)
    title = CharField
    document_type = CharField
    
    # Current working file (gets replaced on save)
    original_file = FileField  # <- This gets replaced
    file_name = CharField
    file_size = PositiveIntegerField
    
    # Edit tracking
    last_edited_by = ForeignKey(Profile)
    last_edited_at = DateTimeField
    
    created_by = ForeignKey(Profile)
    created_at = DateTimeField
```

### DocumentVersion Model
```python
class DocumentVersion(models.Model):
    id = UUIDField
    document = ForeignKey(Document)
    
    # Version info
    version_number = PositiveIntegerField  # Auto-increments
    change_summary = TextField
    
    # Snapshot of file at this version
    file = FileField  # <- Permanent snapshot
    file_name = CharField
    file_size = PositiveIntegerField
    file_hash = CharField  # SHA-256 for integrity
    
    # Version metadata
    is_current = BooleanField  # Latest version flag
    immutable_flag = BooleanField
    
    created_by = ForeignKey(Profile)
    created_at = DateTimeField
```

---

## API Usage Examples

### Saving Progress (Replace File)
```javascript
// User clicks "Save" button in SuperDoc
const handleSave = async () => {
  const docxBlob = await editorRef.current.exportDocx();
  const formData = new FormData();
  formData.append('file', docxBlob, 'manuscript.docx');
  
  await instance.post(
    `/api/v1/submissions/documents/${documentId}/save/`,
    formData
  );
  
  // Old file deleted, new file saved
  alert('Progress saved!');
};
```

### Submitting for Review (Create Version)
```javascript
// User clicks "Submit for Review" button
const handleSubmit = async () => {
  // First, save current work
  const docxBlob = await editorRef.current.exportDocx();
  const saveFormData = new FormData();
  saveFormData.append('file', docxBlob, 'manuscript.docx');
  await instance.post(
    `/api/v1/submissions/documents/${documentId}/save/`,
    saveFormData
  );
  
  // Then create version snapshot
  await instance.post(
    `/api/v1/submissions/documents/${documentId}/create-version/`,
    { change_summary: 'Initial submission for review' }
  );
  
  // Update submission status
  await instance.patch(
    `/api/v1/submissions/${submissionId}/`,
    { status: 'SUBMITTED' }
  );
  
  alert('Manuscript submitted for review!');
};
```

---

## File Deletion Behavior

### On Save
```python
# In superdoc_views.py save_document()
if document.original_file:
    old_file = document.original_file
    document.original_file = docx_file
    old_file.delete(save=False)  # Explicitly delete old file
else:
    document.original_file = docx_file
```

### On Version Creation
```python
# In superdoc_views.py create_version()
# File is COPIED to version, not moved
version = DocumentVersion.objects.create(
    document=document,
    file=document.original_file,  # Copy reference
    # ...
)
# Original document.original_file remains unchanged
```

---

## Future Enhancements

### Possible Features
1. **Auto-versioning:** Automatically create versions at certain intervals
2. **Version comparison:** UI to compare Version 1 vs Version 2
3. **Version rollback:** Restore document to a previous version
4. **Version download:** Download any specific version
5. **Version metadata:** Track which reviewers saw which version

### Not Currently Implemented
- ❌ Auto-save versioning (only manual submission versioning)
- ❌ Diff tracking between versions
- ❌ Version branching
- ❌ Concurrent version editing
