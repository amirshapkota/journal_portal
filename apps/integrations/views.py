from urllib.parse import urlencode
from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone
from django.shortcuts import redirect
from django.contrib.sites.shortcuts import get_current_site
from django.views import View

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from .utils import (
    search_ror_organizations, get_ror_organization,
	search_openalex_authors, get_openalex_author,
    search_openalex_institutions, get_openalex_institution,
    search_openalex_works, get_openalex_work,
	doaj_search_journals, doaj_search_articles, doaj_check_inclusion,
	doaj_fetch_journal_metadata, doaj_fetch_article_metadata, doaj_submit_or_update,
	ojs_list_reviews, ojs_get_review, ojs_create_review, ojs_update_review, ojs_delete_review,
	ojs_list_comments, ojs_get_comment, ojs_create_comment, ojs_update_comment, ojs_delete_comment,
	ojs_list_users, ojs_get_user, ojs_create_user, ojs_update_user, ojs_delete_user,
	ojs_list_articles, ojs_get_article, ojs_create_article, ojs_update_article, ojs_delete_article,
	ojs_list_journals, ojs_list_submissions, ojs_create_submission, ojs_update_submission
)
from .serializers import (
    ROROrganizationSerializer,
	OpenAlexAuthorSerializer, OpenAlexInstitutionSerializer, OpenAlexWorkSerializer,
	DOAJJournalSerializer, DOAJArticleSerializer, DOAJInclusionCheckSerializer, DOAJSubmitUpdateSerializer,
	OJSReviewSerializer, OJSCommentSerializer, OJSUserSerializer, OJSArticleSerializer,
	OJSJournalSerializer, OJSSubmissionSerializer
)
from rest_framework.permissions import IsAuthenticatedOrReadOnly


import json
import base64
import secrets
import requests

from apps.users.models import Profile
from .models import ORCIDIntegration, ORCIDOAuthState


def _fernet():
	# Derive fernet key from SECRET_KEY (for demo). In production, use KMS.
	from cryptography.fernet import Fernet
	key = base64.urlsafe_b64encode(settings.SECRET_KEY[:32].encode().ljust(32, b'0')[:32])
	return Fernet(key)


def encrypt_blob(s: str) -> bytes:
	return _fernet().encrypt(s.encode())


def decrypt_blob(b: bytes) -> str:
	return _fernet().decrypt(b).decode()


def build_orcid_authorize_url(request):
	client_id = settings.ORCID_CLIENT_ID
	base_auth_url = getattr(settings, 'ORCID_AUTH_URL', 'https://sandbox.orcid.org/oauth/authorize')
	redirect_uri = request.build_absolute_uri('/api/v1/integrations/orcid/callback/')
	# Use openid for Public API (free tier)
	# Member API would use: /read-limited /activities/update /person/update
	scope = 'openid'
	params = {
		'client_id': client_id,
		'response_type': 'code',
		'scope': scope,
		'redirect_uri': redirect_uri,
	}
	return f"{base_auth_url}?{urlencode(params)}"


def exchange_code_for_token(code: str, redirect_uri: str):
	token_url = getattr(settings, 'ORCID_TOKEN_URL', f"{settings.ORCID_API_BASE_URL}/oauth/token")
	auth = (settings.ORCID_CLIENT_ID, settings.ORCID_CLIENT_SECRET)
	headers = {'Accept': 'application/json'}
	data = {
		'client_id': settings.ORCID_CLIENT_ID,
		'client_secret': settings.ORCID_CLIENT_SECRET,
		'grant_type': 'authorization_code',
		'code': code,
		'redirect_uri': redirect_uri,
	}
	resp = requests.post(token_url, data=data, headers=headers, auth=None, timeout=20)
	resp.raise_for_status()
	return resp.json()


def fetch_orcid_record(orcid_id: str, access_token: str):
	api = settings.ORCID_API_BASE_URL.rstrip('/')
	url = f"{api}/v3.0/{orcid_id}/record"
	headers = {
		'Accept': 'application/json',
		'Authorization': f'Bearer {access_token}',
	}
	r = requests.get(url, headers=headers, timeout=20)
	r.raise_for_status()
	return r.json()


