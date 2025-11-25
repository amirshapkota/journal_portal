
"""
URL configuration for integrations app.
Handles ORCID/OJS connectors and external services.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    OJSArticleListView,
    OJSArticleDetailView,
    ORCIDAuthorizeView,
    ORCIDCallbackView,
    ORCIDStatusView,
    ORCIDDisconnectView,
    ORCIDSyncProfileView,
    ROROrganizationSearchView,
    ROROrganizationDetailView,
    OpenAlexAuthorSearchView,
    OpenAlexAuthorDetailView,
    OpenAlexInstitutionSearchView,
    OpenAlexInstitutionDetailView,
    OpenAlexWorkSearchView,
    OpenAlexWorkDetailView,
    DOAJJournalSearchView,
    DOAJArticleSearchView,
    DOAJInclusionCheckView,
    DOAJJournalMetadataView,
    DOAJArticleMetadataView,
    DOAJSubmitUpdateView,
    OJSJournalListView,
    OJSSubmissionListView,
    OJSSubmissionCreateView,
    OJSSubmissionUpdateView,
    SentryProjectListView,
    SentryIssueListView,
    SentryIssueDetailView,
    SentryIssueEventsView,
    SentryEventDetailView,
    SentryProjectStatsView,
    OJSUserSyncAPIView, OJSUserDetailSyncAPIView,
    OJSReviewSyncAPIView, OJSReviewDetailSyncAPIView,
    OJSCommentSyncAPIView, OJSCommentDetailSyncAPIView,
)

router = DefaultRouter()

urlpatterns = [
    # OJS article sync endpoints
    path('ojs/articles/', OJSArticleListView.as_view(), name='ojs_article_list'),
    path('ojs/articles/<str:article_id>/', OJSArticleDetailView.as_view(), name='ojs_article_detail'),
    path('', include(router.urls)),
    # ORCID OAuth flow
    path('orcid/authorize/', ORCIDAuthorizeView.as_view(), name='orcid_authorize'),
    path('orcid/callback/', ORCIDCallbackView.as_view(), name='orcid_callback'),
    path('orcid/status/', ORCIDStatusView.as_view(), name='orcid_status'),
    path('orcid/disconnect/', ORCIDDisconnectView.as_view(), name='orcid_disconnect'),
    path('orcid/sync-profile/', ORCIDSyncProfileView.as_view(), name='orcid_sync_profile'),
    # ROR endpoints
    path('ror/search/', ROROrganizationSearchView.as_view(), name='ror_search'),
    path('ror/<str:ror_id>/', ROROrganizationDetailView.as_view(), name='ror_detail'),
    # OpenAlex endpoints
    path('openalex/authors/search/', OpenAlexAuthorSearchView.as_view(), name='openalex_author_search'),
    path('openalex/authors/<path:author_id>/', OpenAlexAuthorDetailView.as_view(), name='openalex_author_detail'),
    path('openalex/institutions/search/', OpenAlexInstitutionSearchView.as_view(), name='openalex_institution_search'),
    path('openalex/institutions/<path:inst_id>/', OpenAlexInstitutionDetailView.as_view(), name='openalex_institution_detail'),
    path('openalex/works/search/', OpenAlexWorkSearchView.as_view(), name='openalex_work_search'),
    path('openalex/works/<path:work_id>/', OpenAlexWorkDetailView.as_view(), name='openalex_work_detail'),

    # DOAJ endpoints
    path('doaj/journals/search/', DOAJJournalSearchView.as_view(), name='doaj_journal_search'),
    path('doaj/articles/search/', DOAJArticleSearchView.as_view(), name='doaj_article_search'),
    path('doaj/journals/inclusion/', DOAJInclusionCheckView.as_view(), name='doaj_inclusion_check'),
    path('doaj/journals/<str:journal_id>/', DOAJJournalMetadataView.as_view(), name='doaj_journal_metadata'),
    path('doaj/articles/<str:article_id>/', DOAJArticleMetadataView.as_view(), name='doaj_article_metadata'),
    path('doaj/submit/', DOAJSubmitUpdateView.as_view(), name='doaj_submit_update'),

    # OJS sync endpoints
    path('ojs/journals/', OJSJournalListView.as_view(), name='ojs_journal_list'),
    path('ojs/submissions/', OJSSubmissionListView.as_view(), name='ojs_submission_list'),
    path('ojs/submissions/create/', OJSSubmissionCreateView.as_view(), name='ojs_submission_create'),
    path('ojs/submissions/<str:submission_id>/update/', OJSSubmissionUpdateView.as_view(), name='ojs_submission_update'),
    # OJS User sync endpoints
    path('ojs/users/', OJSUserSyncAPIView.as_view(), name='ojs_user_sync'),
    path('ojs/users/<str:user_id>/', OJSUserDetailSyncAPIView.as_view(), name='ojs_user_detail_sync'),
    # OJS Review sync endpoints
    path('ojs/reviews/', OJSReviewSyncAPIView.as_view(), name='ojs_review_sync'),
    path('ojs/reviews/<str:review_id>/', OJSReviewDetailSyncAPIView.as_view(), name='ojs_review_detail_sync'),
    # OJS Comment sync endpoints
    path('ojs/comments/', OJSCommentSyncAPIView.as_view(), name='ojs_comment_sync'),
    path('ojs/comments/<str:comment_id>/', OJSCommentDetailSyncAPIView.as_view(), name='ojs_comment_detail_sync'),
    
    # Sentry endpoints
    path('sentry/projects/', SentryProjectListView.as_view(), name='sentry_project_list'),
    path('sentry/projects/<str:project_slug>/issues/', SentryIssueListView.as_view(), name='sentry_issue_list'),
    path('sentry/issues/<str:issue_id>/', SentryIssueDetailView.as_view(), name='sentry_issue_detail'),
    path('sentry/issues/<str:issue_id>/events/', SentryIssueEventsView.as_view(), name='sentry_issue_events'),
    path('sentry/projects/<str:project_slug>/events/<str:event_id>/', SentryEventDetailView.as_view(), name='sentry_event_detail'),
    path('sentry/projects/<str:project_slug>/stats/', SentryProjectStatsView.as_view(), name='sentry_project_stats'),
]