# Auto-Scoring Systems - Complete Guide

## Overview

Your journal portal has **2 automated scoring systems** that help streamline operations:

1. **Verification Auto-Score** (0-100 scale) - Validates user identity/credentials
2. **Review Scoring System** (customizable) - Evaluates paper quality

Both use **rule-based algorithms** (no ML training required) to automatically calculate scores.

---

## 1. Verification Auto-Score (User Identity)

### Purpose
Automatically evaluate how trustworthy a user's credentials are when they request verification as a reviewer/author.

### Location in Code
- **Model**: `apps/users/models.py` → `VerificationRequest` model
- **Method**: `calculate_auto_score()`
- **Score Range**: 0-100 points

### How It Scores

The system awards points across **6 categories**:

| Category | Max Points | What It Checks |
|----------|-----------|----------------|
| **ORCID Verification** | 30 | User has verified ORCID ID connected |
| **Institutional Email** | 25 | Email from .edu, .ac.uk, .ac.in, etc. |
| **Email-Affiliation Match** | 15 | Email domain matches claimed institution |
| **Research Interests** | 10 | Detailed research interests (>50 chars) |
| **Academic Position** | 10 | Position title provided (Professor, PhD, etc.) |
| **Supporting Documents** | 10 | Uploaded CV, publications, etc. |
| **TOTAL** | **100** | Maximum possible score |

### Scoring Logic (Step-by-Step)

```python
def calculate_auto_score(self):
    score = 0
    details = {}
    
    # 1. ORCID Verification (30 points) - HIGHEST WEIGHT
    if self.orcid_verified and self.orcid_id:
        score += 30  # ✅ User connected and verified ORCID
        details['orcid'] = 30
    else:
        details['orcid'] = 0  # ❌ No ORCID or not verified
    
    # 2. Institutional Email (25 points) - SECOND HIGHEST
    email_domain = self.affiliation_email.split('@')[-1].lower()
    institutional_domains = ['edu', 'ac.uk', 'ac.in', 'edu.au', 'ac.jp', 'edu.cn']
    
    if any(domain in email_domain for domain in institutional_domains):
        score += 25  # ✅ Email from recognized academic domain
        details['institutional_email'] = 25
    else:
        details['institutional_email'] = 0  # ❌ Gmail, Yahoo, etc.
    
    # 3. Email-Affiliation Match (15 points)
    if self.affiliation and email_domain in self.affiliation.lower().replace(' ', ''):
        score += 15  # ✅ Email domain appears in affiliation name
        details['email_affiliation_match'] = 15
    else:
        details['email_affiliation_match'] = 0
    
    # 4. Research Interests (10 points)
    if self.research_interests and len(self.research_interests) > 50:
        score += 10  # ✅ Detailed research description provided
        details['research_interests'] = 10
    else:
        details['research_interests'] = 0  # ❌ Too brief or missing
    
    # 5. Academic Position (10 points)
    if self.academic_position:
        score += 10  # ✅ Position specified (Professor, Postdoc, etc.)
        details['academic_position'] = 10
    else:
        details['academic_position'] = 0  # ❌ No position provided
    
    # 6. Supporting Documents (10 points)
    if self.supporting_documents and len(self.supporting_documents) > 0:
        score += 10  # ✅ CV, publications, or other docs uploaded
        details['supporting_documents'] = 10
    else:
        details['supporting_documents'] = 0  # ❌ No documents
    
    # Save and return
    self.auto_score = score
    self.score_details = details  # JSON breakdown for transparency
    return score
```

### Scoring Examples

#### Example 1: High Score (90/100) - Trustworthy User
```json
{
  "user": "dr.smith@stanford.edu",
  "auto_score": 90,
  "score_details": {
    "orcid": 30,              // ✅ ORCID verified
    "institutional_email": 25, // ✅ stanford.edu
    "email_affiliation_match": 15, // ✅ "Stanford" in email
    "research_interests": 10,  // ✅ Detailed description
    "academic_position": 10,   // ✅ "Associate Professor"
    "supporting_documents": 0  // ❌ No docs uploaded
  }
}
```
**Interpretation**: Very trustworthy. Only missing documents. Fast-track verification.

#### Example 2: Medium Score (55/100) - Needs Review
```json
{
  "user": "researcher123@gmail.com",
  "auto_score": 55,
  "score_details": {
    "orcid": 30,              // ✅ ORCID verified
    "institutional_email": 0,  // ❌ Gmail (not institutional)
    "email_affiliation_match": 0, // ❌ No match
    "research_interests": 10,  // ✅ Detailed description
    "academic_position": 10,   // ✅ "PhD Student"
    "supporting_documents": 10 // ✅ Uploaded CV
  }
}
```
**Interpretation**: ORCID is good, but personal email raises flags. Manual review recommended.

