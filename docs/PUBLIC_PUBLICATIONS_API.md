# Public Publications API

## Overview

The Public Publications API provides read-only access to published articles without requiring authentication. This endpoint is designed for public access to showcase published research articles with complete metadata, author information, and downloadable documents.

## Base URL

```
/api/common/publications/
```

## Features

- **No Authentication Required** - Public endpoint accessible to anyone
- **Complete Publication Details** - Full article metadata, authors, journal info
- **Advanced Filtering** - Filter by journal, section, category, date range, DOI
- **Full-Text Search** - Search across titles, abstracts, keywords, and DOIs
- **Document Downloads** - Public access to published manuscripts and final versions
- **Pagination Support** - Efficient handling of large datasets
- **Optimized Queries** - Pre-fetched related data for performance

## Endpoints

### 1. List All Published Articles

**GET** `/api/common/publications/`

Returns a paginated list of all published articles.

#### Query Parameters

| Parameter             | Type     | Description                         | Example                                               |
| --------------------- | -------- | ----------------------------------- | ----------------------------------------------------- |
| `journal`             | UUID     | Filter by journal ID                | `?journal=123e4567-e89b-12d3-a456-426614174000`       |
| `journal__short_name` | String   | Filter by journal short name        | `?journal__short_name=Nature`                         |
| `section`             | UUID     | Filter by section ID                | `?section=123e4567-e89b-12d3-a456-426614174000`       |
| `category`            | UUID     | Filter by category ID               | `?category=123e4567-e89b-12d3-a456-426614174000`      |
| `research_type`       | UUID     | Filter by research type             | `?research_type=123e4567-e89b-12d3-a456-426614174000` |
| `area`                | UUID     | Filter by area                      | `?area=123e4567-e89b-12d3-a456-426614174000`          |
| `doi`                 | String   | Filter by DOI                       | `?doi=10.1234/example.2024.001`                       |
| `submitted_at__gte`   | DateTime | Articles submitted after date       | `?submitted_at__gte=2024-01-01`                       |
| `submitted_at__lte`   | DateTime | Articles submitted before date      | `?submitted_at__lte=2024-12-31`                       |
| `search`              | String   | Search in title, abstract, keywords | `?search=machine+learning`                            |
| `ordering`            | String   | Order results                       | `?ordering=-submitted_at`                             |
| `page`                | Integer  | Page number                         | `?page=2`                                             |
| `page_size`           | Integer  | Results per page                    | `?page_size=20`                                       |

#### Ordering Options

- `submitted_at` - Order by submission date (ascending)
- `-submitted_at` - Order by submission date (descending, default)
- `created_at` - Order by creation date
- `updated_at` - Order by update date
- `title` - Order alphabetically by title

#### Example Request

```bash
curl -X GET "https://your-domain.com/api/common/publications/?journal__short_name=Nature&search=quantum&ordering=-submitted_at&page=1&page_size=10"
```

#### Example Response

