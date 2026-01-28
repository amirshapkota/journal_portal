# Public Publications Endpoint - Quick Start Guide

## Overview

A new public API endpoint has been created in the `common` app that provides read-only access to published submissions. This endpoint allows anyone (without authentication) to browse and search published articles with complete details.

## What Was Implemented

### 1. New API Endpoint

**Base URL:** `/api/common/publications/`

**Features:**

- Public access (no authentication required)
- List all published articles with pagination
- Search by title, abstract, keywords, DOI
- Filter by journal, section, category, research type, area, date
- Order by submission date, title, etc.
- Download published documents
- Complete metadata including authors, journal info, taxonomy

### 2. Files Modified

```
apps/common/
├── serializers.py  ← Added PublicationDetailSerializer and related serializers
├── views.py        ← Added PublicPublicationViewSet
└── urls.py         ← Registered new endpoint

docs/
├── PUBLIC_PUBLICATIONS_API.md            ← Complete API documentation
└── PUBLIC_PUBLICATIONS_IMPLEMENTATION.md  ← Implementation details

Root:
├── test_public_api.py           ← API testing script
└── create_test_publications.py  ← Test data creation script
```

## Quick Start

### Step 1: Create Test Data (Optional)

If you don't have published submissions yet, create some test data:

```bash
# In Django shell
python manage.py shell

# Then run:
exec(open('create_test_publications.py').read())
```

This will create:

- A test journal
- A test author profile
- 3 sample published submissions

### Step 2: Test the Endpoint

Make sure your Django server is running:

```bash
python manage.py runserver
```

Then test the endpoint:

```bash
# List all published articles
curl http://localhost:8000/api/common/publications/

# Search for articles
curl "http://localhost:8000/api/common/publications/?search=quantum"

# Filter by journal
curl "http://localhost:8000/api/common/publications/?journal__short_name=TestJournal"

# Get single article
curl http://localhost:8000/api/common/publications/{uuid}/
```

### Step 3: Run Automated Tests

Run the comprehensive test script:

```bash
# Install requests if needed
pip install requests

# Run tests
python test_public_api.py
```

## API Examples

### List Publications

```bash
GET /api/common/publications/
```

**Response:**

```json
{
  "count": 3,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "title": "Advances in Quantum Computing",
      "abstract": "...",
      "doi": "10.1234/testjournal.2024.001",
      "journal": {
        "title": "Test Journal of Science",
        "short_name": "TestJournal",
        "issn_print": "1234-5678"
      },
      "authors": [...],
      "documents": [...],
      "keywords": ["quantum computing", "drug discovery"]
    }
  ]
}
```

### Search Publications

```bash
GET /api/common/publications/?search=quantum
```

### Filter by Journal

```bash
GET /api/common/publications/?journal__short_name=Nature
```

### Filter by Date Range

```bash
GET /api/common/publications/?submitted_at__gte=2024-01-01&submitted_at__lte=2024-12-31
```

### Order Results

```bash
# Newest first (default)
GET /api/common/publications/?ordering=-submitted_at

# Alphabetical by title
GET /api/common/publications/?ordering=title
```

### Pagination

```bash
GET /api/common/publications/?page=2&page_size=20
```

### Download Document

```bash
GET /api/common/publications/documents/{document_uuid}/download/
```

## Frontend Integration Examples

### JavaScript/React

```javascript
// Fetch published articles
fetch("http://localhost:8000/api/common/publications/")
  .then((response) => response.json())
  .then((data) => {
    console.log(`Found ${data.count} publications`);
    data.results.forEach((article) => {
      console.log(`${article.title} - ${article.doi}`);
    });
  });
```

### Python

```python
import requests

response = requests.get('http://localhost:8001/api/common/publications/')
data = response.json()

for article in data['results']:
    print(f"{article['title']}")
    print(f"Authors: {len(article['authors'])}")
    print(f"DOI: {article.get('doi', 'N/A')}")
    print("-" * 80)
```

### WordPress

```php
<?php
$response = wp_remote_get('http://localhost:8000/api/common/publications/');
$articles = json_decode(wp_remote_retrieve_body($response), true);

foreach ($articles['results'] as $article) {
    echo "<h2>{$article['title']}</h2>";
    echo "<p>{$article['abstract']}</p>";
}
?>
```

## Available Filters

