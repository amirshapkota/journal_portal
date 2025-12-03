"""
Anomaly Detection System for Journal Portal
Detects suspicious behavior patterns and potential fraud.
"""

from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Avg, Q, F
from collections import defaultdict
import numpy as np

from apps.submissions.models import Submission
from apps.reviews.models import ReviewAssignment, Review
from apps.users.models import Profile
from django.contrib.auth import get_user_model

User = get_user_model()


class AnomalyDetectionEngine:
    """
    ML-based anomaly detection engine for identifying suspicious patterns.
    """
    
    # Thresholds for various anomalies
    RAPID_SUBMISSION_THRESHOLD = 5  # submissions in 24 hours
    RAPID_SUBMISSION_WINDOW = 24  # hours
    
    HIGH_SELF_CITATION_THRESHOLD = 0.3  # 30% self-citations
    
    SUSPICIOUS_REVIEW_RATE_THRESHOLD = 0.9  # 90% always accept or reject
    MIN_REVIEWS_FOR_PATTERN = 10
    
    REVIEW_RING_MIN_RECIPROCAL = 3  # minimum reciprocal reviews
    
    SUSPICIOUS_ACTIVITY_SCORE_THRESHOLD = 0.7  # 0-1 scale
    
    def __init__(self):
        """Initialize the anomaly detection engine."""
        self.anomalies = []
    
    # ==================== Author Behavior Anomalies ====================
    
    def detect_rapid_submissions(self, author_profile):
        """
        Detect if an author is submitting papers too rapidly.
        
        Args:
            author_profile: Profile object of the author
            
        Returns:
            dict with anomaly details or None
        """
        cutoff_time = timezone.now() - timedelta(hours=self.RAPID_SUBMISSION_WINDOW)
        
        recent_submissions = Submission.objects.filter(
            corresponding_author=author_profile,
            created_at__gte=cutoff_time
        ).count()
        
        if recent_submissions >= self.RAPID_SUBMISSION_THRESHOLD:
            return {
                'type': 'RAPID_SUBMISSIONS',
                'severity': 'HIGH',
                'author': author_profile.user.email,
                'author_id': str(author_profile.id),
                'count': recent_submissions,
                'window_hours': self.RAPID_SUBMISSION_WINDOW,
                'description': f'Author submitted {recent_submissions} papers in {self.RAPID_SUBMISSION_WINDOW} hours',
                'recommendation': 'Review for potential spam or bot activity'
            }
        return None
    
    def detect_excessive_self_citations(self, submission):
        """
        Detect if a submission has excessive self-citations.
        
        Args:
            submission: Submission object
            
        Returns:
            dict with anomaly details or None
        """
        metadata = submission.metadata_json
        
        # Handle case where metadata might be a string
        if isinstance(metadata, str):
            try:
                import json
                metadata = json.loads(metadata)
            except:
                metadata = {}
        
        references = metadata.get('references', []) if isinstance(metadata, dict) else []
        
        if not references or len(references) < 10:
            return None  # Too few references to judge
        
        author_name = submission.corresponding_author.get_full_name().lower()
        
        # Count self-citations
        self_citations = 0
        for ref in references:
            ref_text = str(ref).lower() if isinstance(ref, str) else ''
            if author_name in ref_text:
                self_citations += 1
        
        self_citation_rate = self_citations / len(references)
        
        if self_citation_rate >= self.HIGH_SELF_CITATION_THRESHOLD:
            return {
                'type': 'EXCESSIVE_SELF_CITATIONS',
                'severity': 'MEDIUM',
                'submission_id': str(submission.id),
                'submission_title': submission.title,
                'author': submission.corresponding_author.user.email if submission.corresponding_author else 'Unknown',
                'self_citation_count': self_citations,
                'total_citations': len(references),
                'rate': round(self_citation_rate, 2),
                'description': f'{int(self_citation_rate*100)}% self-citations ({self_citations}/{len(references)})',
                'recommendation': 'Review for citation manipulation'
            }
        return None
    
    def detect_duplicate_content(self, submission):
        """
        Detect if submission content is too similar to other submissions.
        Simple implementation using title/abstract similarity.
        
        Args:
            submission: Submission object
            
        Returns:
            dict with anomaly details or None
        """
        # Skip if no corresponding author
        if not submission.corresponding_author:
            return None
        
        # Get other submissions by the same author
        other_submissions = Submission.objects.filter(
            corresponding_author=submission.corresponding_author
        ).exclude(id=submission.id)
        
        # Simple similarity check using title overlap
        submission_title_words = set(submission.title.lower().split())
        
        for other in other_submissions:
            other_title_words = set(other.title.lower().split())
            
            # Calculate Jaccard similarity
            intersection = submission_title_words & other_title_words
            union = submission_title_words | other_title_words
            
            if union:
                similarity = len(intersection) / len(union)
                
                if similarity > 0.7:  # 70% title similarity
                    return {
                        'type': 'DUPLICATE_CONTENT',
                        'severity': 'HIGH',
                        'submission_id': str(submission.id),
                        'submission_title': submission.title,
                        'similar_submission_id': str(other.id),
                        'similar_submission_title': other.title,
                        'similarity_score': round(similarity, 2),
                        'description': f'Submission highly similar to another paper by same author',
                        'recommendation': 'Check for duplicate submission or plagiarism'
                    }
        return None
    
    # ==================== Reviewer Behavior Anomalies ====================
    
    def detect_biased_reviewer(self, reviewer_profile):
        """
        Detect if a reviewer consistently accepts or rejects submissions.
        
        Args:
            reviewer_profile: Profile object of the reviewer
            
        Returns:
            dict with anomaly details or None
        """
        completed_reviews = Review.objects.filter(
            assignment__reviewer=reviewer_profile,
            recommendation__isnull=False
        )
        
        total_reviews = completed_reviews.count()
        
        if total_reviews < self.MIN_REVIEWS_FOR_PATTERN:
            return None  # Not enough data
        
        # Count recommendations
        accept_count = completed_reviews.filter(
            recommendation__in=['ACCEPT', 'MINOR_REVISION']
        ).count()
        
        reject_count = completed_reviews.filter(
            recommendation__in=['REJECT', 'MAJOR_REVISION']
        ).count()
        
        accept_rate = accept_count / total_reviews
        reject_rate = reject_count / total_reviews
        
        if accept_rate >= self.SUSPICIOUS_REVIEW_RATE_THRESHOLD:
            return {
                'type': 'BIASED_REVIEWER_ACCEPTS',
                'severity': 'MEDIUM',
                'reviewer': reviewer_profile.user.email,
                'reviewer_id': str(reviewer_profile.id),
                'accept_rate': round(accept_rate, 2),
                'total_reviews': total_reviews,
                'description': f'Reviewer accepts {int(accept_rate*100)}% of submissions',
                'recommendation': 'Review for potential bias or collusion'
            }
        
        if reject_rate >= self.SUSPICIOUS_REVIEW_RATE_THRESHOLD:
            return {
                'type': 'BIASED_REVIEWER_REJECTS',
                'severity': 'MEDIUM',
                'reviewer': reviewer_profile.user.email,
                'reviewer_id': str(reviewer_profile.id),
                'reject_rate': round(reject_rate, 2),
                'total_reviews': total_reviews,
                'description': f'Reviewer rejects {int(reject_rate*100)}% of submissions',
                'recommendation': 'Review for potential bias or overly critical reviewer'
            }
        
        return None
    
    def detect_review_rings(self):
        """
        Detect potential review rings (authors reviewing each other's work favorably).
        
        Returns:
            list of anomaly dicts
        """
        anomalies = []
        
        # Get all reviewer-author pairs with favorable reviews
        favorable_reviews = Review.objects.filter(
            recommendation__in=['ACCEPT', 'MINOR_REVISION']
        ).select_related('assignment__reviewer', 'assignment__submission__corresponding_author')
        
        # Build graph of favorable reviews
        review_graph = defaultdict(lambda: defaultdict(int))
        
        for review in favorable_reviews:
            reviewer = review.assignment.reviewer
            author = review.assignment.submission.corresponding_author
            
            if reviewer and author and reviewer != author:
                review_graph[reviewer.id][author.id] += 1
        
        # Detect reciprocal patterns
        checked_pairs = set()
        
        for reviewer_id, reviewed_authors in review_graph.items():
            for author_id, count in reviewed_authors.items():
                # Check if this author has also reviewed the reviewer's papers
                reciprocal_count = review_graph.get(author_id, {}).get(reviewer_id, 0)
                
                pair_key = tuple(sorted([reviewer_id, author_id]))
                
                if reciprocal_count >= self.REVIEW_RING_MIN_RECIPROCAL and pair_key not in checked_pairs:
                    checked_pairs.add(pair_key)
                    
                    reviewer_profile = Profile.objects.get(id=reviewer_id)
                    author_profile = Profile.objects.get(id=author_id)
                    
                    anomalies.append({
                        'type': 'REVIEW_RING',
                        'severity': 'HIGH',
                        'user1': reviewer_profile.user.email,
                        'user1_id': str(reviewer_id),
                        'user2': author_profile.user.email,
                        'user2_id': str(author_id),
                        'reciprocal_reviews': count + reciprocal_count,
                        'description': f'Mutual favorable reviews detected between users',
                        'recommendation': 'Investigate for potential collusion'
                    })
        
        return anomalies
    
    def detect_rushed_reviews(self, review):
        """
        Detect if a review was completed suspiciously quickly.
        
        Args:
            review: Review object
            
        Returns:
            dict with anomaly details or None
        """
        assignment = review.assignment
        
        # Use accepted_at or invited_at as start time
        start_time = assignment.accepted_at or assignment.invited_at
        
        if not start_time or not review.submitted_at:
            return None
        
        time_taken = review.submitted_at - start_time
        hours_taken = time_taken.total_seconds() / 3600
        
        # Suspicious if completed in less than 1 hour
        if hours_taken < 1:
            return {
                'type': 'RUSHED_REVIEW',
                'severity': 'MEDIUM',
                'review_id': str(review.id),
                'reviewer': assignment.reviewer.user.email,
                'submission_title': assignment.submission.title,
                'hours_taken': round(hours_taken, 2),
                'description': f'Review completed in {round(hours_taken, 2)} hours',
                'recommendation': 'Verify review quality and thoroughness'
            }
        return None
    
    # ==================== Account Behavior Anomalies ====================
    
    def detect_bot_account(self, profile):
        """
        Detect potential bot accounts based on behavior patterns.
        
        Args:
            profile: Profile object
            
        Returns:
            dict with anomaly details or None
        """
        user = profile.user
        
        # Check for suspicious patterns
        suspicion_score = 0
        reasons = []
        
        # Recently created account with immediate submissions
        account_age_days = (timezone.now() - user.created_at).days
        submissions_count = Submission.objects.filter(corresponding_author=profile).count()
        
        if account_age_days < 7 and submissions_count > 3:
            suspicion_score += 0.3
            reasons.append('New account with multiple submissions')
        
        # Generic/suspicious email pattern
        email = user.email.lower()
        if any(pattern in email for pattern in ['test', 'temp', 'fake', '123', 'dummy']):
            suspicion_score += 0.2
            reasons.append('Suspicious email pattern')
        
        # No profile information
        if not profile.bio and not profile.affiliation_name and not profile.orcid_id:
            suspicion_score += 0.2
            reasons.append('No profile information')
        
        # No expertise areas
        if profile.expertise_areas.count() == 0:
            suspicion_score += 0.15
            reasons.append('No expertise areas')
        
        # Rapid activity
        if account_age_days > 0:
            activity_rate = submissions_count / account_age_days
            if activity_rate > 2:  # More than 2 submissions per day on average
                suspicion_score += 0.15
                reasons.append(f'High activity rate ({activity_rate:.1f} submissions/day)')
        
        if suspicion_score >= self.SUSPICIOUS_ACTIVITY_SCORE_THRESHOLD:
            return {
                'type': 'BOT_ACCOUNT',
                'severity': 'HIGH',
                'user_email': user.email,
                'user_id': str(profile.id),
                'suspicion_score': round(suspicion_score, 2),
                'reasons': reasons,
                'account_age_days': account_age_days,
                'description': 'Potential bot or fake account detected',
                'recommendation': 'Verify account authenticity and consider suspension'
            }
        
        return None
    
    # ==================== Main Detection Methods ====================
    
    def scan_author(self, author_profile):
        """
        Run all author-related anomaly checks.
        
        Args:
            author_profile: Profile object
            
        Returns:
            list of detected anomalies
        """
        anomalies = []
        
        # Check for rapid submissions
        anomaly = self.detect_rapid_submissions(author_profile)
        if anomaly:
            anomalies.append(anomaly)
        
        # Check for bot account
        anomaly = self.detect_bot_account(author_profile)
        if anomaly:
            anomalies.append(anomaly)
        
        # Check each submission for issues
        submissions = Submission.objects.filter(corresponding_author=author_profile)
        for submission in submissions:
            # Check self-citations
            anomaly = self.detect_excessive_self_citations(submission)
            if anomaly:
                anomalies.append(anomaly)
            
            # Check duplicate content
            anomaly = self.detect_duplicate_content(submission)
            if anomaly:
                anomalies.append(anomaly)
        
        return anomalies
    
    def scan_reviewer(self, reviewer_profile):
        """
        Run all reviewer-related anomaly checks.
        
        Args:
            reviewer_profile: Profile object
            
        Returns:
            list of detected anomalies
        """
        anomalies = []
        
        # Check for biased reviewer
        anomaly = self.detect_biased_reviewer(reviewer_profile)
        if anomaly:
            anomalies.append(anomaly)
        
        # Check for rushed reviews
        reviews = Review.objects.filter(
            assignment__reviewer=reviewer_profile,
            submitted_at__isnull=False
        )
        for review in reviews:
            anomaly = self.detect_rushed_reviews(review)
            if anomaly:
                anomalies.append(anomaly)
        
        return anomalies
    
    def scan_submission(self, submission):
        """
        Run all submission-related anomaly checks.
        
        Args:
            submission: Submission object
            
        Returns:
            list of detected anomalies
        """
        anomalies = []
        
        # Check self-citations
        anomaly = self.detect_excessive_self_citations(submission)
        if anomaly:
            anomalies.append(anomaly)
        
        # Check duplicate content
        anomaly = self.detect_duplicate_content(submission)
        if anomaly:
            anomalies.append(anomaly)
        
        return anomalies
    
    def scan_all(self):
        """
        Run a comprehensive scan of the entire system.
        
        Returns:
            dict with categorized anomalies
        """
        all_anomalies = {
            'author_anomalies': [],
            'reviewer_anomalies': [],
            'submission_anomalies': [],
            'review_ring_anomalies': [],
            'total_count': 0,
            'severity_counts': {
                'HIGH': 0,
                'MEDIUM': 0,
                'LOW': 0
            }
        }
        
        # Scan all authors
        authors = Profile.objects.filter(
            corresponding_submissions__isnull=False
        ).distinct()
        
        for author in authors:
            anomalies = self.scan_author(author)
            all_anomalies['author_anomalies'].extend(anomalies)
        
        # Scan all reviewers
        reviewers = Profile.objects.filter(
            review_assignments__isnull=False
        ).distinct()
        
        for reviewer in reviewers:
            anomalies = self.scan_reviewer(reviewer)
            all_anomalies['reviewer_anomalies'].extend(anomalies)
        
        # Detect review rings
        ring_anomalies = self.detect_review_rings()
        all_anomalies['review_ring_anomalies'].extend(ring_anomalies)
        
        # Count totals
        all_detected = (
            all_anomalies['author_anomalies'] +
            all_anomalies['reviewer_anomalies'] +
            all_anomalies['review_ring_anomalies']
        )
        
        all_anomalies['total_count'] = len(all_detected)
        
        # Count by severity
        for anomaly in all_detected:
            severity = anomaly.get('severity', 'LOW')
            all_anomalies['severity_counts'][severity] += 1
        
        return all_anomalies
    
    def get_user_risk_score(self, profile):
        """
        Calculate an overall risk score for a user.
        
        Args:
            profile: Profile object
            
        Returns:
            dict with risk score and contributing factors
        """
        anomalies = self.scan_author(profile) + self.scan_reviewer(profile)
        
        if not anomalies:
            return {
                'user_email': profile.user.email,
                'risk_score': 0.0,
                'risk_level': 'LOW',
                'anomaly_count': 0,
                'anomalies': []
            }
        
        # Calculate risk score based on anomaly severity
        risk_score = 0
        for anomaly in anomalies:
            if anomaly['severity'] == 'HIGH':
                risk_score += 0.4
            elif anomaly['severity'] == 'MEDIUM':
                risk_score += 0.2
            else:
                risk_score += 0.1
        
        risk_score = min(risk_score, 1.0)  # Cap at 1.0
        
        # Determine risk level
        if risk_score >= 0.7:
            risk_level = 'HIGH'
        elif risk_score >= 0.4:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'
        
        return {
            'user_email': profile.user.email,
            'user_id': str(profile.id),
            'risk_score': round(risk_score, 2),
            'risk_level': risk_level,
            'anomaly_count': len(anomalies),
            'anomalies': anomalies
        }