class ORCIDAuthorizeView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		if not settings.ORCID_CLIENT_ID:
			return Response({'detail': 'ORCID is not configured.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
		
		# Generate state token and store in database (not session)
		# This allows the OAuth flow to work across different sessions
		state = secrets.token_urlsafe(32)
		
		# Clean up any expired or old state tokens for this user
		ORCIDOAuthState.objects.filter(
			user=request.user,
			expires_at__lt=timezone.now()
		).delete()
		
		# Create new state token with 10 minute expiry
		ORCIDOAuthState.objects.create(
			state_token=state,
			user=request.user,
			expires_at=timezone.now() + timedelta(minutes=10)
		)
		
		authorize_url = build_orcid_authorize_url(request)
		# Add state parameter
		authorize_url += f"&state={state}"
		
		# Log for debugging
		import logging
		logger = logging.getLogger(__name__)
		logger.info(f"Generated ORCID authorize URL: {authorize_url}")
		
		# Return URL or redirect directly
		if request.query_params.get('redirect') == 'true':
			return redirect(authorize_url)
		return Response({'authorize_url': authorize_url})


class ORCIDCallbackView(APIView):
	permission_classes = [AllowAny]  # Changed to AllowAny since ORCID redirects here

	def get(self, request):
		# EXTENSIVE DEBUG INFO
		import logging
		logger = logging.getLogger(__name__)
		
		# Log everything about the request
		logger.info(f"=" * 80)
		logger.info(f"ORCID Callback Hit!")
		logger.info(f"Request method: {request.method}")
		logger.info(f"Request path: {request.path}")
		logger.info(f"Request GET: {dict(request.GET)}")
		logger.info(f"Request query_params: {dict(request.query_params)}")
		logger.info(f"Request full path: {request.get_full_path()}")
		logger.info(f"Request META keys: {list(request.META.keys())}")
		logger.info(f"Query string: {request.META.get('QUERY_STRING', '')}")
		logger.info(f"=" * 80)
		
		code = request.query_params.get('code')
		error = request.query_params.get('error')
		state = request.query_params.get('state')
		
		# Return detailed debug info if no params
		if not code and not error and not state:
			return Response({
				'detail': 'Missing authorization code from ORCID',
				'debug': {
					'received_GET_params': dict(request.GET),
					'received_query_params': dict(request.query_params),
					'full_path': request.get_full_path(),
					'query_string': request.META.get('QUERY_STRING', ''),
					'request_method': request.method,
					'content_type': request.content_type,
				},
				'help': 'Make sure your ORCID application redirect URI is exactly: http://127.0.0.1:8000/api/v1/integrations/orcid/callback/'
			}, status=status.HTTP_400_BAD_REQUEST)
		
		if error:
			return Response({
				'detail': 'ORCID authorization denied', 
				'error': error,
				'error_description': request.query_params.get('error_description', '')
			}, status=status.HTTP_400_BAD_REQUEST)
		
		if not code:
			return Response({
				'detail': 'Missing authorization code from ORCID',
				'received_params': list(request.query_params.keys()),
				'state_present': bool(state),
				'help': 'Make sure your ORCID application redirect URI is exactly: http://127.0.0.1:8000/api/v1/integrations/orcid/callback/'
			}, status=status.HTTP_400_BAD_REQUEST)
		
		if not state:
			return Response({
				'detail': 'Missing state parameter',
				'help': 'State parameter is required for security'
			}, status=status.HTTP_400_BAD_REQUEST)
		
		# Look up state token in database (not session)
		try:
			oauth_state = ORCIDOAuthState.objects.get(
				state_token=state,
				used=False,
				expires_at__gt=timezone.now()
			)
		except ORCIDOAuthState.DoesNotExist:
			return Response({
				'detail': 'Invalid or expired state parameter',
				'help': 'Please start the authorization process again'
			}, status=status.HTTP_400_BAD_REQUEST)
		
		# Mark state as used
		oauth_state.used = True
		oauth_state.save(update_fields=['used'])
		
		# Get user from state token
		user = oauth_state.user

		redirect_uri = request.build_absolute_uri('/api/v1/integrations/orcid/callback/')
		try:
			token_data = exchange_code_for_token(code, redirect_uri)
		except requests.HTTPError as e:
			return Response({'detail': 'Token exchange failed', 'error': str(e)}, status=status.HTTP_502_BAD_GATEWAY)

		orcid_id = token_data.get('orcid') or token_data.get('orcid_id')
		access_token = token_data.get('access_token')
		refresh_token = token_data.get('refresh_token')
		scope = token_data.get('scope', '')
		expires_in = token_data.get('expires_in')

		if not orcid_id or not access_token:
			return Response({'detail': 'Invalid token response from ORCID'}, status=status.HTTP_502_BAD_GATEWAY)

		# Create or update integration record
		profile: Profile = user.profile
		integ, _ = ORCIDIntegration.objects.get_or_create(profile=profile, defaults={
			'orcid_id': orcid_id,
			'access_token_encrypted': encrypt_blob(access_token),
			'refresh_token_encrypted': encrypt_blob(refresh_token) if refresh_token else None,
			'token_scope': scope,
			'status': 'CONNECTED',
		})

		# Update existing if needed
		integ.orcid_id = orcid_id
		integ.access_token_encrypted = encrypt_blob(access_token)
		integ.refresh_token_encrypted = encrypt_blob(refresh_token) if refresh_token else None
		integ.token_scope = scope or ''
		if expires_in:
			integ.token_expires_at = timezone.now() + timedelta(seconds=int(expires_in))
		integ.status = 'CONNECTED'

		# Fetch profile summary (only if we have appropriate scope)
		# openid scope only provides authentication, not profile read access
		if '/read-limited' in scope or '/person/read' in scope:
			try:
				record = fetch_orcid_record(orcid_id, access_token)
				integ.orcid_data = record
			except requests.HTTPError as e:
				integ.sync_errors = f"Fetch ORCID record failed: {e}"
				logger.warning(f"Failed to fetch ORCID record: {e}")
				# Don't set ERROR status if it's just profile fetch failing
		else:
			# openid scope - authentication only
			integ.orcid_data = {
				'orcid-identifier': {
					'uri': f'https://orcid.org/{orcid_id}',
					'path': orcid_id,
					'host': 'orcid.org'
				},
				'note': 'Limited data available with openid scope. Apply for Member API for full profile access.'
			}
		
		integ.last_sync_at = timezone.now()
		integ.save()

		# Optionally set profile.orcid_id
		if not profile.orcid_id:
			profile.orcid_id = orcid_id
			profile.encrypt_orcid_token(access_token)
			profile.save(update_fields=['orcid_id', 'orcid_token_encrypted'])

		# Clean up old state tokens for this user
		ORCIDOAuthState.objects.filter(user=user).delete()

		# Return success page or JSON
		return Response({
			'detail': 'ORCID connected successfully!', 
			'orcid_id': orcid_id,
			'user_email': user.email,
			'message': 'You can now close this window and check your profile.'
		})


class ORCIDStatusView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		profile: Profile = request.user.profile
		try:
			integ = profile.orcid_integration
		except ORCIDIntegration.DoesNotExist:
			return Response({'connected': False})
		expires_at = integ.token_expires_at.isoformat() if integ.token_expires_at else None
		return Response({
			'connected': integ.status == 'CONNECTED',
			'status': integ.status,
			'orcid_id': integ.orcid_id,
			'token_scope': integ.token_scope,
			'expires_at': expires_at,
			'last_sync_at': integ.last_sync_at.isoformat() if integ.last_sync_at else None,
		})


class ORCIDDisconnectView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request):
		profile: Profile = request.user.profile
		try:
			integ = profile.orcid_integration
		except ORCIDIntegration.DoesNotExist:
			return Response({'detail': 'Not connected'}, status=status.HTTP_404_NOT_FOUND)
		# Remove tokens and mark disconnected
		integ.access_token_encrypted = b''
		integ.refresh_token_encrypted = None
		integ.status = 'DISCONNECTED'
		integ.save(update_fields=['access_token_encrypted', 'refresh_token_encrypted', 'status'])
		# Also clear profile fields
		profile.orcid_id = None
		profile.orcid_token_encrypted = None
		profile.save(update_fields=['orcid_id', 'orcid_token_encrypted'])
		return Response({'detail': 'ORCID disconnected'})


class ORCIDSyncProfileView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request):
		profile: Profile = request.user.profile
		try:
			integ = profile.orcid_integration
		except ORCIDIntegration.DoesNotExist:
			return Response({'detail': 'Not connected'}, status=status.HTTP_404_NOT_FOUND)

		# Check if we have appropriate scope for reading profile
		scope = integ.token_scope or ''
		if 'openid' in scope and '/read-limited' not in scope and '/person/read' not in scope:
			return Response({
				'detail': 'Profile sync not available',
				'reason': 'Current scope (openid) only provides authentication. Apply for ORCID Member API to sync profile data.',
				'orcid_id': integ.orcid_id,
				'scope': scope
			}, status=status.HTTP_400_BAD_REQUEST)

		try:
			access_token = decrypt_blob(integ.access_token_encrypted)
		except Exception:
			return Response({'detail': 'Invalid or missing token'}, status=status.HTTP_400_BAD_REQUEST)

		try:
			record = fetch_orcid_record(integ.orcid_id, access_token)
		except requests.HTTPError as e:
			return Response({
				'detail': 'Fetch failed', 
				'error': str(e),
				'help': 'You may need Member API access to read ORCID profiles. Contact ORCID for institutional membership.'
			}, status=status.HTTP_502_BAD_GATEWAY)

		# Basic profile sync: display_name and affiliation if present
		try:
			name_parts = record.get('person', {}).get('name', {})
			given = (name_parts.get('given-names') or {}).get('value')
			family = (name_parts.get('family-name') or {}).get('value')
			display = ' '.join(p for p in [given, family] if p)
			if display:
				profile.display_name = display
		except Exception:
			pass

		try:
			employments = record.get('activities-summary', {}).get('employments', {}).get('employment-summary', [])
			if employments:
				last_emp = employments[0]
				org = (last_emp.get('organization') or {}).get('name')
				if org:
					profile.affiliation_name = org
		except Exception:
			pass

		profile.save(update_fields=['display_name', 'affiliation_name'])

		integ.orcid_data = record
		integ.last_sync_at = timezone.now()
		integ.status = 'CONNECTED'
		integ.save(update_fields=['orcid_data', 'last_sync_at', 'status'])

		return Response({'detail': 'Profile synced', 'display_name': profile.display_name, 'affiliation_name': profile.affiliation_name})


