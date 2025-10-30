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

# OJS API base URL and key from settings
OJS_API_BASE = getattr(settings, 'OJS_API_BASE_URL', '')
OJS_API_KEY = getattr(settings, 'OJS_API_KEY', '')

# --- OJS → Django ---
def ojs_list_journals():
    url = f"{OJS_API_BASE}/api/v1/journals"
    headers = {"Authorization": f"Token {OJS_API_KEY}"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()

def ojs_list_submissions():
    url = f"{OJS_API_BASE}/api/v1/submissions"
    headers = {"Authorization": f"Token {OJS_API_KEY}"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()

# --- Django → OJS ---
def ojs_create_submission(data):
    url = f"{OJS_API_BASE}/api/v1/submissions"
    headers = {"Authorization": f"Token {OJS_API_KEY}", "Content-Type": "application/json"}
    resp = requests.post(url, json=data, headers=headers)
    resp.raise_for_status()
    return resp.json()

def ojs_update_submission(submission_id, data):
    url = f"{OJS_API_BASE}/api/v1/submissions/{submission_id}"
    headers = {"Authorization": f"Token {OJS_API_KEY}", "Content-Type": "application/json"}
    resp = requests.put(url, json=data, headers=headers)
    resp.raise_for_status()
    return resp.json()

# --- OJS Article (Submission) Sync Utilities ---

def ojs_list_articles():
    url = f"{OJS_API_BASE}/api/v1/articles"
    headers = {"Authorization": f"Token {OJS_API_KEY}"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()

def ojs_get_article(article_id):
    url = f"{OJS_API_BASE}/api/v1/articles/{article_id}"
    headers = {"Authorization": f"Token {OJS_API_KEY}"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()

def ojs_create_article(data):
    url = f"{OJS_API_BASE}/api/v1/articles"
    headers = {"Authorization": f"Token {OJS_API_KEY}", "Content-Type": "application/json"}
    resp = requests.post(url, json=data, headers=headers)
    resp.raise_for_status()
    return resp.json()

def ojs_update_article(article_id, data):
    url = f"{OJS_API_BASE}/api/v1/articles/{article_id}"
    headers = {"Authorization": f"Token {OJS_API_KEY}", "Content-Type": "application/json"}
    resp = requests.put(url, json=data, headers=headers)
    resp.raise_for_status()
    return resp.json()

def ojs_delete_article(article_id):
    url = f"{OJS_API_BASE}/api/v1/articles/{article_id}"
    headers = {"Authorization": f"Token {OJS_API_KEY}"}
    resp = requests.delete(url, headers=headers)
    resp.raise_for_status()
    return resp.status_code == 204

# --- OJS User Sync Utilities ---

def ojs_list_users():
    url = f"{OJS_API_BASE}/api/v1/users"
    headers = {"Authorization": f"Token {OJS_API_KEY}"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()

def ojs_get_user(user_id):
    url = f"{OJS_API_BASE}/api/v1/users/{user_id}"
    headers = {"Authorization": f"Token {OJS_API_KEY}"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()

def ojs_create_user(data):
    url = f"{OJS_API_BASE}/api/v1/users"
    headers = {"Authorization": f"Token {OJS_API_KEY}", "Content-Type": "application/json"}
    resp = requests.post(url, json=data, headers=headers)
    resp.raise_for_status()
    return resp.json()

def ojs_update_user(user_id, data):
    url = f"{OJS_API_BASE}/api/v1/users/{user_id}"
    headers = {"Authorization": f"Token {OJS_API_KEY}", "Content-Type": "application/json"}
    resp = requests.put(url, json=data, headers=headers)
    resp.raise_for_status()
    return resp.json()

def ojs_delete_user(user_id):
    url = f"{OJS_API_BASE}/api/v1/users/{user_id}"
    headers = {"Authorization": f"Token {OJS_API_KEY}"}
    resp = requests.delete(url, headers=headers)
    resp.raise_for_status()
    return resp.status_code == 204

# --- OJS Review Sync Utilities ---

def ojs_list_reviews():
    url = f"{OJS_API_BASE}/api/v1/reviews"
    headers = {"Authorization": f"Token {OJS_API_KEY}"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()

def ojs_get_review(review_id):
    url = f"{OJS_API_BASE}/api/v1/reviews/{review_id}"
    headers = {"Authorization": f"Token {OJS_API_KEY}"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()

def ojs_create_review(data):
    url = f"{OJS_API_BASE}/api/v1/reviews"
    headers = {"Authorization": f"Token {OJS_API_KEY}", "Content-Type": "application/json"}
    resp = requests.post(url, json=data, headers=headers)
    resp.raise_for_status()
    return resp.json()

def ojs_update_review(review_id, data):
    url = f"{OJS_API_BASE}/api/v1/reviews/{review_id}"
    headers = {"Authorization": f"Token {OJS_API_KEY}", "Content-Type": "application/json"}
    resp = requests.put(url, json=data, headers=headers)
    resp.raise_for_status()
    return resp.json()

def ojs_delete_review(review_id):
    url = f"{OJS_API_BASE}/api/v1/reviews/{review_id}"
    headers = {"Authorization": f"Token {OJS_API_KEY}"}
    resp = requests.delete(url, headers=headers)
    resp.raise_for_status()
    return resp.status_code == 204

# --- OJS Comment Sync Utilities ---

def ojs_list_comments():
    url = f"{OJS_API_BASE}/api/v1/comments"
    headers = {"Authorization": f"Token {OJS_API_KEY}"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()

def ojs_get_comment(comment_id):
    url = f"{OJS_API_BASE}/api/v1/comments/{comment_id}"
    headers = {"Authorization": f"Token {OJS_API_KEY}"}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()

def ojs_create_comment(data):
    url = f"{OJS_API_BASE}/api/v1/comments"
    headers = {"Authorization": f"Token {OJS_API_KEY}", "Content-Type": "application/json"}
    resp = requests.post(url, json=data, headers=headers)
    resp.raise_for_status()
    return resp.json()

def ojs_update_comment(comment_id, data):
    url = f"{OJS_API_BASE}/api/v1/comments/{comment_id}"
    headers = {"Authorization": f"Token {OJS_API_KEY}", "Content-Type": "application/json"}
    resp = requests.put(url, json=data, headers=headers)
    resp.raise_for_status()
    return resp.json()

def ojs_delete_comment(comment_id):
    url = f"{OJS_API_BASE}/api/v1/comments/{comment_id}"
    headers = {"Authorization": f"Token {OJS_API_KEY}"}
    resp = requests.delete(url, headers=headers)
    resp.raise_for_status()
    return resp.status_code == 204