| Filter                | Type    | Example                         |
| --------------------- | ------- | ------------------------------- |
| `journal`             | UUID    | `?journal=uuid`                 |
| `journal__short_name` | String  | `?journal__short_name=Nature`   |
| `section`             | UUID    | `?section=uuid`                 |
| `category`            | UUID    | `?category=uuid`                |
| `research_type`       | UUID    | `?research_type=uuid`           |
| `area`                | UUID    | `?area=uuid`                    |
| `doi`                 | String  | `?doi=10.1234/example`          |
| `submitted_at__gte`   | Date    | `?submitted_at__gte=2024-01-01` |
| `submitted_at__lte`   | Date    | `?submitted_at__lte=2024-12-31` |
| `search`              | String  | `?search=quantum`               |
| `ordering`            | String  | `?ordering=-submitted_at`       |
| `page`                | Integer | `?page=2`                       |
| `page_size`           | Integer | `?page_size=20`                 |

## Security Features

**Only Published Content** - Only submissions with `status='PUBLISHED'` are accessible

**Safe Document Types** - Only MANUSCRIPT and FINAL_VERSION documents can be downloaded

**Public Metadata Only** - Internal workflow data, reviewer comments, and sensitive information are excluded

**No Authentication Required** - Truly public endpoint for open access

## Response Structure

Each publication includes:

- **Basic Info**: title, abstract, DOI, submission number
- **Journal Info**: title, ISSN, publisher, website
- **Authors**: display name, affiliation, ORCID, contribution role
- **Taxonomy**: section, category, research type, area
- **Documents**: title, type, file size, download URL
- **Metadata**: keywords, funding, acknowledgments
- **Dates**: submitted_at, created_at, updated_at

## Performance Optimization

The endpoint uses optimized database queries:

```python
# Efficient query with select_related and prefetch_related
Submission.objects.filter(
    status='PUBLISHED'
).select_related(
    'journal', 'corresponding_author', 'section', ...
).prefetch_related(
    'documents', 'author_contributions', ...
)
```

This prevents N+1 query problems and ensures fast response times.

## Documentation

Complete documentation is available in:

- **[PUBLIC_PUBLICATIONS_API.md](docs/PUBLIC_PUBLICATIONS_API.md)** - Full API reference with examples
- **[PUBLIC_PUBLICATIONS_IMPLEMENTATION.md](docs/PUBLIC_PUBLICATIONS_IMPLEMENTATION.md)** - Implementation details

## Troubleshooting

### No Results Returned

**Problem:** API returns empty results

**Solution:**

1. Ensure you have submissions with `status='PUBLISHED'`
2. Run the test data creation script: `exec(open('create_test_publications.py').read())`

### 404 Not Found

**Problem:** Endpoint returns 404

**Solution:**

1. Check that the server is running: `python manage.py runserver`
2. Verify the URL: `http://localhost:8000/api/common/publications/`
3. Check that the endpoint is registered in `apps/common/urls.py`

### Document Download Fails

**Problem:** Cannot download documents

**Solution:**

1. Ensure the submission status is 'PUBLISHED'
2. Verify the document type is MANUSCRIPT or FINAL_VERSION
3. Check that the file exists in the media folder

## Next Steps

### Production Deployment

Before deploying to production:

1. **Configure CORS** - Allow frontend domains to access the API
2. **Set up CDN** - Cache static publication data
3. **Add Rate Limiting** - Prevent API abuse
4. **Enable Compression** - Reduce response size
5. **Monitor Performance** - Track API usage and response times

### Future Enhancements

Consider adding:

- Citation export (BibTeX, RIS, EndNote)
- RSS/Atom feeds for new publications
- Full-text search on document content
- Article metrics (views, downloads, citations)
- Related articles recommendations
- Social media sharing metadata
- OAI-PMH for metadata harvesting

## Support

For questions or issues:

1. Check the documentation in `docs/PUBLIC_PUBLICATIONS_API.md`
2. Review implementation details in `docs/PUBLIC_PUBLICATIONS_IMPLEMENTATION.md`
3. Run the test script to verify the endpoint: `python test_public_api.py`

## Summary

**Endpoint Created:** `/api/common/publications/`
**Public Access:** No authentication required
**Complete Data:** Full publication details with authors, journal, documents
**Advanced Features:** Search, filter, order, paginate
**Secure:** Only published content, safe metadata
**Optimized:** Efficient database queries
**Documented:** Complete API reference and examples
**Tested:** Test scripts included

The public publications endpoint is now ready to use! 🚀
