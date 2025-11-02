# How to Connect Your Platform to OJS Systems

## Overview
Your Django Journal Portal can connect to multiple Open Journal Systems (OJS) installations. Each journal can have its own independent OJS instance.

---

## Step 1: Get OJS API Credentials

### In Your OJS Installation:

1. **Login to OJS** as Journal Manager or Administrator
2. **Navigate to API Settings:**
   - OJS 3.x: `Settings → Website → Plugins`
   - Enable **REST API Plugin** (if not already enabled)
   
3. **Generate API Key:**
   - Go to: `Users & Roles → [Your User] → API Key`
   - Click **Enable API Access** or **Generate API Key**
   - **Copy the API Key** (looks like: `eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...`)

4. **Get Journal Information:**
   - **Journal Path**: Found in journal URL (e.g., `/index.php/jair/`)
   - **Journal ID**: Found in journal settings (usually a number)
   - **API Base URL**: `https://your-domain.com/index.php/journal-path/api/v1`

### Example OJS URLs:
```
OJS Installation: https://journals.university.edu/ojs/
Journal Path: /index.php/medical-journal/
API Base URL: https://journals.university.edu/ojs/index.php/medical-journal/api/v1
```

---

## Step 2: Add OJS Connection in Django

### Method 1: Django Admin Interface (Recommended)

1. **Login to Django Admin:**
   ```
   http://localhost:8000/admin/
   ```

2. **Navigate to Journals:**
   ```
   Admin → Journals → Add Journal
   ```

3. **Fill in Basic Information:**
   - **Title**: `Journal of Medical Research`
   - **Short Name**: `jmr`
   - **ISSN**: `1234-5678`
   - **Publisher**: `University Press`

4. **Configure OJS Integration:**
   - ✅ **OJS Enabled**: Check this box
   - **OJS API URL**: `https://journals.university.edu/ojs/index.php/jmr/api/v1`
   - **OJS API Key**: `eyJ0eXAiOiJKV1QiLCJhbGc...` (paste your key)
   - **OJS Journal ID**: `1` (or the ID from OJS)
   - ✅ **Sync Enabled**: Check this box
   - **Sync Interval Hours**: `1` (sync every hour)

5. **Save** the journal

### Method 2: Django Shell (For Developers)

```bash
python manage.py shell
```

```python
from apps.journals.models import Journal

# Create a new journal with OJS connection
journal = Journal.objects.create(
    title="Journal of Medical Research",
    short_name="jmr",
    issn_online="1234-5678",
    publisher="University Medical Press",
    
    # OJS Connection Settings
    ojs_enabled=True,
    ojs_api_url="https://journals.university.edu/ojs/index.php/jmr/api/v1",
    ojs_api_key="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",  # Your actual API key
    ojs_journal_id=1,
    
    # Sync Settings
    sync_enabled=True,
    sync_interval_hours=1,  # Sync every hour
    
    is_active=True
)

print(f"✓ Journal created: {journal.title}")
print(f"  OJS URL: {journal.ojs_api_url}")
```

### Method 3: Programmatically via API

```python
import requests

# Create journal via your Django REST API
response = requests.post(
    "http://localhost:8000/api/journals/",
    headers={"Authorization": "Bearer YOUR_DJANGO_TOKEN"},
    json={
        "title": "Journal of Medical Research",
        "short_name": "jmr",
        "issn_online": "1234-5678",
        "ojs_enabled": True,
        "ojs_api_url": "https://journals.university.edu/ojs/index.php/jmr/api/v1",
        "ojs_api_key": "eyJ0eXAiOiJKV1QiLCJhbGc...",
        "ojs_journal_id": 1,
        "sync_enabled": True,
        "sync_interval_hours": 1
    }
)
```

---

## Step 3: Test the Connection

### Test 1: Manual Sync Test

```bash
# Test sync for specific journal
python manage.py sync_ojs --journal "jmr" --type submissions

# Expected output:
# Syncing journal: Journal of Medical Research
# ✓ Synced X submissions for Journal of Medical Research
# ✓ Sync command completed
```

### Test 2: Health Check

```bash
python manage.py sync_ojs --health-check

# Expected output:
# Journals checked: 1
# Issues found: 0
# ✓ All journals healthy
```

### Test 3: Check in Django Shell

```python
from apps.journals.models import Journal

journal = Journal.objects.get(short_name="jmr")

# Check OJS configuration
print(f"OJS Enabled: {journal.ojs_enabled}")
print(f"OJS URL: {journal.ojs_api_url}")
print(f"Has API Key: {bool(journal.ojs_api_key)}")
print(f"Last Synced: {journal.last_synced_at}")

# Test API connection (helper function)
from apps.integrations.tasks import fetch_from_journal_ojs

result = fetch_from_journal_ojs(
    journal, 
    endpoint='/submissions',
    params={'count': 1}
)

if result:
    print("✓ Connection successful!")
    print(f"  Found {len(result.get('items', []))} submissions")
else:
    print("✗ Connection failed - check credentials")
```

