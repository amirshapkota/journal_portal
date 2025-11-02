# Reviewer Recommendation System - ML-Powered

## Overview
ML-powered reviewer recommendation system using TF-IDF and cosine similarity to match reviewers with submissions based on expertise, availability, quality, and response rates.

---

## Features

###  Intelligent Matching
- **TF-IDF Vectorization**: Analyzes submission content (title, abstract, keywords)
- **Cosine Similarity**: Matches reviewers based on expertise areas and profile
- **Multi-factor Scoring**: Combines multiple metrics for optimal recommendations

###  Scoring Factors

1. **Similarity Score (0-1)** - Content/Expertise Match
   - Submission: title (3x weight), abstract (2x), keywords, tags
   - Reviewer: expertise areas (5x weight), bio, affiliation, name

2. **Availability Score (0-1)** - Current Workload
   - 0 active reviews = 1.0 score
   - 5+ active reviews = 0.0 score
   - Linear scaling between

3. **Quality Score (0-1)** - Past Review Quality
   - Average of past review quality scores (0-10 scale, normalized)
   - New reviewers get 0.5 (neutral)

4. **Response Rate Score (0-1)** - Reliability
   - 60% weight: invitation acceptance rate
   - 40% weight: on-time completion rate
   - New reviewers get 0.5 (neutral)

###  Composite Scoring
Default weights:
- Similarity: 50%
- Availability: 20%
- Quality: 20%
- Response Rate: 10%

**Customizable weights** via API endpoint.

---

## API Endpoints

### 1. Get Reviewer Recommendations

```http
GET /api/v1/ml/reviewer-recommendations/<submission_id>/
```

**Query Parameters:**
- `max_recommendations` (optional): Max number of recommendations (1-50, default: 10)

**Response:**
```json
{
  "submission_id": "123e4567-e89b-12d3-a456-426614174000",
  "submission_title": "Machine Learning in Healthcare",
  "total_potential_reviewers": 25,
  "recommendation_count": 10,
  "recommendations": [
    {
      "reviewer_id": "456e7890-e89b-12d3-a456-426614174001",
      "reviewer_name": "Dr. Jane Smith",
      "reviewer_email": "jane.smith@university.edu",
      "affiliation": "Stanford University",
      "expertise_areas": ["Machine Learning", "Healthcare AI", "Medical Imaging"],
      "orcid_id": "0000-0001-2345-6789",
      "openalex_id": "A1234567890",
      "scores": {
        "composite": 0.847,
        "similarity": 0.92,
        "availability": 0.8,
        "quality": 0.85,
        "response_rate": 0.75
      },
      "metrics": {
        "active_reviews": 1,
        "total_reviews_completed": 15,
        "average_quality_score": 8.5
      },
      "recommendation_reason": "Strong expertise match, High availability, High-quality reviewer"
    }
  ]
}
```

### 2. Get Recommendations with Custom Weights

```http
POST /api/v1/ml/reviewer-recommendations/<submission_id>/custom-weights/
```

**Request Body:**
```json
{
  "weights": {
    "similarity": 0.6,
    "availability": 0.2,
    "quality": 0.15,
    "response_rate": 0.05
  },
  "max_recommendations": 15
}
```

**Note:** Weights should ideally sum to 1.0 but are not required to.

---

## Installation

### 1. Install ML Dependencies

```bash
pip install -r requirements/ml.txt
```

Or manually:
```bash
pip install scikit-learn==1.5.2 numpy==2.0.2
```

### 2. Run Migrations

```bash
python manage.py migrate
```

### 3. Test the System

```bash
python test_reviewer_recommendations.py
```

---

## Setup Requirements

### 1. Reviewers Must Have:
-  User account with `Reviewer` role
-  Active status (`is_active=True`)
-  Expertise areas assigned (for better matching)
-  Bio (optional but improves matching)

### 2. Submissions Must Have:
-  Title
-  Abstract (recommended)
-  Keywords in `metadata_json` (recommended)
-  Tags in `metadata_json` (optional)

