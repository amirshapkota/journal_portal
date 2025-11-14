# Analytics API Documentation

Comprehensive analytics dashboard for journal management platform providing metrics for admins, editors, and individual users.

## Overview

The Analytics API provides detailed insights into:
- **Submission metrics**: Volume, trends, processing times
- **Review performance**: Reviewer statistics, response times
- **Journal analytics**: Journal-specific metrics
- **User activity**: Registration, verification, role distribution
- **Personal analytics**: Individual user performance

## Authentication

All analytics endpoints require authentication via JWT token:
```
Authorization: Bearer <access_token>
```

## Permissions

- **Admin/Editor Analytics**: Requires `ADMIN` role or `EDITOR` role
- **Personal Analytics**: Available to all authenticated users

---

## Endpoints

### 1. Dashboard Overview

**GET** `/api/v1/analytics/dashboard/`

Get comprehensive dashboard overview with key metrics.

**Permission**: Admin or Editor

**Response**:
```json
{
  "overview": {
    "total_submissions": 1250,
    "pending_submissions": 45,
    "submissions_last_30_days": 89,
    "acceptance_rate": 42.5,
    "total_reviews": 2100,
    "pending_reviews": 23,
    "avg_review_time_days": 14
  },
  "submissions": {
    "total": 1250,
    "pending": 45,
    "accepted": 530,
    "rejected": 418,
    "under_review": 67
  },
  "reviews": {
    "total": 2100,
    "pending": 23,
    "completed": 1850,
    "declined": 120
  },
  "users": {
    "total": 450,
    "verified": 380,
    "pending_verifications": 12,
    "authors": 320,
    "reviewers": 150
  },
  "journals": {
    "total": 15,
    "active": 12,
    "inactive": 3
  }
}
```

**Use Cases**:
- Admin dashboard main view
- Executive summary for stakeholders
- Quick health check of platform

---

### 2. Submission Analytics

**GET** `/api/v1/analytics/submissions/`

Get detailed submission analytics and trends.

**Permission**: Admin or Editor

**Query Parameters**:
- `days` (optional): Number of days to analyze (default: 30)
- `journal_id` (optional): Filter by specific journal UUID

**Example Request**:
```
GET /api/v1/analytics/submissions/?days=90&journal_id=123e4567-e89b-12d3-a456-426614174000
```

**Response**:
```json
{
  "period": {
    "days": 90,
    "start_date": "2025-08-15",
    "end_date": "2025-11-14"
  },
  "total_submissions": 267,
  "submissions_by_date": [
    {"date": "2025-08-15", "count": 3},
    {"date": "2025-08-16", "count": 5},
    ...
  ],
  "status_breakdown": [
    {"status": "ACCEPTED", "count": 85},
    {"status": "REJECTED", "count": 42},
    {"status": "UNDER_REVIEW", "count": 67},
    {"status": "SUBMITTED", "count": 45}
  ],
  "avg_processing_time_days": 28,
  "top_journals": [
    {
      "journal__id": "123e4567-e89b-12d3-a456-426614174000",
      "journal__name": "Journal of Computer Science",
      "count": 120
    },
    ...
  ]
}
```

**Use Cases**:
- Track submission trends over time
- Identify bottlenecks in processing
- Compare journal performance
- Generate reports for stakeholders

---

### 3. Reviewer Analytics

**GET** `/api/v1/analytics/reviewers/`

Get reviewer performance metrics and statistics.

**Permission**: Admin or Editor

**Query Parameters**:
- `days` (optional): Number of days to analyze (default: 90)

**Example Request**:
```
GET /api/v1/analytics/reviewers/?days=180
```

**Response**:
```json
{
  "period": {
    "days": 180,
    "start_date": "2025-05-18",
    "end_date": "2025-11-14"
  },
  "assignments": {
    "total": 450,
    "accepted": 380,
    "completed": 340,
    "declined": 45,
    "pending": 25
  },
  "rates": {
    "acceptance_rate": 84.44,
    "completion_rate": 75.56
  },
  "timing": {
    "avg_response_time_days": 3,
    "avg_completion_time_days": 21
  },
  "top_reviewers": [
    {
      "reviewer__id": "123e4567-e89b-12d3-a456-426614174001",
      "reviewer__display_name": "Dr. John Smith",
      "reviewer__user__email": "j.smith@university.edu",
      "reviews_completed": 45
    },
    ...
  ],
  "avg_quality_score": 4.2
}
```

