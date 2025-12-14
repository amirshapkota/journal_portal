"""
OJS Synchronization Service
Handles importing data from OJS and syncing submissions bidirectionally.
"""
from django.utils import timezone
from django.db import transaction
from django.core.cache import cache
from apps.submissions.models import Submission
from apps.integrations.models import OJSMapping
from apps.integrations.utils import (
    ojs_list_submissions, ojs_create_submission, ojs_update_submission
)
import logging
import requests

logger = logging.getLogger(__name__)


class OJSSyncService:
    """Service for synchronizing data between Django and OJS."""
    
    def __init__(self, journal):
        """
        Initialize sync service for a specific journal.
        
        Args:
            journal: Journal instance with OJS configuration
        """
        self.journal = journal
        self.api_url = journal.ojs_api_url
        self.api_key = journal.ojs_api_key
        # Ensure ojs_journal_id is an integer
        self.ojs_journal_id = int(journal.ojs_journal_id) if journal.ojs_journal_id else None
        
        if not self.api_url or not self.api_key:
            raise ValueError("Journal does not have OJS configured")
        
        # Create persistent session for cookie handling (bot detection)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        # Initialize session by visiting the site to get cookies
        import re
        import time
        try:
            base_url = self.api_url.replace('/api/v1', '')
            init_resp = self.session.get(base_url, timeout=10)
            logger.info(f"Initial session response: status={init_resp.status_code}, cookies={len(self.session.cookies)}")
            
            # Check if we got a bot detection response
            if init_resp.status_code == 409 or 'document.cookie' in init_resp.text:
                logger.info("Bot detection triggered, extracting cookie...")
                # Extract cookie from JavaScript: document.cookie = "humans_21909=1"
                cookie_match = re.search(r'document\.cookie\s*=\s*"([^=]+)=([^"]+)"', init_resp.text)
                if cookie_match:
                    cookie_name = cookie_match.group(1)
                    cookie_value = cookie_match.group(2)
                    logger.info(f"Setting bot detection cookie: {cookie_name}={cookie_value}")
                    self.session.cookies.set(cookie_name, cookie_value, domain=base_url.split('//')[1].split('/')[0])
                    
                    # Wait a moment then reload the page as the script expects
                    time.sleep(0.5)
                    init_resp = self.session.get(base_url, timeout=10)
                    logger.info(f"After cookie retry: status={init_resp.status_code}, cookies={len(self.session.cookies)}")
            
            logger.info(f"Session initialized successfully with {len(self.session.cookies)} cookies")
        except Exception as e:
            logger.warning(f"Could not initialize session: {str(e)}")
    
    def import_all_from_ojs(self):
        """
        Import all submissions from OJS into Django database.
        Creates new Submission records with OJSMapping for tracking.
        
        Returns:
            dict: Summary of import operation
        """
        # Create a unique cache key for this journal's import progress
        progress_key = f"ojs_import_progress_{self.journal.id}"
        
        summary = {
            'total_ojs_submissions': 0,
            'imported': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0,
            'error_details': []
        }
        
        try:
            # Initialize progress tracking
            progress = {
                'status': 'fetching',
                'current': 0,
                'total': 0,
                'percentage': 0,
                'stage': 'Fetching submissions from OJS',
                'imported': 0,
                'updated': 0,
                'skipped': 0,
                'errors': 0
            }
            cache.set(progress_key, progress, timeout=3600)  # 1 hour timeout
            
            # Fetch all submissions from OJS with pagination
            logger.info(f"Fetching submissions from OJS for journal {self.journal.title}")
            
            all_items = []
            offset = 0
            count = 100  # Fetch 100 items per page
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Accept': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            while True:
                # Fetch page of submissions using session
                url = f"{self.api_url}/submissions"
                params = {'offset': offset, 'count': count}
                
                logger.info(f"Fetching submissions: {url} (offset {offset})")
                resp = self.session.get(url, headers=headers, params=params)
                resp.raise_for_status()
                
                data = resp.json()
                items = data.get('items', [])
                items_max = data.get('itemsMax', 0)
                
                all_items.extend(items)
                
                # Update progress with percentage
                progress['total'] = items_max
                progress['current'] = len(all_items)
                progress['percentage'] = round((len(all_items) / items_max * 100), 2) if items_max > 0 else 0
                progress['stage'] = f'Fetching submissions from OJS ({len(all_items)}/{items_max})'
                cache.set(progress_key, progress, timeout=3600)
                
                logger.info(f"Fetched {len(items)} submissions (offset {offset}), total so far: {len(all_items)}/{items_max}")
                
                # Check if we have all items
                if len(items) < count or len(all_items) >= items_max:
                    break
                
                offset += count
            
            summary['total_ojs_submissions'] = len(all_items)
            logger.info(f"Found {len(all_items)} total submissions to process")
            
            # Sort submissions by ID to ensure consistent processing order
            all_items.sort(key=lambda x: x.get('id', 0))
            
            # Update progress to processing stage
            progress['status'] = 'processing'
            progress['stage'] = 'Processing submissions'
            progress['total'] = len(all_items)
            progress['current'] = 0
            progress['percentage'] = 0
            cache.set(progress_key, progress, timeout=3600)
            
            # Process each OJS submission in order
            for idx, ojs_submission in enumerate(all_items, 1):
                try:
                    result = self._import_single_submission(ojs_submission)
                    if result == 'imported':
                        summary['imported'] += 1
                        progress['imported'] += 1
                    elif result == 'updated':
                        summary['updated'] += 1
                        progress['updated'] += 1
                    elif result == 'skipped':
                        summary['skipped'] += 1
                        progress['skipped'] += 1
                except Exception as e:
                    summary['errors'] += 1
                    progress['errors'] += 1
                    error_msg = f"Error importing OJS ID {ojs_submission.get('id')}: {str(e)}"
                    summary['error_details'].append(error_msg)
                    logger.error(error_msg)
                
                # Update progress every submission with percentage
                progress['current'] = idx
                progress['percentage'] = round((idx / len(all_items) * 100), 2) if len(all_items) > 0 else 0
                progress['stage'] = f'Processing submission {idx}/{len(all_items)}'
                cache.set(progress_key, progress, timeout=3600)
            
            # Mark as complete
            progress['status'] = 'completed'
            progress['percentage'] = 100
            progress['stage'] = 'Import completed'
            cache.set(progress_key, progress, timeout=3600)
            
            logger.info(f"Import complete: {summary}")
            return summary
            
        except Exception as e:
            error_msg = f"Failed to fetch submissions from OJS: {str(e)}"
            summary['error_details'].append(error_msg)
            logger.error(error_msg)
            return summary
    
    def _import_single_submission(self, ojs_submission):
        """
        Import a single submission from OJS.
        Each submission is processed independently to prevent cascading failures.
        
        Args:
            ojs_submission: OJS submission data
            
        Returns:
            str: 'imported', 'updated', or 'skipped'
        """
        ojs_id = ojs_submission.get('id')
        
        try:
            with transaction.atomic():
                # Check if already imported
                existing_mapping = OJSMapping.objects.filter(
                    ojs_submission_id=ojs_id,
                    local_submission__journal=self.journal
                ).first()
                
                if existing_mapping:
                    # Update existing submission
                    logger.info(f"Updating existing submission from OJS ID {ojs_id}")
                    self._update_submission_from_ojs(existing_mapping.local_submission, ojs_submission)
                    existing_mapping.sync_metadata = ojs_submission
                    existing_mapping.last_synced_at = timezone.now()
                    existing_mapping.sync_status = 'COMPLETED'
                    existing_mapping.save()
                    return 'updated'
                
                # Create new submission from OJS data
                logger.info(f"Creating new submission from OJS ID {ojs_id}")
                submission = self._create_submission_from_ojs(ojs_submission)
                
                if submission:
                    # Create mapping
                    OJSMapping.objects.create(
                        local_submission=submission,
                        ojs_submission_id=str(ojs_id),
                        sync_direction='FROM_OJS',
                        sync_status='COMPLETED',
                        last_synced_at=timezone.now(),
                        sync_metadata=ojs_submission
                    )
                    return 'imported'
                
                return 'skipped'
        except Exception as e:
            logger.error(f"Error importing submission {ojs_id}: {str(e)}")
            raise
    
    def _create_submission_from_ojs(self, ojs_data):
        """
        Create a Django Submission from OJS data.
        Fetches full publication details to get abstract and authors.
        
        Args:
            ojs_data: OJS submission data
            
        Returns:
            Submission instance or None
        """
        try:
            # Extract publication data (OJS stores the latest published version)
            publications = ojs_data.get('publications', [])
            if not publications:
                logger.warning(f"OJS submission {ojs_data.get('id')} has no publications")
                return None
            
            pub = publications[0]  # Latest publication
            ojs_submission_id = ojs_data.get('id')
            publication_id = pub.get('id')
            
            # Fetch full publication details to get abstract and authors
            import requests
            url = f"{self.api_url}/submissions/{ojs_submission_id}/publications/{publication_id}"
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            logger.info(f"Fetching full publication details for OJS ID {ojs_submission_id}")
            resp = self.session.get(url, headers=headers)
            
            if resp.status_code != 200:
                logger.error(f"Failed to fetch publication details: {resp.status_code} - {resp.text[:500]}")
                # Try to continue with data from the original publications array
                logger.warning("Attempting to use data from original publications array")
                full_pub = pub  # Use the publication data we already have
            else:
                full_pub = resp.json()
            
            # Log the full publication data for debugging
            logger.info(f"Full publication data keys: {list(full_pub.keys())}")
            logger.debug(f"Full publication data: {full_pub}")
            
            # Extract title - try multiple fields
            title = None
            if 'fullTitle' in full_pub and full_pub['fullTitle']:
                title = full_pub['fullTitle'].get('en_US') or full_pub['fullTitle'].get('en')
            if not title and 'title' in full_pub and full_pub['title']:
                title = full_pub['title'].get('en_US') or full_pub['title'].get('en')
            if not title:
                # Fallback to checking the original publications data
                title = pub.get('fullTitle', {}).get('en_US') or pub.get('title', {}).get('en_US', 'Untitled')
            
            logger.info(f"Extracted title: {title}")
            
            # Extract abstract (strip HTML tags from abstract)
            abstract_html = full_pub.get('abstract', {}).get('en_US') or full_pub.get('abstract', {}).get('en', '')
            
            # Strip HTML tags from abstract
            import re
            abstract = re.sub(r'<[^>]+>', '', abstract_html)
            abstract = re.sub(r'\s+', ' ', abstract).strip()  # Clean up whitespace
            
            # Map OJS status to Django status
            ojs_status = ojs_data.get('status')
            status_map = {
                1: 'SUBMITTED',      # Queued
                2: 'UNDER_REVIEW',   # Scheduled
                3: 'PUBLISHED',      # Published
                4: 'REJECTED',       # Declined
                5: 'DRAFT'           # Incomplete
            }
            status = status_map.get(ojs_status, 'SUBMITTED')
            
            # Parse date with timezone
            from django.utils.dateparse import parse_datetime
            from django.utils import timezone as tz
            submitted_at = None
            if ojs_data.get('dateSubmitted'):
                # OJS returns naive datetime, make it aware
                naive_dt = parse_datetime(ojs_data.get('dateSubmitted'))
                if naive_dt:
                    submitted_at = tz.make_aware(naive_dt, tz.get_default_timezone())
            
            # Extract additional metadata
            pages = full_pub.get('pages', '')
            published_date = full_pub.get('datePublished')
            section_id = full_pub.get('sectionId')
            
            # Parse published date
            published_at = None
            if published_date:
                from django.utils.dateparse import parse_date
                parsed_date = parse_date(published_date)
                if parsed_date:
                    import datetime
                    published_at = tz.make_aware(
                        datetime.datetime.combine(parsed_date, datetime.time.min),
                        tz.get_default_timezone()
                    )
            
            # Try to find matching section by OJS section ID
            from apps.journals.models import Section
            section = None
            if section_id:
                # Store OJS section ID for future mapping
                logger.info(f"OJS Section ID: {section_id}")
                # For now, we don't map sections automatically
                # This could be enhanced to map based on section names
            
            # Create submission
            submission = Submission.objects.create(
                journal=self.journal,
                title=title[:500],  # Respect max_length
                abstract=abstract,
                status=status,
                submitted_at=submitted_at,
                # corresponding_author will be set after creating authors
            )
            
            # Store additional metadata in a JSON field if available, or log it
            logger.info(f"Submission metadata - Pages: {pages}, Section ID: {section_id}, Published: {published_date}")
            
            # Create author profiles and link them
            authors_data = full_pub.get('authors', [])
            if authors_data:
                self._create_authors_for_submission(submission, authors_data)
            
            # Import submission files/documents
            files_count = self._import_submission_files(submission, ojs_submission_id)
            
            # Import reviews and review assignments
            reviews_count = self._import_reviews_for_submission(submission, ojs_submission_id)
            
            logger.info(f"Created submission {submission.id} from OJS ID {ojs_submission_id} with {len(authors_data)} authors, {files_count} files, and {reviews_count} reviews")
            return submission
            
        except Exception as e:
            logger.error(f"Failed to create submission from OJS data: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def _create_authors_for_submission(self, submission, authors_data):
        """
        Link author profiles to submission from OJS authors data.
        Matches existing users imported from OJS by email.
        
        Args:
            submission: Django Submission instance
            authors_data: List of author dictionaries from OJS
        """
        from apps.users.models import CustomUser, Profile
        from apps.submissions.models import AuthorContribution
        
        try:
            # Sort authors by sequence
            sorted_authors = sorted(authors_data, key=lambda x: x.get('seq', 999))
            
            logger.info(f"Creating authors for submission {submission.id}: {len(sorted_authors)} authors")
            logger.info(f"Authors data: {authors_data}")
            
            for idx, author in enumerate(sorted_authors):
                email = author.get('email', f'author{idx}@imported.ojs')
                # Try en_US first, then en as fallback
                given_name = author.get('givenName', {}).get('en_US') or author.get('givenName', {}).get('en', '')
                family_name = author.get('familyName', {}).get('en_US') or author.get('familyName', {}).get('en', '')
                affiliation = author.get('affiliation', {}).get('en_US') or author.get('affiliation', {}).get('en', '')
                orcid_raw = author.get('orcid', '')
                
                # Extract ORCID ID from URL if it's a full URL
                orcid = None
                if orcid_raw:
                    if 'orcid.org/' in orcid_raw:
                        # Extract the ID part from URL
                        orcid = orcid_raw.split('orcid.org/')[-1]
                    else:
                        orcid = orcid_raw
                
                # First, check if a profile with this ORCID already exists
                profile = None
                if orcid:
                    profile = Profile.objects.filter(orcid_id=orcid).first()
                    if profile:
                        logger.info(f"Found existing profile with ORCID {orcid} for user {profile.user.email}")
                
                # If no profile found by ORCID, try to find by email
                if not profile:
                    user = CustomUser.objects.filter(email=email).first()
                    
                    # If user doesn't exist, create them (fallback for authors not in user list)
                    if not user:
                        user = CustomUser.objects.create(
                            email=email,
                            username=email,
                            first_name=given_name,
                            last_name=family_name,
                            imported_from=self.journal.id,
                        )
                        user.set_unusable_password()
                        user.save()
                        logger.info(f"Created missing user during submission import: {email}")
                    # If user already exists, just use it without updating
                    
                    # Get or create profile for this user
                    display_name = f"{given_name} {family_name}".strip()
                    
                    profile, profile_created = Profile.objects.get_or_create(
                        user=user,
                        defaults={
                            'display_name': display_name if display_name else None,
                            'affiliation_name': affiliation,
                            'orcid_id': orcid if orcid else None,
                        }
                    )
                    
                    # Update profile if it exists but missing display_name
                    if not profile_created and not profile.display_name and display_name:
                        profile.display_name = display_name
                        profile.save(update_fields=['display_name'])
                        logger.info(f"Updated display_name for existing profile: {profile.user.email}")
                    # If profile already exists, just use it without updating
                
                # Create author contribution (use get_or_create to avoid duplicates)
                AuthorContribution.objects.get_or_create(
                    submission=submission,
                    profile=profile,
                    defaults={
                        'order': idx + 1,
                        'contrib_role': 'FIRST' if idx == 0 else 'CO_AUTHOR',
                        'contribution_details': {'imported_from_ojs': True}
                    }
                )
                
                # Set first author as corresponding author
                if idx == 0:
                    submission.corresponding_author = profile
                    submission.save(update_fields=['corresponding_author'])
                    logger.info(f"Set corresponding author to: {profile.display_name or profile.user.email}")
            
            logger.info(f"Successfully linked {len(sorted_authors)} authors to submission {submission.id}")
            logger.info(f"Corresponding author: {submission.corresponding_author}")
            
        except Exception as e:
            logger.error(f"Failed to link authors to submission {submission.id}: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _import_submission_files(self, submission, ojs_submission_id):
        """
        Import files/documents from OJS for a submission.
        Downloads all submission files (DOCX, PDF, etc.) from all workflow stages.
        
        Args:
            submission: Django Submission instance
            ojs_submission_id: OJS submission ID
        """
        import requests
        from django.core.files.base import ContentFile
        from apps.submissions.models import Document
        
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            files_imported = 0
            
            # Method 1: Import from submission files endpoint (all stages)
            files_url = f"{self.api_url}/submissions/{ojs_submission_id}/files"
            logger.info(f"Fetching files from: {files_url}")
            files_resp = self.session.get(files_url, headers=headers)
            
            logger.info(f"Files API response status: {files_resp.status_code}")
            
            submission_files = []
            if files_resp.status_code == 200:
                files_data = files_resp.json()
                submission_files = files_data.get('items', [])
                
                logger.info(f"Found {len(submission_files)} files in OJS submission {ojs_submission_id}")
            else:
                logger.warning(f"Failed to fetch files directly: {files_resp.status_code} - {files_resp.text[:200]}")
                logger.info("Trying to fetch files from publication galleys as fallback")
                
                # Fallback: Get files from publication galleys
                try:
                    sub_url = f"{self.api_url}/submissions/{ojs_submission_id}"
                    sub_resp = self.session.get(sub_url, headers=headers)
                    if sub_resp.status_code == 200:
                        sub_data = sub_resp.json()
                        publications = sub_data.get('publications', [])
                        
                        if publications:
                            pub = publications[0]
                            galleys = pub.get('galleys', [])
                            logger.info(f"Found {len(galleys)} galleys in publication")
                            
                            # Convert galleys to submission_files format
                            for galley in galleys:
                                submission_files.append({
                                    'id': galley.get('submissionFileId') or galley.get('id'),
                                    'name': galley.get('label', {}) or {'en_US': galley.get('file', {}).get('name', 'document')},
                                    'mimetype': galley.get('file', {}).get('mimetype', 'application/pdf'),
                                    'fileStage': 10,  # Production ready
                                    'galleyId': galley.get('id'),
                                    'path': None  # Will use galley download
                                })
                    else:
                        logger.error(f"Failed to fetch submission data for galleys: {sub_resp.status_code}")
                except Exception as e:
                    logger.error(f"Error fetching galleys: {str(e)}")
            
            if not submission_files:
                logger.info("No files found for this submission")
                return 0
            
            for file_data in submission_files:
                    try:
                        file_id = file_data.get('id')
                        file_name_obj = file_data.get('name', {})
                        # Handle name as multilingual object
                        file_name = file_name_obj.get('en_US') or file_name_obj.get('en') or f'document_{file_id}'
                        mime_type = file_data.get('mimetype', 'application/octet-stream')
                        file_stage = file_data.get('fileStage', 0)
                        
                        # Get the direct download URL from OJS API response
                        file_url = file_data.get('url')
                        file_path = file_data.get('path')
                        
                        logger.info(f"Processing file: {file_name} (ID: {file_id}, Stage: {file_stage})")
                        logger.info(f"  URL: {file_url}, Path: {file_path}")
                        
                        # Map OJS file stage to Django document type
                        # OJS fileStage values: 2=submission, 4=review, 9=copyedit, 10=production
                        stage_to_type_map = {
                            2: 'MANUSCRIPT',           # Submission files
                            3: 'MANUSCRIPT',           # Review file
                            4: 'REVIEWER_RESPONSE',    # Review attachments
                            5: 'REVISED_MANUSCRIPT',   # Review revision
                            9: 'REVISED_MANUSCRIPT',   # Copyediting
                            10: 'FINAL_VERSION',       # Production ready
                            15: 'SUPPLEMENTARY',       # Supplementary files
                        }
                        
                        doc_type = stage_to_type_map.get(file_stage, 'MANUSCRIPT')
                        
                        # Special handling for DOCX files - always mark as MANUSCRIPT
                        if 'word' in mime_type.lower() or file_name.endswith('.docx'):
                            doc_type = 'MANUSCRIPT'
                        
                        # For downloading files from OJS
                        base_url = self.api_url.replace('/api/v1', '')
                        
                        # Try different download methods
                        file_content = None
                        
                        # Method 1: Use the 'url' field from the API response (preferred)
                        if file_url:
                            logger.info(f"Attempting download from API-provided URL: {file_url}")
                            
                            file_headers_with_auth = {
                                'Authorization': f'Bearer {self.api_key}',
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                            }
                            file_resp = self.session.get(file_url, headers=file_headers_with_auth, allow_redirects=True)
                            
                            if file_resp.status_code == 200 and len(file_resp.content) > 0:
                                # Verify it's not an error page
                                if not (len(file_resp.content) < 1000 and b'<html' in file_resp.content.lower()):
                                    file_content = file_resp.content
                                    logger.info(f"✓ Downloaded file from API URL: {len(file_content)} bytes")
                            else:
                                logger.warning(f"URL download failed: {file_resp.status_code} - {file_resp.text[:200]}")
                        
                        # Method 2: Try using the file path directly (OJS stores files in files_dir)
                        if not file_content and file_path:
                            # Try to access via OJS's files directory
                            # OJS usually serves files from: /files/{path}
                            direct_file_url = f"{base_url.rsplit('/', 2)[0]}/files/{file_path}"
                            
                            logger.info(f"Attempting direct file download: {direct_file_url}")
                            
                            file_headers_minimal = {
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                            }
                            file_resp = self.session.get(direct_file_url, headers=file_headers_minimal, allow_redirects=True)
                            
                            if file_resp.status_code == 200 and len(file_resp.content) > 0:
                                # Verify it's not an error page
                                if not (len(file_resp.content) < 1000 and b'<html' in file_resp.content.lower()):
                                    file_content = file_resp.content
                                    logger.info(f"✓ Downloaded file via direct path: {len(file_content)} bytes")
                        
                        # Method 3: Try OJS file API (may not work due to permissions)
                        if not file_content:
                            file_stage_id = file_data.get('fileStage', 1)
                            file_api_url = f"{base_url}/$$$call$$$/api/file/file-api/download-file"
                            file_api_params = {
                                'submissionFileId': file_id,
                                'submissionId': ojs_submission_id,
                                'stageId': file_stage_id
                            }
                            
                            logger.info(f"Attempting to download file {file_id} ({file_name}) using file API")
                            
                            # Try with authorization header
                            file_headers = {
                                'Authorization': f'Bearer {self.api_key}',
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                            }
                            
                            file_resp = self.session.get(
                                file_api_url, 
                                params=file_api_params, 
                                headers=file_headers, 
                                allow_redirects=True,
                                stream=True
                            )
                            
                            if file_resp.status_code == 200 and len(file_resp.content) > 0:
                                # Check content type
                                content_type = file_resp.headers.get('Content-Type', '')
                                content = file_resp.content
                                
                                # Skip if it's a JSON error response
                                if 'application/json' in content_type:
                                    try:
                                        error_data = file_resp.json()
                                        if error_data.get('status') == False:
                                            logger.warning(f"File API returned error: {error_data.get('content', 'Unknown error')}")
                                        else:
                                            file_content = content
                                            logger.info(f"Successfully downloaded file via file API: {len(file_content)} bytes")
                                    except:
                                        file_content = content
                                        logger.info(f"Successfully downloaded file via file API: {len(file_content)} bytes")
                                # Verify it's not an HTML error page
                                elif not (len(content) < 1000 and b'<html' in content.lower()):
                                    file_content = content
                                    logger.info(f"Successfully downloaded file via file API: {len(file_content)} bytes")
                                else:
                                    logger.warning(f"File API returned HTML error: {content[:200]}")
                        
                        # Method 3: Try publication galleys (for published files)
                        # Check if this file data already has a galleyId (from fallback method)
                        if not file_content and file_data.get('galleyId'):
                            galley_id = file_data.get('galleyId')
                            download_url = f"{base_url}/article/download/{ojs_submission_id}/{galley_id}"
                            
                            logger.info(f"Trying direct galley download from: {download_url}")
                            
                            # Try without Authorization to avoid ModSecurity blocks
                            galley_headers = {
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                            }
                            galley_resp = self.session.get(download_url, headers=galley_headers, allow_redirects=True, timeout=30)
                            
                            if galley_resp.status_code == 200:
                                # Check if it's actually a file (not HTML error page or JSON)
                                content_type = galley_resp.headers.get('Content-Type', '')
                                is_file = 'application/pdf' in content_type or 'application/octet-stream' in content_type or 'application/msword' in content_type or 'officedocument' in content_type
                                
                                if is_file and len(galley_resp.content) > 1000:
                                    file_content = galley_resp.content
                                    logger.info(f"Successfully downloaded file via direct galley: {len(file_content)} bytes")
                                elif 'application/json' in content_type:
                                    logger.warning(f"Galley returned JSON error: {galley_resp.text[:200]}")
                                else:
                                    logger.warning(f"Galley returned unexpected content type: {content_type}")
                                if not (len(galley_resp.content) < 1000 and b'<html' in galley_resp.content.lower()):
                                    file_content = galley_resp.content
                                    logger.info(f"Successfully downloaded file via direct galley: {len(file_content)} bytes")
                        
                        # Method 4: Try fetching submission and looking for galleys
                        if not file_content:
                            sub_resp = self.session.get(f"{self.api_url}/submissions/{ojs_submission_id}", headers=headers)
                            if sub_resp.status_code == 200:
                                sub_data = sub_resp.json()
                                publications = sub_data.get('publications', [])
                                
                                if publications:
                                    pub = publications[0]
                                    galleys = pub.get('galleys', [])
                                    
                                    # Find matching galley by file ID
                                    for galley in galleys:
                                        if galley.get('submissionFileId') == file_id:
                                            galley_id = galley.get('id')
                                            download_url = f"{base_url}/article/download/{ojs_submission_id}/{galley_id}"
                                            
                                            logger.info(f"Trying galley download from: {download_url}")
                                            galley_headers_minimal = {
                                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                                            }
                                            galley_resp = self.session.get(download_url, headers=galley_headers_minimal, allow_redirects=True)
                                            
                                            if galley_resp.status_code == 200:
                                                if not (len(galley_resp.content) < 1000 and b'<html' in galley_resp.content.lower()):
                                                    file_content = galley_resp.content
                                                    logger.info(f"Successfully downloaded file via galley: {len(file_content)} bytes")
                                            break
                        
                        # If still no file content, skip this file
                        if not file_content:
                            logger.warning(f"File {file_id} ({file_name}) could not be downloaded after trying all methods, skipping")
                            continue
                        
                        logger.info(f"Successfully obtained file content for {file_name}: {len(file_content)} bytes")
                        
                        # Get or create the document creator
                        creator = submission.corresponding_author
                        if not creator:
                            first_contrib = submission.author_contributions.order_by('order').first()
                            if first_contrib:
                                creator = first_contrib.profile
                            else:
                                from apps.users.models import CustomUser
                                admin_user = CustomUser.objects.filter(is_superuser=True).first()
                                if admin_user and hasattr(admin_user, 'profile'):
                                    creator = admin_user.profile
                                else:
                                    logger.warning(f"No creator found for document, skipping file {file_name}")
                                    continue
                        
                        logger.info(f"Using creator: {creator.user.email} for document {file_name}")
                        
                        # Check if document already exists
                        existing_doc = Document.objects.filter(
                            submission=submission,
                            file_name=file_name
                        ).first()
                        
                        if existing_doc:
                            logger.info(f"Document {file_name} already exists for submission {submission.id}, skipping to preserve existing document")
                            continue
                        
                        # Create document
                        document = Document.objects.create(
                            submission=submission,
                            title=file_name,
                            document_type=doc_type,
                            description=f"Imported from OJS (Stage: {file_stage}, MIME: {mime_type})",
                            created_by=creator,
                            file_name=file_name,
                            file_size=len(file_content)
                        )
                        
                        # Save the file
                        document.original_file.save(
                            file_name,
                            ContentFile(file_content),
                            save=True
                        )
                        
                        files_imported += 1
                        logger.info(f"Imported file {file_name} ({doc_type}) for submission {submission.id}")
                        
                    except Exception as e:
                        logger.error(f"Error importing file {file_data.get('id')}: {str(e)}")
                        continue
            
            return files_imported
            
        except Exception as e:
            logger.error(f"Failed to import files for submission {ojs_submission_id}: {str(e)}")
            import traceback
            traceback.print_exc()
            return 0
    
    def _import_reviews_for_submission(self, submission, ojs_submission_id):
        """
        Import reviews and review assignments for a specific submission.
        
        Args:
            submission: Django Submission instance
            ojs_submission_id: OJS submission ID
            
        Returns:
            int: Number of review assignments imported
        """
        import requests
        from apps.reviews.models import ReviewAssignment
        from apps.users.models import CustomUser, Profile
        
        review_count = 0
        
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            # OJS 3.x stores reviews in reviewRounds, not directly in submission
            # Try to fetch review rounds first using internal editorial endpoint
            # The public API may not expose reviewer information
            review_rounds_url = f"{self.api_url.replace('/api/v1', '')}/$$$call$$$/api/workflow/index"
            
            logger.info(f"Attempting to fetch review data for OJS submission {ojs_submission_id}")
            
            # First try the standard submissions endpoint
            resp = self.session.get(f"{self.api_url}/submissions/{ojs_submission_id}", headers=headers)
            
            if resp.status_code != 200:
                logger.warning(f"Could not fetch submission data for {ojs_submission_id}: status {resp.status_code}")
                return 0
            
            full_data = resp.json()
            
            # Check for reviewRounds (OJS 3.x structure)
            review_rounds = full_data.get('reviewRounds', [])
            logger.info(f"Found {len(review_rounds)} review rounds for OJS submission {ojs_submission_id}")
            
            if not review_rounds:
                logger.info(f"No review rounds found for submission {ojs_submission_id}")
                logger.debug(f"Available keys in response: {list(full_data.keys())}")
                return 0
            
            # OJS public API doesn't expose reviewer identities in review assignments
            # The reviewAssignments in reviewRounds only contain assignment metadata, not reviewer info
            # This is by design for privacy - only editors can see reviewer assignments
            # We would need to use OJS's internal API or database access to get reviewer information
            
            logger.warning(f"OJS API does not expose reviewer identities in public endpoints. "
                          f"Review assignments found but cannot import without reviewer information. "
                          f"Consider using OJS database access or internal API for complete review import.")
            
            return 0
            
        except Exception as e:
            logger.error(f"Failed to import reviews for submission {ojs_submission_id}: {str(e)}")
            import traceback
            traceback.print_exc()
            return 0
    
    def _create_review_assignment(self, submission, ra, round_number=1):
        """
        Create a review assignment from OJS review assignment data.
        
        Args:
            submission: Django Submission instance
            ra: OJS review assignment data
            round_number: Review round number
            
        Returns:
            int: 1 if created, 0 if already exists
        """
        import requests
        from apps.reviews.models import ReviewAssignment
        from apps.users.models import CustomUser, Profile
        from django.utils.dateparse import parse_datetime
        from django.utils import timezone as tz
        from datetime import timedelta
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        # The review assignment from reviewRounds may not include reviewerId
        # Try to get it from the assignment data first
        reviewer_id = ra.get('reviewerId')
        
        if not reviewer_id:
            # If reviewerId is not present, try to fetch full review assignment details
            assignment_id = ra.get('id')
            if assignment_id:
                logger.info(f"Fetching full review assignment details for assignment ID {assignment_id}")
                # Try to get full assignment details - OJS may have endpoint like:
                # /reviewAssignments/{id} or we may need to parse from submission data
                # For now, log what we have and skip
                logger.warning(f"Review assignment {assignment_id} has no reviewerId. Available fields: {list(ra.keys())}")
                logger.debug(f"Full review assignment data: {ra}")
                # We cannot create a review without knowing who the reviewer is
                return 0
            else:
                logger.warning(f"Review assignment has no reviewerId or id. Available fields: {list(ra.keys())}")
                return 0
        
        # Fetch reviewer details
        user_resp = self.session.get(f"{self.api_url}/users/{reviewer_id}", headers=headers)
        if user_resp.status_code != 200:
            logger.warning(f"Could not fetch user {reviewer_id}: status {user_resp.status_code}")
            return 0
        
        user_data = user_resp.json()
        email = user_data.get('email')
        
        if not email:
            logger.warning(f"Reviewer {reviewer_id} has no email, skipping")
            return 0
        
        # Get or create user
        full_name = user_data.get('fullName', '')
        name_parts = full_name.split(' ', 1)
        first_name = name_parts[0] if name_parts else ''
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        user, _ = CustomUser.objects.get_or_create(
            email=email,
            defaults={
                'username': user_data.get('userName', email.split('@')[0]),
                'first_name': first_name,
                'last_name': last_name,
                'imported_from': self.journal.id,
            }
        )
        
        # Get or create profile
        profile, _ = Profile.objects.get_or_create(user=user)
        
        # Get assigned by (use journal editor or first staff member)
        assigned_by = self.journal.staff_members.filter(
            role='EDITOR_IN_CHIEF',
            is_active=True
        ).first()
        
        if not assigned_by:
            assigned_by = self.journal.staff_members.filter(is_active=True).first()
        
        if not assigned_by:
            logger.warning(f"No staff member found to assign review, skipping")
            return 0
        
        # Map OJS review status to Django status
        ojs_status = ra.get('statusId', 0)
        status_map = {
            0: 'PENDING',       # REVIEW_ASSIGNMENT_STATUS_AWAITING_RESPONSE
            1: 'DECLINED',      # REVIEW_ASSIGNMENT_STATUS_DECLINED
            4: 'ACCEPTED',      # REVIEW_ASSIGNMENT_STATUS_ACCEPTED
            5: 'COMPLETED',     # REVIEW_ASSIGNMENT_STATUS_COMPLETE
            6: 'CANCELLED',     # REVIEW_ASSIGNMENT_STATUS_THANKED
            7: 'CANCELLED',     # REVIEW_ASSIGNMENT_STATUS_CANCELLED
        }
        
        status = status_map.get(ojs_status, 'PENDING')
        
        # Parse dates
        due_date = None
        if ra.get('dateResponseDue'):
            due_date = parse_datetime(ra.get('dateResponseDue'))
            if due_date and not tz.is_aware(due_date):
                due_date = tz.make_aware(due_date)
        
        if not due_date:
            # Default to 30 days from now
            due_date = tz.now() + timedelta(days=30)
        
        # Create or get review assignment
        assignment, created = ReviewAssignment.objects.get_or_create(
            submission=submission,
            reviewer=profile,
            review_round=round_number,
            defaults={
                'assigned_by': assigned_by.profile,
                'status': status,
                'due_date': due_date,
            }
        )
        
        if created:
            logger.info(f"Created review assignment for submission {submission.id}, reviewer {email}, round {round_number}")
            return 1
        else:
            logger.debug(f"Review assignment already exists for submission {submission.id}, reviewer {email}")
            return 0
    
    def _update_submission_from_ojs(self, submission, ojs_data):
        """
        Update existing submission with OJS data.
        
        Args:
            submission: Django Submission instance
            ojs_data: OJS submission data
        """
        try:
            ojs_submission_id = ojs_data.get('id')
            
            publications = ojs_data.get('publications', [])
            if publications:
                pub = publications[0]
                submission.title = pub.get('fullTitle', {}).get('en_US', submission.title)[:500]
                submission.abstract = pub.get('abstract', {}).get('en_US', submission.abstract)
            
            # Update status
            ojs_status = ojs_data.get('status')
            status_map = {
                1: 'SUBMITTED',
                2: 'UNDER_REVIEW',
                3: 'PUBLISHED',
                4: 'REJECTED',
                5: 'DRAFT'
            }
            submission.status = status_map.get(ojs_status, submission.status)
            submission.save()
            
            # Import submission files (they may have been added or updated in OJS)
            files_count = self._import_submission_files(submission, ojs_submission_id)
            
            # Import reviews and review assignments (they may have been added after initial import)
            reviews_count = self._import_reviews_for_submission(submission, ojs_submission_id)
            
            logger.info(f"Updated submission {submission.id} from OJS with {files_count} files and {reviews_count} reviews")
            
        except Exception as e:
            logger.error(f"Failed to update submission {submission.id}: {str(e)}")
    
    def push_submission_to_ojs(self, submission):
        """
        Push a Django submission to OJS.
        Creates or updates the submission in OJS.
        
        Args:
            submission: Django Submission instance
            
        Returns:
            dict: Result of the operation
        """
        result = {
            'success': False,
            'ojs_id': None,
            'action': None,
            'error': None
        }
        
        try:
            # Check if already linked to OJS
            try:
                mapping = submission.ojs_mapping
                # Update existing OJS submission
                result['action'] = 'update'
                ojs_data = self._prepare_ojs_data(submission)
                response = ojs_update_submission(
                    self.api_url,
                    self.api_key,
                    mapping.ojs_submission_id,
                    ojs_data
                )
                result['success'] = True
                result['ojs_id'] = mapping.ojs_submission_id
                
                # Upload/sync documents to OJS (also for updates)
                try:
                    uploaded_files = self._upload_submission_files_to_ojs(submission, result['ojs_id'])
                    if uploaded_files > 0:
                        logger.info(f"Successfully uploaded {uploaded_files} files to OJS submission {result['ojs_id']}")
                    else:
                        logger.info(f"No files to upload for submission {result['ojs_id']}")
                except Exception as e:
                    logger.error(f"Failed to upload files to OJS: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    # Don't fail the whole operation if file upload fails
                
                # Update mapping
                mapping.last_synced_at = timezone.now()
                mapping.sync_status = 'COMPLETED'
                mapping.sync_metadata = response
                mapping.save()
                
            except OJSMapping.DoesNotExist:
                # Create new OJS submission with publication
                result['action'] = 'create'
                
                import requests
                headers = {
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }
                
                # Step 1: Create minimal submission first
                submission_data = {
                    'contextId': self.ojs_journal_id,
                    'submissionProgress': 0,  # Mark as complete
                }
                
                # If we have a section, add it
                if submission.section:
                    submission_data['sectionId'] = submission.section.id
                
                url = f"{self.api_url}/submissions"
                
                logger.info(f"Creating submission in OJS: {url}")
                logger.info(f"Submission data: {submission_data}")
                
                response = self.session.post(url, json=submission_data, headers=headers)
                logger.info(f"Create submission response: {response.status_code}")
                logger.info(f"Create submission body: {response.text}")
                
                if response.status_code not in [200, 201]:
                    result['error'] = f"OJS API returned {response.status_code}: {response.text}"
                    logger.error(result['error'])
                    return result
                
                response.raise_for_status()
                ojs_submission = response.json()
                result['ojs_id'] = ojs_submission.get('id')
                
                logger.info(f"Created OJS submission ID: {result['ojs_id']}")
                
                # Step 2: Create publication for the submission
                publication_data = self._prepare_publication_data(submission)
                pub_url = f"{self.api_url}/submissions/{result['ojs_id']}/publications"
                
                logger.info(f"Creating publication in OJS: {pub_url}")
                logger.info(f"Publication data: {publication_data}")
                
                pub_response = self.session.post(pub_url, json=publication_data, headers=headers)
                logger.info(f"Create publication response: {pub_response.status_code}")
                logger.info(f"Create publication body: {pub_response.text}")
                
                if pub_response.status_code in [200, 201]:
                    pub_data = pub_response.json()
                    logger.info(f"Successfully created publication {pub_data.get('id')} for submission {result['ojs_id']}")
                    result['success'] = True
                else:
                    logger.error(f"Failed to create publication: {pub_response.status_code} - {pub_response.text}")
                    # Still mark as success since submission was created, just warn
                    result['success'] = True
                    result['warning'] = f"Submission created but publication failed: {pub_response.text}"
                
                # Step 4: Upload documents to OJS
                try:
                    uploaded_files = self._upload_submission_files_to_ojs(submission, result['ojs_id'])
                    if uploaded_files > 0:
                        logger.info(f"Successfully uploaded {uploaded_files} files to OJS submission {result['ojs_id']}")
                    else:
                        logger.info(f"No files to upload for submission {result['ojs_id']}")
                except Exception as e:
                    logger.error(f"Failed to upload files to OJS: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    # Don't fail the whole operation if file upload fails
                
                # Create mapping
                OJSMapping.objects.create(
                    local_submission=submission,
                    ojs_submission_id=str(result['ojs_id']),
                    sync_direction='TO_OJS',
                    sync_status='COMPLETED',
                    last_synced_at=timezone.now(),
                    sync_metadata=ojs_submission
                )
            
            logger.info(f"Pushed submission {submission.id} to OJS: {result['action']}")
            return result
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Failed to push submission {submission.id} to OJS: {str(e)}")
            return result
    
    def _upload_submission_files_to_ojs(self, submission, ojs_submission_id):
        """
        Upload documents from Django submission to OJS.
        Only uploads files that don't already exist in OJS.
        
        Args:
            submission: Django Submission instance
            ojs_submission_id: OJS submission ID
            
        Returns:
            int: Number of files uploaded
        """
        import requests
        
        uploaded_count = 0
        
        # Get all documents for this submission
        documents = submission.documents.all().order_by('created_at')
        
        logger.info(f"Found {documents.count()} documents to upload for submission {submission.id}")
        
        # First, get existing files in OJS to avoid duplicates
        existing_files = []
        try:
            files_url = f"{self.api_url}/submissions/{ojs_submission_id}/files"
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            files_response = self.session.get(files_url, headers=headers, timeout=30)
            if files_response.status_code == 200:
                files_data = files_response.json()
                existing_files = files_data.get('items', [])
                logger.info(f"Found {len(existing_files)} existing files in OJS submission {ojs_submission_id}")
        except Exception as e:
            logger.warning(f"Could not fetch existing files: {str(e)}")
        
        # Create a set of existing file names for quick lookup
        existing_file_names = {f.get('name', {}).get('en_US', '') for f in existing_files}
        
        for document in documents:
            try:
                # Skip documents without files
                if not document.original_file:
                    logger.warning(f"Skipping document {document.id} - no file attached")
                    continue
                
                # Get file name
                file_name = document.file_name or document.original_file.name
                
                # Check if file already exists in OJS
                if file_name in existing_file_names:
                    logger.info(f"Skipping file {file_name} - already exists in OJS")
                    continue
                
                # Map Django document types to OJS file stages
                # OJS fileStage values: 2=submission, 15=supplementary
                file_stage = 2 if document.document_type == 'MANUSCRIPT' else 15
                
                logger.info(f"Uploading file: {file_name} (type: {document.document_type}) to OJS")
                
                # Read file content
                document.original_file.seek(0)  # Reset file pointer
                file_content = document.original_file.read()
                
                # Determine MIME type from file extension
                import mimetypes
                mime_type, _ = mimetypes.guess_type(file_name)
                mime_type = mime_type or 'application/octet-stream'
                
                # Prepare file upload according to OJS API documentation
                # OJS expects multipart/form-data with JSON metadata and binary file
                url = f"{self.api_url}/submissions/{ojs_submission_id}/files"
                headers = {
                    'Authorization': f'Bearer {self.api_key}',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                }
                
                # Prepare multipart form data with file and metadata
                files = {
                    'file': (file_name, file_content, mime_type)
                }
                
                # Add required form fields as per OJS documentation
                form_data = {
                    'fileStage': str(file_stage),
                    'genreId': '1',  # Article Text genre
                    'name[en_US]': file_name,
                    'submissionId': str(ojs_submission_id),
                }
                
                logger.info(f"Upload URL: {url}")
                logger.info(f"Form data: {form_data}")
                
                # Upload file to OJS
                response = self.session.post(url, headers=headers, files=files, data=form_data, timeout=60)
                
                # Log response for debugging
                logger.info(f"Upload response status: {response.status_code}")
                logger.info(f"Upload response body: {response.text[:500]}")  # First 500 chars
                
                if response.status_code not in [200, 201]:
                    logger.error(f"OJS file upload failed. Status: {response.status_code}, Body: {response.text}")
                    continue  # Skip this file but don't fail
                
                response.raise_for_status()
                
                uploaded_count += 1
                logger.info(f"Successfully uploaded file {file_name} to OJS submission {ojs_submission_id}")
                
            except Exception as e:
                file_name = document.file_name if hasattr(document, 'file_name') else 'unknown'
                logger.error(f"Failed to upload file {file_name} to OJS: {str(e)}")
                import traceback
                traceback.print_exc()
                continue
        
        return uploaded_count
    
    def _prepare_ojs_data(self, submission):
        """
        Prepare Django submission data for OJS API.
        
        Args:
            submission: Django Submission instance
            
        Returns:
            dict: OJS-compatible submission data
        """
        # Map Django status to OJS status
        status_reverse_map = {
            'DRAFT': 5,
            'SUBMITTED': 1,
            'UNDER_REVIEW': 2,
            'REVISION_REQUIRED': 2,
            'REVISION_REQUESTED': 2,
            'REVISED': 2,
            'ACCEPTANCE_REQUESTED': 1,
            'REJECTION_REQUESTED': 1,
            'ACCEPTED': 1,
            'PUBLISHED': 3,
            'REJECTED': 4,
            'WITHDRAWN': 4,
        }
        
        ojs_data = {
            'contextId': self.ojs_journal_id,
            'locale': 'en_US',
            'status': status_reverse_map.get(submission.status, 1),
            'submissionProgress': 0,
            'title': {
                'en_US': submission.title
            },
            'abstract': {
                'en_US': submission.abstract or ''
            }
        }
        
        # Add section if available
        if submission.section:
            ojs_data['sectionId'] = submission.section.id
        
        # Add authors from author_contributions
        authors = []
        for contrib in submission.author_contributions.all().order_by('order'):
            author_data = {
                'givenName': {
                    'en_US': contrib.profile.user.first_name or 'Unknown'
                },
                'familyName': {
                    'en_US': contrib.profile.user.last_name or 'Unknown'
                },
                'email': contrib.profile.user.email,
                'userGroupId': 14,  # Author group in OJS (typically 14)
                'includeInBrowse': True,
            }
            
            # Add ORCID if available
            if contrib.profile.orcid_id:
                author_data['orcid'] = f"https://orcid.org/{contrib.profile.orcid_id}"
            
            # Add affiliation if available
            if contrib.profile.affiliation_name:
                author_data['affiliation'] = {
                    'en_US': contrib.profile.affiliation_name
                }
            
            # Mark primary contact (first author or corresponding author)
            if contrib.order == 1:
                author_data['primaryContact'] = True
            
            authors.append(author_data)
        
        if authors:
            ojs_data['authors'] = authors
        
        # Add keywords if available in metadata
        if hasattr(submission, 'metadata_json') and submission.metadata_json:
            keywords = submission.metadata_json.get('keywords', [])
            if keywords:
                if isinstance(keywords, list):
                    ojs_data['keywords'] = {
                        'en_US': keywords
                    }
                elif isinstance(keywords, str):
                    ojs_data['keywords'] = {
                        'en_US': [k.strip() for k in keywords.split(',')]
                    }
        
        return ojs_data
    
    def _prepare_publication_data(self, submission):
        """
        Prepare publication data for OJS.
        A publication is required for the submission to be visible in OJS.
        
        Args:
            submission: Django Submission instance
            
        Returns:
            dict: Publication data for OJS
        """
        # Prepare authors for publication
        authors = []
        for contrib in submission.author_contributions.all().order_by('order'):
            author_data = {
                'givenName': {
                    'en_US': contrib.profile.user.first_name or 'Unknown'
                },
                'familyName': {
                    'en_US': contrib.profile.user.last_name or 'Unknown'
                },
                'email': contrib.profile.user.email,
                'userGroupId': 14,
                'includeInBrowse': True,
            }
            
            if contrib.profile.orcid_id:
                author_data['orcid'] = f"https://orcid.org/{contrib.profile.orcid_id}"
            
            if contrib.profile.affiliation_name:
                author_data['affiliation'] = {
                    'en_US': contrib.profile.affiliation_name
                }
            
            if contrib.order == 1:
                author_data['primaryContact'] = True
            
            authors.append(author_data)
        
        publication_data = {
            'title': {
                'en_US': submission.title
            },
            'abstract': {
                'en_US': submission.abstract or ''
            },
            'locale': 'en_US',
            'authors': authors,
            'status': 1,  # STATUS_QUEUED - submitted but not scheduled
            'version': 1,  # Required by OJS
        }
        
        # Add keywords if available
        if hasattr(submission, 'metadata_json') and submission.metadata_json:
            keywords = submission.metadata_json.get('keywords', [])
            if keywords:
                if isinstance(keywords, list):
                    publication_data['keywords'] = {
                        'en_US': keywords
                    }
                elif isinstance(keywords, str):
                    publication_data['keywords'] = {
                        'en_US': [k.strip() for k in keywords.split(',')]
                    }
        
        return publication_data
    
    def import_users(self):
        """
        Import users from OJS into Django database.
        Creates user accounts and profiles.
        
        Returns:
            dict: Summary with count of imported users
        """
        import requests
        from apps.users.models import CustomUser, Profile
        
        summary = {
            'total_users': 0,
            'imported': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0,
            'error_details': []
        }
        
        try:
            # Fetch users from OJS with pagination
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            
            all_users = []
            offset = 0
            count = 100
            
            while True:
                url = f"{self.api_url}/users"
                params = {'offset': offset, 'count': count}
                
                logger.info(f"Fetching users from OJS: {url} (offset {offset})")
                resp = self.session.get(url, headers=headers, params=params)
                resp.raise_for_status()
                
                data = resp.json()
                users = data.get('items', [])
                items_max = data.get('itemsMax', 0)
                
                all_users.extend(users)
                
                logger.info(f"Fetched {len(users)} users (offset {offset}), total so far: {len(all_users)}/{items_max}")
                
                # Check if we have all items
                if len(users) < count or len(all_users) >= items_max:
                    break
                
                offset += count
            
            summary['total_users'] = len(all_users)
            logger.info(f"Found {len(all_users)} total users in OJS")
            
            for ojs_user in all_users:
                try:
                    email = ojs_user.get('email', '')
                    if not email:
                        logger.warning(f"Skipping user {ojs_user.get('id')} - no email")
                        summary['skipped'] += 1
                        continue
                    
                    # Parse name from fullName
                    full_name = ojs_user.get('fullName', '')
                    name_parts = full_name.split(' ', 1)
                    first_name = name_parts[0] if name_parts else ''
                    last_name = name_parts[1] if len(name_parts) > 1 else ''
                    
                    username = ojs_user.get('userName', email.split('@')[0])
                    orcid = ojs_user.get('orcid', '')
                    
                    # Extract ORCID ID from URL if needed
                    if orcid and 'orcid.org/' in orcid:
                        orcid = orcid.split('orcid.org/')[-1]
                    
                    # Check if user already exists
                    user = CustomUser.objects.filter(email=email).first()
                    
                    if user:
                        # Update existing user
                        if not user.first_name:
                            user.first_name = first_name
                        if not user.last_name:
                            user.last_name = last_name
                        user.save()
                        
                        # Get or create profile
                        profile, _ = Profile.objects.get_or_create(
                            user=user,
                            defaults={'orcid_id': orcid if orcid else None}
                        )
                        
                        # Update ORCID if needed
                        if orcid and not profile.orcid_id:
                            profile.orcid_id = orcid
                            profile.save()
                        
                        summary['updated'] += 1
                        logger.info(f"Updated user: {email}")
                    else:
                        # Create new user without password (will need to set password later)
                        user = CustomUser.objects.create(
                            email=email,
                            username=username,
                            first_name=first_name,
                            last_name=last_name,
                            imported_from=self.journal.id,
                            email_verified=False
                        )
                        # Set unusable password for imported users
                        user.set_unusable_password()
                        user.save()
                        
                        # Create profile
                        Profile.objects.create(
                            user=user,
                            orcid_id=orcid if orcid else None
                        )
                        
                        summary['imported'] += 1
                        logger.info(f"Created user: {email} (imported from OJS, password required)")
                        
                except Exception as e:
                    error_msg = f"Error importing user {ojs_user.get('id')}: {str(e)}"
                    logger.error(error_msg)
                    summary['errors'] += 1
                    summary['error_details'].append(error_msg)
            
            logger.info(f"User import complete: {summary}")
            
        except Exception as e:
            error_msg = f"Failed to fetch users from OJS: {str(e)}"
            logger.error(error_msg)
            summary['errors'] += 1
            summary['error_details'].append(error_msg)
        
        return summary
    


def import_all_ojs_data_for_journal(journal):
    """
    Import all OJS data for a journal (users first, then submissions).
    This ensures imported submissions are properly linked to imported users.
    
    Args:
        journal: Journal instance
        
    Returns:
        dict: Combined import summary
    """
    sync_service = OJSSyncService(journal)
    
    # Import users first
    logger.info("Step 1: Importing users from OJS...")
    user_summary = sync_service.import_users()
    
    # Then import submissions (which will link to the imported users)
    logger.info("Step 2: Importing submissions from OJS...")
    submission_summary = sync_service.import_all_from_ojs()
    
    # Combine summaries
    combined_summary = {
        'users': user_summary,
        'submissions': submission_summary,
        'total_imported': {
            'users': user_summary.get('imported', 0),
            'submissions': submission_summary.get('imported', 0)
        }
    }
    
    logger.info(f"OJS import complete: {combined_summary['total_imported']}")
    return combined_summary




def sync_submission_to_ojs(submission):
    """
    Convenience function to sync a submission to OJS.
    
    Args:
        submission: Submission instance
        
    Returns:
        dict: Sync result
    """
    if not submission.journal.ojs_api_url or not submission.journal.ojs_api_key:
        return {
            'success': False,
            'error': 'OJS not configured for this journal'
        }
    
    sync_service = OJSSyncService(submission.journal)
    return sync_service.push_submission_to_ojs(submission)
