"""
ML-powered features API views.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from apps.submissions.models import Submission
from .reviewer_recommendation import ReviewerRecommendationEngine


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
