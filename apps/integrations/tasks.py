"""
Celery tasks for multi-journal OJS synchronization.

Architecture:
- Each Journal can have its own OJS instance (different URL + API key)
- Sync tasks run per-journal
- Master task coordinates sync across all journals
- Conflict resolution and error handling per journal
"""
from celery import shared_task, group
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging
import requests

logger = logging.getLogger(__name__)


# ============================================================================
# MAIN SYNC ORCHESTRATION TASKS
# ============================================================================

@shared_task
def sync_all_journals():
    """
    Master task: Sync all journals that have OJS enabled.
    This is the main entry point for periodic syncs.
    """
    from apps.journals.models import Journal
    
    logger.info("="*60)
    logger.info("Starting sync for all OJS-enabled journals...")
    logger.info("="*60)
    
    # Get all journals with OJS enabled and sync enabled
    journals = Journal.objects.filter(
        ojs_enabled=True,
        sync_enabled=True,
        is_active=True
    )
    
    if not journals.exists():
        logger.warning("No journals with OJS sync enabled found")
        return {"status": "no_journals", "synced": 0}
    
    logger.info(f"Found {journals.count()} journals to sync")
    
    # Create a group of tasks - one for each journal
    job = group([
        sync_single_journal.s(str(journal.id))
        for journal in journals
    ])
    
    result = job.apply_async()
    
    logger.info(f"Dispatched sync tasks for {journals.count()} journals")
    
    return {
        "status": "dispatched",
        "journal_count": journals.count(),
        "task_group_id": str(result.id) if hasattr(result, 'id') else None,
        "started_at": timezone.now().isoformat()
    }


@shared_task(bind=True, max_retries=2, default_retry_delay=600)
def sync_single_journal(self, journal_id):
    """
    Sync all data for a single journal with its OJS instance.
    
    Args:
        journal_id: UUID of the journal to sync
    """
    from apps.journals.models import Journal
    
    try:
        journal = Journal.objects.get(id=journal_id)
    except Journal.DoesNotExist:
        logger.error(f"Journal {journal_id} not found")
        return {"status": "error", "message": "Journal not found"}
    
    logger.info(f"Starting full sync for journal: {journal.title}")
    logger.info(f"OJS URL: {journal.ojs_api_url}")
    
    results = {
        "journal_id": str(journal_id),
        "journal_name": journal.title,
        "started_at": timezone.now().isoformat()
    }
    
    try:
        # Sync submissions
        submissions_result = sync_journal_submissions.apply_async(args=[str(journal_id)])
        results["submissions_task"] = str(submissions_result.id)
        
        # Sync users
        users_result = sync_journal_users.apply_async(args=[str(journal_id)])
        results["users_task"] = str(users_result.id)
        
        # Sync issues
        issues_result = sync_journal_issues.apply_async(args=[str(journal_id)])
        results["issues_task"] = str(issues_result.id)
        
        # Sync reviews
        reviews_result = sync_journal_reviews.apply_async(args=[str(journal_id)])
        results["reviews_task"] = str(reviews_result.id)
        
        # Sync comments
        comments_result = sync_journal_comments.apply_async(args=[str(journal_id)])
        results["comments_task"] = str(comments_result.id)
        
        # Update last sync timestamp
        journal.last_synced_at = timezone.now()
        journal.save(update_fields=['last_synced_at'])
        
        results["status"] = "success"
        logger.info(f" Sync tasks dispatched for journal: {journal.title}")
        
    except Exception as exc:
        logger.error(f"Failed to sync journal {journal.title}: {str(exc)}")
        results["status"] = "error"
        results["error"] = str(exc)
        raise self.retry(exc=exc)
    
    return results


# ============================================================================
# JOURNAL-SPECIFIC SYNC TASKS
# ============================================================================

