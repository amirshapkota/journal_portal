"""
ROR (Research Organization Registry) API client utilities.
Docs: https://ror.readme.io/reference/search
OpenAlex API client utilities (extended).
Docs: https://docs.openalex.org/api
"""
import requests
from django.conf import settings

ROR_API_BASE = "https://api.ror.org/organizations"
OPENALEX_BASE = "https://api.openalex.org"
DOAJ_API_BASE = "https://doaj.org/api/v2/"

def search_ror_organizations(query, page=1):
    """
    Search ROR for organizations by name, keyword, or ROR ID.
    Returns JSON response from ROR API.
    """
    params = {
        "query": query,
        "page": page,
    }
    resp = requests.get(ROR_API_BASE, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()

def get_ror_organization(ror_id):
    """
    Retrieve a single organization by ROR ID (e.g., ror.org/05hj8vx45)
    """
    url = f"{ROR_API_BASE}/{ror_id}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()

def search_openalex_authors(query, page=1, per_page=10):
    """
    Search OpenAlex for authors by name or keyword.
    Returns JSON response from OpenAlex API.
    """
    params = {
        "search": query,
        "page": page,
        "per_page": per_page,
    }
    resp = requests.get(f"{OPENALEX_BASE}/authors", params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()

def get_openalex_author(author_id):
    """
    Retrieve a single author by OpenAlex ID (e.g., A1969205032)
    """
    url = f"{OPENALEX_BASE}/authors/{author_id}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()

def search_openalex_authors(query, page=1, per_page=10):
    params = {"search": query, "page": page, "per_page": per_page}
    resp = requests.get(f"{OPENALEX_BASE}/authors", params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()

def get_openalex_author(author_id):
    url = f"{OPENALEX_BASE}/authors/{author_id}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()

def search_openalex_institutions(query, page=1, per_page=10):
    params = {"search": query, "page": page, "per_page": per_page}
    resp = requests.get(f"{OPENALEX_BASE}/institutions", params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()

def get_openalex_institution(inst_id):
    url = f"{OPENALEX_BASE}/institutions/{inst_id}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()

def search_openalex_works(query, page=1, per_page=10):
    params = {"search": query, "page": page, "per_page": per_page}
    resp = requests.get(f"{OPENALEX_BASE}/works", params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()

def get_openalex_work(work_id):
    url = f"{OPENALEX_BASE}/works/{work_id}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()

# DOAJ v2 search uses /search/journals/{query} and pagination via 'page' and 'pageSize' params
def doaj_search_journals(query, page=1, page_size=10):
    url = f"{DOAJ_API_BASE}search/journals/{query}"
    params = {"page": page, "pageSize": page_size}
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    data = resp.json()
    # v2 returns 'results' as a list, 'total' as int
    return {
        'results': data.get('results', []),
        'total': data.get('total', len(data.get('results', [])))
    }

# Search articles by query

def doaj_search_articles(query, page=1, page_size=10):
    url = f"{DOAJ_API_BASE}search/articles/{query}"
    params = {"page": page, "pageSize": page_size}
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    data = resp.json()
    return {
        'results': data.get('results', []),
        'total': data.get('total', len(data.get('results', [])))
    }

# Check if a journal is included in DOAJ by ISSN

def doaj_check_inclusion(issn):
    # v2: /search/journals/issn:{issn}
    url = f"{DOAJ_API_BASE}search/journals/issn:{issn}"
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    return data.get('total', 0) > 0

# Fetch journal metadata by DOAJ journal id
def doaj_fetch_journal_metadata(journal_id):
    url = f"{DOAJ_API_BASE}journals/{journal_id}"
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json()

# Fetch article metadata by DOAJ article id
def doaj_fetch_article_metadata(article_id):
    url = f"{DOAJ_API_BASE}articles/{article_id}"
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json()

# Submit or update data (requires API key, not implemented here)
def doaj_submit_or_update(data, api_key, endpoint="journals", method="POST", object_id=None):
    url = f"{DOAJ_API_BASE}{endpoint}/"
    if object_id:
        url += f"{object_id}"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    if method == "POST":
        resp = requests.post(url, json=data, headers=headers)
    else:
        resp = requests.put(url, json=data, headers=headers)
    resp.raise_for_status()
    return resp.json()

# OJS API utilities - now journal-specific
def get_ojs_headers(api_key):
    """Generate headers for OJS API requests."""
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

# --- OJS → Django ---
def ojs_list_journals(api_url, api_key):
    """List journals from a specific OJS instance."""
    url = f"{api_url}/journals"
    headers = get_ojs_headers(api_key)
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()

def ojs_list_submissions(api_url, api_key, journal_id=None):
    """List submissions from OJS instance, optionally filtered by journal."""
    url = f"{api_url}/submissions"
    if journal_id:
        url += f"?journalId={journal_id}"
    headers = get_ojs_headers(api_key)
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()

# --- Django → OJS ---
def ojs_create_submission(api_url, api_key, data):
    """Create submission in OJS instance."""
    url = f"{api_url}/submissions"
    headers = get_ojs_headers(api_key)
    resp = requests.post(url, json=data, headers=headers)
    resp.raise_for_status()
    return resp.json()

def ojs_update_submission(api_url, api_key, submission_id, data):
    """Update submission in OJS instance."""
    url = f"{api_url}/submissions/{submission_id}"
    headers = get_ojs_headers(api_key)
    resp = requests.put(url, json=data, headers=headers)
    resp.raise_for_status()
    return resp.json()

# --- OJS Article (Submission) Sync Utilities ---

def ojs_list_articles(api_url, api_key):
    """List articles from OJS instance."""
    url = f"{api_url}/articles"
    headers = get_ojs_headers(api_key)
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()

def ojs_get_article(api_url, api_key, article_id):
    """Get article from OJS instance."""
    url = f"{api_url}/articles/{article_id}"
    headers = get_ojs_headers(api_key)
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()

def ojs_create_article(api_url, api_key, data):
    """Create article in OJS instance."""
    url = f"{api_url}/articles"
    headers = get_ojs_headers(api_key)
    resp = requests.post(url, json=data, headers=headers)
    resp.raise_for_status()
    return resp.json()

def ojs_update_article(api_url, api_key, article_id, data):
    """Update article in OJS instance."""
    url = f"{api_url}/articles/{article_id}"
    headers = get_ojs_headers(api_key)
    resp = requests.put(url, json=data, headers=headers)
    resp.raise_for_status()
    return resp.json()

def ojs_delete_article(api_url, api_key, article_id):
    """Delete article from OJS instance."""
    url = f"{api_url}/articles/{article_id}"
    headers = get_ojs_headers(api_key)
    resp = requests.delete(url, headers=headers)
    resp.raise_for_status()
    return resp.status_code == 204

# --- OJS User Sync Utilities ---

def ojs_list_users(api_url, api_key):
    """List users from OJS instance."""
    url = f"{api_url}/users"
    headers = get_ojs_headers(api_key)
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()

def ojs_get_user(api_url, api_key, user_id):
    """Get user from OJS instance."""
    url = f"{api_url}/users/{user_id}"
    headers = get_ojs_headers(api_key)
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()

def ojs_create_user(api_url, api_key, data):
    """Create user in OJS instance."""
    url = f"{api_url}/users"
    headers = get_ojs_headers(api_key)
    resp = requests.post(url, json=data, headers=headers)
    resp.raise_for_status()
    return resp.json()

def ojs_update_user(api_url, api_key, user_id, data):
    """Update user in OJS instance."""
    url = f"{api_url}/users/{user_id}"
    headers = get_ojs_headers(api_key)
    resp = requests.put(url, json=data, headers=headers)
    resp.raise_for_status()
    return resp.json()

def ojs_delete_user(api_url, api_key, user_id):
    """Delete user from OJS instance."""
    url = f"{api_url}/users/{user_id}"
    headers = get_ojs_headers(api_key)
    resp = requests.delete(url, headers=headers)
    resp.raise_for_status()
    return resp.status_code == 204

# --- OJS Review Sync Utilities ---

def ojs_list_reviews(api_url, api_key):
    """List reviews from OJS instance."""
    url = f"{api_url}/reviews"
    headers = get_ojs_headers(api_key)
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()

def ojs_get_review(api_url, api_key, review_id):
    """Get review from OJS instance."""
    url = f"{api_url}/reviews/{review_id}"
    headers = get_ojs_headers(api_key)
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()

def ojs_create_review(api_url, api_key, data):
    """Create review in OJS instance."""
    url = f"{api_url}/reviews"
    headers = get_ojs_headers(api_key)
    resp = requests.post(url, json=data, headers=headers)
    resp.raise_for_status()
    return resp.json()

def ojs_update_review(api_url, api_key, review_id, data):
    """Update review in OJS instance."""
    url = f"{api_url}/reviews/{review_id}"
    headers = get_ojs_headers(api_key)
    resp = requests.put(url, json=data, headers=headers)
    resp.raise_for_status()
    return resp.json()

def ojs_delete_review(api_url, api_key, review_id):
    """Delete review from OJS instance."""
    url = f"{api_url}/reviews/{review_id}"
    headers = get_ojs_headers(api_key)
    resp = requests.delete(url, headers=headers)
    resp.raise_for_status()
    return resp.status_code == 204

# --- OJS Comment Sync Utilities ---

def ojs_list_comments(api_url, api_key):
    """List comments from OJS instance."""
    url = f"{api_url}/comments"
    headers = get_ojs_headers(api_key)
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()

def ojs_get_comment(api_url, api_key, comment_id):
    """Get comment from OJS instance."""
    url = f"{api_url}/comments/{comment_id}"
    headers = get_ojs_headers(api_key)
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()

def ojs_create_comment(api_url, api_key, data):
    """Create comment in OJS instance."""
    url = f"{api_url}/comments"
    headers = get_ojs_headers(api_key)
    resp = requests.post(url, json=data, headers=headers)
    resp.raise_for_status()
    return resp.json()

def ojs_update_comment(api_url, api_key, comment_id, data):
    """Update comment in OJS instance."""
    url = f"{api_url}/comments/{comment_id}"
    headers = get_ojs_headers(api_key)
    resp = requests.put(url, json=data, headers=headers)
    resp.raise_for_status()
    return resp.json()

def ojs_delete_comment(api_url, api_key, comment_id):
    """Delete comment from OJS instance."""
    url = f"{api_url}/comments/{comment_id}"
    headers = get_ojs_headers(api_key)
    resp = requests.delete(url, headers=headers)
    resp.raise_for_status()
    return resp.status_code == 204

# Sentry integration utilities
SENTRY_AUTH_TOKEN = getattr(settings, 'SENTRY_AUTH_TOKEN', '')

# --- Sentry API Utilities ---
from decouple import config

SENTRY_API_BASE = config('SENTRY_API_BASE_URL', default='')
SENTRY_AUTH_TOKEN = config('SENTRY_AUTH_TOKEN', default='')
SENTRY_ORG_SLUG = config('SENTRY_ORG_SLUG', default='')

def _get_sentry_headers():
    """Get common headers for Sentry API requests."""
    return {
        "Authorization": f"Bearer {SENTRY_AUTH_TOKEN}",
        "Content-Type": "application/json"
    }

def sanitize_sentry_data(data):
    """
    Sanitize sensitive data from Sentry responses.
    Removes or masks PII and sensitive information.
    """
    if isinstance(data, dict):
        sanitized = {}
        sensitive_keys = ['email', 'ip_address', 'user', 'username', 'password', 'token', 'secret', 'api_key']
        
        for key, value in data.items():
            # Mask sensitive keys
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                if isinstance(value, str) and value:
                    # Mask email addresses
                    if '@' in value:
                        sanitized[key] = '***@***.***'
                    # Mask IP addresses
                    elif key.lower() == 'ip_address':
                        sanitized[key] = '***.***.***.***'
                    else:
                        sanitized[key] = '***REDACTED***'
                elif isinstance(value, dict):
                    sanitized[key] = sanitize_sentry_data(value)
                else:
                    sanitized[key] = '***REDACTED***'
            else:
                sanitized[key] = sanitize_sentry_data(value)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_sentry_data(item) for item in data]
    else:
        return data

def sentry_fetch_issues(project_slug, query=None, status='unresolved', limit=25, cursor=None):
    """
    Fetch issues from a Sentry project.
    
    Args:
        project_slug: The project slug
        query: Search query string
        status: Issue status filter (unresolved, resolved, ignored)
        limit: Number of results to return (max 100)
        cursor: Pagination cursor
    
    Returns:
        Dict with 'results' and pagination info
    """
    url = f"{SENTRY_API_BASE}/projects/{SENTRY_ORG_SLUG}/{project_slug}/issues/"
    params = {
        'statsPeriod': '14d',
        'limit': min(limit, 100),
    }
    
    if query:
        params['query'] = f"{query} is:{status}"
    else:
        params['query'] = f"is:{status}"
    
    if cursor:
        params['cursor'] = cursor
    
    resp = requests.get(url, headers=_get_sentry_headers(), params=params, timeout=30)
    resp.raise_for_status()
    
    # Get pagination info from Link header
    link_header = resp.headers.get('Link', '')
    next_cursor = None
    if 'rel="next"' in link_header:
        # Parse cursor from Link header
        import re
        match = re.search(r'cursor=([^&>]+).*rel="next"', link_header)
        if match:
            next_cursor = match.group(1)
    
    data = resp.json()
    sanitized_data = sanitize_sentry_data(data)
    
    return {
        'results': sanitized_data,
        'next_cursor': next_cursor,
        'count': len(sanitized_data)
    }

def sentry_fetch_issue_detail(issue_id):
    """
    Fetch detailed information about a specific issue.
    
    Args:
        issue_id: The Sentry issue ID
    
    Returns:
        Dict with issue details
    """
    url = f"{SENTRY_API_BASE}/issues/{issue_id}/"
    resp = requests.get(url, headers=_get_sentry_headers(), timeout=30)
    resp.raise_for_status()
    
    data = resp.json()
    return sanitize_sentry_data(data)

def sentry_fetch_issue_events(issue_id, limit=25, cursor=None):
    """
    Fetch events for a specific issue.
    
    Args:
        issue_id: The Sentry issue ID
        limit: Number of results to return (max 100)
        cursor: Pagination cursor
    
    Returns:
        Dict with 'results' and pagination info
    """
    url = f"{SENTRY_API_BASE}/issues/{issue_id}/events/"
    params = {
        'limit': min(limit, 100),
    }
    
    if cursor:
        params['cursor'] = cursor
    
    resp = requests.get(url, headers=_get_sentry_headers(), params=params, timeout=30)
    resp.raise_for_status()
    
    # Get pagination info from Link header
    link_header = resp.headers.get('Link', '')
    next_cursor = None
    if 'rel="next"' in link_header:
        import re
        match = re.search(r'cursor=([^&>]+).*rel="next"', link_header)
        if match:
            next_cursor = match.group(1)
    
    data = resp.json()
    sanitized_data = sanitize_sentry_data(data)
    
    return {
        'results': sanitized_data,
        'next_cursor': next_cursor,
        'count': len(sanitized_data)
    }

def sentry_fetch_event_detail(event_id, project_slug):
    """
    Fetch detailed information about a specific event.
    
    Args:
        event_id: The Sentry event ID
        project_slug: The project slug
    
    Returns:
        Dict with event details
    """
    url = f"{SENTRY_API_BASE}/projects/{SENTRY_ORG_SLUG}/{project_slug}/events/{event_id}/"
    resp = requests.get(url, headers=_get_sentry_headers(), timeout=30)
    resp.raise_for_status()
    
    data = resp.json()
    return sanitize_sentry_data(data)

def sentry_get_project_stats(project_slug, stat='received', since=None, until=None, resolution='1h'):
    """
    Get project statistics.
    
    Args:
        project_slug: The project slug
        stat: Stat to retrieve (received, rejected, blacklisted, generated)
        since: Start timestamp (Unix timestamp)
        until: End timestamp (Unix timestamp)
        resolution: Time resolution (1h, 1d, 1w, 1m)
    
    Returns:
        Dict with statistics data
    """
    url = f"{SENTRY_API_BASE}/projects/{SENTRY_ORG_SLUG}/{project_slug}/stats/"
    
    from datetime import datetime, timedelta
    import time
    
    # Default to last 24 hours if not specified
    if not until:
        until = int(time.time())
    if not since:
        since = int(time.time() - 86400)  # 24 hours ago
    
    params = {
        'stat': stat,
        'since': since,
        'until': until,
        'resolution': resolution,
    }
    
    resp = requests.get(url, headers=_get_sentry_headers(), params=params, timeout=30)
    resp.raise_for_status()
    
    return resp.json()

def sentry_list_projects():
    """
    List all projects in the organization.
    
    Returns:
        List of project dicts
    """
    url = f"{SENTRY_API_BASE}/organizations/{SENTRY_ORG_SLUG}/projects/"
    resp = requests.get(url, headers=_get_sentry_headers(), timeout=30)
    resp.raise_for_status()
    
    data = resp.json()
    return sanitize_sentry_data(data)
