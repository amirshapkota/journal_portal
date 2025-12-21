# Achievements & Recognition System

## Overview

The achievements system provides a comprehensive gamification and recognition framework for rewarding reviewers, authors, and editors for their contributions to the journal platform.

## Features

- **Badges**: Automatic achievement badges for reaching milestones
- **Awards**: Annual awards for top performers (Best Reviewer, Researcher of the Year)
- **Leaderboards**: Rankings by field, country, and journal
- **Certificates**: PDF certificates with verification codes
- **Public Recognition**: Shareable achievement profiles

## Models

### Badge

Represents achievement badges that users can earn.

**Fields:**

- `name`: Badge name (e.g., "10 Reviews Complete")
- `description`: What the badge represents
- `badge_type`: REVIEWER, AUTHOR, or EDITOR
- `level`: BRONZE, SILVER, GOLD, PLATINUM, DIAMOND
- `criteria`: JSON field with requirements
- `points`: Points awarded
- `icon`: Optional badge icon URL
- `color`: Hex color code

**Example Badges:**

- 1st Review Complete (Bronze, 10 points)
- 5 Reviews Complete (Bronze, 50 points)
- 10 Reviews Complete (Silver, 100 points)
- 25 Reviews Complete (Gold, 250 points)
- 50 Reviews Complete (Platinum, 500 points)
- 100 Reviews Complete (Diamond, 1000 points)

### UserBadge

Links users to earned badges.

**Fields:**

- `profile`: User who earned the badge
- `badge`: The badge earned
- `year`: Year earned
- `journal`: Journal context (optional)
- `achievement_data`: JSON with earning details
- `notes`: Additional notes
- `is_featured`: Whether to feature on profile
- `earned_at`: Timestamp

### Award

Annual recognition awards.

**Award Types:**

- `BEST_REVIEWER`: Top reviewer by journal/discipline/country
- `RESEARCHER_OF_YEAR`: Most prolific researcher
- `EDITOR_EXCELLENCE`: Outstanding editorial work
- `SPECIAL_RECOGNITION`: Custom awards

**Fields:**

- `title`: Award title
- `description`: Award description
- `award_type`: Type of award
- `year`: Award year
- `recipient`: User receiving award
- `journal`: Journal context (optional)
- `discipline`: Field/discipline filter (optional)
- `country`: Country filter (optional)
- `citation`: Recognition text
- `metrics`: JSON with performance metrics
- `amount`: Monetary value (optional)
- `certificate_generated`: Whether certificate was created

### Leaderboard

Rankings for competitive metrics.

**Categories:**

- `REVIEWER`: Top reviewers by review count/quality
- `AUTHOR`: Top authors by publications
- `CITATIONS`: Most cited authors
- `CONTRIBUTIONS`: Overall contributions

**Periods:**

- `MONTHLY`: Monthly rankings
- `QUARTERLY`: Quarterly rankings
- `YEARLY`: Annual rankings
- `ALL_TIME`: All-time rankings

**Fields:**

- `profile`: User in ranking
- `category`: Leaderboard category
- `period`: Time period
- `journal`: Journal filter (optional)
- `field`: Research field filter (optional)
- `country`: Country filter (optional)
- `rank`: Position in leaderboard
- `score`: Calculated score
- `metrics`: JSON with detailed metrics
- `period_start` / `period_end`: Time range
- `calculated_at`: Last calculation time

### Certificate

PDF certificates for awards and badges.

**Certificate Types:**

- `BADGE`: Badge achievement certificate
- `AWARD`: Award certificate
- `PARTICIPATION`: Participation certificate

**Fields:**

- `certificate_number`: Unique certificate number (auto-generated)
- `verification_code`: 8-character verification code (auto-generated)
- `recipient`: Certificate recipient
- `certificate_type`: Type of certificate
- `title`: Certificate title
- `description`: Certificate description
- `journal`: Journal context (optional)
- `award`: Associated award (optional)
- `badge`: Associated badge (optional)
- `pdf_file`: Generated PDF file
- `issued_date`: Issue date
- `is_public`: Whether publicly verifiable
- `custom_data`: Additional JSON data

## API Endpoints

### Badges

**List Badges**

```
GET /api/v1/achievements/badges/
```

Query parameters:

- `badge_type`: Filter by REVIEWER, AUTHOR, EDITOR
- `level`: Filter by badge level
- `search`: Search name/description

**Get Badge Detail**

```
GET /api/v1/achievements/badges/{id}/
```

### User Badges

**List My Badges**

```
GET /api/v1/achievements/user-badges/my_badges/
```

Returns all badges earned by authenticated user.

**Get User Badge Detail**

```
GET /api/v1/achievements/user-badges/{id}/
```

### Awards

**List Awards**

```
GET /api/v1/achievements/awards/
```

Query parameters:

- `year`: Filter by year
- `award_type`: Filter by award type
- `journal`: Filter by journal ID
- `discipline`: Filter by discipline
- `country`: Filter by country

**Get Best Reviewer**

```
GET /api/v1/achievements/awards/best-reviewer/{journal_id}/
```

Query parameters:

- `year`: Year (defaults to current year)