```json
{
  "count": 150,
  "next": "https://your-domain.com/api/common/publications/?page=2",
  "previous": null,
  "results": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "title": "Quantum Computing Applications in Drug Discovery",
      "abstract": "This study explores the application of quantum computing algorithms...",
      "submission_number": "NAT-2024-0123",
      "doi": "10.1234/nature.2024.0123",
      "journal": {
        "id": "789e4567-e89b-12d3-a456-426614174000",
        "title": "Nature",
        "short_name": "Nature",
        "publisher": "Nature Publishing Group",
        "issn_print": "0028-0836",
        "issn_online": "1476-4687",
        "website_url": "https://www.nature.com"
      },
      "submitted_at": "2024-03-15T10:30:00Z",
      "created_at": "2024-03-10T08:00:00Z",
      "updated_at": "2024-06-20T14:45:00Z",
      "section": {
        "name": "Physical Sciences",
        "code": "PHYS",
        "category": {
          "name": "Physics",
          "code": "PHYS-001",
          "research_type": {
            "name": "Original Research",
            "code": "ORIG",
            "area": {
              "name": "Quantum Computing",
              "code": "QC",
              "keywords": ["quantum", "computing", "algorithms"]
            }
          }
        }
      },
      "keywords": [
        "quantum computing",
        "drug discovery",
        "molecular simulation"
      ],
      "authors": [
        {
          "id": "456e4567-e89b-12d3-a456-426614174000",
          "display_name": "Dr. Jane Smith",
          "affiliation_name": "MIT",
          "orcid_id": "0000-0001-2345-6789",
          "order": 1,
          "contrib_role": "FIRST"
        },
        {
          "id": "789e4567-e89b-12d3-a456-426614174000",
          "display_name": "Prof. John Doe",
          "affiliation_name": "Stanford University",
          "orcid_id": "0000-0002-3456-7890",
          "order": 2,
          "contrib_role": "CORRESPONDING"
        }
      ],
      "corresponding_author": {
        "id": "789e4567-e89b-12d3-a456-426614174000",
        "display_name": "Prof. John Doe",
        "affiliation_name": "Stanford University",
        "orcid_id": "0000-0002-3456-7890",
        "order": 2,
        "contrib_role": "CORRESPONDING"
      },
      "documents": [
        {
          "id": "321e4567-e89b-12d3-a456-426614174000",
          "title": "Main Manuscript",
          "document_type": "FINAL_VERSION",
          "file_name": "quantum_computing_drug_discovery.pdf",
          "file_size": 2457600,
          "created_at": "2024-06-15T09:00:00Z",
          "download_url": "https://your-domain.com/api/common/publications/documents/321e4567-e89b-12d3-a456-426614174000/download/"
        }
      ],
      "metadata": {
        "keywords": [
          "quantum computing",
          "drug discovery",
          "molecular simulation"
        ],
        "funding": "NSF Grant #12345",
        "acknowledgments": "We thank the reviewers for their valuable feedback."
      }
    }
  ]
}
```

### 2. Retrieve Single Published Article

**GET** `/api/common/publications/{id}/`

Get complete details of a specific published article by its ID.

#### Path Parameters

| Parameter | Type | Description    |
| --------- | ---- | -------------- |
| `id`      | UUID | Publication ID |

#### Example Request

```bash
curl -X GET "https://your-domain.com/api/common/publications/123e4567-e89b-12d3-a456-426614174000/"
```

#### Example Response

Same structure as individual items in the list response above.

### 3. Download Published Document

**GET** `/api/common/publications/documents/{document_id}/download/`

Download a document file from a published article. Only published manuscripts and final versions are available.

#### Path Parameters

| Parameter     | Type | Description |
| ------------- | ---- | ----------- |
| `document_id` | UUID | Document ID |

#### Example Request

```bash
curl -X GET "https://your-domain.com/api/common/publications/documents/321e4567-e89b-12d3-a456-426614174000/download/" \
     -o publication.pdf
```

#### Response

- **200 OK** - File download with appropriate headers
- **403 Forbidden** - Document not publicly available
- **404 Not Found** - Document not found

## Response Schema

### Publication Object

| Field                  | Type     | Description                   |
| ---------------------- | -------- | ----------------------------- |
| `id`                   | UUID     | Unique publication identifier |
| `title`                | String   | Article title                 |
| `abstract`             | String   | Article abstract              |
| `submission_number`    | String   | Internal submission number    |
| `doi`                  | String   | Digital Object Identifier     |
| `journal`              | Object   | Journal information           |
| `submitted_at`         | DateTime | Submission date               |
| `created_at`           | DateTime | Creation date                 |
| `updated_at`           | DateTime | Last update date              |
| `section`              | Object   | Taxonomy classification       |
| `keywords`             | Array    | Article keywords              |
| `authors`              | Array    | All authors with details      |
| `corresponding_author` | Object   | Corresponding author details  |
| `documents`            | Array    | Published documents           |
| `metadata`             | Object   | Additional metadata           |

### Journal Object

| Field         | Type   | Description          |
| ------------- | ------ | -------------------- |
| `id`          | UUID   | Journal ID           |
| `title`       | String | Journal title        |
| `short_name`  | String | Journal abbreviation |
| `publisher`   | String | Publisher name       |
| `issn_print`  | String | Print ISSN           |
| `issn_online` | String | Online ISSN          |
| `website_url` | String | Journal website      |

### Author Object

| Field              | Type    | Description                 |
| ------------------ | ------- | --------------------------- |
| `id`               | UUID    | Author profile ID           |
| `display_name`     | String  | Author name                 |
| `affiliation_name` | String  | Institution/affiliation     |
| `orcid_id`         | String  | ORCID identifier            |
| `order`            | Integer | Author order in publication |
| `contrib_role`     | String  | Contribution role           |