class ROROrganizationSearchView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get('query')
        page = int(request.query_params.get('page', 1))
        if not query:
            return Response({'detail': 'Missing query parameter.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            data = search_ror_organizations(query, page=page)
            results = data.get('items', [])
            serialized = [ROROrganizationSerializer.from_ror_result(r) for r in results]
            return Response({
                'count': data.get('number_of_results', len(results)),
                'results': serialized
            })
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_502_BAD_GATEWAY)

class ROROrganizationDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, ror_id):
        try:
            data = get_ror_organization(ror_id)
            serialized = ROROrganizationSerializer.from_ror_result(data)
            return Response(serialized)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_502_BAD_GATEWAY)

class OpenAlexAuthorSearchView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get('query')
        page = int(request.query_params.get('page', 1))
        per_page = int(request.query_params.get('per_page', 10))
        if not query:
            return Response({'detail': 'Missing query parameter.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            data = search_openalex_authors(query, page=page, per_page=per_page)
            results = data.get('results', [])
            serialized = [OpenAlexAuthorSerializer.from_openalex_result(r) for r in results]
            return Response({
                'count': data.get('meta', {}).get('count', len(results)),
                'results': serialized
            })
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_502_BAD_GATEWAY)

class OpenAlexAuthorDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, author_id):
        try:
            data = get_openalex_author(author_id)
            serialized = OpenAlexAuthorSerializer.from_openalex_result(data)
            return Response(serialized)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_502_BAD_GATEWAY)