**Use Cases**:
- Identify top-performing reviewers
- Monitor reviewer workload
- Track review quality
- Optimize reviewer assignment

---

### 4. Journal Analytics

**GET** `/api/v1/analytics/journals/`

Get detailed analytics for a specific journal.

**Permission**: Admin or Editor

**Query Parameters**:
- `journal_id` (required): Journal UUID
- `days` (optional): Number of days to analyze (default: 90)

**Example Request**:
```
GET /api/v1/analytics/journals/?journal_id=123e4567-e89b-12d3-a456-426614174000&days=90
```

**Response**:
```json
{
  "journal": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "Journal of Computer Science",
    "status": "ACTIVE"
  },
  "period": {
    "days": 90,
    "start_date": "2025-08-15",
    "end_date": "2025-11-14"
  },
  "submissions": {
    "total": 120,
    "status_breakdown": [
      {"status": "ACCEPTED", "count": 35},
      {"status": "REJECTED", "count": 20},
      {"status": "UNDER_REVIEW", "count": 40},
      {"status": "SUBMITTED", "count": 25}
    ],
    "by_month": [
      {"month": "2025-08-01", "count": 38},
      {"month": "2025-09-01", "count": 42},
      {"month": "2025-10-01", "count": 40}
    ],
    "acceptance_rate": 63.64
  },
  "reviews": {
    "total_assignments": 240,
    "avg_reviews_per_submission": 2.0
  }
}
```

**Use Cases**:
- Journal performance reports
- Editorial board meetings
- Publisher reporting
- Resource allocation planning

---

### 5. User Analytics

**GET** `/api/v1/analytics/users/`

Get user registration, verification, and activity metrics.

**Permission**: Admin or Editor

**Query Parameters**:
- `days` (optional): Number of days to analyze (default: 30)

**Example Request**:
```
GET /api/v1/analytics/users/?days=60
```

**Response**:
```json
{
  "period": {
    "days": 60,
    "start_date": "2025-09-15",
    "end_date": "2025-11-14"
  },
  "registrations": {
    "total": 78,
    "by_date": [
      {"date": "2025-09-15", "count": 2},
      {"date": "2025-09-16", "count": 1},
      ...
    ]
  },
  "verification": {
    "status_breakdown": [
      {"verification_status": "GENUINE", "count": 380},
      {"verification_status": "PENDING", "count": 45},
      {"verification_status": "SUSPICIOUS", "count": 5},
      {"verification_status": "UNVERIFIED", "count": 20}
    ],
    "requests_breakdown": [
      {"status": "PENDING", "count": 12},
      {"status": "APPROVED", "count": 350},
      {"status": "REJECTED", "count": 15}
    ]
  },
  "roles": {
    "authors": 320,
    "reviewers": 150,
    "editors": 25
  },
  "integrations": {
    "orcid_connected": 280
  }
}
```

**Use Cases**:
- Track user growth
- Monitor verification backlog
- Understand user role distribution
- Measure ORCID adoption

---

### 6. Personal Analytics

**GET** `/api/v1/analytics/my-analytics/`

Get personal performance metrics for the authenticated user.

**Permission**: Authenticated user (any role)

**Response** (varies by user roles):

**For Author**:
```json
{
  "profile": {
    "id": "123e4567-e89b-12d3-a456-426614174002",
    "name": "Dr. Jane Doe",
    "email": "jane.doe@university.edu",
    "verification_status": "GENUINE",
    "roles": ["AUTHOR", "REVIEWER"]
  },
  "author_stats": {
    "total_submissions": 12,
    "accepted": 5,
    "rejected": 2,
    "under_review": 3,
    "pending": 2
  },
  "reviewer_stats": {
    "total_assignments": 28,
    "pending": 2,
    "accepted": 24,
    "completed": 22,
    "declined": 2,
    "avg_completion_time_days": 18
  },
  "editor_stats": null
}
```

