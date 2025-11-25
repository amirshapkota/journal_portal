"""
Sentry API views for integrations app.
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .utils import (
    sentry_fetch_issues,
    sentry_fetch_issue_detail,
    sentry_fetch_issue_events,
    sentry_fetch_event_detail,
    sentry_get_project_stats,
    sentry_list_projects,
)
from .sentry_serializers import (
    SentryIssueSerializer,
    SentryEventSerializer,
    SentryProjectSerializer,
    SentryStatsSerializer,
)


class SentryProjectListView(APIView):
    """List all Sentry projects in the organization."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            data = sentry_list_projects()
            serialized = [SentryProjectSerializer.from_sentry_result(p) for p in data]
            return Response({'results': serialized, 'count': len(serialized)})
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class SentryIssueListView(APIView):
    """Fetch issues from a Sentry project."""
    permission_classes = [IsAuthenticated]

    def get(self, request, project_slug):
        query = request.query_params.get('query', '')
        issue_status = request.query_params.get('status', 'unresolved')
        limit = int(request.query_params.get('limit', 25))
        cursor = request.query_params.get('cursor')

        try:
            data = sentry_fetch_issues(
                project_slug=project_slug,
                query=query,
                status=issue_status,
                limit=limit,
                cursor=cursor
            )
            serialized = [SentryIssueSerializer.from_sentry_result(issue) for issue in data['results']]
            return Response({
                'results': serialized,
                'count': data['count'],
                'next_cursor': data.get('next_cursor'),
            })
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class SentryIssueDetailView(APIView):
    """Fetch detailed information about a specific Sentry issue."""
    permission_classes = [IsAuthenticated]

    def get(self, request, issue_id):
        try:
            data = sentry_fetch_issue_detail(issue_id)
            serialized = SentryIssueSerializer.from_sentry_result(data)
            return Response(serialized)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class SentryIssueEventsView(APIView):
    """Fetch events for a specific Sentry issue."""
    permission_classes = [IsAuthenticated]

    def get(self, request, issue_id):
        limit = int(request.query_params.get('limit', 25))
        cursor = request.query_params.get('cursor')

        try:
            data = sentry_fetch_issue_events(
                issue_id=issue_id,
                limit=limit,
                cursor=cursor
            )
            serialized = [SentryEventSerializer.from_sentry_result(event) for event in data['results']]
            return Response({
                'results': serialized,
                'count': data['count'],
                'next_cursor': data.get('next_cursor'),
            })
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class SentryEventDetailView(APIView):
    """Fetch detailed information about a specific Sentry event."""
    permission_classes = [IsAuthenticated]

    def get(self, request, project_slug, event_id):
        try:
            data = sentry_fetch_event_detail(event_id, project_slug)
            serialized = SentryEventSerializer.from_sentry_result(data)
            return Response(serialized)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class SentryProjectStatsView(APIView):
    """Get project statistics from Sentry."""
    permission_classes = [IsAuthenticated]

    def get(self, request, project_slug):
        stat = request.query_params.get('stat', 'received')
        since = request.query_params.get('since')
        until = request.query_params.get('until')
        resolution = request.query_params.get('resolution', '1h')

        # Convert since/until to integers if provided
        if since:
            try:
                since = int(since)
            except ValueError:
                return Response({'detail': 'Invalid since parameter'}, status=status.HTTP_400_BAD_REQUEST)
        
        if until:
            try:
                until = int(until)
            except ValueError:
                return Response({'detail': 'Invalid until parameter'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            data = sentry_get_project_stats(
                project_slug=project_slug,
                stat=stat,
                since=since,
                until=until,
                resolution=resolution
            )
            serialized = SentryStatsSerializer.from_sentry_result(data)
            return Response(serialized)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_502_BAD_GATEWAY)