### Document Object

| Field           | Type     | Description                      |
| --------------- | -------- | -------------------------------- |
| `id`            | UUID     | Document ID                      |
| `title`         | String   | Document title                   |
| `document_type` | String   | Type (MANUSCRIPT, FINAL_VERSION) |
| `file_name`     | String   | Original filename                |
| `file_size`     | Integer  | File size in bytes               |
| `created_at`    | DateTime | Upload date                      |
| `download_url`  | String   | Download URL                     |

## Use Cases

### 1. Display Published Articles on Website

```javascript
// Fetch latest 10 published articles
fetch(
  "https://your-domain.com/api/common/publications/?page_size=10&ordering=-submitted_at",
)
  .then((response) => response.json())
  .then((data) => {
    data.results.forEach((article) => {
      console.log(
        `${article.title} by ${article.corresponding_author.display_name}`,
      );
    });
  });
```

### 2. Search for Articles by Keyword

```javascript
// Search for articles about "machine learning"
fetch(
  "https://your-domain.com/api/common/publications/?search=machine+learning",
)
  .then((response) => response.json())
  .then((data) => {
    console.log(`Found ${data.count} articles`);
  });
```

### 3. Filter Articles by Journal and Date Range

```javascript
// Get articles from specific journal in 2024
fetch(
  "https://your-domain.com/api/common/publications/?journal__short_name=Nature&submitted_at__gte=2024-01-01&submitted_at__lte=2024-12-31",
)
  .then((response) => response.json())
  .then((data) => {
    console.log(`${data.count} articles published in Nature during 2024`);
  });
```

### 4. Export Article Metadata

```python
import requests

# Fetch all published articles (handle pagination)
page = 1
all_articles = []

while True:
    response = requests.get(f'https://your-domain.com/api/common/publications/?page={page}')
    data = response.json()

    all_articles.extend(data['results'])

    if not data['next']:
        break

    page += 1

print(f"Total articles: {len(all_articles)}")
```

## Security & Privacy

- **Public Access**: No authentication required
- **Published Only**: Only articles with status='PUBLISHED' are accessible
- **Document Types**: Only MANUSCRIPT and FINAL_VERSION documents are available
- **Safe Metadata**: Only public-safe metadata fields are exposed
- **Author Privacy**: Only public author information is shared

## Performance Considerations

- **Query Optimization**: Uses `select_related` and `prefetch_related` for efficient database queries
- **Pagination**: Default page size limits response size
- **Caching**: Consider implementing CDN caching for static publication data
- **Indexing**: Database indexes on key fields for fast filtering

## Integration Examples

### Frontend React Component

```jsx
import React, { useEffect, useState } from "react";

function PublishedArticles() {
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("https://your-domain.com/api/common/publications/?page_size=10")
      .then((res) => res.json())
      .then((data) => {
        setArticles(data.results);
        setLoading(false);
      });
  }, []);

  if (loading) return <div>Loading...</div>;

  return (
    <div>
      <h1>Published Articles</h1>
      {articles.map((article) => (
        <div key={article.id}>
          <h2>{article.title}</h2>
          <p>{article.abstract}</p>
          <p>DOI: {article.doi}</p>
          <p>
            Authors: {article.authors.map((a) => a.display_name).join(", ")}
          </p>
        </div>
      ))}
    </div>
  );
}
```

### WordPress Integration

```php
<?php
// Fetch and display published articles
$response = wp_remote_get('https://your-domain.com/api/common/publications/?page_size=5');
$articles = json_decode(wp_remote_retrieve_body($response), true);

foreach ($articles['results'] as $article) {
    echo "<h2>{$article['title']}</h2>";
    echo "<p>{$article['abstract']}</p>";
    echo "<p>DOI: {$article['doi']}</p>";
}
?>
```

## Error Responses

### 404 Not Found

```json
{
  "detail": "Not found."
}
```

### 403 Forbidden

```json
{
  "error": "Document is not publicly available"
}
```

## API Versioning

Current version: **v1** (implicit in `/api/common/publications/`)

## Support

For questions or issues regarding the Public Publications API, please contact the technical support team.

## Changelog

### Version 1.0.0 (January 2026)

- Initial release
- Public read-only access to published articles
- Advanced filtering and search capabilities
- Document download support
- Complete metadata and author information
