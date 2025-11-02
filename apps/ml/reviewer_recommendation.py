"""
ML-powered reviewer recommendation system.
Uses TF-IDF and cosine similarity for matching reviewers to submissions.
"""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from typing import List, Dict, Tuple
from django.db.models import Q, Count, Avg
from django.utils import timezone
from datetime import timedelta

from apps.users.models import Profile, Role
from apps.submissions.models import Submission
from apps.reviews.models import ReviewAssignment, Review


class ReviewerRecommendationEngine:
    """
    ML-based reviewer recommendation engine using TF-IDF and cosine similarity.
    """
    
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.95
        )
    
    def get_potential_reviewers(self, submission: Submission, exclude_authors=True) -> List[Profile]:
        """
        Get list of potential reviewers excluding submission authors.
        """
        # Get all reviewers (users with Reviewer role)
        reviewer_role = Role.objects.filter(name='Reviewer').first()
        if not reviewer_role:
            # If no role exists, get profiles with expertise areas
            reviewers = Profile.objects.filter(
                expertise_areas__isnull=False
            ).distinct()
        else:
            reviewers = reviewer_role.profiles.all()
        
        # Exclude submission authors
        if exclude_authors:
            author_ids = [submission.corresponding_author.id]
            coauthor_ids = list(submission.coauthors.values_list('id', flat=True))
            exclude_ids = author_ids + coauthor_ids
            reviewers = reviewers.exclude(id__in=exclude_ids)
        
        # Exclude users who already reviewed this submission
        existing_reviewer_ids = ReviewAssignment.objects.filter(
            submission=submission
        ).values_list('reviewer_id', flat=True)
        reviewers = reviewers.exclude(id__in=existing_reviewer_ids)
        
        # Only active users
        reviewers = reviewers.filter(user__is_active=True)
        
        return list(reviewers.select_related('user').prefetch_related('expertise_areas'))
    
    def extract_text_features(self, submission: Submission) -> str:
        """
        Extract text features from submission for similarity matching.
        """
        features = []
        
        # Title (high weight - repeat 3 times)
        if submission.title:
            features.extend([submission.title] * 3)
        
        # Abstract (medium weight - repeat 2 times)
        if submission.abstract:
            features.extend([submission.abstract] * 2)
        
        # Keywords from metadata
        metadata = submission.metadata_json or {}
        keywords = metadata.get('keywords', [])
        if keywords:
            if isinstance(keywords, list):
                features.append(' '.join(keywords))
            else:
                features.append(str(keywords))
        
        # Tags from metadata
        tags = metadata.get('tags', [])
        if tags:
            if isinstance(tags, list):
                features.append(' '.join(tags))
            else:
                features.append(str(tags))
        
        return ' '.join(features)
    
    def extract_reviewer_features(self, reviewer: Profile) -> str:
        """
        Extract text features from reviewer profile for similarity matching.
        """
        features = []
        
        # Bio
        if reviewer.bio:
            features.append(reviewer.bio)
        
        # Expertise areas (high weight - repeat 5 times for strong match)
        expertise_areas = reviewer.expertise_areas.all()
        if expertise_areas:
            expertise_text = ' '.join([area.name for area in expertise_areas])
            features.extend([expertise_text] * 5)
        
        # Affiliation
        if reviewer.affiliation_name:
            features.append(reviewer.affiliation_name)
        
        # Display name (for name matching)
        if reviewer.display_name:
            features.append(reviewer.display_name)
        
        return ' '.join(features) if features else "no profile information"
    
    def calculate_similarity_scores(
        self,
        submission: Submission,
        reviewers: List[Profile]
    ) -> List[Tuple[Profile, float]]:
        """
        Calculate TF-IDF cosine similarity between submission and reviewers.
        Returns list of (reviewer, similarity_score) tuples.
        """
        if not reviewers:
            return []
        
        # Extract features
        submission_text = self.extract_text_features(submission)
        reviewer_texts = [self.extract_reviewer_features(r) for r in reviewers]
        
        # Create corpus
        corpus = [submission_text] + reviewer_texts
        
        try:
            # Fit TF-IDF vectorizer
            tfidf_matrix = self.vectorizer.fit_transform(corpus)
            
            # Calculate cosine similarity
            # First row is submission, rest are reviewers
            submission_vector = tfidf_matrix[0:1]
            reviewer_vectors = tfidf_matrix[1:]
            
            similarities = cosine_similarity(submission_vector, reviewer_vectors)[0]
            
            # Pair reviewers with their similarity scores
            reviewer_scores = list(zip(reviewers, similarities))
            
            return reviewer_scores
        
        except Exception as e:
            # If TF-IDF fails (e.g., empty text), return zero scores
            return [(r, 0.0) for r in reviewers]
    
    def calculate_availability_score(self, reviewer: Profile) -> float:
        """
        Calculate reviewer availability score (0-1) based on current workload.
        Lower workload = higher score.
        """
        # Count active review assignments
        active_assignments = ReviewAssignment.objects.filter(
            reviewer=reviewer,
            status__in=['PENDING', 'ACCEPTED']
        ).count()
        
        # Scoring: 0 reviews = 1.0, 5+ reviews = 0.0
        max_reviews = 5
        if active_assignments >= max_reviews:
            return 0.0
        else:
            return 1.0 - (active_assignments / max_reviews)
    
    def calculate_quality_score(self, reviewer: Profile) -> float:
        """
        Calculate reviewer quality score (0-1) based on past review quality.
        """
        # Get completed reviews
        completed_reviews = Review.objects.filter(
            reviewer=reviewer,
            quality_score__isnull=False
        )
        
        if not completed_reviews.exists():
            return 0.5  # Neutral score for new reviewers
        
        # Average quality score (already 0-10)
        avg_quality = completed_reviews.aggregate(Avg('quality_score'))['quality_score__avg']
        
        # Normalize to 0-1
        return avg_quality / 10.0 if avg_quality else 0.5
    
    def calculate_response_rate_score(self, reviewer: Profile) -> float:
        """
        Calculate reviewer response rate score (0-1).
        Considers invitation acceptance rate and on-time completion rate.
        """
        # Get all assignments
        all_assignments = ReviewAssignment.objects.filter(reviewer=reviewer)
        total = all_assignments.count()
        
        if total == 0:
            return 0.5  # Neutral score for new reviewers
        
        # Acceptance rate
        accepted = all_assignments.filter(status__in=['ACCEPTED', 'COMPLETED']).count()
        acceptance_rate = accepted / total
        
        # On-time completion rate
        completed = all_assignments.filter(status='COMPLETED')
        if completed.exists():
            on_time = completed.filter(
                completed_at__lte=models.F('due_date')
            ).count()
            completion_rate = on_time / completed.count()
        else:
            completion_rate = 0.5  # Neutral if no completions yet
        
        # Weighted average: 60% acceptance, 40% on-time completion
        return (acceptance_rate * 0.6) + (completion_rate * 0.4)
    
    def recommend_reviewers(
        self,
        submission: Submission,
        max_recommendations: int = 10,
        weights: Dict[str, float] = None
    ) -> List[Dict]:
        """
        Main recommendation function.
        
        Args:
            submission: Submission to find reviewers for
            max_recommendations: Maximum number of recommendations to return
            weights: Dictionary of weights for different scoring factors
                    Default: {'similarity': 0.5, 'availability': 0.2, 'quality': 0.2, 'response_rate': 0.1}
        
        Returns:
            List of dictionaries containing reviewer info and scores
        """
        # Default weights
        if weights is None:
            weights = {
                'similarity': 0.5,      # Content match
                'availability': 0.2,    # Current workload
                'quality': 0.2,         # Past review quality
                'response_rate': 0.1    # Response and completion rates
            }
        
        # Get potential reviewers
        potential_reviewers = self.get_potential_reviewers(submission)
        
        if not potential_reviewers:
            return []
        
        # Calculate similarity scores
        similarity_scores = self.calculate_similarity_scores(submission, potential_reviewers)
        
        # Calculate composite scores
        recommendations = []
        for reviewer, similarity in similarity_scores:
            # Calculate individual scores
            availability = self.calculate_availability_score(reviewer)
            quality = self.calculate_quality_score(reviewer)
            response_rate = self.calculate_response_rate_score(reviewer)
            
            # Calculate weighted composite score
            composite_score = (
                (similarity * weights['similarity']) +
                (availability * weights['availability']) +
                (quality * weights['quality']) +
                (response_rate * weights['response_rate'])
            )
            
            # Get expertise areas for display
            expertise = list(reviewer.expertise_areas.values_list('name', flat=True))
            
            # Get current workload
            active_reviews = ReviewAssignment.objects.filter(
                reviewer=reviewer,
                status__in=['PENDING', 'ACCEPTED']
            ).count()
            
            recommendations.append({
                'reviewer_id': str(reviewer.id),
                'reviewer_name': reviewer.display_name or reviewer.user.get_full_name(),
                'reviewer_email': reviewer.user.email,
                'affiliation': reviewer.affiliation_name or '',
                'expertise_areas': expertise,
                'orcid_id': reviewer.orcid_id or '',
                'openalex_id': reviewer.openalex_id or '',
                'scores': {
                    'composite': round(composite_score, 3),
                    'similarity': round(similarity, 3),
                    'availability': round(availability, 3),
                    'quality': round(quality, 3),
                    'response_rate': round(response_rate, 3),
                },
                'metrics': {
                    'active_reviews': active_reviews,
                    'total_reviews_completed': Review.objects.filter(reviewer=reviewer).count(),
                    'average_quality_score': round(quality * 10, 2),  # Convert back to 0-10 scale
                },
                'recommendation_reason': self._generate_reason(similarity, availability, quality, response_rate)
            })
        
        # Sort by composite score (descending)
        recommendations.sort(key=lambda x: x['scores']['composite'], reverse=True)
        
        # Return top N recommendations
        return recommendations[:max_recommendations]
    
    def _generate_reason(self, similarity: float, availability: float, quality: float, response_rate: float) -> str:
        """Generate human-readable recommendation reason."""
        reasons = []
        
        if similarity > 0.5:
            reasons.append("Strong expertise match")
        elif similarity > 0.3:
            reasons.append("Good expertise match")
        
        if availability > 0.8:
            reasons.append("High availability")
        elif availability > 0.5:
            reasons.append("Moderate availability")
        
        if quality > 0.7:
            reasons.append("High-quality reviewer")
        
        if response_rate > 0.7:
            reasons.append("Reliable response rate")
        
        if not reasons:
            return "Available reviewer"
        
        return ", ".join(reasons)


# Import models at the end to avoid circular imports
from django.db import models
