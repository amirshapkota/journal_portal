import requests

DOAJ_API_BASE = "https://doaj.org/api/v2/"

# Search journals by query
def doaj_search_journals(query, page=1, page_size=10):
    url = f"{DOAJ_API_BASE}search/journals/"
    params = {"q": query, "page": page, "pageSize": page_size}
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    return resp.json()

# Search articles by query
def doaj_search_articles(query, page=1, page_size=10):
    url = f"{DOAJ_API_BASE}search/articles/"
    params = {"q": query, "page": page, "pageSize": page_size}
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    return resp.json()

# Check if a journal is included in DOAJ by ISSN
def doaj_check_inclusion(issn):
    url = f"{DOAJ_API_BASE}search/journals/"
    params = {"q": f"issn:{issn}"}
    resp = requests.get(url, params=params)
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