#### Example 3: Low Score (20/100) - Suspicious
```json
{
  "user": "user456@yahoo.com",
  "auto_score": 20,
  "score_details": {
    "orcid": 0,               // ❌ No ORCID
    "institutional_email": 0,  // ❌ Yahoo email
    "email_affiliation_match": 0, // ❌ No match
    "research_interests": 10,  // ✅ Provided interests
    "academic_position": 10,   // ✅ "Researcher"
    "supporting_documents": 0  // ❌ No documents
  }
}
```
**Interpretation**: Very suspicious. Require additional verification or reject.

### How to Use Verification Scores

#### In Admin Dashboard
```python
# apps/users/admin.py
from django.contrib import admin

class VerificationRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'status', 'auto_score', 'score_badge']
    list_filter = ['status', 'auto_score']
    
    def score_badge(self, obj):
        """Show color-coded score badge."""
        if obj.auto_score >= 70:
            color = 'green'
            label = 'HIGH'
        elif obj.auto_score >= 40:
            color = 'orange'
            label = 'MEDIUM'
        else:
            color = 'red'
            label = 'LOW'
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{} ({})</span>',
            color, label, obj.auto_score
        )
    
    score_badge.short_description = 'Trust Score'
```

#### Auto-Approve High Scores
```python
# apps/users/views.py
class VerificationRequestViewSet(viewsets.ModelViewSet):
    
    def create(self, request):
        """Create verification request with auto-scoring."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        verification = serializer.save()
        
        # Calculate auto-score
        score = verification.calculate_auto_score()
        
        # Auto-approve if score >= 80
        if score >= 80:
            verification.status = 'approved'
            verification.reviewed_at = timezone.now()
            verification.reviewer_notes = 'Auto-approved based on high trust score'
            verification.save()
            
            return Response({
                'message': 'Verification auto-approved!',
                'auto_score': score
            }, status=201)
        
        return Response({
            'message': 'Verification submitted for review',
            'auto_score': score
        }, status=201)
```

---

## 2. Review Scoring System (Paper Quality)

### Purpose
Evaluate paper quality through structured reviewer feedback with customizable criteria.

### Location in Code
- **Model**: `apps/reviews/models.py` → `Review` model
- **Config**: `ReviewTemplate` model → `scoring_criteria` field
- **Score Calculation**: `get_overall_score()` method

### How It Works

This system is **highly customizable** - each journal can define their own scoring criteria.

### Default Scoring Criteria

Typical academic review criteria (customizable):

| Criterion | Weight | Range | Description |
|-----------|--------|-------|-------------|
| **Novelty** | 1.0 | 1-5 | How original is the research? |
| **Methodology** | 1.0 | 1-5 | Are methods sound and appropriate? |
| **Clarity** | 1.0 | 1-5 | Is the paper well-written? |
| **Significance** | 1.0 | 1-5 | Impact on the field? |
| **Reproducibility** | 1.0 | 1-5 | Can results be replicated? |

### Scoring Logic

```python
def get_overall_score(self):
    """Calculate overall score from individual scores."""
    if not self.scores:
        return None
    
    # Extract numeric scores from JSON
    scores = [v for v in self.scores.values() if isinstance(v, (int, float))]
    
    # Calculate average
    return sum(scores) / len(scores) if scores else None
```

### Review Score Structure (JSON)

Reviews store scores as flexible JSON:

```json
{
  "novelty": 4,
  "methodology": 5,
  "clarity": 3,
  "significance": 4,
  "reproducibility": 4,
  "comments": "Strong methodology but could improve presentation"
}
```

**Overall Score Calculation**:
```
(4 + 5 + 3 + 4 + 4) / 5 = 4.0 / 5.0
```

### Customizing Scoring Criteria

Journals can define custom criteria in `ReviewTemplate`:

