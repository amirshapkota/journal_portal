"""
Analytics views for dashboard metrics and reporting.
Provides comprehensive analytics for admins, editors, reviewers, and authors.
"""
from django.db.models import Count, Avg, Q, F, DurationField, ExpressionWrapper
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone
from datetime import timedelta

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter

from apps.submissions.models import Submission
from apps.reviews.models import Review, ReviewAssignment, EditorialDecision
from apps.journals.models import Journal
from apps.users.models import Profile, VerificationRequest


class IsAdminOrEditor(permissions.BasePermission):
    """
    Permission class to allow access only to admin or editor users.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (
            request.user.is_staff or 
            request.user.profile.roles.filter(name='EDITOR').exists()
        )


class AnalyticsDashboardView(APIView):
    """
    Main analytics dashboard providing overview metrics.
    """
    permission_classes = [IsAdminOrEditor]
    
    @extend_schema(
        summary="Get dashboard overview",
        description="Get comprehensive dashboard metrics including submissions, reviews, and user stats."
    )
    def get(self, request):
        """Get dashboard overview metrics."""
        # Time ranges
        today = timezone.now()
        last_30_days = today - timedelta(days=30)
        last_7_days = today - timedelta(days=7)
        
        # Submission metrics
        total_submissions = Submission.objects.count()
        pending_submissions = Submission.objects.filter(
            status__in=['SUBMITTED', 'UNDER_REVIEW']
        ).count()
        accepted_submissions = Submission.objects.filter(status='ACCEPTED').count()
        rejected_submissions = Submission.objects.filter(status='REJECTED').count()
        
        submissions_last_30 = Submission.objects.filter(
            created_at__gte=last_30_days
        ).count()
        
        # Review metrics
        total_reviews = Review.objects.count()
        pending_reviews = ReviewAssignment.objects.filter(
            status='PENDING'
        ).count()
        completed_reviews = ReviewAssignment.objects.filter(
            status='COMPLETED'
        ).count()
        
        # Calculate average review time
        completed_review_assignments = ReviewAssignment.objects.filter(
            status='COMPLETED',
            completed_at__isnull=False
        )
        
        avg_review_time = None
        if completed_review_assignments.exists():
            avg_time = completed_review_assignments.annotate(
                duration=ExpressionWrapper(
                    F('completed_at') - F('invited_at'),
                    output_field=DurationField()
                )
            ).aggregate(avg_duration=Avg('duration'))
            
            if avg_time['avg_duration']:
                avg_review_time = avg_time['avg_duration'].days
        
        # User metrics
        total_users = Profile.objects.count()
        verified_users = Profile.objects.filter(verification_status='GENUINE').count()
        pending_verifications = VerificationRequest.objects.filter(
            status='PENDING'
        ).count()
        
        authors_count = Profile.objects.filter(roles__name='AUTHOR').distinct().count()
        reviewers_count = Profile.objects.filter(roles__name='REVIEWER').distinct().count()
        
        # Journal metrics
        total_journals = Journal.objects.count()
        active_journals = Journal.objects.filter(is_active=True).count()
        
        # Acceptance rate
        total_decided = Submission.objects.filter(
            status__in=['ACCEPTED', 'REJECTED']
        ).count()
        acceptance_rate = (accepted_submissions / total_decided * 100) if total_decided > 0 else 0
        
        return Response({
            'overview': {
                'total_submissions': total_submissions,
                'pending_submissions': pending_submissions,
                'submissions_last_30_days': submissions_last_30,
                'acceptance_rate': round(acceptance_rate, 2),
                'total_reviews': total_reviews,
                'pending_reviews': pending_reviews,
                'avg_review_time_days': avg_review_time,
            },
            'submissions': {
                'total': total_submissions,
                'pending': pending_submissions,
                'accepted': accepted_submissions,
                'rejected': rejected_submissions,
                'under_review': Submission.objects.filter(status='UNDER_REVIEW').count(),
            },
            'reviews': {
                'total': total_reviews,
                'pending': pending_reviews,
                'completed': completed_reviews,
                'declined': ReviewAssignment.objects.filter(status='DECLINED').count(),
            },
            'users': {
                'total': total_users,
                'verified': verified_users,
                'pending_verifications': pending_verifications,
                'authors': authors_count,
                'reviewers': reviewers_count,
            },
            'journals': {
                'total': total_journals,
                'active': active_journals,
                'inactive': Journal.objects.filter(is_active=False).count(),
            }
        })


class SubmissionAnalyticsView(APIView):
    """
    Detailed submission analytics and trends.
    """
    permission_classes = [IsAdminOrEditor]
    
    @extend_schema(
        summary="Get submission analytics",
        description="Get detailed submission metrics, trends, and processing times.",
        parameters=[
            OpenApiParameter(name='days', description='Number of days to analyze (default: 30)', required=False, type=int),
            OpenApiParameter(name='journal_id', description='Filter by journal ID', required=False, type=str),
        ]
    )
    def get(self, request):
        """Get detailed submission analytics."""
        days = int(request.query_params.get('days', 30))
        journal_id = request.query_params.get('journal_id')
        
        start_date = timezone.now() - timedelta(days=days)
        
        # Base queryset
        queryset = Submission.objects.filter(created_at__gte=start_date)
        if journal_id:
            queryset = queryset.filter(journal_id=journal_id)
        
        # Submissions over time
        submissions_by_date = queryset.annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        # Status breakdown
        status_breakdown = queryset.values('status').annotate(
            count=Count('id')
        )
        
        # Processing time analysis
        decided_submissions = queryset.filter(
            status__in=['ACCEPTED', 'REJECTED']
        )
        
        avg_processing_time = None
        if decided_submissions.exists():
            # Get editorial decisions to calculate time
            decisions = EditorialDecision.objects.filter(
                submission__in=decided_submissions
            ).annotate(
                duration=ExpressionWrapper(
                    F('created_at') - F('submission__created_at'),
                    output_field=DurationField()
                )
            ).aggregate(avg_duration=Avg('duration'))
            
            if decisions['avg_duration']:
                avg_processing_time = decisions['avg_duration'].days
        
        # Submissions by journal
        by_journal = queryset.values(
            'journal__id', 'journal__title'
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        return Response({
            'period': {
                'days': days,
                'start_date': start_date.date(),
                'end_date': timezone.now().date(),
            },
            'total_submissions': queryset.count(),
            'submissions_by_date': list(submissions_by_date),
            'status_breakdown': list(status_breakdown),
            'avg_processing_time_days': avg_processing_time,
            'top_journals': list(by_journal),
        })


class ReviewerAnalyticsView(APIView):
    """
    Reviewer performance analytics.
    """
    permission_classes = [IsAdminOrEditor]
    
    @extend_schema(
        summary="Get reviewer analytics",
        description="Get reviewer performance metrics including response times and quality scores.",
        parameters=[
            OpenApiParameter(name='days', description='Number of days to analyze (default: 90)', required=False, type=int),
        ]
    )
    def get(self, request):
        """Get reviewer performance analytics."""
        days = int(request.query_params.get('days', 90))
        start_date = timezone.now() - timedelta(days=days)
        
        # Review assignments in period
        assignments = ReviewAssignment.objects.filter(
            invited_at__gte=start_date
        )
        
        # Response rate
        total_assignments = assignments.count()
        accepted_assignments = assignments.filter(status='ACCEPTED').count()
        completed_assignments = assignments.filter(status='COMPLETED').count()
        declined_assignments = assignments.filter(status='DECLINED').count()
        
        acceptance_rate = (accepted_assignments / total_assignments * 100) if total_assignments > 0 else 0
        completion_rate = (completed_assignments / total_assignments * 100) if total_assignments > 0 else 0
        
        # Average response time (time to accept/decline)
        accepted = assignments.filter(
            status='ACCEPTED',
            accepted_at__isnull=False
        )
        declined = assignments.filter(
            status='DECLINED',
            declined_at__isnull=False
        )
        
        avg_response_time = None
        if accepted.exists() or declined.exists():
            # Calculate average for accepted reviews
            accepted_time = None
            if accepted.exists():
                accepted_avg = accepted.annotate(
                    duration=ExpressionWrapper(
                        F('accepted_at') - F('invited_at'),
                        output_field=DurationField()
                    )
                ).aggregate(avg_duration=Avg('duration'))
                accepted_time = accepted_avg['avg_duration']
            
            # Calculate average for declined reviews
            declined_time = None
            if declined.exists():
                declined_avg = declined.annotate(
                    duration=ExpressionWrapper(
                        F('declined_at') - F('invited_at'),
                        output_field=DurationField()
                    )
                ).aggregate(avg_duration=Avg('duration'))
                declined_time = declined_avg['avg_duration']
            
            # Combine the averages
            if accepted_time and declined_time:
                avg_response_time = ((accepted_time.days + declined_time.days) // 2)
            elif accepted_time:
                avg_response_time = accepted_time.days
            elif declined_time:
                avg_response_time = declined_time.days
        
        # Average completion time
        completed = assignments.filter(
            status='COMPLETED',
            completed_at__isnull=False
        )
        
        avg_completion_time = None
        if completed.exists():
            avg_time = completed.annotate(
                duration=ExpressionWrapper(
                    F('completed_at') - F('invited_at'),
                    output_field=DurationField()
                )
            ).aggregate(avg_duration=Avg('duration'))
            
            if avg_time['avg_duration']:
                avg_completion_time = avg_time['avg_duration'].days
        
        # Top reviewers by completed reviews
        top_reviewers = assignments.filter(
            status='COMPLETED'
        ).values(
            'reviewer__id'
        ).annotate(
            reviews_completed=Count('id')
        ).order_by('-reviews_completed')[:10]
        
        # Average review quality scores (using confidence_level instead of recommendation)
        completed_reviews = Review.objects.filter(
            assignment__in=completed,
            confidence_level__isnull=False
        )
        
        avg_quality_score = completed_reviews.aggregate(
            avg_score=Avg('confidence_level')
        )['avg_score']
        
        return Response({
            'period': {
                'days': days,
                'start_date': start_date.date(),
                'end_date': timezone.now().date(),
            },
            'assignments': {
                'total': total_assignments,
                'accepted': accepted_assignments,
                'completed': completed_assignments,
                'declined': declined_assignments,
                'pending': assignments.filter(status='PENDING').count(),
            },
            'rates': {
                'acceptance_rate': round(acceptance_rate, 2),
                'completion_rate': round(completion_rate, 2),
            },
            'timing': {
                'avg_response_time_days': avg_response_time,
                'avg_completion_time_days': avg_completion_time,
            },
            'top_reviewers': list(top_reviewers),
            'avg_quality_score': round(avg_quality_score, 2) if avg_quality_score else None,
        })


class JournalAnalyticsView(APIView):
    """
    Journal-specific analytics.
    """
    permission_classes = [IsAdminOrEditor]
    
    @extend_schema(
        summary="Get journal analytics",
        description="Get detailed analytics for a specific journal.",
        parameters=[
            OpenApiParameter(name='journal_id', description='Journal ID', required=True, type=str),
            OpenApiParameter(name='days', description='Number of days to analyze (default: 90)', required=False, type=int),
        ]
    )
    def get(self, request):
        """Get journal-specific analytics."""
        journal_id = request.query_params.get('journal_id')
        if not journal_id:
            return Response(
                {'detail': 'journal_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            journal = Journal.objects.get(id=journal_id)
        except Journal.DoesNotExist:
            return Response(
                {'detail': 'Journal not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        days = int(request.query_params.get('days', 90))
        start_date = timezone.now() - timedelta(days=days)
        
        # Submissions for this journal
        submissions = Submission.objects.filter(
            journal=journal,
            created_at__gte=start_date
        )
        
        # Status breakdown
        status_breakdown = submissions.values('status').annotate(
            count=Count('id')
        )
        
        # Submissions over time
        submissions_by_month = submissions.annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')
        
        # Acceptance/rejection stats
        total_decided = submissions.filter(
            status__in=['ACCEPTED', 'REJECTED']
        ).count()
        accepted = submissions.filter(status='ACCEPTED').count()
        acceptance_rate = (accepted / total_decided * 100) if total_decided > 0 else 0
        
        # Review statistics
        review_assignments = ReviewAssignment.objects.filter(
            submission__journal=journal,
            invited_at__gte=start_date
        )
        
        avg_reviews_per_submission = review_assignments.values(
            'submission'
        ).annotate(
            review_count=Count('id')
        ).aggregate(avg_reviews=Avg('review_count'))['avg_reviews']
        
        return Response({
            'journal': {
                'id': str(journal.id),
                'name': journal.title,
                'is_active': journal.is_active,
            },
            'period': {
                'days': days,
                'start_date': start_date.date(),
                'end_date': timezone.now().date(),
            },
            'submissions': {
                'total': submissions.count(),
                'status_breakdown': list(status_breakdown),
                'by_month': list(submissions_by_month),
                'acceptance_rate': round(acceptance_rate, 2),
            },
            'reviews': {
                'total_assignments': review_assignments.count(),
                'avg_reviews_per_submission': round(avg_reviews_per_submission, 2) if avg_reviews_per_submission else 0,
            },
        })


class UserAnalyticsView(APIView):
    """
    User activity analytics.
    """
    permission_classes = [IsAdminOrEditor]
    
    @extend_schema(
        summary="Get user analytics",
        description="Get user registration, verification, and activity metrics.",
        parameters=[
            OpenApiParameter(name='days', description='Number of days to analyze (default: 30)', required=False, type=int),
        ]
    )
    def get(self, request):
        """Get user activity analytics."""
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
        # User registrations over time
        registrations = Profile.objects.filter(
            created_at__gte=start_date
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        # Verification status breakdown
        verification_breakdown = Profile.objects.values(
            'verification_status'
        ).annotate(count=Count('id'))
        
        # Role distribution
        author_count = Profile.objects.filter(roles__name='AUTHOR').distinct().count()
        reviewer_count = Profile.objects.filter(roles__name='REVIEWER').distinct().count()
        editor_count = Profile.objects.filter(roles__name='EDITOR').distinct().count()
        
        # Verification requests
        verification_requests = VerificationRequest.objects.filter(
            created_at__gte=start_date
        )
        
        verification_status = verification_requests.values('status').annotate(
            count=Count('id')
        )
        
        # ORCID connections
        orcid_connected = Profile.objects.filter(
            orcid_integration__status='CONNECTED'
        ).count()
        
        return Response({
            'period': {
                'days': days,
                'start_date': start_date.date(),
                'end_date': timezone.now().date(),
            },
            'registrations': {
                'total': Profile.objects.filter(created_at__gte=start_date).count(),
                'by_date': list(registrations),
            },
            'verification': {
                'status_breakdown': list(verification_breakdown),
                'requests_breakdown': list(verification_status),
            },
            'roles': {
                'authors': author_count,
                'reviewers': reviewer_count,
                'editors': editor_count,
            },
            'integrations': {
                'orcid_connected': orcid_connected,
            }
        })


class MyAnalyticsView(APIView):
    """
    Personal analytics for individual users (authors/reviewers).
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        summary="Get personal analytics",
        description="Get personal performance metrics for the authenticated user."
    )
    def get(self, request):
        """Get personal analytics for the current user."""
        profile = request.user.profile
        
        # Author statistics
        author_stats = None
        if profile.roles.filter(name='AUTHOR').exists():
            submissions = Submission.objects.filter(
                Q(corresponding_author=profile) | Q(coauthors=profile)
            ).distinct()
            
            author_stats = {
                'total_submissions': submissions.count(),
                'accepted': submissions.filter(status='ACCEPTED').count(),
                'rejected': submissions.filter(status='REJECTED').count(),
                'under_review': submissions.filter(status='UNDER_REVIEW').count(),
                'pending': submissions.filter(status='SUBMITTED').count(),
            }
        
        # Reviewer statistics
        reviewer_stats = None
        if profile.roles.filter(name='REVIEWER').exists():
            assignments = ReviewAssignment.objects.filter(reviewer=profile)
            
            completed = assignments.filter(status='COMPLETED')
            avg_completion_time = None
            
            if completed.exists():
                avg_time = completed.annotate(
                    duration=ExpressionWrapper(
                        F('completed_at') - F('invited_at'),
                        output_field=DurationField()
                    )
                ).aggregate(avg_duration=Avg('duration'))
                
                if avg_time['avg_duration']:
                    avg_completion_time = avg_time['avg_duration'].days
            
            reviewer_stats = {
                'total_assignments': assignments.count(),
                'pending': assignments.filter(status='PENDING').count(),
                'accepted': assignments.filter(status='ACCEPTED').count(),
                'completed': completed.count(),
                'declined': assignments.filter(status='DECLINED').count(),
                'avg_completion_time_days': avg_completion_time,
            }
        
        # Editor statistics
        editor_stats = None
        if profile.roles.filter(name='EDITOR').exists():
            # Get journals where user is editor
            from apps.journals.models import JournalStaff
            editor_journals = JournalStaff.objects.filter(
                profile=profile,
                is_active=True
            ).values_list('journal_id', flat=True)
            
            journal_submissions = Submission.objects.filter(
                journal_id__in=editor_journals
            )
            
            decisions = EditorialDecision.objects.filter(
                decided_by=profile
            )
            
            editor_stats = {
                'journals': len(editor_journals),
                'submissions_managed': journal_submissions.count(),
                'decisions_made': decisions.count(),
                'pending_submissions': journal_submissions.filter(
                    status__in=['SUBMITTED', 'UNDER_REVIEW']
                ).count(),
            }
        
        # Journal Manager statistics
        journal_manager_stats = None
        if profile.roles.filter(name='JOURNAL_MANAGER').exists():
            from apps.journals.models import JournalStaff
            
            # Get journals where user is assigned as journal manager
            managed_journals = JournalStaff.objects.filter(
                profile=profile,
                is_active=True,
                permissions__is_journal_manager=True
            ).select_related('journal')
            
            managed_journal_ids = managed_journals.values_list('journal_id', flat=True)
            
            # Get total staff count across all managed journals
            total_staff = JournalStaff.objects.filter(
                journal_id__in=managed_journal_ids,
                is_active=True
            ).exclude(
                permissions__is_journal_manager=True  # Exclude other journal managers from count
            ).count()
            
            # Get submission counts for managed journals
            journal_submissions = Submission.objects.filter(
                journal_id__in=managed_journal_ids
            )
            
            # Get recent activity (last 30 days)
            last_30_days = timezone.now() - timedelta(days=30)
            recent_submissions = journal_submissions.filter(
                created_at__gte=last_30_days
            ).count()
            
            journal_manager_stats = {
                'journals_managed': managed_journals.count(),
                'total_staff_members': total_staff,
                'total_submissions': journal_submissions.count(),
                'recent_submissions_30d': recent_submissions,
                'active_submissions': journal_submissions.filter(
                    status__in=['SUBMITTED', 'UNDER_REVIEW', 'REVISION_REQUIRED']
                ).count(),
                'published_submissions': journal_submissions.filter(
                    status='PUBLISHED'
                ).count(),
                'journals': [
                    {
                        'id': str(staff.journal.id),
                        'title': staff.journal.title,
                        'short_name': staff.journal.short_name,
                        'is_active': staff.journal.is_active,
                    }
                    for staff in managed_journals
                ],
            }
        
        return Response({
            'profile': {
                'id': str(profile.id),
                'name': profile.display_name,
                'email': profile.user.email,
                'verification_status': profile.verification_status,
                'roles': [role.name for role in profile.roles.all()],
            },
            'author_stats': author_stats,
            'reviewer_stats': reviewer_stats,
            'editor_stats': editor_stats,
            'journal_manager_stats': journal_manager_stats,
        })