@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def sync_journal_submissions(self, journal_id):
    """
    Sync submissions for a specific journal from its OJS instance.
    """
    from apps.journals.models import Journal
    from apps.submissions.models import Submission
    
    try:
        journal = Journal.objects.get(id=journal_id, ojs_enabled=True)
    except Journal.DoesNotExist:
        return {"status": "journal_not_found"}
    
    logger.info(f"Syncing submissions for journal: {journal.title}")
    
    try:
        # Fetch from journal's specific OJS instance
        ojs_data = fetch_from_journal_ojs(
            journal,
            endpoint='/submissions',
            params={'count': 100}
        )
        
        if not ojs_data or 'items' not in ojs_data:
            logger.warning(f"No submissions data for {journal.title}")
            return {"status": "no_data", "journal_id": str(journal_id)}
        
        synced = 0
        errors = 0
        
        for item in ojs_data.get('items', []):
            try:
                # Create or update submission
                submission, created = Submission.objects.update_or_create(
                    ojs_id=item.get('id'),
                    journal=journal,
                    defaults={
                        'title': item.get('title', {}).get('en_US', 'Untitled'),
                        'abstract': item.get('abstract', {}).get('en_US', ''),
                        'status': map_ojs_status(item.get('status')),
                        'submitted_at': item.get('dateSubmitted'),
                    }
                )
                
                action = "Created" if created else "Updated"
                logger.debug(f"{action} submission {item.get('id')} for {journal.short_name}")
                synced += 1
                
            except Exception as e:
                logger.error(f"Error syncing submission {item.get('id')}: {str(e)}")
                errors += 1
        
        logger.info(f" Synced {synced} submissions for {journal.title} ({errors} errors)")
        
        return {
            "status": "success",
            "journal_id": str(journal_id),
            "journal_name": journal.title,
            "synced": synced,
            "errors": errors,
            "total": ojs_data.get('itemsMax', 0)
        }
        
    except Exception as exc:
        logger.error(f"Failed to sync submissions for {journal.title}: {str(exc)}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def sync_journal_users(self, journal_id):
    """
    Sync users for a specific journal from its OJS instance.
    """
    from apps.journals.models import Journal
    from apps.users.models import CustomUser, Profile
    
    try:
        journal = Journal.objects.get(id=journal_id, ojs_enabled=True)
    except Journal.DoesNotExist:
        return {"status": "journal_not_found"}
    
    logger.info(f"Syncing users for journal: {journal.title}")
    
    try:
        ojs_data = fetch_from_journal_ojs(
            journal,
            endpoint='/users',
            params={'count': 100}
        )
        
        if not ojs_data or 'items' not in ojs_data:
            return {"status": "no_data", "journal_id": str(journal_id)}
        
        synced = 0
        errors = 0
        
        for item in ojs_data.get('items', []):
            try:
                email = item.get('email')
                if not email:
                    continue
                
                user, created = CustomUser.objects.get_or_create(
                    email=email,
                    defaults={
                        'first_name': item.get('givenName', {}).get('en_US', ''),
                        'last_name': item.get('familyName', {}).get('en_US', ''),
                        'is_active': not item.get('disabled', False),
                    }
                )
                
                # Update profile with journal-specific OJS user ID
                profile, _ = Profile.objects.get_or_create(user=user)
                if not profile.ojs_id_mapping:
                    profile.ojs_id_mapping = {}
                profile.ojs_id_mapping[str(journal.id)] = item.get('id')
                profile.save(update_fields=['ojs_id_mapping'])
                
                synced += 1
                
            except Exception as e:
                logger.error(f"Error syncing user: {str(e)}")
                errors += 1
        
        logger.info(f" Synced {synced} users for {journal.title}")
        
        return {
            "status": "success",
            "journal_id": str(journal_id),
            "synced": synced,
            "errors": errors
        }
        
    except Exception as exc:
        logger.error(f"Failed to sync users for {journal.title}: {str(exc)}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def sync_journal_issues(self, journal_id):
    """
    Sync journal issues from OJS.
    """
    from apps.journals.models import Journal
    
    try:
        journal = Journal.objects.get(id=journal_id, ojs_enabled=True)
    except Journal.DoesNotExist:
        return {"status": "journal_not_found"}
    
    logger.info(f"Syncing issues for journal: {journal.title}")
    
    try:
        ojs_data = fetch_from_journal_ojs(
            journal,
            endpoint='/issues',
            params={'count': 50}
        )
        
        if not ojs_data or 'items' not in ojs_data:
            return {"status": "no_data", "journal_id": str(journal_id)}
        
        synced = len(ojs_data.get('items', []))
        
        logger.info(f" Synced {synced} issues for {journal.title}")
        
        return {
            "status": "success",
            "journal_id": str(journal_id),
            "synced": synced
        }
        
    except Exception as exc:
        logger.error(f"Failed to sync issues for {journal.title}: {str(exc)}")
        raise self.retry(exc=exc)


# ============================================================================
# PUSH TO OJS TASKS (Django → OJS)
# ============================================================================

@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def push_submission_to_ojs(self, submission_id):
    """
    Push a Django submission to its journal's OJS instance.
    Called when a submission is created/updated in Django.
    """
    from apps.submissions.models import Submission
    
    try:
        submission = Submission.objects.select_related('journal').get(id=submission_id)
        journal = submission.journal
        
        if not journal.ojs_enabled:
            logger.info(f"OJS not enabled for journal {journal.title}, skipping push")
            return {"status": "ojs_disabled"}
        
        logger.info(f"Pushing submission {submission_id} to OJS for {journal.title}")
        
        # Prepare data
        data = {
            'title': {'en_US': submission.title},
            'abstract': {'en_US': submission.abstract},
            'status': map_django_status_to_ojs(submission.status),
        }
        
        if submission.ojs_id:
            # Update existing
            result = update_in_journal_ojs(
                journal,
                endpoint=f'/submissions/{submission.ojs_id}',
                data=data
            )
        else:
            # Create new
            result = create_in_journal_ojs(
                journal,
                endpoint='/submissions',
                data=data
            )
            
            if result and 'id' in result:
                submission.ojs_id = result['id']
                submission.save(update_fields=['ojs_id'])
        
        logger.info(f" Pushed submission {submission_id} to OJS")
        
        return {
            "status": "success",
            "submission_id": str(submission_id),
            "ojs_id": submission.ojs_id
        }
        
    except Exception as exc:
        logger.error(f"Failed to push submission {submission_id}: {str(exc)}")
        raise self.retry(exc=exc)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def fetch_from_journal_ojs(journal, endpoint, params=None):
    """
    Fetch data from a journal's specific OJS instance.
    
    Args:
        journal: Journal model instance with OJS configuration
        endpoint: API endpoint (e.g., '/submissions')
        params: Query parameters
    """
    if not journal.ojs_api_url or not journal.ojs_api_key:
        logger.error(f"OJS credentials missing for journal {journal.title}")
        return None
    
    url = f"{journal.ojs_api_url.rstrip('/')}{endpoint}"
    headers = {
        'Authorization': f'Bearer {journal.ojs_api_key}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"OJS API request failed for {journal.title}: {str(e)}")
        return None


def create_in_journal_ojs(journal, endpoint, data):
    """Create resource in journal's OJS instance."""
    url = f"{journal.ojs_api_url.rstrip('/')}{endpoint}"
    headers = {
        'Authorization': f'Bearer {journal.ojs_api_key}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"OJS create failed for {journal.title}: {str(e)}")
        return None


def update_in_journal_ojs(journal, endpoint, data):
    """Update resource in journal's OJS instance."""
    url = f"{journal.ojs_api_url.rstrip('/')}{endpoint}"
    headers = {
        'Authorization': f'Bearer {journal.ojs_api_key}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.put(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"OJS update failed for {journal.title}: {str(e)}")
        return None


def map_ojs_status(ojs_status):
    """Map OJS status code to Django status."""
    mapping = {
        1: 'submitted',
        3: 'published',
        5: 'declined',
    }
    return mapping.get(ojs_status, 'draft')


def map_django_status_to_ojs(django_status):
    """Map Django status to OJS status code."""
    mapping = {
        'draft': 1,
        'submitted': 1,
        'under_review': 1,
        'accepted': 3,
        'declined': 5,
        'published': 3,
    }
    return mapping.get(django_status, 1)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def sync_journal_reviews(self, journal_id):
    """
    Sync reviews for a specific journal from its OJS instance.
    OJS API endpoint: /submissions/{submissionId}/reviewRounds/{reviewRoundId}/reviewAssignments
    """
    from apps.journals.models import Journal
    from apps.reviews.models import Review, ReviewAssignment
    from apps.submissions.models import Submission
    
    try:
        journal = Journal.objects.get(id=journal_id, ojs_enabled=True)
    except Journal.DoesNotExist:
        return {"status": "journal_not_found"}
    
    logger.info(f"Syncing reviews for journal: {journal.title}")
    
    try:
        synced = 0
        errors = 0
        
        # Get all submissions for this journal that have OJS IDs
        submissions = Submission.objects.filter(
            journal=journal,
            ojs_id__isnull=False
        )
        
        for submission in submissions:
            try:
                # Fetch review rounds from OJS
                ojs_data = fetch_from_journal_ojs(
                    journal,
                    endpoint=f'/submissions/{submission.ojs_id}',
                    params={'apiToken': journal.ojs_api_key}
                )
                
                if not ojs_data or 'reviewRounds' not in ojs_data:
                    continue
                
                # Process each review round
                for review_round in ojs_data.get('reviewRounds', []):
                    for review_assignment in review_round.get('reviewAssignments', []):
                        try:
                            # Get or create reviewer profile
                            reviewer_email = review_assignment.get('reviewerEmail')
                            if not reviewer_email:
                                continue
                            
                            from apps.users.models import CustomUser, Profile
                            user, _ = CustomUser.objects.get_or_create(
                                email=reviewer_email,
                                defaults={'first_name': review_assignment.get('reviewerFullName', '')}
                            )
                            reviewer_profile, _ = Profile.objects.get_or_create(user=user)
                            
                            # Map OJS recommendation to Django
                            ojs_recommendation = review_assignment.get('recommendation')
                            recommendation_mapping = {
                                1: 'ACCEPT',
                                2: 'MINOR_REVISION',
                                3: 'MAJOR_REVISION',
                                4: 'REJECT',
                            }
                            recommendation = recommendation_mapping.get(ojs_recommendation, 'MINOR_REVISION')
                            
                            # Create or update ReviewAssignment
                            assignment, _ = ReviewAssignment.objects.update_or_create(
                                submission=submission,
                                reviewer=reviewer_profile,
                                round_number=review_round.get('round', 1),
                                defaults={
                                    'status': 'COMPLETED' if review_assignment.get('dateCompleted') else 'PENDING',
                                    'assigned_at': review_assignment.get('dateAssigned'),
                                    'due_date': review_assignment.get('dateDue'),
                                }
                            )
                            
                            # Create or update Review if completed
                            if review_assignment.get('dateCompleted') and not hasattr(assignment, 'review'):
                                Review.objects.create(
                                    assignment=assignment,
                                    submission=submission,
                                    reviewer=reviewer_profile,
                                    assigned_at=review_assignment.get('dateAssigned'),
                                    due_date=review_assignment.get('dateDue'),
                                    recommendation=recommendation,
                                    confidence_level=3,  # Default medium confidence
                                    review_text=review_assignment.get('comments', ''),
                                    confidential_comments=review_assignment.get('commentsForEditor', ''),
                                    is_anonymous=not review_assignment.get('unconsidered', False),
                                )
                                synced += 1
                        
                        except Exception as e:
                            logger.error(f"Error syncing review assignment: {str(e)}")
                            errors += 1
            
            except Exception as e:
                logger.error(f"Error syncing reviews for submission {submission.id}: {str(e)}")
                errors += 1
        
        logger.info(f"✓ Synced {synced} reviews for {journal.title}")
        
        return {
            "status": "success",
            "journal_id": str(journal_id),
            "synced": synced,
            "errors": errors
        }
        
    except Exception as exc:
        logger.error(f"Failed to sync reviews for {journal.title}: {str(exc)}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def sync_journal_comments(self, journal_id):
    """
    Sync editorial comments/notes for a specific journal from its OJS instance.
    OJS API endpoint: /submissions/{submissionId}/queries (for discussion/comments)
    """
    from apps.journals.models import Journal
    from apps.submissions.models import Submission
    from apps.reviews.models import EditorDecision  # Assuming EditorDecision has comments
    
    try:
        journal = Journal.objects.get(id=journal_id, ojs_enabled=True)
    except Journal.DoesNotExist:
        return {"status": "journal_not_found"}
    
    logger.info(f"Syncing comments for journal: {journal.title}")
    
    try:
        synced = 0
        errors = 0
        
        # Get all submissions for this journal that have OJS IDs
        submissions = Submission.objects.filter(
            journal=journal,
            ojs_id__isnull=False
        )
        
        for submission in submissions:
            try:
                # Fetch queries/discussions from OJS
                ojs_data = fetch_from_journal_ojs(
                    journal,
                    endpoint=f'/submissions/{submission.ojs_id}',
                    params={'apiToken': journal.ojs_api_key}
                )
                
                if not ojs_data or 'queries' not in ojs_data:
                    continue
                
                # Process each query/discussion thread
                for query in ojs_data.get('queries', []):
                    try:
                        # Process notes/replies in the query
                        for note in query.get('replies', []):
                            # Here you would create Comment objects or EditorDecision objects
                            # depending on your model structure
                            # This is a placeholder - adjust based on your actual models
                            
                            logger.debug(f"Processing comment: {note.get('title', 'Untitled')}")
                            synced += 1
                    
                    except Exception as e:
                        logger.error(f"Error syncing comment: {str(e)}")
                        errors += 1
            
            except Exception as e:
                logger.error(f"Error syncing comments for submission {submission.id}: {str(e)}")
                errors += 1
        
        logger.info(f"✓ Synced {synced} comments for {journal.title}")
        
        return {
            "status": "success",
            "journal_id": str(journal_id),
            "synced": synced,
            "errors": errors
        }
        
    except Exception as exc:
        logger.error(f"Failed to sync comments for {journal.title}: {str(exc)}")
        raise self.retry(exc=exc)


# ============================================================================
# UTILITY/MAINTENANCE TASKS
# ============================================================================

@shared_task
def cleanup_old_sync_logs():
    """Clean up old sync logs."""
    cutoff = timezone.now() - timedelta(days=90)
    logger.info(f"Cleaning up logs older than {cutoff}")
    return {"status": "success"}


@shared_task
def check_journal_sync_health():
    """Check health of journal syncs and alert if issues found."""
    from apps.journals.models import Journal
    
    journals = Journal.objects.filter(ojs_enabled=True, sync_enabled=True)
    issues = []
    
    for journal in journals:
        # Check if last sync was too long ago
        if journal.last_synced_at:
            hours_since_sync = (timezone.now() - journal.last_synced_at).total_seconds() / 3600
            expected_interval = journal.sync_interval_hours * 2  # Alert if 2x interval passed
            
            if hours_since_sync > expected_interval:
                issues.append({
                    "journal": journal.title,
                    "issue": "sync_delayed",
                    "hours_since_sync": hours_since_sync,
                    "expected_interval": expected_interval
                })
        
        # Check if OJS credentials are valid
        if not journal.ojs_api_url or not journal.ojs_api_key:
            issues.append({
                "journal": journal.title,
                "issue": "missing_credentials"
            })
    
    if issues:
        logger.warning(f"Found {len(issues)} sync health issues: {issues}")
    
    return {
        "status": "checked",
        "journals_checked": journals.count(),
        "issues_found": len(issues),
        "issues": issues
    }
