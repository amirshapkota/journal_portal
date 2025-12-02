"""
OJS Synchronization Service
Handles importing data from OJS and syncing submissions bidirectionally.
"""
from django.utils import timezone
from django.db import transaction
from apps.submissions.models import Submission
from apps.integrations.models import OJSMapping
from apps.integrations.utils import (
    ojs_list_submissions, ojs_create_submission, ojs_update_submission
)
import logging

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
        self.ojs_journal_id = journal.ojs_journal_id
        
        if not self.api_url or not self.api_key:
            raise ValueError("Journal does not have OJS configured")
    
    def import_all_from_ojs(self):
        """
        Import all submissions from OJS into Django database.
        Creates new Submission records with OJSMapping for tracking.
        
        Returns:
            dict: Summary of import operation
        """
        summary = {
            'total_ojs_submissions': 0,
            'imported': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0,
            'error_details': []
        }
        
        try:
            # Fetch all submissions from OJS
            logger.info(f"Fetching submissions from OJS for journal {self.journal.title}")
            data = ojs_list_submissions(self.api_url, self.api_key, journal_id=None)
            items = data.get('items', [])
            summary['total_ojs_submissions'] = data.get('itemsMax', len(items))
            
            logger.info(f"Found {len(items)} submissions to process")
            
            # Process each OJS submission
            for ojs_submission in items:
                try:
                    result = self._import_single_submission(ojs_submission)
                    if result == 'imported':
                        summary['imported'] += 1
                    elif result == 'updated':
                        summary['updated'] += 1
                    elif result == 'skipped':
                        summary['skipped'] += 1
                except Exception as e:
                    summary['errors'] += 1
                    error_msg = f"Error importing OJS ID {ojs_submission.get('id')}: {str(e)}"
                    summary['error_details'].append(error_msg)
                    logger.error(error_msg)
            
            logger.info(f"Import complete: {summary}")
            return summary
            
        except Exception as e:
            error_msg = f"Failed to fetch submissions from OJS: {str(e)}"
            summary['error_details'].append(error_msg)
            logger.error(error_msg)
            return summary
    
    @transaction.atomic
    def _import_single_submission(self, ojs_submission):
        """
        Import a single submission from OJS.
        
        Args:
            ojs_submission: OJS submission data
            
        Returns:
            str: 'imported', 'updated', or 'skipped'
        """
        ojs_id = ojs_submission.get('id')
        
        # Check if already imported
        existing_mapping = OJSMapping.objects.filter(
            ojs_submission_id=ojs_id,
            local_submission__journal=self.journal
        ).first()
        
        if existing_mapping:
            # Update existing submission
            self._update_submission_from_ojs(existing_mapping.local_submission, ojs_submission)
            existing_mapping.sync_metadata = ojs_submission
            existing_mapping.last_synced_at = timezone.now()
            existing_mapping.sync_status = 'COMPLETED'
            existing_mapping.save()
            return 'updated'
        
        # Create new submission from OJS data
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
                'Content-Type': 'application/json'
            }
            
            logger.info(f"Fetching full publication details for OJS ID {ojs_submission_id}")
            resp = requests.get(url, headers=headers)
            resp.raise_for_status()
            full_pub = resp.json()
            
            # Extract title and abstract (strip HTML tags from abstract)
            title = full_pub.get('fullTitle', {}).get('en_US', 'Untitled')
            abstract_html = full_pub.get('abstract', {}).get('en_US', '')
            
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
            
            # Create submission
            submission = Submission.objects.create(
                journal=self.journal,
                title=title[:500],  # Respect max_length
                abstract=abstract,
                status=status,
                submitted_at=submitted_at,
                # corresponding_author will be set after creating authors
            )
            
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
        Create author profiles and contributions from OJS authors data.
        
        Args:
            submission: Django Submission instance
            authors_data: List of author dictionaries from OJS
        """
        from apps.users.models import CustomUser, Profile
        from apps.submissions.models import AuthorContribution
        
        try:
            # Sort authors by sequence
            sorted_authors = sorted(authors_data, key=lambda x: x.get('seq', 999))
            
            for idx, author in enumerate(sorted_authors):
                email = author.get('email', f'author{idx}@imported.ojs')
                given_name = author.get('givenName', {}).get('en_US', '')
                family_name = author.get('familyName', {}).get('en_US', '')
                affiliation = author.get('affiliation', {}).get('en_US', '')
                orcid_raw = author.get('orcid', '')
                
                # Extract ORCID ID from URL if it's a full URL
                orcid = None
                if orcid_raw:
                    if 'orcid.org/' in orcid_raw:
                        # Extract the ID part from URL
                        orcid = orcid_raw.split('orcid.org/')[-1]
                    else:
                        orcid = orcid_raw
                
                # Create or get user
                user, user_created = CustomUser.objects.get_or_create(
                    email=email,
                    defaults={
                        'username': email,
                        'first_name': given_name,
                        'last_name': family_name,
                    }
                )
                
                # Try to find existing profile by ORCID first (since it's unique)
                profile = None
                if orcid:
                    profile = Profile.objects.filter(orcid_id=orcid).first()
                
                # If no profile found by ORCID, get or create by user
                if not profile:
                    profile, profile_created = Profile.objects.get_or_create(
                        user=user,
                        defaults={
                            'affiliation_name': affiliation,
                            'orcid_id': orcid if orcid else None,
                        }
                    )
                    
                    # Update profile if it was found (not created) and has new info
                    if not profile_created:
                        if affiliation and not profile.affiliation_name:
                            profile.affiliation_name = affiliation
                        # Only set ORCID if profile doesn't have one
                        if orcid and not profile.orcid_id:
                            profile.orcid_id = orcid
                        profile.save()
                
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
            
            logger.info(f"Created {len(sorted_authors)} authors for submission {submission.id}")
            
        except Exception as e:
            logger.error(f"Failed to create authors for submission {submission.id}: {str(e)}")
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
                'Content-Type': 'application/json'
            }
            
            files_imported = 0
            
            # Method 1: Import from submission files endpoint (all stages)
            files_url = f"{self.api_url}/submissions/{ojs_submission_id}/files"
            files_resp = requests.get(files_url, headers=headers)
            
            if files_resp.status_code == 200:
                files_data = files_resp.json()
                submission_files = files_data.get('items', [])
                
                logger.info(f"Found {len(submission_files)} files in OJS submission {ojs_submission_id}")
                
                for file_data in submission_files:
                    try:
                        file_id = file_data.get('id')
                        file_name = file_data.get('name', {}).get('en_US', f'document_{file_id}')
                        mime_type = file_data.get('mimetype', 'application/octet-stream')
                        file_stage = file_data.get('fileStage', 0)
                        
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
                        
                        # For public downloads of published files
                        base_url = self.api_url.replace('/api/v1', '')
                        
                        # Try different download methods
                        download_url = None
                        file_content = None
                        
                        # First, try to get from publication galleys (for published files)
                        sub_resp = requests.get(f"{self.api_url}/submissions/{ojs_submission_id}", headers=headers)
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
                                        break
                        
                        # If not found in galleys, file might not be publicly accessible
                        # OJS API doesn't allow downloading non-public files via API
                        if not download_url:
                            logger.warning(f"File {file_id} ({file_name}) is not publicly accessible, skipping")
                            continue
                        
                        logger.info(f"Downloading file from: {download_url}")
                        
                        # Download the file
                        file_resp = requests.get(download_url, allow_redirects=True)
                        
                        if file_resp.status_code != 200:
                            logger.warning(f"Failed to download file {file_id}: {file_resp.status_code}")
                            continue
                        
                        # Verify file is not an error page
                        if len(file_resp.content) < 1000 and b'<html' in file_resp.content.lower():
                            logger.warning(f"File {file_id} appears to be HTML, skipping")
                            continue
                        
                        file_content = file_resp.content
                        
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
                                    logger.warning(f"No creator found for document, skipping")
                                    continue
                        
                        # Check if document already exists
                        existing_doc = Document.objects.filter(
                            submission=submission,
                            file_name=file_name
                        ).first()
                        
                        if existing_doc:
                            logger.info(f"Document {file_name} already exists for submission {submission.id}")
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
                'Content-Type': 'application/json'
            }
            
            # Fetch full submission details to get review data
            url = f"{self.api_url}/submissions/{ojs_submission_id}"
            resp = requests.get(url, headers=headers)
            resp.raise_for_status()
            full_data = resp.json()
            
            # Import review assignments
            review_assignments = full_data.get('reviewAssignments', [])
            
            for ra in review_assignments:
                try:
                    # Get or create reviewer profile
                    reviewer_id = ra.get('reviewerId')
                    if not reviewer_id:
                        continue
                    
                    # Fetch reviewer details
                    user_resp = requests.get(f"{self.api_url}/users/{reviewer_id}", headers=headers)
                    if user_resp.status_code != 200:
                        continue
                    
                    user_data = user_resp.json()
                    email = user_data.get('email')
                    
                    if not email:
                        continue
                    
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
                        continue
                    
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
                    from django.utils.dateparse import parse_datetime
                    from django.utils import timezone as tz
                    from datetime import timedelta
                    
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
                        review_round=ra.get('round', 1),
                        defaults={
                            'assigned_by': assigned_by.profile,
                            'status': status,
                            'due_date': due_date,
                        }
                    )
                    
                    if created:
                        review_count += 1
                        logger.info(f"Created review assignment for submission {submission.id}, reviewer {email}")
                    
                except Exception as e:
                    logger.error(f"Error importing review assignment: {str(e)}")
                    continue
            
            return review_count
            
        except Exception as e:
            logger.error(f"Failed to import reviews for submission {ojs_submission_id}: {str(e)}")
            import traceback
            traceback.print_exc()
            return 0
    
    def _update_submission_from_ojs(self, submission, ojs_data):
        """
        Update existing submission with OJS data.
        
        Args:
            submission: Django Submission instance
            ojs_data: OJS submission data
        """
        try:
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
            
            logger.info(f"Updated submission {submission.id} from OJS")
            
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
                
                # Update mapping
                mapping.last_synced_at = timezone.now()
                mapping.sync_status = 'COMPLETED'
                mapping.sync_metadata = response
                mapping.save()
                
            except OJSMapping.DoesNotExist:
                # Create new OJS submission
                result['action'] = 'create'
                ojs_data = self._prepare_ojs_data(submission)
                response = ojs_create_submission(
                    self.api_url,
                    self.api_key,
                    ojs_data
                )
                result['success'] = True
                result['ojs_id'] = response.get('id')
                
                # Create mapping
                OJSMapping.objects.create(
                    local_submission=submission,
                    ojs_submission_id=str(result['ojs_id']),
                    sync_direction='TO_OJS',
                    sync_status='COMPLETED',
                    last_synced_at=timezone.now(),
                    sync_metadata=response
                )
            
            logger.info(f"Pushed submission {submission.id} to OJS: {result['action']}")
            return result
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Failed to push submission {submission.id} to OJS: {str(e)}")
            return result
    
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
            'ACCEPTED': 1,
            'PUBLISHED': 3,
            'REJECTED': 4,
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
                'en_US': submission.abstract
            }
        }
        
        # Add section if available
        if submission.section:
            ojs_data['sectionId'] = submission.section.id
        
        return ojs_data
    
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
            # Fetch users from OJS
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            url = f"{self.api_url}/users"
            logger.info(f"Fetching users from OJS: {url}")
            resp = requests.get(url, headers=headers)
            resp.raise_for_status()
            
            data = resp.json()
            users = data.get('items', [])
            summary['total_users'] = len(users)
            
            logger.info(f"Found {len(users)} users in OJS")
            
            for ojs_user in users:
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
                        # Create new user
                        user = CustomUser.objects.create(
                            email=email,
                            username=username,
                            first_name=first_name,
                            last_name=last_name,
                        )
                        
                        # Create profile
                        Profile.objects.create(
                            user=user,
                            orcid_id=orcid if orcid else None
                        )
                        
                        summary['imported'] += 1
                        logger.info(f"Created user: {email}")
                        
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
    


def import_ojs_data_for_journal(journal):
    """
    Convenience function to import all OJS data for a journal.
    
    Args:
        journal: Journal instance
        
    Returns:
        dict: Import summary
    """
    sync_service = OJSSyncService(journal)
    return sync_service.import_all_from_ojs()


def import_users_from_ojs(journal):
    """
    Import users from OJS into Django database.
    
    Args:
        journal: Journal instance with OJS configuration
        
    Returns:
        dict: Summary of import operation
    """
    sync_service = OJSSyncService(journal)
    return sync_service.import_users()




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
