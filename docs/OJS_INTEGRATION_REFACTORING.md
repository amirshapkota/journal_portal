# OJS Integration Refactoring

## Overview

The OJS (Open Journal Systems) integration has been refactored to support **multi-tenant architecture** where each journal can connect to its own OJS instance with independent credentials.

## Changes Made

### 1. Database Models (`apps/integrations/models.py`)

#### OJSMapping Model

- **Removed**: `ojs_instance_url` field (now derived from journal)
- **Added**: Helper methods to get OJS credentials from journal
- **Changed**: Now uses journal's OJS settings instead of global configuration

```python
@property
def journal(self):
    """Get the journal from the submission."""
    return self.local_submission.journal

def get_ojs_credentials(self):
    """Get OJS API credentials from the journal."""
    journal = self.journal
    if not journal.ojs_enabled:
        return None
    return {
        'api_url': journal.ojs_api_url,
        'api_key': journal.ojs_api_key,
        'journal_id': journal.ojs_journal_id
    }
```

### 2. Journal Model (`apps/journals/models.py`)

The Journal model has these OJS fields:

- `ojs_enabled` - Enable/disable OJS connection
- `ojs_api_url` - OJS API base URL
- `ojs_api_key` - API key for authentication
- `ojs_journal_id` - Journal ID in OJS system

**Note:** Automatic background sync is **not supported**. All OJS operations must be triggered manually.

### 3. Utility Functions (`apps/integrations/utils.py`)

All OJS utility functions now require `api_url` and `api_key` parameters:

**Before:**

```python
def ojs_list_submissions():
    url = f"{OJS_API_BASE}/api/v1/submissions"
    headers = {"Authorization": f"Token {OJS_API_KEY}"}
    ...
```

**After:**

```python
def ojs_list_submissions(api_url, api_key, journal_id=None):
    url = f"{api_url}/submissions"
    if journal_id:
        url += f"?journalId={journal_id}"
    headers = get_ojs_headers(api_key)
    ...
```

**Updated Functions:**

- `ojs_list_journals(api_url, api_key)`
- `ojs_list_submissions(api_url, api_key, journal_id=None)`
- `ojs_create_submission(api_url, api_key, data)`
- `ojs_update_submission(api_url, api_key, submission_id, data)`
- `ojs_list_articles(api_url, api_key)`
- `ojs_get_article(api_url, api_key, article_id)`
- `ojs_create_article(api_url, api_key, data)`
- `ojs_update_article(api_url, api_key, article_id, data)`
- `ojs_delete_article(api_url, api_key, article_id)`
- `ojs_list_users(api_url, api_key)`
- `ojs_get_user(api_url, api_key, user_id)`
- `ojs_create_user(api_url, api_key, data)`
- `ojs_update_user(api_url, api_key, user_id, data)`
- `ojs_delete_user(api_url, api_key, user_id)`
- `ojs_list_reviews(api_url, api_key)`
- `ojs_get_review(api_url, api_key, review_id)`
- `ojs_create_review(api_url, api_key, data)`
- `ojs_update_review(api_url, api_key, review_id, data)`
- `ojs_delete_review(api_url, api_key, review_id)`
- `ojs_list_comments(api_url, api_key)`
- `ojs_get_comment(api_url, api_key, comment_id)`
- `ojs_create_comment(api_url, api_key, data)`
- `ojs_update_comment(api_url, api_key, comment_id, data)`
- `ojs_delete_comment(api_url, api_key, comment_id)`

### 4. New API Endpoints (`apps/journals/views.py`)

Added to `JournalViewSet`:

#### Configure OJS Connection

**POST/PUT** `/api/v1/journals/{journal_id}/ojs-connection/`

Configure OJS connection for a journal (Editor-in-Chief or Managing Editor only).

**Request:**

```json
{
  "ojs_api_url": "https://journal.com/index.php/journal/api/v1",
  "ojs_api_key": "your-api-key-here",
  "ojs_journal_id": 1,
  "ojs_enabled": true
}
```

**Response:**

```json
{
  "detail": "OJS connection configured successfully",
  "ojs_enabled": true,
  "ojs_api_url": "https://journal.com/index.php/journal/api/v1",
  "ojs_journal_id": 1
}
```

#### Get OJS Connection Status

**GET** `/api/v1/journals/{journal_id}/ojs-status/`

Get current OJS connection configuration and status.

**Response:**

```json
{
  "ojs_enabled": true,
  "ojs_configured": true,
  "ojs_api_url": "https://journal.com/index.php/journal/api/v1",
  "ojs_journal_id": 1
}
```

#### Test OJS Connection

**POST** `/api/v1/journals/{journal_id}/test-ojs-connection/`