### 3. For Quality & Response Scores:
- Track review completion with `ReviewAssignment` model
- Track review quality with `Review.quality_score` field
- System calculates historical metrics automatically

---

## Usage Examples

### Example 1: Basic Usage (Python)

```python
from apps.ml.reviewer_recommendation import ReviewerRecommendationEngine
from apps.submissions.models import Submission

# Get submission
submission = Submission.objects.get(id='123e4567-e89b-12d3-a456-426614174000')

# Initialize engine
engine = ReviewerRecommendationEngine()

# Get recommendations
recommendations = engine.recommend_reviewers(
    submission=submission,
    max_recommendations=10
)

# Print results
for rec in recommendations:
    print(f"{rec['reviewer_name']}: {rec['scores']['composite']:.3f}")
```

### Example 2: Custom Weights (Python)

```python
# Prioritize expertise match over availability
recommendations = engine.recommend_reviewers(
    submission=submission,
    max_recommendations=5,
    weights={
        'similarity': 0.7,      # Strong emphasis on expertise
        'availability': 0.1,
        'quality': 0.15,
        'response_rate': 0.05
    }
)
```

### Example 3: API Request (cURL)

```bash
# Get recommendations
curl -X GET \
  'http://localhost:8000/api/v1/ml/reviewer-recommendations/<submission_id>/?max_recommendations=10' \
  -H 'Authorization: Bearer YOUR_ACCESS_TOKEN'

# Custom weights
curl -X POST \
  'http://localhost:8000/api/v1/ml/reviewer-recommendations/<submission_id>/custom-weights/' \
  -H 'Authorization: Bearer YOUR_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
    "weights": {
      "similarity": 0.8,
      "availability": 0.1,
      "quality": 0.05,
      "response_rate": 0.05
    },
    "max_recommendations": 15
  }'
```

### Example 4: Frontend Integration (JavaScript)

```javascript
// Fetch reviewer recommendations
const getReviewerRecommendations = async (submissionId) => {
  const response = await fetch(
    `http://localhost:8000/api/v1/ml/reviewer-recommendations/${submissionId}/?max_recommendations=10`,
    {
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
    }
  );
  
  const data = await response.json();
  return data.recommendations;
};

// Display recommendations
const recommendations = await getReviewerRecommendations(submissionId);
recommendations.forEach(rec => {
  console.log(`${rec.reviewer_name} - Score: ${rec.scores.composite}`);
  console.log(`Expertise: ${rec.expertise_areas.join(', ')}`);
  console.log(`Reason: ${rec.recommendation_reason}`);
});
```

---

## How It Works

### 1. **Feature Extraction**
```
Submission → [title × 3, abstract × 2, keywords, tags]
Reviewer   → [expertise × 5, bio, affiliation, name]
```

### 2. **TF-IDF Vectorization**
Converts text into numerical vectors representing term importance:
- **TF** (Term Frequency): How often a term appears
- **IDF** (Inverse Document Frequency): How unique a term is

### 3. **Cosine Similarity**
Measures angle between vectors (0 = no match, 1 = perfect match):
```
similarity = (A · B) / (||A|| × ||B||)
```

### 4. **Multi-Factor Scoring**
```
composite_score = (similarity × 0.5) + 
                  (availability × 0.2) + 
                  (quality × 0.2) + 
                  (response_rate × 0.1)
