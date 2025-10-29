"""
ROR (Research Organization Registry) API client utilities.
Docs: https://ror.readme.io/reference/search
OpenAlex API client utilities (extended).
Docs: https://docs.openalex.org/api
"""
import requests

ROR_API_BASE = "https://api.ror.org/organizations"
OPENALEX_BASE = "https://api.openalex.org"

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
