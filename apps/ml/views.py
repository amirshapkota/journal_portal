"""
ML-powered features API views.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from django.utils import timezone

from apps.submissions.models import Submission
from apps.users.models import Profile
from .reviewer_recommendation import ReviewerRecommendationEngine
from .anomaly_detection import AnomalyDetectionEngine
from .permissions import IsAdminOrEditor, CanViewOwnRiskScore


class ReviewerRecommendationView(APIView):
    """
    Get ML-powered reviewer recommendations for a submission.
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Get reviewer recommendations",
        description="""
        Get ML-powered reviewer recommendations for a submission.
        
        The system uses TF-IDF and cosine similarity to match reviewers based on:
        - Expertise areas matching submission content
        - Current availability (workload)
        - Past review quality
        - Response and completion rates
        
        Returns a ranked list of recommended reviewers with scores and reasons.
        """,
        parameters=[
            OpenApiParameter(
                name='submission_id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description='UUID of the submission'
            ),
            OpenApiParameter(
                name='max_recommendations',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Maximum number of recommendations to return (default: 10)',
                required=False
            ),
        ],
        responses={
            200: {
                'description': 'Reviewer recommendations',
                'content': {
                    'application/json': {
                        'example': {
                            'submission_id': '123e4567-e89b-12d3-a456-426614174000',
                            'submission_title': 'Machine Learning in Healthcare',
                            'total_potential_reviewers': 25,
                            'recommendations': [
                                {
                                    'reviewer_id': '456e7890-e89b-12d3-a456-426614174001',
                                    'reviewer_name': 'Dr. Jane Smith',
                                    'reviewer_email': 'jane.smith@university.edu',
                                    'affiliation': 'Stanford University',
                                    'expertise_areas': ['Machine Learning', 'Healthcare AI', 'Medical Imaging'],
                                    'orcid_id': '0000-0001-2345-6789',
                                    'scores': {
                                        'composite': 0.847,
                                        'similarity': 0.92,
                                        'availability': 0.8,
                                        'quality': 0.85,
                                        'response_rate': 0.75
                                    },
                                    'metrics': {
                                        'active_reviews': 1,
                                        'total_reviews_completed': 15,
                                        'average_quality_score': 8.5
                                    },
                                    'recommendation_reason': 'Strong expertise match, High availability, High-quality reviewer'
                                }
                            ]
                        }
                    }
                }
            },
            404: {'description': 'Submission not found'}
        }
    )
    def get(self, request, submission_id):
        """Get reviewer recommendations for a submission."""
        try:
            submission = Submission.objects.get(id=submission_id)
        except Submission.DoesNotExist:
            return Response(
                {'detail': 'Submission not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get max recommendations parameter
        max_recommendations = int(request.query_params.get('max_recommendations', 10))
        max_recommendations = min(max(max_recommendations, 1), 50)  # Limit to 1-50
        
        # Initialize recommendation engine
        engine = ReviewerRecommendationEngine()
        
        # Get recommendations
        recommendations = engine.recommend_reviewers(
            submission=submission,
            max_recommendations=max_recommendations
        )
        
        # Get total potential reviewers
        potential_reviewers = engine.get_potential_reviewers(submission)
        
        return Response({
            'submission_id': str(submission.id),
            'submission_title': submission.title,
            'total_potential_reviewers': len(potential_reviewers),
            'recommendations': recommendations,
            'recommendation_count': len(recommendations)
        })


class ReviewerRecommendationCustomWeightsView(APIView):
    """
    Get reviewer recommendations with custom scoring weights.
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Get reviewer recommendations with custom weights",
        description="""
        Get reviewer recommendations with custom scoring weights.
        
        Allows you to adjust the importance of different factors:
        - similarity: How well reviewer expertise matches submission content (0-1)
        - availability: Reviewer's current workload (0-1)
        - quality: Past review quality scores (0-1)
        - response_rate: Historical response and completion rates (0-1)
        
        Weights should sum to 1.0 for best results.
        """,
        request={
            'application/json': {
                'example': {
                    'weights': {
                        'similarity': 0.6,
                        'availability': 0.2,
                        'quality': 0.15,
                        'response_rate': 0.05
                    },
                    'max_recommendations': 15
                }
            }
        },
        responses={
            200: {'description': 'Reviewer recommendations with custom weights'},
            400: {'description': 'Invalid weights'},
            404: {'description': 'Submission not found'}
        }
    )
    def post(self, request, submission_id):
        """Get recommendations with custom weights."""
        try:
            submission = Submission.objects.get(id=submission_id)
        except Submission.DoesNotExist:
            return Response(
                {'detail': 'Submission not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get weights from request
        weights = request.data.get('weights', {})
        
        # Validate weights
        required_keys = ['similarity', 'availability', 'quality', 'response_rate']
        if not all(key in weights for key in required_keys):
            return Response(
                {
                    'detail': 'Missing weight keys. Required: similarity, availability, quality, response_rate',
                    'example': {
                        'similarity': 0.5,
                        'availability': 0.2,
                        'quality': 0.2,
                        'response_rate': 0.1
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate weight values
        try:
            weights = {k: float(v) for k, v in weights.items()}
            if not all(0 <= v <= 1 for v in weights.values()):
                raise ValueError("Weights must be between 0 and 1")
        except (ValueError, TypeError) as e:
            return Response(
                {'detail': f'Invalid weights: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get max recommendations
        max_recommendations = int(request.data.get('max_recommendations', 10))
        max_recommendations = min(max(max_recommendations, 1), 50)
        
        # Initialize engine and get recommendations
        engine = ReviewerRecommendationEngine()
        recommendations = engine.recommend_reviewers(
            submission=submission,
            max_recommendations=max_recommendations,
            weights=weights
        )
        
        return Response({
            'submission_id': str(submission.id),
            'submission_title': submission.title,
            'weights_used': weights,
            'recommendations': recommendations,
            'recommendation_count': len(recommendations)
        })


# ==================== Anomaly Detection Views ====================


class AnomalyDetectionScanView(APIView):
    """
    Run a comprehensive anomaly detection scan.
    
    **Admin/Editor Only** - This endpoint is restricted to administrators and editors
    as it reveals sensitive security information about users and submissions.
    """
    permission_classes = [IsAdminOrEditor]
    
    @extend_schema(
        summary="Run comprehensive anomaly detection scan",
        description="""
        Scans the entire system for suspicious patterns and anomalies:
        
        - Rapid submissions from authors
        - Excessive self-citations
        - Biased reviewers (always accept/reject)
        - Review rings (mutual favorable reviews)
        - Bot/fake accounts
        - Rushed reviews
        - Duplicate content
        
        Returns categorized anomalies with severity levels.
        """,
        responses={
            200: {
                'description': 'Anomaly scan results',
                'content': {
                    'application/json': {
                        'example': {
                            'scan_completed_at': '2025-11-04T10:30:00Z',
                            'total_anomalies': 15,
                            'severity_counts': {
                                'HIGH': 5,
                                'MEDIUM': 7,
                                'LOW': 3
                            },
                            'author_anomalies': [],
                            'reviewer_anomalies': [],
                            'review_ring_anomalies': []
                        }
                    }
                }
            }
        }
    )
    def get(self, request):
        """Run comprehensive anomaly scan."""
        engine = AnomalyDetectionEngine()
        results = engine.scan_all()
        
        return Response({
            'scan_completed_at': timezone.now().isoformat(),
            **results
        })


class UserRiskScoreView(APIView):
    """
    Get risk score for a specific user.
    
    **Permission Levels:**
    - Users can view their own risk score
    - Admins/Editors can view anyone's risk score
    """
    permission_classes = [CanViewOwnRiskScore]
    
    @extend_schema(
        summary="Get user risk score",
        description="""
        Calculate a risk score for a specific user based on detected anomalies.
        
        Risk levels:
        - LOW (0.0 - 0.39): Normal behavior
        - MEDIUM (0.4 - 0.69): Some suspicious patterns
        - HIGH (0.7 - 1.0): Multiple red flags
        
        Returns detailed anomalies contributing to the risk score.
        """,
        parameters=[
            OpenApiParameter(
                name='user_id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description='UUID of the user profile'
            ),
        ],
        responses={
            200: {
                'description': 'User risk assessment',
                'content': {
                    'application/json': {
                        'example': {
                            'user_email': 'user@example.com',
                            'user_id': '123e4567-e89b-12d3-a456-426614174000',
                            'risk_score': 0.6,
                            'risk_level': 'MEDIUM',
                            'anomaly_count': 3,
                            'anomalies': [
                                {
                                    'type': 'RAPID_SUBMISSIONS',
                                    'severity': 'HIGH',
                                    'description': 'Author submitted 7 papers in 24 hours'
                                }
                            ]
                        }
                    }
                }
            },
            404: {'description': 'User not found'}
        }
    )
    def get(self, request, user_id):
        """Get risk score for a user."""
        try:
            profile = Profile.objects.get(id=user_id)
        except Profile.DoesNotExist:
            return Response(
                {'detail': 'User not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        engine = AnomalyDetectionEngine()
        risk_assessment = engine.get_user_risk_score(profile)
        
        return Response(risk_assessment)


class SubmissionAnomaliesView(APIView):
    """
    Detect anomalies in a specific submission.
    
    **Admin/Editor Only** - Checks submissions for fraud/suspicious patterns.
    """
    permission_classes = [IsAdminOrEditor]
    
    @extend_schema(
        summary="Detect submission anomalies",
        description="""
        Check a specific submission for suspicious patterns:
        
        - Excessive self-citations
        - Duplicate content
        - Author behavior issues
        
        Returns list of detected anomalies.
        """,
        parameters=[
            OpenApiParameter(
                name='submission_id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description='UUID of the submission'
            ),
        ],
        responses={
            200: {
                'description': 'Submission anomalies',
                'content': {
                    'application/json': {
                        'example': {
                            'submission_id': '123e4567-e89b-12d3-a456-426614174000',
                            'submission_title': 'Sample Paper',
                            'anomaly_count': 1,
                            'anomalies': [
                                {
                                    'type': 'EXCESSIVE_SELF_CITATIONS',
                                    'severity': 'MEDIUM',
                                    'rate': 0.35,
                                    'description': '35% self-citations (14/40)'
                                }
                            ]
                        }
                    }
                }
            },
            404: {'description': 'Submission not found'}
        }
    )
    def get(self, request, submission_id):
        """Detect anomalies in a submission."""
        try:
            submission = Submission.objects.get(id=submission_id)
        except Submission.DoesNotExist:
            return Response(
                {'detail': 'Submission not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        engine = AnomalyDetectionEngine()
        anomalies = engine.scan_submission(submission)
        
        return Response({
            'submission_id': str(submission.id),
            'submission_title': submission.title,
            'author': submission.corresponding_author.user.email,
            'anomaly_count': len(anomalies),
            'anomalies': anomalies
        })


class ReviewerAnomaliesView(APIView):
    """
    Detect anomalies in reviewer behavior.
    
    **Admin/Editor Only** - Checks reviewers for bias/misconduct.
    """
    permission_classes = [IsAdminOrEditor]
    
    @extend_schema(
        summary="Detect reviewer anomalies",
        description="""
        Check a reviewer's behavior for suspicious patterns:
        
        - Biased reviewing (always accept/reject)
        - Rushed reviews
        - Review ring participation
        
        Returns list of detected anomalies.
        """,
        parameters=[
            OpenApiParameter(
                name='reviewer_id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description='UUID of the reviewer profile'
            ),
        ],
        responses={
            200: {
                'description': 'Reviewer anomalies',
                'content': {
                    'application/json': {
                        'example': {
                            'reviewer_id': '123e4567-e89b-12d3-a456-426614174000',
                            'reviewer_email': 'reviewer@example.com',
                            'anomaly_count': 1,
                            'anomalies': [
                                {
                                    'type': 'BIASED_REVIEWER_ACCEPTS',
                                    'severity': 'MEDIUM',
                                    'accept_rate': 0.95,
                                    'description': 'Reviewer accepts 95% of submissions'
                                }
                            ]
                        }
                    }
                }
            },
            404: {'description': 'Reviewer not found'}
        }
    )
    def get(self, request, reviewer_id):
        """Detect anomalies in reviewer behavior."""
        try:
            reviewer = Profile.objects.get(id=reviewer_id)
        except Profile.DoesNotExist:
            return Response(
                {'detail': 'Reviewer not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        engine = AnomalyDetectionEngine()
        anomalies = engine.scan_reviewer(reviewer)
        
        return Response({
            'reviewer_id': str(reviewer.id),
            'reviewer_email': reviewer.user.email,
            'anomaly_count': len(anomalies),
            'anomalies': anomalies
        })