Calculates and returns (or creates) the best reviewer award for a journal. Metrics include:

- Total reviews completed
- Average quality score
- Average review turnaround time

**Get Researcher of the Year**

```
GET /api/v1/achievements/awards/researcher-of-year/{journal_id}/
```

Query parameters:

- `year`: Year (defaults to current year)

Calculates and returns (or creates) the researcher of the year. Metrics include:

- Total publications
- Acceptance rate

**Create Award**

```
POST /api/v1/achievements/awards/
```

Body:

```json
{
  "title": "Best Reviewer 2024",
  "description": "Outstanding review contributions",
  "award_type": "BEST_REVIEWER",
  "year": 2024,
  "recipient": "recipient-profile-id",
  "journal": "journal-id",
  "citation": "In recognition of excellent service",
  "metrics": {
    "reviews_completed": 50,
    "avg_quality": 4.8
  }
}
```

### Leaderboards

**List Leaderboards**

```
GET /api/v1/achievements/leaderboards/
```

Query parameters:

- `category`: REVIEWER, AUTHOR, CITATIONS, CONTRIBUTIONS
- `period`: MONTHLY, QUARTERLY, YEARLY, ALL_TIME
- `journal`: Filter by journal ID
- `field`: Filter by field
- `country`: Filter by country

**Get Top Reviewers**

```
GET /api/v1/achievements/leaderboards/top_reviewers/
```

Query parameters:

- `period`: Time period (default: YEARLY)
- `journal_id`: Filter by journal
- `field`: Filter by field
- `country`: Filter by country
- `limit`: Number of results (default: 10)

### Certificates

**List My Certificates**

```
GET /api/v1/achievements/certificates/
```

Returns certificates for authenticated user.

**Generate Award Certificate**

```
POST /api/v1/achievements/certificates/generate-award/{award_id}/
```

Generates a certificate for an existing award.

**Verify Certificate**

```
GET /api/v1/achievements/certificates/verify/?code={verification_code}
```

Public endpoint to verify a certificate by its verification code.

Response:

```json
{
  "valid": true,
  "certificate": {
    "certificate_number": "CERT-2024-ABC123",
    "verification_code": "A1B2C3D4",
    "title": "Best Reviewer 2024",
    "recipient": {
      "display_name": "John Doe"
    },
    "issued_date": "2024-12-20"
  }
}
```

## Auto-Badge Assignment

The system automatically awards badges through Django signals:

### Reviewer Badges

Triggered when `ReviewAssignment.status` changes to `COMPLETED`:

- Counts total reviews for current year
- Awards appropriate badge tier (1, 5, 10, 25, 50, 100 reviews)
- Creates `UserBadge` entry if not already awarded

### Author Badges

Triggered when `Submission.status` changes to `ACCEPTED` or `PUBLISHED`:

- Counts total publications for current year
- Awards appropriate badge tier (1, 3, 5, 10, 20 publications)
- Creates `UserBadge` entry if not already awarded

## Admin Interface

All models are registered in Django admin with:

- List displays with relevant fields
- Filters by type, year, status
- Search capabilities
- Readonly fields for auto-generated data
- Organized fieldsets

## Integration Examples

### Calculate Best Reviewer for Journal

```python
from apps.achievements.views import AwardViewSet
from apps.journals.models import Journal

journal = Journal.objects.get(slug='my-journal')
response = AwardViewSet.as_view({'get': 'best_reviewer'})(
    request,
    journal_id=str(journal.id)
)
```

### Check User's Badges

```python
from apps.achievements.models import UserBadge

user_badges = UserBadge.objects.filter(
    profile=user.profile,
    year=2024
).select_related('badge')

for ub in user_badges:
    print(f"{ub.badge.name} - {ub.badge.level} ({ub.badge.points} points)")
```

### Get Top Reviewers Leaderboard

```python
from apps.achievements.models import Leaderboard

top_reviewers = Leaderboard.objects.filter(
    category='REVIEWER',
    period='YEARLY',
    period_end__year=2024
).order_by('rank')[:10]
```

## Permissions

- **Badges**: Read-only for all authenticated users
- **User Badges**: Users see only their own badges; admins see all
- **Awards**: Read-only for authenticated users; admins can create/edit
- **Leaderboards**: Read-only for all authenticated users
- **Certificates**: Users see only their own; verification endpoint is public

## Future Enhancements

1. **PDF Generation**: Implement actual PDF certificate generation using ReportLab or WeasyPrint
2. **Email Notifications**: Send emails when badges/awards are earned
3. **Social Sharing**: Generate shareable badge images
4. **Analytics Dashboard**: Comprehensive analytics for achievements
5. **Custom Badge Creation**: Allow journals to create custom badges
6. **Badge Tiers**: Multiple levels within each badge type
7. **Leaderboard Automation**: Scheduled tasks to auto-calculate leaderboards
8. **Achievement Points System**: Redeem points for benefits
9. **Milestone Tracking**: Progress bars toward next badge
10. **Team Achievements**: Group badges for collaborative work

## Testing

Run tests:

```bash
python manage.py test apps.achievements
```

## Migration

Create and apply migrations:

```bash
python manage.py makemigrations achievements
python manage.py migrate achievements
```
