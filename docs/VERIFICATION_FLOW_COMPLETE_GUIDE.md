# Verification System - Complete Flow Guide

## Table of Contents

1. [Overview](#overview)
2. [User Journey - Step by Step](#user-journey---step-by-step)
3. [Admin Journey - Step by Step](#admin-journey---step-by-step)
4. [API Endpoints Reference](#api-endpoints-reference)
5. [Data Flow Diagrams](#data-flow-diagrams)
6. [Auto-Scoring System](#auto-scoring-system)
7. [Status Lifecycle](#status-lifecycle)
8. [Frontend Integration Examples](#frontend-integration-examples)

---

## Overview

The verification system validates user identities before granting them **Author** or **Reviewer** roles in the journal portal. It uses:

- **Rule-based auto-scoring** (0-100 points) to evaluate trustworthiness
- **ORCID integration** for identity verification
- **Admin review workflow** with approve/reject/request info actions
- **Supporting letter** from supervisor/institution for credential verification

### Key Roles

**User (Unverified)** → Submits verification request → **Admin** reviews → **User (Verified)** gains Author/Reviewer role

---

## User Journey - Step by Step

### Step 1: User Registration

**What happens**: User creates an account

**API Endpoint**:
```http
POST /api/v1/auth/register/
Content-Type: application/json

{
  "email": "researcher@university.edu",
  "password": "SecurePass123!",
  "first_name": "Jane",
  "last_name": "Smith"
}
```

**Response**:
```json
{
  "user": {
    "id": "uuid",
    "email": "researcher@university.edu",
    "first_name": "Jane",
    "last_name": "Smith"
  },
  "profile": {
    "id": "uuid",
    "verification_status": "UNVERIFIED",
    "roles": []
  },
  "tokens": {
    "access": "jwt_access_token",
    "refresh": "jwt_refresh_token"
  }
}
```

**Frontend Actions**:
- Save tokens (cookies or localStorage)
- Redirect to profile completion page

---

### Step 2: Complete Profile (Optional but Recommended)

**What happens**: User fills out profile to improve verification score

**API Endpoint**:
```http
PATCH /api/v1/users/profile/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "bio": "Researcher in Machine Learning",
  "affiliation": "Stanford University",
  "research_interests": "Deep Learning, Computer Vision, Natural Language Processing",
  "academic_position": "PhD Student"
}
```

**Response**:
```json
{
  "id": "uuid",
  "user": {
    "email": "researcher@university.edu",
    "first_name": "Jane",
    "last_name": "Smith"
  },
  "bio": "Researcher in Machine Learning",
  "affiliation": "Stanford University",
  "verification_status": "UNVERIFIED",
  "roles": []
}
```

**Information Auto-Grabbed**:
- Email domain (used for institutional email check)
- Profile completeness (research interests, position)

**Frontend Actions**:
- Show profile completion progress bar
- Highlight missing fields that boost verification score

---

### Step 3: Connect ORCID (Highly Recommended - 30 Points!)

**What happens**: User connects their ORCID iD for verification

**API Flow**:

**3a. Initiate ORCID Connection**:
```http
GET /api/v1/users/orcid/connect/
Authorization: Bearer {access_token}
```

**Response**:
```json
{
  "authorization_url": "https://orcid.org/oauth/authorize?client_id=...",
  "state": "random_state_token"
}
```

**Frontend Actions**:
- Open authorization_url in popup or redirect
- User logs into ORCID and authorizes

**3b. ORCID Callback** (handled by backend):
```http
GET /api/v1/users/orcid/callback/?code=auth_code&state=state_token
```

**Backend Actions**:
- Exchanges code for ORCID access token
- Fetches ORCID profile data
- Creates ORCIDIntegration record
- Status set to 'CONNECTED'

**3c. Check ORCID Status**:
```http
GET /api/v1/users/orcid/status/
Authorization: Bearer {access_token}
```

**Response**:
```json
{
  "connected": true,
  "orcid_id": "0000-0002-1234-5678",
  "status": "CONNECTED",
  "orcid_profile": {
    "name": "Jane Smith",
    "email": "researcher@university.edu"
  }
}
```

**Information Auto-Grabbed**:
- ORCID iD (0000-0002-1234-5678)
- Verified identity from ORCID
- Publications (if available)
- Institutional affiliations from ORCID

---

### Step 4: Submit Verification Request

**What happens**: User submits request with all information

**API Endpoint**:
```http
POST /api/v1/users/verification-requests/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "requested_roles": ["AUTHOR", "REVIEWER"],
  "affiliation": "Stanford University",
  "affiliation_email": "researcher@stanford.edu",
  "research_interests": "Deep Learning, Computer Vision, Natural Language Processing. Focus on transformer architectures and attention mechanisms.",
  "academic_position": "PhD Student",
  "supporting_letter": "Dear Verification Team,\n\nThis letter is to confirm that Jane Smith is a PhD student in the Computer Science Department at Stanford University under my supervision. She joined the program in Fall 2022 and her research focuses on deep learning and computer vision.\n\nSincerely,\nDr. Andrew Ng\nProfessor of Computer Science"
}
```

**Backend Actions (Automatic)**:
1. Creates VerificationRequest record
2. Checks if ORCID is connected
3. **Calculates auto-score** (0-100):
   - ORCID verified: 30 points ✅
   - stanford.edu email: 25 points ✅
   - "Stanford" in email: 15 points ✅
   - Research interests >50 chars: 10 points ✅
   - Academic position: 10 points ✅
   - Supporting letter >100 chars: 10 points ✅
   - **Total: 100/100** 🎉
4. Saves score_details JSON
5. Sets status to 'PENDING'

**Response**:
```json
{
  "id": "uuid",
  "status": "PENDING",
  "requested_roles": ["AUTHOR", "REVIEWER"],
  "auto_score": 100,
  "score_breakdown": [
    {
      "criterion": "ORCID Verification",
      "description": "Verified ORCID iD connected to account",
      "points_earned": 30,
      "points_possible": 30,
      "status": "completed",
      "weight": "highest"
    },
    {
      "criterion": "Institutional Email",
      "description": "Email from recognized academic domain",
      "points_earned": 25,
      "points_possible": 25,
      "status": "completed",
      "weight": "high"
    },
    {
      "criterion": "Email-Affiliation Match",
      "description": "Email domain matches claimed institution",
      "points_earned": 15,
      "points_possible": 15,
      "status": "completed",
      "weight": "medium"
    },
    {
      "criterion": "Research Interests",
      "description": "Detailed research interests provided",
      "points_earned": 10,
      "points_possible": 10,
      "status": "completed",
      "weight": "low"
    },
    {
      "criterion": "Academic Position",
      "description": "Academic position/title specified",
      "points_earned": 10,
      "points_possible": 10,
      "status": "completed",
      "weight": "low"
    },
    {
      "criterion": "Supporting Letter",
      "description": "Letter from supervisor/institution (100+ characters)",
      "points_earned": 10,
      "points_possible": 10,
      "status": "completed",
      "weight": "low"
    }
  ],
  "created_at": "2025-11-04T10:30:00Z",
  "message": "Verification request submitted successfully"
}
```

**Frontend Actions**:
- Show success message
- Display auto-score with breakdown
- Explain next steps (admin review)
- Redirect to verification status page

---

### Step 6: Check Verification Status

**What happens**: User monitors their request status

**API Endpoint**:
```http
GET /api/v1/users/verification/status/
Authorization: Bearer {access_token}
```

**Response (Pending)**:
```json
{
  "profile_status": "UNVERIFIED",
  "is_verified": false,
  "has_pending_request": true,
  "latest_request": {
    "id": "uuid",
    "status": "PENDING",
    "requested_roles": ["AUTHOR", "REVIEWER"],
    "auto_score": 100,
    "score_breakdown": [...],
    "created_at": "2025-11-04T10:30:00Z"
  },
  "orcid_connected": true,
  "roles": []
}
```

**Frontend Actions**:
- Show "Pending Review" badge
- Display estimated review time (24-48 hours)
- Show score breakdown
- Allow withdrawal option

---

### Step 7a: Additional Info Requested (If Needed)

**What happens**: Admin requests more information

**Notification**: User receives email/notification

**API Endpoint to Check**:
```http
GET /api/v1/users/verification-requests/{request_id}/
Authorization: Bearer {access_token}
```

**Response**:
```json
{
  "id": "uuid",
  "status": "INFO_REQUESTED",
  "requested_roles": ["AUTHOR", "REVIEWER"],
  "auto_score": 55,
  "additional_info_requested": "Please provide a letter from your supervisor confirming your PhD enrollment at Stanford University.",
  "created_at": "2025-11-04T10:30:00Z",
  "reviewed_by": {
    "email": "admin@journal.com"
  }
}
```

**User Response Endpoint**:
```http
POST /api/v1/users/verification-requests/{request_id}/respond/
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "response": "I have attached the enrollment letter from my supervisor Dr. Andrew Ng. The letter confirms my PhD enrollment and expected graduation date."
}
```

**Response**:
```json
{
  "detail": "Response submitted successfully",
  "status": "PENDING"
}
```

**Frontend Actions**:
- Show info request notification
- Display admin's message
- Provide text area for response
- Change status back to PENDING

---

### Step 7b: Verification Approved ✅

**What happens**: Admin approves the request

**Notification**: User receives approval email

**API Endpoint to Check**:
```http
GET /api/v1/users/verification/status/
Authorization: Bearer {access_token}
```

**Response**:
```json
{
  "profile_status": "GENUINE",
  "is_verified": true,
  "has_pending_request": false,
  "latest_request": {
    "id": "uuid",
    "status": "APPROVED",
    "requested_roles": ["AUTHOR", "REVIEWER"],
    "auto_score": 100,
    "created_at": "2025-11-04T10:30:00Z",
    "reviewed_at": "2025-11-04T15:45:00Z",
    "reviewed_by": {
      "email": "admin@journal.com"
    }
  },
  "orcid_connected": true,
  "roles": ["Author", "Reviewer"]
}
```

**Information Auto-Grabbed on Approval**:
- Profile verification_status → "GENUINE"
- Roles added: Author and/or Reviewer
- Reviewed timestamp
- Admin who approved

**Frontend Actions**:
- Show success celebration 🎉
- Display new roles
- Enable submission features
- Enable reviewer features
- Show "Verified" badge

---

### Step 7c: Verification Rejected ❌

**What happens**: Admin rejects the request

**Notification**: User receives rejection email

**API Response**:
```json
{
  "profile_status": "UNVERIFIED",
  "is_verified": false,
  "has_pending_request": false,
  "latest_request": {
    "id": "uuid",
    "status": "REJECTED",
    "requested_role": "BOTH",
    "auto_score": 20,
    "rejection_reason": "The provided email address could not be verified as belonging to an academic institution. Please use your institutional email or provide additional documentation.",
    "created_at": "2025-11-04T10:30:00Z",
    "reviewed_at": "2025-11-04T15:45:00Z"
  },
  "orcid_connected": false,
  "roles": []
}
```

**Frontend Actions**:
- Show rejection message
- Display rejection reason
- Offer to submit new request
- Suggest improvements (connect ORCID, use institutional email)

---

## Admin Journey - Step by Step

### Step 1: Admin Login

**API Endpoint**:
```http
POST /api/v1/auth/login/
Content-Type: application/json

{
  "email": "admin@journal.com",
  "password": "AdminPass123!"
}
```

**Response**:
```json
{
  "access": "jwt_access_token",
  "refresh": "jwt_refresh_token",
  "user": {
    "email": "admin@journal.com",
    "is_staff": true,
    "is_superuser": true
  }
}
```

---

### Step 2: View Pending Verification Requests

**API Endpoint - All Pending**:
```http
GET /api/v1/users/admin/verification-requests/pending_review/
Authorization: Bearer {admin_access_token}
```

**Response**:
```json
{
  "count": 15,
  "results": [
    {
      "id": "uuid-1",
      "profile": {
        "user": {
          "email": "researcher@stanford.edu",
          "name": "Jane Smith"
        }
      },
      "requested_role": "BOTH",
      "status": "PENDING",
      "auto_score": 100,
      "affiliation": "Stanford University",
      "affiliation_email": "researcher@stanford.edu",
      "orcid_verified": true,
      "orcid_id": "0000-0002-1234-5678",
      "created_at": "2025-11-04T10:30:00Z"
    },
    {
      "id": "uuid-2",
      "profile": {
        "user": {
          "email": "user123@gmail.com",
          "name": "John Doe"
        }
      },
      "requested_role": "AUTHOR",
      "status": "PENDING",
      "auto_score": 25,
      "affiliation": "Unknown University",
      "affiliation_email": "user123@gmail.com",
      "orcid_verified": false,
      "created_at": "2025-11-03T14:20:00Z"
    }
  ]
}
```

**API Endpoint - High Score (Fast Track)**:
```http
GET /api/v1/users/admin/verification-requests/high_score/
Authorization: Bearer {admin_access_token}
```

**Response**: Same format, filtered for auto_score >= 70

**Frontend Actions**:
- Display table sorted by auto_score (high to low)
- Show color-coded score badges:
  - 🟢 Green: 70-100 (High Trust)
  - 🟡 Yellow: 40-69 (Medium Trust)
  - 🔴 Red: 0-39 (Low Trust)
- Filter by status, role, date
- Search by email, affiliation

---

### Step 3: Review Individual Request

**API Endpoint**:
```http
GET /api/v1/users/admin/verification-requests/{request_id}/
Authorization: Bearer {admin_access_token}
```

**Response**:
```json
{
  "id": "uuid",
  "profile": {
    "id": "uuid",
    "user": {
      "email": "researcher@stanford.edu",
      "first_name": "Jane",
      "last_name": "Smith",
      "date_joined": "2025-11-01T09:00:00Z"
    },
    "bio": "Researcher in Machine Learning",
    "affiliation": "Stanford University",
    "research_interests": "Deep Learning, Computer Vision",
    "verification_status": "UNVERIFIED"
  },
  "requested_role": "BOTH",
  "status": "PENDING",
  "affiliation": "Stanford University",
  "affiliation_email": "researcher@stanford.edu",
  "research_interests": "Deep Learning, Computer Vision, Natural Language Processing. Focus on transformer architectures.",
  "academic_position": "PhD Student",
  "supporting_letter": "Dear Verification Team,\n\nThis letter confirms that Jane Smith is a PhD student under my supervision in the Computer Science Department at Stanford University...",
  "orcid_verified": true,
  "orcid_id": "0000-0002-1234-5678",
  "auto_score": 100,
  "score_details": {
    "orcid": 30,
    "institutional_email": 25,
    "email_affiliation_match": 15,
    "research_interests": 10,
    "academic_position": 10,
    "supporting_letter": 10
  },
  "created_at": "2025-11-04T10:30:00Z"
}
```

**Frontend Actions**:
- Display user profile information
- Show ORCID verification badge
- Display score breakdown with visual bars
- Show supporting letter content
- Provide action buttons: Approve, Reject, Request Info

---

### Step 4a: Approve Request ✅

**API Endpoint**:
```http
POST /api/v1/users/admin/verification-requests/{request_id}/approve/
Authorization: Bearer {admin_access_token}
Content-Type: application/json

{
  "admin_notes": "All credentials verified. ORCID confirmed, Stanford email verified."
}
```

**Backend Actions (Automatic)**:
1. Sets status to 'APPROVED'
2. Records admin and timestamp
3. Updates profile.verification_status to 'GENUINE'
4. Adds roles to profile:
   - If requested_role = 'AUTHOR': Adds Author role
   - If requested_role = 'REVIEWER': Adds Reviewer role
   - If requested_role = 'BOTH': Adds both roles
5. Sends approval email to user

**Response**:
```json
{
  "detail": "Verification approved",
  "profile_status": "GENUINE",
  "roles_granted": "BOTH"
}
```

**Frontend Actions**:
- Show success message
- Remove from pending list
- Update request status to APPROVED
- Show approval timestamp

---

### Step 4b: Reject Request ❌

**API Endpoint**:
```http
POST /api/v1/users/admin/verification-requests/{request_id}/reject/
Authorization: Bearer {admin_access_token}
Content-Type: application/json

{
  "rejection_reason": "Unable to verify institutional affiliation. The email provided is not from a recognized academic domain.",
  "admin_notes": "Gmail address used, no ORCID, no supporting documents."
}
```

**Backend Actions (Automatic)**:
1. Sets status to 'REJECTED'
2. Records admin, timestamp, and reason
3. Profile remains 'UNVERIFIED'
4. Sends rejection email to user with reason

**Response**:
```json
{
  "detail": "Verification rejected",
  "reason": "Unable to verify institutional affiliation..."
}
```

**Frontend Actions**:
- Show rejection confirmation
- Remove from pending list
- Update status to REJECTED

---

### Step 4c: Request Additional Information ℹ️

**API Endpoint**:
```http
POST /api/v1/users/admin/verification-requests/{request_id}/request_info/
Authorization: Bearer {admin_access_token}
Content-Type: application/json

{
  "additional_info_requested": "Please provide a letter from your supervisor confirming your enrollment as a PhD student at Stanford University.",
  "admin_notes": "Need confirmation of PhD enrollment"
}
```

**Backend Actions (Automatic)**:
1. Sets status to 'INFO_REQUESTED'
2. Records admin and timestamp
3. Sends email to user with info request
4. User can respond via API

**Response**:
```json
{
  "detail": "Additional information requested",
  "info_requested": "Please provide a letter from your supervisor..."
}
```

**Frontend Actions**:
- Show info request confirmation
- Move to "Awaiting User Response" list
- Update status to INFO_REQUESTED

---

### Step 5: Monitor Info Requested Cases

**API Endpoint**:
```http
GET /api/v1/users/admin/verification-requests/info_requested/
Authorization: Bearer {admin_access_token}
```

**Response**:
```json
{
  "count": 3,
  "results": [
    {
      "id": "uuid",
      "profile": {...},
      "status": "INFO_REQUESTED",
      "additional_info_requested": "Please provide...",
      "user_response": null,
      "user_response_at": null,
      "created_at": "2025-11-03T10:00:00Z",
      "reviewed_at": "2025-11-03T15:00:00Z"
    }
  ]
}
```

**When User Responds**: Status changes back to 'PENDING' and appears in pending list again

---

## API Endpoints Reference

### User Endpoints (Authenticated)

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| `POST` | `/api/v1/auth/register/` | Register new account | Public |
| `POST` | `/api/v1/auth/login/` | Login and get tokens | Public |
| `PATCH` | `/api/v1/users/profile/` | Update profile | Authenticated |
| `GET` | `/api/v1/users/orcid/connect/` | Get ORCID auth URL | Authenticated |
| `GET` | `/api/v1/users/orcid/callback/` | ORCID callback (auto) | Authenticated |
| `GET` | `/api/v1/users/orcid/status/` | Check ORCID connection | Authenticated |
| `POST` | `/api/v1/users/verification-requests/` | Submit verification (with letter) | Authenticated |
| `GET` | `/api/v1/users/verification-requests/` | List own requests | Authenticated |
| `GET` | `/api/v1/users/verification-requests/{id}/` | Get request details | Authenticated |
| `GET` | `/api/v1/users/verification/status/` | Quick status check | Authenticated |
| `POST` | `/api/v1/users/verification-requests/{id}/respond/` | Respond to info request | Authenticated |
| `POST` | `/api/v1/users/verification-requests/{id}/withdraw/` | Withdraw request | Authenticated |

### Admin Endpoints (Admin Only)

| Method | Endpoint | Description | Permission |
|--------|----------|-------------|------------|
| `GET` | `/api/v1/users/admin/verification-requests/` | List all requests | Admin |
| `GET` | `/api/v1/users/admin/verification-requests/pending_review/` | Get pending requests | Admin |
| `GET` | `/api/v1/users/admin/verification-requests/high_score/` | Get high score requests (≥70) | Admin |
| `GET` | `/api/v1/users/admin/verification-requests/info_requested/` | Get info requested cases | Admin |
| `GET` | `/api/v1/users/admin/verification-requests/{id}/` | Get request details | Admin |
| `POST` | `/api/v1/users/admin/verification-requests/{id}/approve/` | Approve request | Admin |
| `POST` | `/api/v1/users/admin/verification-requests/{id}/reject/` | Reject request | Admin |
| `POST` | `/api/v1/users/admin/verification-requests/{id}/request_info/` | Request more info | Admin |

---

## Data Flow Diagrams

### User Verification Flow

```
┌──────────────┐
│ Registration │
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│ Complete Profile │ ← Auto-grabbed: email domain, profile fields
└──────┬───────────┘
       │
       ▼
┌──────────────┐
│ Connect ORCID│ ← Auto-grabbed: ORCID iD, verified identity
└──────┬───────┘
       │
       ▼
┌───────────────────┐
│ Upload Documents  │ ← Auto-grabbed: file metadata, count
└──────┬────────────┘
       │
       ▼
┌────────────────────┐
│ Submit Verification│ ← Auto-calculates: score (0-100)
└──────┬─────────────┘
       │
       ▼
┌──────────────┐
│   PENDING    │
└──────┬───────┘
       │
       ├─────────────┬─────────────┐
       ▼             ▼             ▼
┌──────────┐  ┌─────────────┐  ┌──────────┐
│ APPROVED │  │INFO_REQUESTED│  │ REJECTED │
└──────────┘  └──────┬──────┘  └──────────┘
                     │
                     ▼
              ┌──────────────┐
              │User Responds │
              └──────┬───────┘
                     │
                     ▼
              ┌─────────────┐
              │ Back PENDING│
              └─────────────┘
```

### Admin Review Flow

```
┌───────────────────┐
│ Admin Dashboard   │
└────────┬──────────┘
         │
         ▼
┌───────────────────────┐
│ View Pending Requests │
│ (sorted by score)     │
└────────┬──────────────┘
         │
         ▼
┌─────────────────────┐
│ Review Individual   │
│ - Profile info      │
│ - ORCID verification│
│ - Documents         │
│ - Auto-score        │
└────────┬────────────┘
         │
         ├────────────┬────────────┐
         ▼            ▼            ▼
┌───────────┐  ┌──────────┐  ┌──────────────┐
│ APPROVE   │  │ REJECT   │  │ REQUEST INFO │
│ ↓         │  │ ↓        │  │ ↓            │
│Grant Roles│  │Send Reason│ │Ask Question │
└───────────┘  └──────────┘  └──────────────┘
```

---

## Auto-Scoring System

### What Information is Auto-Grabbed?

| Data Source | Information Grabbed | Points | When Grabbed |
|-------------|---------------------|--------|--------------|
| **Email Address** | Domain (.edu, .ac.uk, etc.) | 25 | Registration |
| **Email + Affiliation** | Domain matches institution name | 15 | Verification submission |
| **ORCID Integration** | Verified ORCID iD | 30 | ORCID OAuth callback |
| **ORCID Profile** | Name, publications, affiliations | - | ORCID OAuth callback |
| **Profile Fields** | Research interests length | 10 | Profile update |
| **Profile Fields** | Academic position provided | 10 | Profile update |
| **Supporting Letter** | Letter length > 100 chars | 10 | Verification submission |
| **Profile Completeness** | Bio, affiliation, etc. | - | Profile update |

### Score Calculation (Automatic)

```python
def calculate_auto_score(verification_request):
    score = 0
    
    # 1. ORCID (30 points) - HIGHEST PRIORITY
    if verification_request.orcid_verified and verification_request.orcid_id:
        score += 30
    
    # 2. Institutional Email (25 points)
    email_domain = verification_request.affiliation_email.split('@')[-1]
    if '.edu' in email_domain or '.ac.' in email_domain:
        score += 25
    
    # 3. Email-Affiliation Match (15 points)
    if email_domain in verification_request.affiliation.lower():
        score += 15
    
    # 4. Research Interests (10 points)
    if len(verification_request.research_interests) > 50:
        score += 10
    
    # 5. Academic Position (10 points)
    if verification_request.academic_position:
        score += 10
    
    # 6. Supporting Letter (10 points)
    if len(verification_request.supporting_letter) > 100:
        score += 10
    
    return score  # 0-100
```

---

## Status Lifecycle

```
PENDING → APPROVED ✅
   ↓
   ↓ → INFO_REQUESTED → (User Responds) → PENDING
   ↓
   ↓ → REJECTED ❌
   ↓
   ↓ → WITHDRAWN (by user)
```

### Status Descriptions

| Status | Description | User Actions | Admin Actions |
|--------|-------------|--------------|---------------|
| `PENDING` | Awaiting admin review | View status, Withdraw | Approve, Reject, Request Info |
| `INFO_REQUESTED` | Admin needs more info | Respond with info | View response, then Approve/Reject |
| `APPROVED` | Verification approved | None (final state) | None (final state) |
| `REJECTED` | Verification rejected | Submit new request | None (final state) |
| `WITHDRAWN` | User cancelled request | Submit new request | None (final state) |

---

## Frontend Integration Examples

### User Dashboard - Verification Status Widget

```typescript
// components/VerificationStatus.tsx
import { useState, useEffect } from 'react';

interface VerificationStatus {
  profile_status: string;
  is_verified: boolean;
  has_pending_request: boolean;
  latest_request: {
    status: string;
    auto_score: number;
    score_breakdown: Array<{
      criterion: string;
      points_earned: number;
      points_possible: number;
      status: 'completed' | 'missing';
    }>;
  } | null;
}

export function VerificationStatusWidget() {
  const [status, setStatus] = useState<VerificationStatus | null>(null);

  useEffect(() => {
    fetchStatus();
    // Poll every 30 seconds
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchStatus = async () => {
    const response = await fetch('/api/v1/users/verification/status/', {
      headers: {
        'Authorization': `Bearer ${getAccessToken()}`
      }
    });
    const data = await response.json();
    setStatus(data);
  };

  if (!status) return <div>Loading...</div>;

  if (status.is_verified) {
    return (
      <div className="status-verified">
        <div className="badge badge-success">
          ✅ Verified
        </div>
        <p>Your account is verified as {status.profile_status}</p>
      </div>
    );
  }

  if (status.has_pending_request) {
    const request = status.latest_request!;
    
    return (
      <div className="status-pending">
        <div className="badge badge-warning">
          ⏳ Verification Pending
        </div>
        
        <div className="score-display">
          <h3>Trust Score: {request.auto_score}/100</h3>
          <div className="progress-bar">
            <div 
              className="progress-fill"
              style={{ width: `${request.auto_score}%` }}
            />
          </div>
        </div>

        <div className="score-breakdown">
          <h4>Score Breakdown</h4>
          {request.score_breakdown.map((item, index) => (
            <div key={index} className="score-item">
              <span className={`status-icon ${item.status}`}>
                {item.status === 'completed' ? '✅' : '❌'}
              </span>
              <span className="criterion">{item.criterion}</span>
              <span className="points">
                {item.points_earned}/{item.points_possible}
              </span>
            </div>
          ))}
        </div>

        {request.status === 'INFO_REQUESTED' && (
          <div className="alert alert-info">
            <p>The admin has requested additional information.</p>
            <button onClick={() => navigateToResponse()}>
              Respond Now
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="status-unverified">
      <div className="badge badge-secondary">
        Unverified
      </div>
      <p>Get verified to submit papers and review submissions.</p>
      <button onClick={() => navigateToVerification()}>
        Start Verification
      </button>
    </div>
  );
}
```

### Admin Dashboard - Verification Queue

```typescript
// components/admin/VerificationQueue.tsx
import { useState, useEffect } from 'react';

interface VerificationRequest {
  id: string;
  profile: {
    user: {
      email: string;
      name: string;
    };
  };
  requested_role: string;
  auto_score: number;
  status: string;
  orcid_verified: boolean;
  created_at: string;
}

export function VerificationQueue() {
  const [requests, setRequests] = useState<VerificationRequest[]>([]);
  const [filter, setFilter] = useState<'all' | 'high_score'>('all');

  useEffect(() => {
    fetchRequests();
  }, [filter]);

  const fetchRequests = async () => {
    const endpoint = filter === 'high_score'
      ? '/api/v1/users/admin/verification-requests/high_score/'
      : '/api/v1/users/admin/verification-requests/pending_review/';
    
    const response = await fetch(endpoint, {
      headers: {
        'Authorization': `Bearer ${getAdminToken()}`
      }
    });
    const data = await response.json();
    setRequests(data.results);
  };

  const handleApprove = async (requestId: string) => {
    await fetch(`/api/v1/users/admin/verification-requests/${requestId}/approve/`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${getAdminToken()}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        admin_notes: 'Approved via quick action'
      })
    });
    fetchRequests(); // Refresh list
  };

  const getScoreBadgeColor = (score: number) => {
    if (score >= 70) return 'success';
    if (score >= 40) return 'warning';
    return 'danger';
  };

  return (
    <div className="verification-queue">
      <div className="header">
        <h2>Verification Queue</h2>
        <div className="filters">
          <button 
            className={filter === 'all' ? 'active' : ''}
            onClick={() => setFilter('all')}
          >
            All Pending ({requests.length})
          </button>
          <button
            className={filter === 'high_score' ? 'active' : ''}
            onClick={() => setFilter('high_score')}
          >
            High Score (Fast Track)
          </button>
        </div>
      </div>

      <table className="requests-table">
        <thead>
          <tr>
            <th>User</th>
            <th>Role</th>
            <th>Score</th>
            <th>ORCID</th>
            <th>Submitted</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {requests.map(request => (
            <tr key={request.id}>
              <td>{request.profile.user.email}</td>
              <td>{request.requested_role}</td>
              <td>
                <span className={`badge badge-${getScoreBadgeColor(request.auto_score)}`}>
                  {request.auto_score}/100
                </span>
              </td>
              <td>
                {request.orcid_verified ? '✅' : '❌'}
              </td>
              <td>{new Date(request.created_at).toLocaleDateString()}</td>
              <td>
                <button
                  className="btn btn-sm btn-success"
                  onClick={() => handleApprove(request.id)}
                >
                  ✅ Quick Approve
                </button>
                <button
                  className="btn btn-sm btn-primary"
                  onClick={() => navigateToReview(request.id)}
                >
                  📋 Review
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

---

## Summary

### User Journey (4-6 Steps)

1. **Register** → Auto-grabs email domain
2. **Complete Profile** → Auto-grabs research interests, position
3. **Connect ORCID** → Auto-grabs ORCID iD (+30 points!)
4. **Submit Verification** → Include supporting letter, auto-calculates score (0-100)
5. **Check Status** → Monitor progress
6. **Get Approved** → Auto-grants roles

### Admin Journey (3-4 Steps)

1. **View Pending Queue** → Sorted by auto-score
2. **Review Request** → See all auto-grabbed data + score breakdown
3. **Take Action** → Approve/Reject/Request Info
4. **Monitor Info Requests** (if applicable)

### Key Auto-Grabbed Information

✅ **Email domain** (for institutional check)  
✅ **ORCID iD** (highest weight: 30 points)  
✅ **Profile completeness** (research interests, position)  
✅ **Supporting letter** (length validation)  
✅ **Email-affiliation match** (algorithmic check)  
✅ **Verification timestamp** (all actions logged)  

### Everything is API-First!

Every action has a corresponding REST API endpoint, making it easy to build any frontend (React, Vue, mobile apps, etc.)

🚀 **System is production-ready with full auto-scoring and admin workflow!**
