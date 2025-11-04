# Anomaly Detection System - Complete Guide

## Table of Contents

1. [Overview](#overview)
2. [How It Works](#how-it-works)
3. [Detection Methods](#detection-methods)
4. [API Endpoints](#api-endpoints)
5. [Permission System](#permission-system)
6. [Implementation Guide](#implementation-guide)
7. [Configuration](#configuration)
8. [Testing](#testing)
9. [Troubleshooting](#troubleshooting)

---

## Overview

The Anomaly Detection System is a **rule-based machine learning** security feature that identifies suspicious patterns and potential fraud in your journal submission and review process. It acts as an automated security guard that continuously monitors for:

- **Author Misbehavior**: Spam submissions, fake accounts, citation manipulation
- **Reviewer Misconduct**: Bias, rushed reviews, collusion
- **System-Wide Fraud**: Review rings, coordinated schemes

### Key Features

 **7 Detection Methods** - Comprehensive fraud detection  
 **Risk Scoring** - LOW/MEDIUM/HIGH risk levels for users  
 **REST API** - 4 endpoints with OpenAPI documentation  
 **Role-Based Access** - Admin/Editor only for security  
 **Real-Time Checks** - Instant anomaly detection  
 **No Training Required** - Rule-based, works immediately  

---

## How It Works

### System Architecture

```
┌─────────────────────┐
│  Frontend/Client    │
│  (Admin Dashboard)  │
└──────────┬──────────┘
           │ HTTP Request (JWT Auth)
           ▼
┌─────────────────────────────────────────┐
│  Django REST API                        │
│  /api/v1/ml/anomaly-detection/...      │
│  - Authentication Check                 │
│  - Permission Check (Admin/Editor)      │
└──────────┬──────────────────────────────┘
           │ Calls Detection Engine
           ▼
┌─────────────────────────────────────────┐
│  AnomalyDetectionEngine                 │
│  - Query database                       │
│  - Analyze patterns                     │
│  - Calculate statistics                 │
│  - Apply thresholds                     │
│  - Calculate risk scores                │
└──────────┬──────────────────────────────┘
           │ Reads from
           ▼
┌─────────────────────────────────────────┐
│  PostgreSQL Database                    │
│  - Submissions (created_at, metadata)   │
│  - Reviews (completion times, decisions)│
│  - Users (profiles, activity)           │
│  - ReviewAssignments (relationships)    │
└─────────────────────────────────────────┘
```

### Detection Flow

1. **Data Collection** - System queries database for relevant records
2. **Pattern Analysis** - Applies statistical analysis and graph algorithms
3. **Threshold Comparison** - Compares patterns against configurable thresholds
4. **Anomaly Creation** - Creates anomaly records with severity levels
5. **Risk Calculation** - Aggregates anomalies into user risk scores
6. **Response** - Returns JSON with anomalies and recommendations

---

## Detection Methods

### 1. Rapid Submissions (HIGH Severity)

**What it detects**: Authors submitting too many papers in a short time

**Threshold**: 5+ submissions in 24 hours

**Why it matters**: Indicates spam, bot activity, or gaming the system

**Example**:
```json
{
  "type": "RAPID_SUBMISSIONS",
  "severity": "HIGH",
  "author": "spammer@example.com",
  "count": 7,
  "window_hours": 24,
  "description": "Author submitted 7 papers in 24 hours",
  "recommendation": "Review for potential spam or bot activity"
}
```

### 2. Excessive Self-Citations (MEDIUM Severity)

**What it detects**: Papers with abnormally high self-citation rates

**Threshold**: >30% self-citations (minimum 10 references required)

**Why it matters**: Citation manipulation to inflate impact metrics

**Example**:
```json
{
  "type": "EXCESSIVE_SELF_CITATIONS",
  "severity": "MEDIUM",
  "self_citation_count": 14,
  "total_citations": 40,
  "rate": 0.35,
  "description": "35% self-citations (14/40)",
  "recommendation": "Review for citation manipulation"
}
```

### 3. Duplicate Content (HIGH Severity)

**What it detects**: Highly similar submission titles from same author

**Threshold**: 70%+ Jaccard similarity

**Why it matters**: Duplicate submissions, plagiarism, or resubmissions

**Example**:
```json
{
  "type": "DUPLICATE_CONTENT",
  "severity": "HIGH",
  "similar_submission_id": "uuid-123",
  "similarity_score": 0.85,
  "description": "Submission highly similar to another paper by same author",
  "recommendation": "Check for duplicate submission or plagiarism"
}
```

### 4. Bot Account (HIGH Severity)

**What it detects**: Fake or automated user accounts

**Factors checked**:
- Generic email patterns (test@, admin@, user123@)
- Incomplete profiles (no bio, no affiliation)
- Suspicious activity (too many submissions)
- Short account age with high activity

**Threshold**: Composite score >0.7

**Example**:
```json
{
  "type": "BOT_ACCOUNT",
  "severity": "HIGH",
  "suspicion_score": 0.8,
  "description": "Account shows bot-like patterns (score: 0.80)",
  "recommendation": "Verify account authenticity"
}
```

### 5. Biased Reviewer (MEDIUM Severity)

**What it detects**: Reviewers who consistently accept or reject papers

**Threshold**: >90% accept or reject rate (minimum 10 reviews)

**Why it matters**: Indicates bias, poor judgment, or collusion

**Example**:
```json
{
  "type": "BIASED_REVIEWER_ACCEPTS",
  "severity": "MEDIUM",
  "reviewer": "reviewer@example.com",
  "accept_rate": 0.95,
  "total_reviews": 20,
  "description": "Reviewer accepts 95% of submissions",
  "recommendation": "Review for potential bias or collusion"
}
```

### 6. Rushed Review (MEDIUM Severity)

**What it detects**: Reviews completed suspiciously quickly

**Threshold**: <1 hour completion time

**Why it matters**: May lack thoroughness, indicates fake reviews

**Example**:
```json
{
  "type": "RUSHED_REVIEW",
  "severity": "MEDIUM",
  "review_id": "uuid-456",
  "hours_taken": 0.5,
  "submission_title": "Paper Title",
  "description": "Review completed in 0.5 hours",
  "recommendation": "Verify review quality and thoroughness"
}
```

### 7. Review Ring (HIGH Severity)

**What it detects**: Mutual favorable reviews between users (collusion)

**Threshold**: 3+ reciprocal favorable reviews

**How it works**: Graph analysis to detect bidirectional review patterns

**Why it matters**: Strong indicator of academic fraud

**Example**:
```json
{
  "type": "REVIEW_RING",
  "severity": "HIGH",
  "user1": "user1@example.com",
  "user2": "user2@example.com",
  "reciprocal_reviews": 6,
  "description": "Mutual favorable reviews detected between users",
  "recommendation": "Investigate for potential collusion"
}
```

---

## API Endpoints

### Authentication

All endpoints require **JWT authentication**. Include token in Authorization header:

```http
Authorization: Bearer <your_jwt_token>
```

### 1. Comprehensive System Scan

**Endpoint**: `GET /api/v1/ml/anomaly-detection/scan/`

**Permission**: Admin/Editor only

**Description**: Runs a complete scan of the entire system for all anomaly types

**Response**:
```json
{
  "scan_completed_at": "2025-11-04T10:30:00Z",
  "total_anomalies": 15,
  "severity_counts": {
    "HIGH": 5,
    "MEDIUM": 7,
    "LOW": 3
  },
  "author_anomalies": [
    {
      "type": "RAPID_SUBMISSIONS",
      "severity": "HIGH",
      "author": "user@example.com",
      "author_id": "uuid",
      "count": 7,
      "window_hours": 24,
      "description": "Author submitted 7 papers in 24 hours",
      "recommendation": "Review for potential spam or bot activity"
    }
  ],
  "reviewer_anomalies": [
    {
      "type": "BIASED_REVIEWER_ACCEPTS",
      "severity": "MEDIUM",
      "reviewer": "reviewer@example.com",
      "reviewer_id": "uuid",
      "accept_rate": 0.95,
      "total_reviews": 20,
      "description": "Reviewer accepts 95% of submissions",
      "recommendation": "Review for potential bias or collusion"
    }
  ],
  "review_ring_anomalies": [
    {
      "type": "REVIEW_RING",
      "severity": "HIGH",
      "user1": "user1@example.com",
      "user1_id": "uuid",
      "user2": "user2@example.com",
      "user2_id": "uuid",
      "reciprocal_reviews": 6,
      "description": "Mutual favorable reviews detected between users",
      "recommendation": "Investigate for potential collusion"
    }
  ]
}
```

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/v1/ml/anomaly-detection/scan/" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 2. User Risk Score

**Endpoint**: `GET /api/v1/ml/anomaly-detection/user/<user_id>/`

**Permission**: User can view own score, Admin/Editor can view all

**Description**: Calculates a risk score (0-1) for a specific user

**Risk Levels**:
- **LOW** (0.0 - 0.39): Normal behavior
- **MEDIUM** (0.4 - 0.69): Some suspicious patterns
- **HIGH** (0.7 - 1.0): Multiple red flags

**Response**:
```json
{
  "user_email": "user@example.com",
  "user_id": "uuid",
  "risk_score": 0.6,
  "risk_level": "MEDIUM",
  "anomaly_count": 3,
  "anomalies": [
    {
      "type": "RAPID_SUBMISSIONS",
      "severity": "HIGH",
      "description": "Author submitted 7 papers in 24 hours"
    },
    {
      "type": "EXCESSIVE_SELF_CITATIONS",
      "severity": "MEDIUM",
      "rate": 0.35,
      "description": "35% self-citations (14/40)"
    }
  ]
}
```

**Example Request**:
```bash
curl -X GET "http://localhost:8000/api/v1/ml/anomaly-detection/user/<USER_ID>/" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. Submission Anomalies

**Endpoint**: `GET /api/v1/ml/anomaly-detection/submission/<submission_id>/`

**Permission**: Admin/Editor only

**Description**: Checks a specific submission for anomalies

**Response**:
```json
{
  "submission_id": "uuid",
  "submission_title": "Sample Paper Title",
  "author": "author@example.com",
  "anomaly_count": 2,
  "anomalies": [
    {
      "type": "EXCESSIVE_SELF_CITATIONS",
      "severity": "MEDIUM",
      "self_citation_count": 14,
      "total_citations": 40,
      "rate": 0.35,
      "description": "35% self-citations (14/40)",
      "recommendation": "Review for citation manipulation"
    },
    {
      "type": "DUPLICATE_CONTENT",
      "severity": "HIGH",
      "similar_submission_id": "other-uuid",
      "similarity_score": 0.85,
      "description": "Submission highly similar to another paper",
      "recommendation": "Check for duplicate submission"
    }
  ]
}
```

### 4. Reviewer Anomalies

**Endpoint**: `GET /api/v1/ml/anomaly-detection/reviewer/<reviewer_id>/`

**Permission**: Admin/Editor only

**Description**: Checks a reviewer's behavior for anomalies

**Response**:
```json
{
  "reviewer_id": "uuid",
  "reviewer_email": "reviewer@example.com",
  "anomaly_count": 2,
  "anomalies": [
    {
      "type": "BIASED_REVIEWER_ACCEPTS",
      "severity": "MEDIUM",
      "accept_rate": 0.95,
      "total_reviews": 20,
      "description": "Reviewer accepts 95% of submissions",
      "recommendation": "Review for potential bias or collusion"
    },
    {
      "type": "RUSHED_REVIEW",
      "severity": "MEDIUM",
      "review_id": "uuid",
      "hours_taken": 0.5,
      "description": "Review completed in 0.5 hours",
      "recommendation": "Verify review quality"
    }
  ]
}
```

---

## Permission System

### Access Control Summary

| Endpoint | Who Can Access | Purpose |
|----------|----------------|---------|
| **Comprehensive Scan** | ⚠️ Admin/Editor ONLY | System-wide security overview |
| **Submission Check** | ⚠️ Admin/Editor ONLY | Fraud detection before publication |
| **Reviewer Check** | ⚠️ Admin/Editor ONLY | Reviewer quality control |
| **User Risk Score** |  User (own) + Admin/Editor (all) | Transparency + moderation |

### Who Has Admin/Editor Access?

**Admins**:
- `user.is_superuser = True` OR
- `user.profile.role = 'admin'`

**Editors**:
- `user.profile.role = 'editor'` OR
- `user.profile.role = 'chief_editor'` OR
- `user.is_staff = True`

**Regular Users**:
- Can only view their **own** risk score
- Cannot access comprehensive scans
- Cannot check other users' anomalies

### Permission Classes

The system uses 3 custom permission classes in `apps/ml/permissions.py`:

#### 1. IsAdminOrEditor
```python
# Used for: Comprehensive scans, submission checks, reviewer checks
# Allows: Superusers, staff, and users with 'editor'/'admin' role
```

#### 2. CanViewOwnRiskScore
```python
# Used for: User risk score endpoint
# Allows: 
#   - Users to view their own risk score
#   - Admins/editors to view anyone's risk score
```

#### 3. IsAdminOnly
```python
# Available for highly sensitive operations
# Allows: Only superusers and users with 'admin' role
```

### API Response Examples

####  Admin Accessing Scan
```bash
curl -X GET "http://localhost:8000/api/v1/ml/anomaly-detection/scan/" \
  -H "Authorization: Bearer <admin_token>"

# Response: 200 OK
{
  "total_anomalies": 15,
  "severity_counts": {...}
}
```

#### ❌ Regular User Accessing Scan
```bash
curl -X GET "http://localhost:8000/api/v1/ml/anomaly-detection/scan/" \
  -H "Authorization: Bearer <user_token>"

# Response: 403 Forbidden
{
  "detail": "You must be an admin or editor to access this resource."
}
```

####  User Viewing Own Risk Score
```bash
curl -X GET "http://localhost:8000/api/v1/ml/anomaly-detection/user/<own_id>/" \
  -H "Authorization: Bearer <user_token>"

# Response: 200 OK
{
  "user_email": "user@example.com",
  "risk_score": 0.0,
  "risk_level": "LOW"
}
```

#### ❌ User Viewing Someone Else's Risk Score
```bash
curl -X GET "http://localhost:8000/api/v1/ml/anomaly-detection/user/<other_id>/" \
  -H "Authorization: Bearer <user_token>"

# Response: 403 Forbidden
{
  "detail": "You do not have permission to perform this action."
}
```

---

## Implementation Guide

### Scenario 1: Daily Automated Monitoring

**Goal**: Run daily scans to catch suspicious activity early

**Step 1: Create Django Management Command**

```python
# apps/ml/management/commands/scan_anomalies.py
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from apps.ml.anomaly_detection import AnomalyDetectionEngine

class Command(BaseCommand):
    help = 'Run daily anomaly detection scan'
    
    def handle(self, *args, **options):
        engine = AnomalyDetectionEngine()
        results = engine.scan_all()
        
        self.stdout.write(f"Found {results['total_count']} anomalies")
        
        # Alert on high-severity issues
        if results['severity_counts']['HIGH'] > 0:
            self.send_alert_email(results)
    
    def send_alert_email(self, results):
        """Send email alert to admins."""
        high_severity = results['severity_counts']['HIGH']
        send_mail(
            subject=f'⚠️ {high_severity} High-Severity Anomalies Detected',
            message=f'Review immediately: {high_severity} high-severity issues found.',
            from_email='system@journal.com',
            recipient_list=['admin@journal.com'],
        )
```

**Step 2: Schedule with Cron or Task Scheduler**

```bash
# Linux/Mac - Add to crontab
0 2 * * * cd /path/to/project && python manage.py scan_anomalies

# Windows - Task Scheduler
schtasks /create /tn "Anomaly Scan" /tr "python manage.py scan_anomalies" /sc daily /st 02:00
```

**Step 3: Or Use Celery**

```python
# apps/ml/tasks.py
from celery import shared_task
from apps.ml.anomaly_detection import AnomalyDetectionEngine

@shared_task
def daily_anomaly_scan():
    engine = AnomalyDetectionEngine()
    results = engine.scan_all()
    # Process results...
    return results

# In settings.py
from celery.schedules import crontab

CELERYBEAT_SCHEDULE = {
    'daily-anomaly-scan': {
        'task': 'apps.ml.tasks.daily_anomaly_scan',
        'schedule': crontab(hour=2, minute=0),
    },
}
```

### Scenario 2: Real-Time Dashboard

**Frontend (React/Next.js)**:

```typescript
// components/AnomalyDashboard.tsx
import { useState, useEffect } from 'react';

interface ScanResults {
  total_anomalies: number;
  severity_counts: {
    HIGH: number;
    MEDIUM: number;
    LOW: number;
  };
  scan_completed_at: string;
}

export default function AnomalyDashboard() {
  const [scanData, setScanData] = useState<ScanResults | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAnomalies();
    // Refresh every 5 minutes
    const interval = setInterval(fetchAnomalies, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const fetchAnomalies = async () => {
    try {
      const response = await fetch('/api/v1/ml/anomaly-detection/scan/', {
        headers: {
          'Authorization': `Bearer ${getAccessToken()}`,
        },
      });
      const data = await response.json();
      setScanData(data);
      setLoading(false);
    } catch (error) {
      console.error('Failed to fetch anomalies:', error);
      setLoading(false);
    }
  };

  if (loading) return <div>Loading anomaly scan...</div>;

  return (
    <div className="anomaly-dashboard">
      <h2>Security Anomalies</h2>
      
      <div className="stats-grid">
        <div className="stat-card">
          <h3>{scanData?.total_anomalies || 0}</h3>
          <p>Total Anomalies</p>
        </div>
        
        <div className="stat-card danger">
          <h3>{scanData?.severity_counts.HIGH || 0}</h3>
          <p>High Severity</p>
        </div>
        
        <div className="stat-card warning">
          <h3>{scanData?.severity_counts.MEDIUM || 0}</h3>
          <p>Medium Severity</p>
        </div>
        
        <div className="stat-card info">
          <h3>{scanData?.severity_counts.LOW || 0}</h3>
          <p>Low Severity</p>
        </div>
      </div>
      
      {scanData?.severity_counts.HIGH > 0 && (
        <div className="alert alert-danger">
          ⚠️ {scanData.severity_counts.HIGH} high-severity anomalies require immediate attention!
        </div>
      )}
      
      <p className="last-scan">
        Last scan: {new Date(scanData?.scan_completed_at || '').toLocaleString()}
      </p>
      
      <button onClick={fetchAnomalies}>Refresh Scan</button>
    </div>
  );
}

function getAccessToken() {
  return document.cookie.split('; ')
    .find(row => row.startsWith('access_token='))
    ?.split('=')[1] || '';
}
```

### Scenario 3: Pre-Publication Check

**Goal**: Block publication if fraud detected

```python
# apps/submissions/views.py
from rest_framework.decorators import action
from apps.ml.anomaly_detection import AnomalyDetectionEngine

class SubmissionViewSet(viewsets.ModelViewSet):
    
    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Publish submission after anomaly check."""
        submission = self.get_object()
        
        # Run anomaly check BEFORE publishing
        engine = AnomalyDetectionEngine()
        anomalies = engine.scan_submission(submission)
        
        # Block if HIGH severity anomalies found
        high_severity = [a for a in anomalies if a['severity'] == 'HIGH']
        if high_severity:
            return Response({
                'error': 'Cannot publish: High-severity anomalies detected',
                'anomalies': high_severity
            }, status=400)
        
        # Proceed with publication
        submission.status = 'PUBLISHED'
        submission.published_at = timezone.now()
        submission.save()
        
        return Response({'message': 'Published successfully'})
```

### Scenario 4: Reviewer Assignment Verification

**Goal**: Check reviewers before assigning

```python
# apps/reviews/views.py
class ReviewAssignmentViewSet(viewsets.ModelViewSet):
    
    def create(self, request, *args, **kwargs):
        """Create assignment with anomaly check."""
        reviewer_id = request.data.get('reviewer_id')
        
        # Check reviewer for anomalies
        engine = AnomalyDetectionEngine()
        reviewer_profile = Profile.objects.get(id=reviewer_id)
        anomalies = engine.scan_reviewer(reviewer_profile)
        
        # Warn if anomalies found
        if anomalies:
            return Response({
                'warning': 'Reviewer has anomalies on record',
                'anomalies': anomalies,
                'proceed_anyway': False
            }, status=400)
        
        return super().create(request, *args, **kwargs)
```

### Scenario 5: User Registration Validation

**Goal**: Detect bot accounts during registration

```python
# apps/users/views.py
class UserRegistrationView(APIView):
    
    def post(self, request):
        """Register new user with bot detection."""
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.save()
        
        # Check for bot patterns
        engine = AnomalyDetectionEngine()
        bot_check = engine.detect_bot_account(user.profile)
        
        if bot_check:
            # Flag for manual review
            user.profile.requires_manual_verification = True
            user.profile.save()
            
            return Response({
                'message': 'Registration successful. Account pending verification.',
                'verification_required': True
            }, status=201)
        
        return Response({
            'message': 'Registration successful'
        }, status=201)
```

### Python API Client

```python
# utils/anomaly_client.py
import requests

class AnomalyDetectionClient:
    """Client for interacting with anomaly detection API."""
    
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    def comprehensive_scan(self):
        """Run full system scan."""
        response = requests.get(
            f'{self.base_url}/api/v1/ml/anomaly-detection/scan/',
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def get_user_risk(self, user_id: str):
        """Get risk score for specific user."""
        response = requests.get(
            f'{self.base_url}/api/v1/ml/anomaly-detection/user/{user_id}/',
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def check_submission(self, submission_id: str):
        """Check specific submission."""
        response = requests.get(
            f'{self.base_url}/api/v1/ml/anomaly-detection/submission/{submission_id}/',
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def check_reviewer(self, reviewer_id: str):
        """Check specific reviewer."""
        response = requests.get(
            f'{self.base_url}/api/v1/ml/anomaly-detection/reviewer/{reviewer_id}/',
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()

# Usage
client = AnomalyDetectionClient('http://localhost:8000', 'your_jwt_token')
scan_results = client.comprehensive_scan()
print(f"Total anomalies: {scan_results['total_anomalies']}")
```

---

## Configuration

### Adjusting Detection Thresholds

Edit `apps/ml/anomaly_detection.py`:

```python
class AnomalyDetectionEngine:
    # Customize these values
    RAPID_SUBMISSION_THRESHOLD = 5  # submissions in 24 hours
    RAPID_SUBMISSION_WINDOW = 24  # hours
    
    HIGH_SELF_CITATION_THRESHOLD = 0.3  # 30% self-citations
    
    SUSPICIOUS_REVIEW_RATE_THRESHOLD = 0.9  # 90% accept/reject
    MIN_REVIEWS_FOR_PATTERN = 10
    
    REVIEW_RING_MIN_RECIPROCAL = 3  # minimum reciprocal reviews
    
    SUSPICIOUS_ACTIVITY_SCORE_THRESHOLD = 0.7  # bot detection
    
    DUPLICATE_SIMILARITY_THRESHOLD = 0.7  # 70% similarity
    
    RUSHED_REVIEW_HOURS = 1  # minimum review time
```

### Risk Score Calculation

Risk scores are calculated by summing anomaly weights:

- **HIGH severity**: 0.4 per anomaly
- **MEDIUM severity**: 0.2 per anomaly
- **LOW severity**: 0.1 per anomaly

**Risk Levels**:
- **LOW**: 0.0 - 0.39
- **MEDIUM**: 0.4 - 0.69
- **HIGH**: 0.7 - 1.0

---

## Testing

### Direct Engine Testing

Run the direct engine test:

```bash
python qa/test_anomaly_detection.py
```

This tests the detection engine directly without HTTP layer.

### API Endpoint Testing

Run the API endpoint test:

```bash
python qa/test_anomaly_api.py
```

This tests all 4 REST API endpoints via HTTP requests.

### Permission Testing

Run the permission test:

```bash
python qa/test_anomaly_permissions.py
```

This verifies role-based access control is working correctly.

### Manual Testing with cURL

```bash
# Get authentication token
curl -X POST "http://localhost:8000/api/v1/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}'

# Save the access token and use it:
TOKEN="your_access_token_here"

# Run comprehensive scan
curl -X GET "http://localhost:8000/api/v1/ml/anomaly-detection/scan/" \
  -H "Authorization: Bearer $TOKEN"

# Check user risk score
curl -X GET "http://localhost:8000/api/v1/ml/anomaly-detection/user/<USER_ID>/" \
  -H "Authorization: Bearer $TOKEN"

# Check submission
curl -X GET "http://localhost:8000/api/v1/ml/anomaly-detection/submission/<SUBMISSION_ID>/" \
  -H "Authorization: Bearer $TOKEN"

# Check reviewer
curl -X GET "http://localhost:8000/api/v1/ml/anomaly-detection/reviewer/<REVIEWER_ID>/" \
  -H "Authorization: Bearer $TOKEN"
```

### Manual Testing with PowerShell

```powershell
# Login and get token
$login = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/login/" `
  -Method POST `
  -Body (@{email="admin@example.com"; password="admin123"} | ConvertTo-Json) `
  -ContentType "application/json"

$token = $login.access

# Run comprehensive scan
$scan = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/ml/anomaly-detection/scan/" `
  -Method GET `
  -Headers @{Authorization="Bearer $token"}

Write-Host "Total anomalies: $($scan.total_anomalies)"
Write-Host "High severity: $($scan.severity_counts.HIGH)"
```

---

## Troubleshooting

### Issue: No Anomalies Detected

**Possible Causes**:
- System is working correctly (no suspicious activity)
- Thresholds are too high
- Insufficient data

**Solutions**:
1. Check if sufficient data exists:
   ```python
   from apps.submissions.models import Submission
   from apps.reviews.models import Review
   
   print(f"Submissions: {Submission.objects.count()}")
   print(f"Reviews: {Review.objects.count()}")
   ```

2. Lower thresholds for testing:
   ```python
   engine.RAPID_SUBMISSION_THRESHOLD = 2  # More sensitive
   ```

3. Run direct engine tests to see detailed output

### Issue: 403 Forbidden Errors

**Possible Causes**:
- User doesn't have admin/editor permissions
- JWT token expired
- User profile missing

**Solutions**:
1. Check user permissions:
   ```python
   from django.contrib.auth import get_user_model
   User = get_user_model()
   
   user = User.objects.get(email='your@email.com')
   print(f"Superuser: {user.is_superuser}")
   print(f"Staff: {user.is_staff}")
   print(f"Role: {user.profile.role if hasattr(user, 'profile') else 'No profile'}")
   ```

2. Grant admin access:
   ```python
   user.is_staff = True  # Makes them editor
   user.save()
   
   # OR
   
   user.profile.role = 'admin'
   user.profile.save()
   ```

3. Get a fresh token:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/auth/login/" \
     -H "Content-Type: application/json" \
     -d '{"email":"admin@example.com","password":"admin123"}'
   ```

### Issue: 500 Internal Server Error

**Possible Causes**:
- Database connection issue
- Missing profile for user
- Bug in detection logic

**Solutions**:
1. Check Django server logs for stack trace

2. Verify database connectivity:
   ```bash
   python manage.py dbshell
   ```

3. Check if profiles exist:
   ```python
   from apps.users.models import Profile
   print(f"Profiles: {Profile.objects.count()}")
   ```

4. Test with detailed error logging:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

### Issue: Slow Scan Performance

**Possible Causes**:
- Large database
- Missing database indexes
- Complex queries

**Solutions**:
1. Add database indexes:
   ```python
   # In models.py
   class Submission(models.Model):
       class Meta:
           indexes = [
               models.Index(fields=['created_at']),
               models.Index(fields=['corresponding_author']),
           ]
   ```

2. Run scans during off-peak hours

3. Use Celery for background processing

4. Cache frequent queries:
   ```python
   from django.core.cache import cache
   
   risk_score = cache.get(f'risk_{user_id}')
   if not risk_score:
       risk_score = engine.get_user_risk_score(profile)
       cache.set(f'risk_{user_id}', risk_score, timeout=3600)
   ```

### Issue: False Positives

**Possible Causes**:
- Legitimate behavior triggering thresholds
- Special circumstances (conferences, special issues)

**Solutions**:
1. Adjust thresholds higher:
   ```python
   engine.RAPID_SUBMISSION_THRESHOLD = 10  # Less sensitive
   ```

2. Add context checking:
   ```python
   # Check if special issue submission
   if submission.special_issue:
       # Skip rapid submission check
       pass
   ```

3. Implement whitelist:
   ```python
   TRUSTED_USERS = ['trusted@university.edu']
   
   if user.email in TRUSTED_USERS:
       return []  # Skip anomaly checks
   ```

4. Manual review all anomalies before taking action

---

## Best Practices

###  DO

1. **Run Regular Scans** - Daily automated scans during off-peak hours
2. **Review Manually** - Always investigate before taking action
3. **Adjust Thresholds** - Tune for your journal's patterns
4. **Monitor Performance** - Cache frequently-checked scores
5. **Keep Logs** - Save scan results for audit trail
6. **Provide Transparency** - Let users see their own risk scores
7. **Document Decisions** - Record why actions were taken

### ❌ DON'T

1. **Auto-Ban Users** - Anomalies are flags, not proof
2. **Ignore Context** - Consider special circumstances
3. **Set Too Low** - Avoid overwhelming false positives
4. **Block Everything** - Allow appeals and manual override
5. **Skip Testing** - Always test before production
6. **Forget Privacy** - Protect user data appropriately

---

## File Structure

```
apps/
├── ml/
│   ├── anomaly_detection.py          # Core detection engine (~450 lines)
│   ├── permissions.py                # 3 permission classes
│   ├── views.py                      # 4 REST API views
│   ├── urls.py                       # URL routing
│   └── management/
│       └── commands/
│           └── scan_anomalies.py     # Daily scan command
│
qa/
├── test_anomaly_detection.py         # Direct engine tests
├── test_anomaly_api.py               # API endpoint tests
└── test_anomaly_permissions.py       # Permission tests
│
docs/
└── ANOMALY_DETECTION_COMPLETE_GUIDE.md  # This file
```

---

## Summary

### What's Included

 **7 Detection Methods** - Comprehensive fraud detection  
 **4 REST API Endpoints** - Full HTTP access  
 **Role-Based Permissions** - Admin/Editor security  
 **Risk Scoring System** - LOW/MEDIUM/HIGH levels  
 **Test Suite** - 3 test scripts included  
 **Documentation** - Complete implementation guide  

### Quick Start

1. **Test the system**:
   ```bash
   python qa/test_anomaly_permissions.py
   ```

2. **Access from frontend**:
   ```typescript
   const response = await fetch('/api/v1/ml/anomaly-detection/scan/', {
     headers: { 'Authorization': `Bearer ${token}` }
   });
   ```

3. **Set up daily scans**:
   ```bash
   # Add to crontab
   0 2 * * * python manage.py scan_anomalies
   ```

### Support

- **Test Scripts**: Run tests in `qa/` folder
- **API Docs**: Available at `/api/schema/swagger-ui/`
- **Django Logs**: Check server terminal for errors
- **Database**: Verify data exists with `python manage.py shell`

---

**System Status**:  Production Ready

**Last Updated**: November 4, 2025

**Version**: 1.0
