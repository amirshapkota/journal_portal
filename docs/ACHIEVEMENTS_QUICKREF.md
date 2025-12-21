# Achievements System - Quick Reference

## Created Files

```
apps/achievements/
├── __init__.py
├── apps.py (updated with signals)
├── models.py (5 models: Badge, UserBadge, Award, Leaderboard, Certificate)
├── serializers.py (5 serializers)
├── views.py (5 ViewSets with custom actions)
├── urls.py (Router configuration)
├── admin.py (Admin interfaces for all models)
├── signals.py (Auto-badge assignment)
├── README.md (Full documentation)
└── migrations/
    └── 0001_initial.py
```

## API Endpoints Summary

### Base URL: `/api/v1/achievements/`

### Badges

- `GET /badges/` - List all badges (filterable by type, level)
- `GET /badges/{id}/` - Badge detail
- `POST /badges/` - Create badge (admin)
- `PUT /badges/{id}/` - Update badge (admin)
- `DELETE /badges/{id}/` - Delete badge (admin)

### User Badges

- `GET /user-badges/` - List user's badges
- `GET /user-badges/{id}/` - Badge detail
- `GET /user-badges/my_badges/` - Get my badges (custom action)

### Awards

- `GET /awards/` - List awards (filterable by year, type, journal, discipline, country)
- `GET /awards/{id}/` - Award detail
- `POST /awards/` - Create award (admin)
- `PUT /awards/{id}/` - Update award (admin)
- `DELETE /awards/{id}/` - Delete award (admin)
- `GET /awards/best-reviewer/{journal_id}/?year=2024` - **Get/calculate best reviewer**
- `GET /awards/researcher-of-year/{journal_id}/?year=2024` - **Get/calculate researcher of year**

### Leaderboards

- `GET /leaderboards/` - List leaderboard entries
- `GET /leaderboards/{id}/` - Leaderboard entry detail
- `GET /leaderboards/top_reviewers/?period=YEARLY&journal_id=xxx&limit=10` - **Top reviewers leaderboard**

### Certificates

- `GET /certificates/` - List my certificates
- `GET /certificates/{id}/` - Certificate detail
- `POST /certificates/` - Create certificate (admin)
- `POST /certificates/generate-award/{award_id}/` - **Generate certificate for award**
- `GET /certificates/verify/?code=A1B2C3D4` - **Verify certificate (public)**

## Key Features Implemented

### 1. Auto-Badge Assignment via Signals

- ✅ Reviewer badges (1, 5, 10, 25, 50, 100 reviews)
- ✅ Author badges (1, 3, 5, 10, 20 publications)
- ✅ Automatic creation when milestones reached

### 2. Best Reviewer Calculation

Endpoint: `GET /awards/best-reviewer/{journal_id}/?year=2024`

**Metrics Used:**

- Total reviews completed in year
- Average quality score
- Average review turnaround time

**Logic:**

1. Filters ReviewAssignment by journal and year
2. Counts completed reviews per reviewer
3. Calculates average quality and timeliness
4. Ranks by reviews completed and quality
5. Creates or updates Award for top reviewer

### 3. Researcher of the Year Calculation

Endpoint: `GET /awards/researcher-of-year/{journal_id}/?year=2024`

**Metrics Used:**

- Total publications (ACCEPTED/PUBLISHED)
- Acceptance rate

**Logic:**

1. Filters Submissions by journal and year
2. Counts accepted/published papers per author
3. Ranks by publication count
4. Creates or updates Award for top researcher

### 4. Leaderboards

Endpoint: `GET /leaderboards/top_reviewers/`

**Filters:**

- `period`: MONTHLY, QUARTERLY, YEARLY, ALL_TIME
- `journal_id`: Filter by journal
- `field`: Filter by research field
- `country`: Filter by country
- `limit`: Number of results (default: 10)

**Categories:**

- REVIEWER: Top reviewers by activity
- AUTHOR: Top authors by publications
- CITATIONS: Most cited researchers
- CONTRIBUTIONS: Overall contributions

### 5. Certificate Generation & Verification

**Generation:**

- `POST /certificates/generate-award/{award_id}/`
- Auto-generates certificate number (CERT-YYYY-XXXXXX)
- Auto-generates 8-character verification code
- Links to award/badge
- Stores metadata in JSON

**Verification:**

- `GET /certificates/verify/?code=A1B2C3D4`
- Public endpoint (no auth required)
- Returns certificate details if valid and public

## Badge System Details

### Badge Levels

- **BRONZE**: Entry-level achievements (1-5 milestones)
- **SILVER**: Intermediate achievements (10-15 milestones)
- **GOLD**: Advanced achievements (25-30 milestones)
- **PLATINUM**: Expert achievements (50-75 milestones)
- **DIAMOND**: Elite achievements (100+ milestones)

### Badge Types