```python
# Example: Custom scoring criteria
review_template = ReviewTemplate.objects.create(
    journal=my_journal,
    name="Computer Science Review",
    scoring_criteria={
        "criteria": [
            {
                "name": "technical_soundness",
                "label": "Technical Soundness",
                "type": "numeric",
                "min": 1,
                "max": 5,
                "weight": 2.0,  # Double weight
                "required": True
            },
            {
                "name": "innovation",
                "label": "Innovation",
                "type": "numeric",
                "min": 1,
                "max": 5,
                "weight": 1.5,
                "required": True
            },
            {
                "name": "code_quality",
                "label": "Code Quality (if applicable)",
                "type": "numeric",
                "min": 1,
                "max": 5,
                "weight": 1.0,
                "required": False
            },
            {
                "name": "dataset_quality",
                "label": "Dataset Quality",
                "type": "numeric",
                "min": 1,
                "max": 5,
                "weight": 1.0,
                "required": False
            }
        ]
    }
)
```

### Weighted Score Calculation

For weighted criteria:

```python
def get_weighted_overall_score(self):
    """Calculate weighted average score."""
    if not self.scores or not self.assignment.template:
        return self.get_overall_score()
    
    criteria = self.assignment.template.scoring_criteria.get('criteria', [])
    
    total_score = 0
    total_weight = 0
    
    for criterion in criteria:
        name = criterion['name']
        weight = criterion.get('weight', 1.0)
        
        if name in self.scores:
            score = self.scores[name]
            if isinstance(score, (int, float)):
                total_score += score * weight
                total_weight += weight
    
    return total_score / total_weight if total_weight > 0 else None
```

### Review Score Examples

#### Example 1: Strong Paper (4.2/5.0)
```json
{
  "review_id": "uuid-123",
  "submission": "Machine Learning Paper",
  "reviewer": "dr.expert@university.edu",
  "scores": {
    "novelty": 5,          // Highly novel approach
    "methodology": 4,       // Sound methods
    "clarity": 4,           // Well-written
    "significance": 5,      // High impact potential
    "reproducibility": 3    // Missing some details
  },
  "overall_score": 4.2,
  "recommendation": "accept"
}
```

#### Example 2: Weak Paper (2.4/5.0)
```json
{
  "review_id": "uuid-456",
  "submission": "Incremental Research",
  "reviewer": "prof.reviewer@institute.edu",
  "scores": {
    "novelty": 2,          // Not original
    "methodology": 3,       // Methods okay
    "clarity": 2,           // Poor writing
    "significance": 2,      // Limited impact
    "reproducibility": 3    // Some reproducibility
  },
  "overall_score": 2.4,
  "recommendation": "reject"
}
```

### Using Review Scores

#### Editorial Decision Support
```python
# apps/submissions/views.py
class SubmissionViewSet(viewsets.ModelViewSet):
    
    @action(detail=True, methods=['get'])
    def review_summary(self, request, pk=None):
        """Get aggregated review scores for decision-making."""
        submission = self.get_object()
        reviews = submission.reviews.filter(status='submitted')
        
        if not reviews.exists():
            return Response({'message': 'No reviews yet'})
        
        # Aggregate scores
        overall_scores = [r.get_overall_score() for r in reviews if r.get_overall_score()]
        
        if not overall_scores:
            return Response({'message': 'No scores available'})
        
        # Calculate statistics
        avg_score = sum(overall_scores) / len(overall_scores)
        min_score = min(overall_scores)
        max_score = max(overall_scores)
        
        # Recommendation based on average
        if avg_score >= 4.0:
            recommendation = 'ACCEPT'
        elif avg_score >= 3.0:
            recommendation = 'MAJOR_REVISION'
        elif avg_score >= 2.0:
            recommendation = 'MINOR_REVISION'
        else:
            recommendation = 'REJECT'
        
        return Response({
            'review_count': len(reviews),
            'average_score': round(avg_score, 2),
            'min_score': min_score,
            'max_score': max_score,
            'recommendation': recommendation,
            'individual_reviews': [
                {
                    'reviewer': r.assignment.reviewer.user.email,
                    'score': r.get_overall_score(),
                    'recommendation': r.recommendation
                }
                for r in reviews
            ]
        })
```