---

## Step 4: Connect Multiple OJS Systems

You can connect multiple journals, each with different OJS installations:

```python
from apps.journals.models import Journal

# Journal 1: Medical Journal at University A
journal1 = Journal.objects.create(
    title="Medical Research Journal",
    short_name="mrj",
    ojs_enabled=True,
    ojs_api_url="https://ojs.university-a.edu/index.php/mrj/api/v1",
    ojs_api_key="key_for_university_a_journal",
    ojs_journal_id=1,
    sync_enabled=True,
    is_active=True
)

# Journal 2: AI Journal at University B (Different OJS installation)
journal2 = Journal.objects.create(
    title="AI Research Quarterly",
    short_name="airq",
    ojs_enabled=True,
    ojs_api_url="https://journals.university-b.org/ojs/index.php/airq/api/v1",
    ojs_api_key="different_key_for_university_b",
    ojs_journal_id=5,
    sync_enabled=True,
    is_active=True
)

# Journal 3: Physics Journal (No OJS - standalone)
journal3 = Journal.objects.create(
    title="Physics Review",
    short_name="pr",
    ojs_enabled=False,  # Not using OJS
    is_active=True
)
```

---

## Common OJS API Endpoints

Your platform will connect to these OJS API endpoints:

| Endpoint | Purpose | Django Task |
|----------|---------|-------------|
| `/submissions` | Get submissions | `sync_journal_submissions()` |
| `/users` | Get users/authors | `sync_journal_users()` |
| `/issues` | Get published issues | `sync_journal_issues()` |
| `/submissions/{id}` | Get submission details (includes reviews) | `sync_journal_reviews()` |
| `POST /submissions` | Create new submission | `push_submission_to_ojs()` |

---

## Troubleshooting Connection Issues

### Issue 1: "Connection Failed" or "Unauthorized"

**Check:**
1. API Key is correct (no extra spaces)
2. API URL ends with `/api/v1` (not `/api/v1/`)
3. REST API plugin is enabled in OJS
4. User account has Journal Manager permissions
5. OJS is accessible from your server (not behind firewall)

**Test with curl:**
```bash
curl -X GET "https://journals.university.edu/ojs/index.php/jmr/api/v1/submissions" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json"
```

### Issue 2: "Journal Not Found"

**Check:**
- `ojs_journal_id` matches the journal ID in OJS
- Journal path in URL is correct

### Issue 3: "No Data Synced"

**Check:**
- OJS journal actually has submissions/users
- User has permission to access the data in OJS
- Check Django logs: `tail -f logs/django.log`

### Issue 4: "SSL Certificate Error"

**For development/testing only:**
```python
# In tasks.py (NOT for production)
response = requests.get(url, headers=headers, params=params, timeout=30, verify=False)
```

---

## Security Best Practices

### 1. Store API Keys Securely

**Don't:** Hardcode API keys in code
```python
# ❌ BAD - Don't do this
ojs_api_key = "eyJ0eXAiOiJKV1QiLCJhbGc..."
```

**Do:** Store in environment variables or database
```python
# ✅ GOOD - Store in database (encrypted) or env vars
journal.ojs_api_key = os.getenv('OJS_API_KEY_JOURNAL1')
```

### 2. Use HTTPS Only
```python
# Always use HTTPS for OJS connections
ojs_api_url = "https://journals.edu/ojs/api/v1"  # ✅ HTTPS
# NOT: "http://journals.edu/ojs/api/v1"  # ❌ HTTP
```

### 3. Rotate API Keys Regularly
- Generate new API keys every 3-6 months
- Update in Django admin when changed in OJS

### 4. Use Restricted API Keys
- In OJS, create API keys with minimal required permissions
- Use different API keys for different journals

---

## Next Steps

1. ✅ Obtain API credentials from OJS
2. ✅ Add journal in Django admin with OJS settings
3. ✅ Test connection with manual sync
4. ✅ Enable automatic background sync
5. ✅ Monitor sync logs and health checks

For multiple journals, repeat steps 1-3 for each OJS installation.

---

## Example: Complete Setup Flow

```bash
# 1. Get OJS credentials (manually from OJS admin panel)
# 2. Create journal in Django
python manage.py shell
```

```python
from apps.journals.models import Journal

journal = Journal.objects.create(
    title="Medical AI Journal",
    short_name="maj",
    ojs_enabled=True,
    ojs_api_url="https://ojs.medical-ai.org/index.php/maj/api/v1",
    ojs_api_key="your-actual-api-key-from-ojs",
    ojs_journal_id=1,
    sync_enabled=True,
    sync_interval_hours=1,
    is_active=True
)
exit()
```

```bash
# 3. Test the connection
python manage.py sync_ojs --journal "maj" --type submissions

# 4. If successful, start automatic sync
python manage.py sync_ojs --async  # Run in background

# 5. Monitor sync status
python manage.py sync_ojs --health-check
```

Done! Your Django platform is now connected to OJS and syncing data automatically.
