# Document Anonymization for Blind Review

## Overview

This feature implements automatic document anonymization for submissions when the journal is configured for Single Blind or Double Blind peer review processes. Author names are replaced with "**\*\***" to maintain reviewer anonymity.

## Implementation

### 1. Journal Settings Structure

Journals must configure their review process in the `settings` JSONField:

```json
{
  "review_process": {
    "type": "SINGLE_BLIND" // or "DOUBLE_BLIND", "OPEN"
  }
}
```

### 2. Components

#### DocumentAnonymizer Utility (`apps/submissions/utils/document_anonymizer.py`)

The main anonymization logic that:

- Determines if anonymization is needed based on journal settings
- Extracts all author name variations from submission
- Anonymizes document content based on file type

**Supported File Formats:**

- **DOCX**: Full text anonymization including document metadata
- **TXT, MD, TEX, RTF**: Full text anonymization
- **PDF**: Metadata anonymization only (text replacement requires additional libraries)

**Name Variations Detected:**
For an author "John Smith", the system detects and replaces:

- `John Smith`
- `Smith, John`
- `J. Smith`
- `Smith, J.`
- `John S.`
- `J. S.`
- Individual names: `John`, `Smith`
- Display name (if different from full name)

#### DocumentUploadSerializer Integration

The serializer automatically calls the anonymizer before storing files:

```python
# In DocumentUploadSerializer.create()
from apps.submissions.utils import DocumentAnonymizer

anonymized_content, was_anonymized = DocumentAnonymizer.anonymize_file(file, submission)

if was_anonymized:
    # Create new file object with anonymized content
    anonymized_file = InMemoryUploadedFile(...)
    file_to_store = anonymized_file
```

#### DocumentVersion Metadata

The `DocumentVersion` model includes a `metadata` JSONField to track anonymization:

```python
metadata = {
    'anonymized': True  # Indicates if this version was anonymized
}
```

### 3. Workflow

1. Author uploads document via `/api/v1/submissions/{id}/upload_document/`
2. System checks journal's review process type
3. If Single Blind or Double Blind:
   - Extract all author names from `submission.author_contributions`
   - Generate name variations
   - Replace all occurrences with "**\*\***" (case-insensitive)
   - Update document metadata
4. Store anonymized document
5. Record anonymization status in version metadata

### 4. Database Changes

**Migration:** `0009_documentversion_metadata.py`

Added `metadata` field to `DocumentVersion` model:

```python
metadata = models.JSONField(
    default=dict,
    blank=True,
    help_text='Additional version metadata (e.g., anonymization status)'
)
```

### 5. Dependencies

**Required packages:**

- `PyPDF2==3.0.1` - PDF metadata handling
- `python-docx==1.1.2` - DOCX text manipulation

Both are in `requirements.txt` and must be installed.

## Testing

Run the test script to verify anonymization:

```bash
python test_anonymization.py
```

**Test Coverage:**

- Journal settings validation (Single/Double/Open blind)
- Author name extraction with variations
- Text anonymization with pattern matching
- Case-insensitive replacement

## Limitations

1. **PDF Text Anonymization**: PyPDF2 doesn't support text replacement in PDF content. Only metadata is anonymized. Authors should submit DOCX for full anonymization.

2. **Name Detection**: The system uses pattern matching based on registered author names. It may not catch:

   - Nicknames not in the system
   - Institutional affiliations
   - Email addresses (unless they contain the name)

3. **Context-Aware Replacement**: The system does simple text replacement and doesn't understand context. Words that happen to match author names (e.g., common words) will also be replaced.

## Future Enhancements

1. **Enhanced PDF Support**: Integrate libraries like `pdf-redactor` for actual text removal from PDFs
2. **Affiliation Detection**: Anonymize institutional affiliations mentioned in documents
3. **Email Anonymization**: Detect and anonymize email addresses
4. **Smart Context Detection**: Use NLP to avoid replacing false positives
5. **Preview Before Upload**: Allow authors to preview anonymized documents before submission

## Configuration Examples

### Single Blind Review

Authors remain anonymous to reviewers. Documents are anonymized.

```json
{
  "review_process": {
    "type": "SINGLE_BLIND"
  }
}
```

### Double Blind Review

Both authors and reviewers remain anonymous. Documents are anonymized.

```json
{
  "review_process": {
    "type": "DOUBLE_BLIND"
  }
}
```

### Open Review

No anonymization. Author information visible to reviewers.

```json
{
  "review_process": {
    "type": "OPEN"
  }
}
```

## API Behavior

### Document Upload Endpoint

`POST /api/v1/submissions/{id}/upload_document/`

**Request:**

```
POST /api/v1/submissions/123/upload_document/
Content-Type: multipart/form-data

file: research_paper.docx
document_type: manuscript
change_summary: Initial submission
```

**Response (Anonymized):**

```json
{
  "id": 456,
  "document": {
    "id": 789,
    "document_type": "manuscript"
  },
  "version_number": 1,
  "file_name": "research_paper.docx",
  "file_size": 245760,
  "change_summary": "Initial upload (anonymized)",
  "metadata": {
    "anonymized": true
  },
  "created_at": "2025-01-15T10:30:00Z"
}
```

## Troubleshooting

### Documents Not Being Anonymized

1. **Check Journal Settings**: Verify `journal.settings.review_process.type` is set to `SINGLE_BLIND` or `DOUBLE_BLIND`
2. **Check Author Contributions**: Ensure authors are properly registered with `first_name` and `last_name`
3. **Check File Format**: Confirm file is DOCX, TXT, MD, TEX, or RTF (PDF has limitations)
4. **Check Logs**: Look for errors in Django logs with "Error anonymizing" messages

### Names Not Fully Replaced

1. **Check Name Variations**: System uses registered names only
2. **Check Spelling**: Exact spelling matters for matching
3. **Check Special Characters**: Names with special characters may need encoding fixes
4. **Manual Review**: For critical submissions, manually review anonymized documents

## Security Considerations

1. **Original Files**: Original files are overwritten with anonymized versions. Consider backup strategy.
2. **Metadata Leakage**: Document metadata (creation date, software used) may still reveal author identity.
3. **Image Content**: Images in documents are not processed and may contain author information.
4. **Revision History**: DOCX track changes and comments are not removed automatically.

## Recommendations for Authors

To ensure proper anonymization:

1. Use DOCX format instead of PDF
2. Remove track changes and comments before upload
3. Remove headers/footers with names
4. Remove image captions or embedded images with names
5. Anonymize acknowledgments section
6. Use third-person references for self-citations