- **REVIEWER**: For review-related achievements
- **AUTHOR**: For publication-related achievements
- **EDITOR**: For editorial work achievements

### Example Badges Created by Signals

**Reviewer Badges:**

- 1st Review Complete (Bronze, 10 points)
- 5 Reviews Complete (Bronze, 50 points)
- 10 Reviews Complete (Silver, 100 points)
- 25 Reviews Complete (Gold, 250 points)
- 50 Reviews Complete (Platinum, 500 points)
- 100 Reviews Complete (Diamond, 1000 points)

**Author Badges:**

- 1st Publication (Bronze, 20 points)
- 3 Publications (Silver, 60 points)
- 5 Publications (Gold, 100 points)
- 10 Publications (Platinum, 200 points)
- 20 Publications (Diamond, 400 points)

## Award Types

- **BEST_REVIEWER**: Top reviewer by reviews completed, quality, timeliness
- **RESEARCHER_OF_YEAR**: Most prolific researcher by publications
- **EDITOR_EXCELLENCE**: Outstanding editorial contributions
- **SPECIAL_RECOGNITION**: Custom awards for unique contributions

## Testing the Endpoints

### 1. Check Badges

```bash
curl http://localhost:8000/api/v1/achievements/badges/
```

### 2. Get Best Reviewer (requires auth token)

```bash
curl -H "Authorization: Bearer {token}" \
  http://localhost:8000/api/v1/achievements/awards/best-reviewer/{journal-id}/?year=2024
```

### 3. Get My Badges (requires auth token)

```bash
curl -H "Authorization: Bearer {token}" \
  http://localhost:8000/api/v1/achievements/user-badges/my_badges/
```

### 4. Verify Certificate (public)

```bash
curl http://localhost:8000/api/v1/achievements/certificates/verify/?code=A1B2C3D4
```

### 5. Top Reviewers Leaderboard

```bash
curl http://localhost:8000/api/v1/achievements/leaderboards/top_reviewers/?period=YEARLY&limit=10
```

## Database Schema

### Tables Created

1. `achievements_badge` - Badge definitions
2. `achievements_userbadge` - User-badge relationships
3. `achievements_award` - Award records
4. `achievements_leaderboard` - Leaderboard entries
5. `achievements_certificate` - Certificate records

### Key Indexes

- Awards: year+type, journal+year, recipient
- UserBadge: profile+earned_at, badge+year
- Leaderboard: category+period+score, journal+category+period, field+category+period
- Certificate: verification_code, certificate_number, recipient+issued_date

### Unique Constraints

- Award: (journal, award_type, year, recipient)
- Leaderboard: (profile, category, period, period_start, period_end, journal, field, country)

## Integration with Existing Apps

### With Reviews App

- Signals listen to `ReviewAssignment.post_save`
- Auto-awards badges when reviews completed
- Best reviewer calculation uses `ReviewAssignment` model

### With Submissions App

- Signals listen to `Submission.post_save`
- Auto-awards badges when papers accepted/published
- Researcher of year calculation uses `Submission` model

### With Journals App

- Awards and leaderboards can be filtered by journal
- Journal-specific recognition

### With Users App

- All achievements linked to user profiles
- Profile-based leaderboards and badges

## Permissions Summary

| Endpoint                 | Permission                 |
| ------------------------ | -------------------------- |
| Badges (GET)             | Authenticated or ReadOnly  |
| Badges (POST/PUT/DELETE) | Admin                      |
| User Badges (GET)        | Authenticated (own badges) |
| Awards (GET)             | Authenticated or ReadOnly  |
| Awards (POST/PUT/DELETE) | Admin                      |
| Leaderboards (GET)       | Authenticated or ReadOnly  |
| Certificates (GET)       | Authenticated (own certs)  |
| Certificate Verify (GET) | Public (no auth)           |

## Admin Features

All models available in Django admin at `/admin/`:

- Create custom badges
- Manually assign awards
- View all user achievements
- Manage leaderboards
- Generate certificates
- Filter and search all records

## Next Steps for Production

1. **Implement PDF Generation**

   - Use ReportLab or WeasyPrint
   - Create certificate templates
   - Add signature images

2. **Add Email Notifications**

   - Send when badges earned
   - Send when awards received
   - Certificate ready notifications

3. **Create Leaderboard Calculation Task**

   - Celery periodic task
   - Auto-calculate monthly/quarterly/yearly
   - Update all leaderboard entries

4. **Add Analytics Dashboard**

   - Badge distribution charts
   - Award history timeline
   - Leaderboard trends

5. **Social Features**
   - Shareable badge images
   - Public achievement profiles
   - Achievement wall of fame

## Documentation

Full documentation available in: `apps/achievements/README.md`

## Status

- All models created and migrated
- All ViewSets and endpoints working
- Auto-badge assignment via signals
- Best reviewer/researcher calculations
- Certificate generation and verification
- Admin interfaces configured
- URLs registered
- Server running successfully