class OpenAlexInstitutionSearchView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get('query')
        page = int(request.query_params.get('page', 1))
        per_page = int(request.query_params.get('per_page', 10))
        if not query:
            return Response({'detail': 'Missing query parameter.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            data = search_openalex_institutions(query, page=page, per_page=per_page)
            results = data.get('results', [])
            serialized = [OpenAlexInstitutionSerializer.from_openalex_result(r) for r in results]
            return Response({
                'count': data.get('meta', {}).get('count', len(results)),
                'results': serialized
            })
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_502_BAD_GATEWAY)

class OpenAlexInstitutionDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, inst_id):
        try:
            data = get_openalex_institution(inst_id)
            serialized = OpenAlexInstitutionSerializer.from_openalex_result(data)
            return Response(serialized)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_502_BAD_GATEWAY)

class OpenAlexWorkSearchView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        query = request.query_params.get('query')
        page = int(request.query_params.get('page', 1))
        per_page = int(request.query_params.get('per_page', 10))
        if not query:
            return Response({'detail': 'Missing query parameter.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            data = search_openalex_works(query, page=page, per_page=per_page)
            results = data.get('results', [])
            serialized = [OpenAlexWorkSerializer.from_openalex_result(r) for r in results]
            return Response({
                'count': data.get('meta', {}).get('count', len(results)),
                'results': serialized
            })
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_502_BAD_GATEWAY)

class OpenAlexWorkDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, work_id):
        try:
            data = get_openalex_work(work_id)
            serialized = OpenAlexWorkSerializer.from_openalex_result(data)
            return Response(serialized)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_502_BAD_GATEWAY)
