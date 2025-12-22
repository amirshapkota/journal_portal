"""
Views for achievements, awards, leaderboards, and certificates.
"""
from django.db import models
from django.db.models import Count, Avg, Sum, Q, F
from django.utils import timezone
from datetime import timedelta, date
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import Badge, UserBadge, Award, Leaderboard, Certificate
from .serializers import (
    BadgeSerializer, UserBadgeSerializer, AwardSerializer,
    LeaderboardSerializer, CertificateSerializer
)
from apps.reviews.models import ReviewAssignment, Review
from apps.submissions.models import Submission


class BadgeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing badges.
    """
    queryset = Badge.objects.filter(is_active=True)
    serializer_class = BadgeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filterset_fields = ['badge_type', 'level', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'points', 'created_at']
    ordering = ['-points', 'name']


class UserBadgeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing user badges.
    """
    queryset = UserBadge.objects.select_related('badge', 'profile', 'journal')
    serializer_class = UserBadgeSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['year', 'is_featured', 'journal']
    ordering = ['-earned_at']
    
    def get_queryset(self):
        """Filter to show user's own badges or allow admins to see all."""
        if self.request.user.is_superuser:
            return self.queryset
        return self.queryset.filter(profile=self.request.user.profile)
    
    @extend_schema(
        summary="Get my badges",
        description="Get all badges earned by the authenticated user."
    )
    @action(detail=False, methods=['get'])
    def my_badges(self, request):
        """Get authenticated user's badges."""
        badges = self.queryset.filter(profile=request.user.profile)
        
        # Apply pagination if available
        page = self.paginate_queryset(badges)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(badges, many=True)
        return Response(serializer.data)


class AwardViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing awards.
    """
    queryset = Award.objects.select_related('recipient', 'journal')
    serializer_class = AwardSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filterset_fields = ['year', 'award_type', 'journal', 'discipline', 'country']
    search_fields = ['title', 'description', 'recipient__user__email']
    ordering = ['-year', '-announced_at']
    
    @extend_schema(
        summary="Get best reviewer by journal",
        description="Get the best reviewer for a specific journal and year.",
        parameters=[
            OpenApiParameter(
                name='journal_id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description='Journal ID'
            ),
            OpenApiParameter(
                name='year',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Year (defaults to current year)'
            )
        ]
    )
    @action(detail=False, methods=['get'], url_path='best-reviewer/(?P<journal_id>[^/.]+)')
    def best_reviewer(self, request, journal_id=None):
        """Get best reviewer for a journal by year."""
        year = request.query_params.get('year', timezone.now().year)
        
        # Get all reviewers for this journal in the specified year
        from apps.journals.models import Journal
        from apps.users.models import Profile
        
        try:
            journal = Journal.objects.get(id=journal_id)
        except Journal.DoesNotExist:
            return Response(
                {'error': 'Journal not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Calculate reviewer metrics
        year_start = date(int(year), 1, 1)
        year_end = date(int(year), 12, 31)
        
        reviewer_stats = ReviewAssignment.objects.filter(
            submission__journal=journal,
            invited_at__date__gte=year_start,
            invited_at__date__lte=year_end,
            status='COMPLETED'
        ).values('reviewer').annotate(
            reviews_completed=Count('id'),
            avg_quality=Avg('review__quality_score'),
            avg_timeliness=Avg(
                F('completed_at') - F('accepted_at'),
                output_field=models.DurationField()
            )
        ).order_by('-reviews_completed', '-avg_quality')
        
        if not reviewer_stats.exists():
            return Response(
                {'message': 'No reviews found for this journal in the specified year'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        best_reviewer_data = reviewer_stats.first()
        best_reviewer = Profile.objects.get(id=best_reviewer_data['reviewer'])
        
        # Check if award already exists
        award, created = Award.objects.get_or_create(
            journal=journal,
            award_type='BEST_REVIEWER',
            year=year,
            defaults={
                'title': f'Best Reviewer {year}',
                'description': f'Awarded to the top reviewer for {journal.title} in {year}',
                'recipient': best_reviewer,
                'citation': f'In recognition of outstanding review contributions with {best_reviewer_data["reviews_completed"]} completed reviews',
                'metrics': {
                    'reviews_completed': best_reviewer_data['reviews_completed'],
                    'avg_quality': float(best_reviewer_data['avg_quality']) if best_reviewer_data['avg_quality'] else 0,
                }
            }
        )
        
        if not created and award.recipient != best_reviewer:
            # Update if different reviewer
            award.recipient = best_reviewer
            award.metrics = {
                'reviews_completed': best_reviewer_data['reviews_completed'],
                'avg_quality': float(best_reviewer_data['avg_quality']) if best_reviewer_data['avg_quality'] else 0,
            }
            award.save()
        
        serializer = AwardSerializer(award)
        return Response(serializer.data)
    
    @extend_schema(
        summary="Get researcher of the year by journal",
        description="Get the researcher of the year for a specific journal.",
        parameters=[
            OpenApiParameter(
                name='journal_id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description='Journal ID'
            ),
            OpenApiParameter(
                name='year',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Year (defaults to current year)'
            )
        ]
    )
    @action(detail=False, methods=['get'], url_path='researcher-of-year/(?P<journal_id>[^/.]+)')
    def researcher_of_year(self, request, journal_id=None):
        """Get researcher of the year for a journal."""
        year = request.query_params.get('year', timezone.now().year)
        
        from apps.journals.models import Journal
        from apps.users.models import Profile
        
        try:
            journal = Journal.objects.get(id=journal_id)
        except Journal.DoesNotExist:
            return Response(
                {'error': 'Journal not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Calculate author metrics
        year_start = date(int(year), 1, 1)
        year_end = date(int(year), 12, 31)
        
        author_stats = Submission.objects.filter(
            journal=journal,
            created_at__date__gte=year_start,
            created_at__date__lte=year_end,
            status__in=['ACCEPTED', 'PUBLISHED']
        ).values('corresponding_author').annotate(
            publications=Count('id'),
            acceptance_rate=Count('id', filter=Q(status='ACCEPTED') | Q(status='PUBLISHED'))
        ).order_by('-publications')
        
        if not author_stats.exists():
            return Response(
                {'message': 'No publications found for this journal in the specified year'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        top_researcher_data = author_stats.first()
        top_researcher = Profile.objects.get(id=top_researcher_data['corresponding_author'])
        
        # Check if award already exists
        award, created = Award.objects.get_or_create(
            journal=journal,
            award_type='RESEARCHER_OF_YEAR',
            year=year,
            defaults={
                'title': f'Researcher of the Year {year}',
                'description': f'Awarded to the most prolific researcher for {journal.title} in {year}',
                'recipient': top_researcher,
                'citation': f'In recognition of outstanding research contributions with {top_researcher_data["publications"]} publications',
                'metrics': {
                    'publications': top_researcher_data['publications'],
                }
            }
        )
        
        if not created and award.recipient != top_researcher:
            # Update if different researcher
            award.recipient = top_researcher
            award.metrics = {
                'publications': top_researcher_data['publications'],
            }
            award.save()
        
        serializer = AwardSerializer(award)
        return Response(serializer.data)


class LeaderboardViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing leaderboards.
    """
    queryset = Leaderboard.objects.select_related('profile', 'journal')
    serializer_class = LeaderboardSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filterset_fields = ['category', 'period', 'journal', 'field', 'country']
    ordering = ['rank']
    
    @extend_schema(
        summary="Get top reviewers",
        description="Get top reviewers leaderboard with optional filters.",
        parameters=[
            OpenApiParameter('period', OpenApiTypes.STR, description='Period: MONTHLY, QUARTERLY, YEARLY, ALL_TIME'),
            OpenApiParameter('journal_id', OpenApiTypes.UUID, description='Filter by journal'),
            OpenApiParameter('field', OpenApiTypes.STR, description='Filter by field'),
            OpenApiParameter('country', OpenApiTypes.STR, description='Filter by country'),
            OpenApiParameter('limit', OpenApiTypes.INT, description='Number of results (default: 10)')
        ]
    )
    @action(detail=False, methods=['get'])
    def top_reviewers(self, request):
        """Get top reviewers leaderboard."""
        period = request.query_params.get('period', 'YEARLY')
        journal_id = request.query_params.get('journal_id')
        field = request.query_params.get('field')
        country = request.query_params.get('country')
        limit = int(request.query_params.get('limit', 10))
        
        queryset = self.queryset.filter(category='REVIEWER', period=period)
        
        if journal_id:
            queryset = queryset.filter(journal_id=journal_id)
        if field:
            queryset = queryset.filter(field=field)
        if country:
            queryset = queryset.filter(country=country)
        
        leaderboard_entries = queryset.order_by('rank')[:limit]
        serializer = self.get_serializer(leaderboard_entries, many=True)
        
        # Structure the response to match frontend expectations
        response_data = {
            'name': f'Top Reviewers - {period.replace("_", " ").title()}',
            'description': 'Ranking of top reviewers based on performance metrics',
            'period': period.lower(),
            'data': serializer.data
        }
        
        return Response(response_data)


class CertificateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing certificates.
    """
    queryset = Certificate.objects.select_related('recipient', 'journal', 'award', 'badge')
    serializer_class = CertificateSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['certificate_type', 'issued_date', 'journal']
    ordering = ['-issued_date']
    
    def get_queryset(self):
        """Filter to show user's own certificates or allow admins to see all."""
        if self.request.user.is_superuser:
            return self.queryset
        return self.queryset.filter(recipient=self.request.user.profile)
    
    @extend_schema(
        summary="Generate certificate for award",
        description="Generate a certificate for a specific award.",
        parameters=[
            OpenApiParameter(
                name='award_id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description='Award ID'
            )
        ]
    )
    @action(detail=False, methods=['post'], url_path='generate-award/(?P<award_id>[^/.]+)')
    def generate_award_certificate(self, request, award_id=None):
        """Generate certificate for an award."""
        try:
            award = Award.objects.get(id=award_id)
        except Award.DoesNotExist:
            return Response(
                {'error': 'Award not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if certificate already exists
        existing_cert = Certificate.objects.filter(award=award).first()
        if existing_cert:
            serializer = CertificateSerializer(existing_cert)
            return Response(serializer.data)
        
        # Create certificate
        certificate = Certificate.objects.create(
            recipient=award.recipient,
            certificate_type='AWARD',
            title=award.title,
            description=f'This certificate is awarded to {award.recipient.display_name} for {award.title}',
            award=award,
            journal=award.journal,
            issued_date=date.today(),
            custom_data={
                'award_type': award.award_type,
                'year': award.year,
                'citation': award.citation
            }
        )
        
        # Mark award as having certificate
        award.certificate_generated = True
        award.save()
        
        serializer = CertificateSerializer(certificate)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @extend_schema(
        summary="Verify certificate",
        description="Verify a certificate by verification code.",
        parameters=[
            OpenApiParameter(
                name='code',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Verification code'
            )
        ]
    )
    @action(detail=False, methods=['get'], permission_classes=[permissions.AllowAny])
    def verify(self, request):
        """Verify a certificate by code."""
        code = request.query_params.get('code')
        if not code:
            return Response(
                {'error': 'Verification code is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            certificate = Certificate.objects.get(verification_code=code, is_public=True)
            serializer = CertificateSerializer(certificate)
            return Response({
                'valid': True,
                'certificate': serializer.data
            })
        except Certificate.DoesNotExist:
            return Response({
                'valid': False,
                'message': 'Invalid verification code or certificate is not public'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @extend_schema(
        summary="Generate PDF for certificate",
        description="Generate PDF file for a certificate.",
        parameters=[
            OpenApiParameter(
                name='id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description='Certificate ID'
            )
        ]
    )
    @action(detail=True, methods=['post'])
    def generate_pdf(self, request, pk=None):
        """Generate PDF for certificate."""
        certificate = self.get_object()
        
        # Check if PDF already exists
        if certificate.pdf_generated and certificate.file_url:
            return Response({
                'status': 'already_generated',
                'message': 'PDF already exists',
                'file_url': certificate.file_url
            })
        
        # Generate PDF asynchronously
        from .pdf_tasks import generate_certificate_pdf_task
        task = generate_certificate_pdf_task.delay(str(certificate.id))
        
        return Response({
            'status': 'generating',
            'message': 'PDF generation started',
            'task_id': task.id
        }, status=status.HTTP_202_ACCEPTED)
    
    @extend_schema(
        summary="Download certificate PDF",
        description="Download the PDF file for a certificate.",
        parameters=[
            OpenApiParameter(
                name='id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description='Certificate ID'
            )
        ]
    )
    @action(detail=True, methods=['get'])
    def download_pdf(self, request, pk=None):
        """Download certificate PDF."""
        from django.http import HttpResponse, FileResponse
        from .pdf_generator import generate_certificate_pdf
        
        certificate = self.get_object()
        
        # If PDF exists in storage, redirect to it
        if certificate.pdf_generated and certificate.file_url:
            from django.shortcuts import redirect
            return redirect(certificate.file_url)
        
        # Generate PDF on-the-fly
        pdf_buffer = generate_certificate_pdf(certificate)
        
        # Return as file download
        response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="certificate_{certificate.certificate_number}.pdf"'
        
        return response
    
    @extend_schema(
        summary="Preview certificate PDF",
        description="Preview the PDF file for a certificate in browser.",
        parameters=[
            OpenApiParameter(
                name='id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description='Certificate ID'
            )
        ]
    )
    @action(detail=True, methods=['get'], permission_classes=[permissions.AllowAny])
    def preview_pdf(self, request, pk=None):
        """Preview certificate PDF in browser."""
        from django.http import HttpResponse
        from .pdf_generator import generate_certificate_pdf
        
        certificate = self.get_object()
        
        # Generate PDF
        pdf_buffer = generate_certificate_pdf(certificate)
        
        # Return for inline display
        response = HttpResponse(pdf_buffer.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="certificate_{certificate.certificate_number}.pdf"'
        
        return response