```

### 5. **Ranking & Filtering**
- Sort by composite score (descending)
- Return top N recommendations
- Exclude submission authors
- Exclude existing reviewers

---

## Filtering Logic

### Reviewers are Automatically Excluded if:
1.  They are the submission's corresponding author
2.  They are a co-author on the submission
3.  They already have a review assignment for this submission
4.  Their user account is inactive

### Reviewers are Prioritized if:
1.  Strong expertise match (high similarity score)
2.  Low current workload (high availability score)
3.  High past review quality scores
4.  Good acceptance and completion rates

---

## Improving Recommendations

### For Better Matches:
1. **Enrich Submission Data:**
   - Add detailed abstracts
   - Include comprehensive keywords
   - Add relevant tags in metadata

2. **Enrich Reviewer Profiles:**
   - Add detailed bios
   - Assign multiple expertise areas
   - Link ORCID and OpenAlex profiles
   - Keep affiliation information updated

3. **Track Review History:**
   - Mark reviews as completed
   - Assign quality scores to completed reviews
   - Track response times and acceptance rates

4. **Tune Weights:**
   - For urgent reviews: increase `availability` weight
   - For high-stakes papers: increase `quality` weight
   - For niche topics: increase `similarity` weight

---

## Performance Considerations

### Scalability:
-  TF-IDF vectorization is efficient (O(n×m) where n=docs, m=features)
-  Cosine similarity is fast (O(n) for n reviewers)
-  Database queries use proper indexing
-  Can handle 100s of potential reviewers efficiently

### Optimization Tips:
1. Cache expertise areas with `prefetch_related()`
2. Limit max_recommendations to reasonable number (≤50)
3. Consider caching recommendations for unchanged submissions
4. Index ReviewAssignment queries on status and reviewer

---

## Future Enhancements

### Planned Features:
1. **Deep Learning Models**: Neural networks for better matching
2. **Collaborative Filtering**: Learn from past successful assignments
3. **Citation Networks**: Use OpenAlex citation data for matching
4. **Topic Modeling**: LDA/BERT for semantic topic extraction
5. **Conflict of Interest Detection**: Automatic CoI checking
6. **Geographic Preferences**: Consider reviewer location/timezone
7. **Language Matching**: Match reviewer language capabilities

### Integration Points:
- **OpenAlex**: Import publication history for expertise detection
- **ORCID**: Verify researcher credentials
- **ROR**: Validate institutional affiliations
- **Semantic Scholar**: Alternative publication data source

---

## Troubleshooting

### No Recommendations Returned

**Problem:** API returns empty recommendations list

**Solutions:**
1. Check that reviewers exist with Reviewer role
2. Verify reviewers have expertise areas assigned
3. Ensure submission has title/abstract
4. Check that reviewers aren't submission authors
5. Verify users are active (`is_active=True`)

### Low Similarity Scores

**Problem:** All recommendations have low similarity scores (<0.3)

**Solutions:**
1. Add more detailed expertise areas to reviewers
2. Include comprehensive keywords in submission metadata
3. Write detailed reviewer bios
4. Ensure abstract is present and detailed
5. Consider lowering similarity weight if needed

### ImportError: No module named 'sklearn'

**Problem:** scikit-learn not installed

**Solution:**
```bash
pip install scikit-learn==1.5.2 numpy==2.0.2
```

### All Reviewers Have Same Availability Score

**Problem:** Availability scores are identical

**Cause:** No ReviewAssignment records exist

**Solution:** System is working correctly - new reviewers get neutral scores. Scores will differentiate as reviews are completed.

---

## Testing

### Run Test Script:
```bash
python test_reviewer_recommendations.py
```

### Expected Output:
```
==============================================================
Testing Reviewer Recommendation System
==============================================================

 scikit-learn version: 1.5.2
 numpy version: 2.0.2
 Found 5 submissions to test
 Recommendation engine initialized

 Testing with submission: Machine Learning in Healthcare...
   Abstract: This paper explores the application of machine...

 Found 12 potential reviewers

 Generating ML recommendations...
 Generated 10 recommendations

==============================================================
TOP RECOMMENDATIONS:
==============================================================

1. Dr. Jane Smith
   Affiliation: Stanford University
   Expertise: Machine Learning, Healthcare AI, Medical Imaging
   Scores:
     - Composite:    0.847
     - Similarity:   0.920
     - Availability: 0.800
     - Quality:      0.850
     - Response:     0.750
   ...

 ALL TESTS PASSED!
```

---

## Summary

 **ML-powered** reviewer matching using TF-IDF and cosine similarity  
 **Multi-factor scoring** (similarity, availability, quality, response rate)  
 **Customizable weights** for different scenarios  
 **REST API endpoints** with OpenAPI documentation  
 **Automatic filtering** of authors and existing reviewers  
 **Scalable** for large reviewer pools  
 **Production-ready** with proper error handling  

**The system is ready to use!** 🚀