class DOAJJournalSearchView(APIView):
	permission_classes = [AllowAny]

	def get(self, request):
		query = request.query_params.get('query')
		page = int(request.query_params.get('page', 1))
		page_size = int(request.query_params.get('page_size', 10))
		if not query:
			return Response({'detail': 'Missing query parameter.'}, status=status.HTTP_400_BAD_REQUEST)
		try:
			data = doaj_search_journals(query, page=page, page_size=page_size)
			results = data.get('results', [])
			serialized = [DOAJJournalSerializer.from_doaj_result(r) for r in results]
			return Response({
				'count': data.get('total', len(results)),
				'results': serialized
			})
		except Exception as e:
			return Response({'detail': str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class DOAJArticleSearchView(APIView):
	permission_classes = [AllowAny]

	def get(self, request):
		query = request.query_params.get('query')
		page = int(request.query_params.get('page', 1))
		page_size = int(request.query_params.get('page_size', 10))
		if not query:
			return Response({'detail': 'Missing query parameter.'}, status=status.HTTP_400_BAD_REQUEST)
		try:
			data = doaj_search_articles(query, page=page, page_size=page_size)
			results = data.get('results', [])
			serialized = [DOAJArticleSerializer.from_doaj_result(r) for r in results]
			return Response({
				'count': data.get('total', len(results)),
				'results': serialized
			})
		except Exception as e:
			return Response({'detail': str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class DOAJInclusionCheckView(APIView):
	permission_classes = [AllowAny]

	def get(self, request):
		issn = request.query_params.get('issn')
		if not issn:
			return Response({'detail': 'Missing issn parameter.'}, status=status.HTTP_400_BAD_REQUEST)
		try:
			included = doaj_check_inclusion(issn)
			return Response({'issn': issn, 'included': included})
		except Exception as e:
			return Response({'detail': str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class DOAJJournalMetadataView(APIView):
	permission_classes = [AllowAny]

	def get(self, request, journal_id):
		try:
			data = doaj_fetch_journal_metadata(journal_id)
			serialized = DOAJJournalSerializer.from_doaj_result(data)
			return Response(serialized)
		except Exception as e:
			return Response({'detail': str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class DOAJArticleMetadataView(APIView):
	permission_classes = [AllowAny]

	def get(self, request, article_id):
		try:
			data = doaj_fetch_article_metadata(article_id)
			serialized = DOAJArticleSerializer.from_doaj_result(data)
			return Response(serialized)
		except Exception as e:
			return Response({'detail': str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class DOAJSubmitUpdateView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request):
		api_key = request.data.get('api_key')
		endpoint = request.data.get('endpoint', 'journals')
		method = request.data.get('method', 'POST')
		object_id = request.data.get('object_id')
		data = request.data.get('data')
		if not api_key or not data:
			return Response({'detail': 'api_key and data are required.'}, status=status.HTTP_400_BAD_REQUEST)
		try:
			resp = doaj_submit_or_update(data, api_key, endpoint=endpoint, method=method, object_id=object_id)
			return Response({'status': 'success', 'message': resp})
		except Exception as e:
			return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_502_BAD_GATEWAY)
		
# --- OJS Review Sync APIViews ---
class OJSReviewSyncAPIView(APIView):
	def get(self, request):
		reviews = ojs_list_reviews()
		data = [OJSReviewSerializer.from_ojs_result(r) for r in reviews]
		return Response(data)

	def post(self, request):
		serializer = OJSReviewSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		review = ojs_create_review(serializer.validated_data)
		return Response(OJSReviewSerializer.from_ojs_result(review), status=201)

class OJSReviewDetailSyncAPIView(APIView):
	def get(self, request, review_id):
		review = ojs_get_review(review_id)
		if not review:
			return Response({'detail': 'Not found.'}, status=404)
		return Response(OJSReviewSerializer.from_ojs_result(review))

	def put(self, request, review_id):
		serializer = OJSReviewSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		review = ojs_update_review(review_id, serializer.validated_data)
		return Response(OJSReviewSerializer.from_ojs_result(review))

	def delete(self, request, review_id):
		ojs_delete_review(review_id)
		return Response(status=204)

# --- OJS Comment Sync APIViews ---
class OJSCommentSyncAPIView(APIView):
	def get(self, request):
		comments = ojs_list_comments()
		data = [OJSCommentSerializer.from_ojs_result(c) for c in comments]
		return Response(data)

	def post(self, request):
		serializer = OJSCommentSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		comment = ojs_create_comment(serializer.validated_data)
		return Response(OJSCommentSerializer.from_ojs_result(comment), status=201)

class OJSCommentDetailSyncAPIView(APIView):
	def get(self, request, comment_id):
		comment = ojs_get_comment(comment_id)
		if not comment:
			return Response({'detail': 'Not found.'}, status=404)
		return Response(OJSCommentSerializer.from_ojs_result(comment))

	def put(self, request, comment_id):
		serializer = OJSCommentSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		comment = ojs_update_comment(comment_id, serializer.validated_data)
		return Response(OJSCommentSerializer.from_ojs_result(comment))

	def delete(self, request, comment_id):
		ojs_delete_comment(comment_id)
		return Response(status=204)
	
# --- OJS User Sync APIViews ---
class OJSUserSyncAPIView(APIView):
	"""List and create OJS users via sync."""
	def get(self, request):
		users = ojs_list_users()
		data = [OJSUserSerializer.from_ojs_result(u) for u in users]
		return Response(data)

	def post(self, request):
		serializer = OJSUserSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		user = ojs_create_user(serializer.validated_data)
		return Response(OJSUserSerializer.from_ojs_result(user), status=201)


class OJSUserDetailSyncAPIView(APIView):
	"""Retrieve, update, or delete a single OJS user via sync."""
	def get(self, request, user_id):
		user = ojs_get_user(user_id)
		if not user:
			return Response({'detail': 'Not found.'}, status=404)
		return Response(OJSUserSerializer.from_ojs_result(user))

	def put(self, request, user_id):
		serializer = OJSUserSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		user = ojs_update_user(user_id, serializer.validated_data)
		return Response(OJSUserSerializer.from_ojs_result(user))

	def delete(self, request, user_id):
		ojs_delete_user(user_id)
		return Response(status=204)

# --- OJS Article Sync API Views ---
class OJSArticleListView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		try:
			data = ojs_list_articles()
			results = data.get('items', data)
			serialized = [OJSArticleSerializer.from_ojs_result(a) for a in results]
			return Response({'results': serialized})
		except Exception as e:
			return Response({'detail': str(e)}, status=status.HTTP_502_BAD_GATEWAY)

	def post(self, request):
		try:
			resp = ojs_create_article(request.data)
			return Response({'status': 'success', 'result': resp})
		except Exception as e:
			return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class OJSArticleDetailView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request, article_id):
		try:
			data = ojs_get_article(article_id)
			serialized = OJSArticleSerializer.from_ojs_result(data)
			return Response(serialized)
		except Exception as e:
			return Response({'detail': str(e)}, status=status.HTTP_502_BAD_GATEWAY)

	def put(self, request, article_id):
		try:
			resp = ojs_update_article(article_id, request.data)
			return Response({'status': 'success', 'result': resp})
		except Exception as e:
			return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_502_BAD_GATEWAY)

	def delete(self, request, article_id):
		try:
			success = ojs_delete_article(article_id)
			return Response({'status': 'success', 'deleted': success})
		except Exception as e:
			return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_502_BAD_GATEWAY)

# --- OJS Sync API Views ---
class OJSJournalListView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		try:
			data = ojs_list_journals()
			results = data.get('items', data)  # OJS API may return list or dict
			serialized = [OJSJournalSerializer.from_ojs_result(j) for j in results]
			return Response({'results': serialized})
		except Exception as e:
			return Response({'detail': str(e)}, status=status.HTTP_502_BAD_GATEWAY)

class OJSSubmissionListView(APIView):
	permission_classes = [IsAuthenticated]

	def get(self, request):
		try:
			data = ojs_list_submissions()
			results = data.get('items', data)
			serialized = [OJSSubmissionSerializer.from_ojs_result(s) for s in results]
			return Response({'results': serialized})
		except Exception as e:
			return Response({'detail': str(e)}, status=status.HTTP_502_BAD_GATEWAY)

class OJSSubmissionCreateView(APIView):
	permission_classes = [IsAuthenticated]

	def post(self, request):
		try:
			resp = ojs_create_submission(request.data)
			return Response({'status': 'success', 'result': resp})
		except Exception as e:
			return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_502_BAD_GATEWAY)

class OJSSubmissionUpdateView(APIView):
	permission_classes = [IsAuthenticated]

	def put(self, request, submission_id):
		try:
			resp = ojs_update_submission(submission_id, request.data)
			return Response({'status': 'success', 'result': resp})
		except Exception as e:
			return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_502_BAD_GATEWAY)