#### Frontend Display
```typescript
// components/ReviewScoreCard.tsx
interface ReviewScore {
  novelty: number;
  methodology: number;
  clarity: number;
  significance: number;
  reproducibility: number;
}

function ReviewScoreCard({ scores }: { scores: ReviewScore }) {
  const overall = Object.values(scores).reduce((a, b) => a + b, 0) / 
                  Object.values(scores).length;
  
  const getColor = (score: number) => {
    if (score >= 4) return 'green';
    if (score >= 3) return 'orange';
    return 'red';
  };
  
  return (
    <div className="score-card">
      <h3>Review Scores</h3>
      
      <div className="overall-score" style={{ color: getColor(overall) }}>
        <span className="score-value">{overall.toFixed(1)}</span>
        <span className="score-max">/ 5.0</span>
      </div>
      
      <div className="score-breakdown">
        {Object.entries(scores).map(([criterion, score]) => (
          <div key={criterion} className="score-item">
            <span className="criterion">{criterion}</span>
            <div className="score-bar">
              <div 
                className="score-fill" 
                style={{ 
                  width: `${(score / 5) * 100}%`,
                  backgroundColor: getColor(score)
                }}
              />
            </div>
            <span className="score-num">{score}/5</span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

## Comparison: Verification vs Review Scoring

| Feature | Verification Score | Review Score |
|---------|-------------------|--------------|
| **Purpose** | User identity trust | Paper quality assessment |
| **Range** | 0-100 points | 1-5 or 1-10 (customizable) |
| **Method** | Rule-based heuristics | Reviewer subjective rating |
| **Automation** | Fully automatic | Manual review required |
| **Customization** | Fixed criteria | Highly customizable |
| **Use Case** | Account verification | Editorial decisions |
| **Transparency** | Score breakdown in JSON | Individual criteria scores |

---

## Best Practices

### For Verification Scores

✅ **DO**:
- Auto-approve scores ≥ 80 to speed up onboarding
- Require manual review for scores < 40
- Show score breakdown to users for transparency
- Use as a ranking tool, not absolute truth

❌ **DON'T**:
- Auto-reject based solely on low scores
- Hide scoring criteria from users
- Ignore context (some legitimate users have low scores)
- Weight all factors equally if your needs differ

### For Review Scores

✅ **DO**:
- Customize criteria for your journal's field
- Use weights to emphasize important factors
- Aggregate multiple reviews before decisions
- Provide scoring guidelines to reviewers

❌ **DON'T**:
- Make decisions on a single review
- Use generic criteria for specialized fields
- Ignore reviewer comments in favor of numbers
- Skip reviewer training on scoring system

---

## Configuration

### Adjusting Verification Score Weights

Edit `apps/users/models.py`:

```python
class VerificationRequest(models.Model):
    def calculate_auto_score(self):
        score = 0
        
        # Adjust these weights based on your priorities
        if self.orcid_verified and self.orcid_id:
            score += 40  # Increase ORCID importance (was 30)
        
        if institutional_email:
            score += 20  # Decrease email importance (was 25)
        
        # ... adjust other weights as needed
        
        return score
```

### Customizing Review Criteria

Via Django Admin or API:

```python
# In Django shell or migration
from apps.reviews.models import ReviewTemplate

template = ReviewTemplate.objects.create(
    name="Biology Journal Review",
    scoring_criteria={
        "criteria": [
            {"name": "experimental_design", "weight": 2.0, "min": 1, "max": 5},
            {"name": "statistical_analysis", "weight": 1.5, "min": 1, "max": 5},
            {"name": "biological_significance", "weight": 1.5, "min": 1, "max": 5},
            {"name": "presentation", "weight": 1.0, "min": 1, "max": 5}
        ]
    }
)
```

---

## API Endpoints

### Get Verification Score

```bash
# Admin viewing verification request
GET /api/v1/users/verification-requests/<id>/

# Response includes auto_score
{
  "id": "uuid",
  "user": "researcher@university.edu",
  "status": "pending",
  "auto_score": 85,
  "score_details": {
    "orcid": 30,
    "institutional_email": 25,
    ...
  }
}
```

### Get Review Scores

```bash
# Get submission with review scores
GET /api/v1/submissions/<id>/

# Response includes reviews with scores
{
  "id": "uuid",
  "title": "Paper Title",
  "reviews": [
    {
      "reviewer": "expert@university.edu",
      "scores": {
        "novelty": 4,
        "methodology": 5,
        ...
      },
      "overall_score": 4.2,
      "recommendation": "accept"
    }
  ]
}
```

---

## Summary

### Verification Auto-Score
- **0-100 point scale**
- **6 criteria**: ORCID (30), Email (25), Match (15), Interests (10), Position (10), Docs (10)
- **Fully automated** - calculates on submission
- **Use for**: Fast-tracking trustworthy users, flagging suspicious accounts

### Review Scoring
- **Customizable scale** (typically 1-5)
- **Flexible criteria**: Define your own based on field
- **Manual input** by reviewers
- **Use for**: Editorial decisions, paper quality assessment

Both systems are **production-ready** and work together to streamline your journal operations! 🚀