Test the OJS API connection with current credentials.

**Response (Success):**

```json
{
  "success": true,
  "message": "OJS connection successful",
  "journals_found": 3
}
```

**Response (Failure):**

```json
{
  "success": false,
  "message": "OJS connection failed: Connection refused"
}
```

#### Disconnect OJS

**POST** `/api/v1/journals/{journal_id}/disconnect-ojs/`

Disable and clear OJS connection (Editor-in-Chief or Managing Editor only).

**Response:**

```json
{
  "detail": "OJS disconnected successfully"
}
```

## Usage Flow

### 1. Editor Configures OJS Connection

1. Editor logs into the journal management system
2. Navigates to their journal settings
3. Enters OJS connection details:
   - OJS API URL (e.g., `https://myjournal.org/index.php/journal/api/v1`)
   - OJS API Key (obtained from OJS system)
   - OJS Journal ID (numeric ID from OJS)
4. Saves configuration

### 2. Test Connection

Before enabling the connection, editor can test it:

```bash
POST /api/v1/journals/{journal_id}/test-ojs-connection/
```

### 3. Manual Sync to OJS

OJS integration supports **manual sync only**. To sync submissions to OJS:

```python
from apps.integrations.utils import ojs_create_submission
from apps.integrations.models import OJSMapping

# Get journal's OJS credentials
journal = submission.journal
if not journal.ojs_enabled:
    raise Exception("OJS not enabled for this journal")

# Prepare submission data
submission_data = {
    'title': submission.title,
    'abstract': submission.abstract,
    # ... other fields
}

# Create in OJS using journal's credentials
ojs_response = ojs_create_submission(
    api_url=journal.ojs_api_url,
    api_key=journal.ojs_api_key,
    data=submission_data
)

# Create mapping
OJSMapping.objects.create(
    local_submission=submission,
    ojs_submission_id=ojs_response['id'],
    sync_direction='TO_OJS',
    sync_status='COMPLETED'
)
```

## Migration

Run the migrations to update the database schema:

```bash
python manage.py migrate integrations
python manage.py migrate journals
```

This will:

- Remove `ojs_instance_url` field from `OJSMapping`
- Update indexes on `OJSMapping` model
- Remove automatic sync fields (`last_synced_at`, `sync_enabled`, `sync_interval_hours`) from `Journal` model

## Security Considerations

### API Key Storage

Currently, API keys are stored in plain text in the database. **Recommended improvements:**

1. **Encrypt API keys** using Django's encryption utilities
2. **Use environment variables** for sensitive defaults
3. **Implement key rotation** mechanism
4. **Add audit logging** for OJS configuration changes

### Example Encryption Implementation:

```python
import base64
from cryptography.fernet import Fernet
from django.conf import settings

def encrypt_api_key(key):
    fernet_key = base64.urlsafe_b64encode(
        settings.SECRET_KEY[:32].encode().ljust(32, b'0')[:32]
    )
    f = Fernet(fernet_key)
    return f.encrypt(key.encode())

def decrypt_api_key(encrypted_key):
    fernet_key = base64.urlsafe_b64encode(
        settings.SECRET_KEY[:32].encode().ljust(32, b'0')[:32]
    )
    f = Fernet(fernet_key)
    return f.decrypt(encrypted_key).decode()
```

## Benefits of Refactoring

1. **Multi-Tenancy**: Each journal can connect to different OJS instances
2. **Scalability**: Supports journals using different OJS platforms
3. **Flexibility**: Journals can enable/disable OJS independently
4. **Security**: Credentials isolated per journal
5. **Maintainability**: Cleaner separation of concerns
6. **Control**: Journal editors manage their own integrations
7. **Manual Control**: No automatic background sync - all OJS operations are explicit and controlled

## Implementation Notes

### Manual Sync Only

The OJS integration is designed for **manual synchronization only**. There is no automatic background sync functionality. This means:

- Editors must explicitly trigger OJS operations (create, update, sync submissions)
- No background Celery tasks or scheduled jobs for OJS sync
- Full control over when data is sent to/from OJS
- Easier to debug and monitor OJS interactions
- No risk of automatic sync conflicts or failures

### Future Enhancements

1. ✅ Update `OJSMapping` model
2. ✅ Refactor utility functions to accept credentials
3. ✅ Add journal OJS management endpoints
4. ✅ Create migrations
5. ✅ Remove automatic sync functionality
6. ⏳ Update existing views to use new utility function signatures
7. ⏳ Add API key encryption
8. ⏳ Add comprehensive error handling and retry logic
9. ⏳ Create admin interface for OJS configuration
10. ⏳ Add detailed audit logging
11. ⏳ Add manual sync endpoints for submissions