**For Editor**:
```json
{
  "profile": {
    "id": "123e4567-e89b-12d3-a456-426614174003",
    "name": "Prof. Robert Lee",
    "email": "r.lee@university.edu",
    "verification_status": "GENUINE",
    "roles": ["EDITOR", "AUTHOR"]
  },
  "author_stats": {
    "total_submissions": 8,
    "accepted": 6,
    "rejected": 1,
    "under_review": 1,
    "pending": 0
  },
  "reviewer_stats": null,
  "editor_stats": {
    "journals": 2,
    "submissions_managed": 156,
    "decisions_made": 98,
    "pending_submissions": 34
  }
}
```

**Use Cases**:
- Personal dashboard for users
- Track individual contribution
- Monitor workload
- Performance self-assessment

---

## Common Use Cases

### Admin Dashboard
```bash
# Get overview
GET /api/v1/analytics/dashboard/

# Get 30-day submission trends
GET /api/v1/analytics/submissions/?days=30

# Check reviewer performance
GET /api/v1/analytics/reviewers/?days=90

# Monitor user growth
GET /api/v1/analytics/users/?days=30
```

### Journal Editor Dashboard
```bash
# Get journal-specific metrics
GET /api/v1/analytics/journals/?journal_id=<uuid>&days=90

# Get submission analytics for my journal
GET /api/v1/analytics/submissions/?journal_id=<uuid>&days=90

# Check my editorial performance
GET /api/v1/analytics/my-analytics/
```

### Reviewer Dashboard
```bash
# Check my review statistics
GET /api/v1/analytics/my-analytics/
```

### Author Dashboard
```bash
# Track my submissions
GET /api/v1/analytics/my-analytics/
```

---

## Response Time Analysis

The analytics system tracks timing metrics using Django's `DurationField`:

- **Review Response Time**: Time from assignment to acceptance/decline
- **Review Completion Time**: Time from assignment to review submission
- **Processing Time**: Time from submission to editorial decision

All times are calculated in **days** for easy interpretation.

---

## Data Aggregation

Analytics use Django ORM aggregation functions:
- `Count()`: Total counts
- `Avg()`: Average values
- `TruncDate()`: Daily aggregation
- `TruncMonth()`: Monthly aggregation

Performance is optimized through:
- Database-level aggregation (no Python loops)
- Indexed date fields
- Efficient querysets with `select_related` and `prefetch_related`

---

## Error Handling

**400 Bad Request**:
- Missing required parameters (e.g., `journal_id` for journal analytics)

**401 Unauthorized**:
- Missing or invalid JWT token

**403 Forbidden**:
- User doesn't have required role (Admin/Editor)

**404 Not Found**:
- Journal ID doesn't exist

---

## Best Practices

1. **Use appropriate time ranges**:
   - Dashboard overview: 30 days
   - Reviewer performance: 90 days
   - Long-term trends: 180-365 days

2. **Filter by journal** for targeted analysis:
   ```
   GET /api/v1/analytics/submissions/?journal_id=<uuid>
   ```

3. **Cache dashboard results** on frontend to reduce API calls

4. **Refresh analytics periodically** (e.g., every 5 minutes) for real-time dashboards

5. **Export data** for reporting:
   - Use the API responses to generate CSV/PDF reports
   - Store historical snapshots for trend analysis

---

## Future Enhancements

Planned features for Phase 6:
- **Export endpoints**: CSV and PDF generation
- **Custom date ranges**: Specific start/end dates
- **Comparison views**: Year-over-year, period-over-period
- **Predictive analytics**: Forecast submission volume, reviewer availability
- **Real-time updates**: WebSocket support for live dashboards

---

## Performance Considerations

- **Caching**: Consider implementing Redis caching for frequently accessed metrics
- **Background jobs**: For heavy analytics (e.g., annual reports), use Celery tasks
- **Pagination**: Large result sets (e.g., `submissions_by_date`) may need pagination
- **Database optimization**: Ensure indexes on `created_at`, `status`, and foreign keys

---

## Support

For issues or questions:
- Check API documentation at `/api/docs/`
- Review error messages in response
- Contact platform administrators
