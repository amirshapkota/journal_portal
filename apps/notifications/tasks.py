"""
Celery tasks for email notifications.
Handles async email sending with retry logic.
"""
from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def send_email_task(self, email_log_id):
    """
    Send an email using the EmailLog record.
    Retries up to 3 times with 5 minute delays.
    """
    from apps.notifications.models import EmailLog
    
    try:
        email_log = EmailLog.objects.get(id=email_log_id)
        
        # Create email message
        email = EmailMultiAlternatives(
            subject=email_log.subject,
            body=email_log.body_text or '',
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email_log.recipient],
        )
        
        # Add HTML version if available
        if email_log.body_html:
            email.attach_alternative(email_log.body_html, "text/html")
        
        # Send email
        email.send(fail_silently=False)
        
        # Update log
        email_log.status = 'SENT'
        email_log.sent_at = timezone.now()
        email_log.save()
        
        logger.info(f"Email sent successfully to {email_log.recipient} (template: {email_log.template_type})")
        
        return {
            'status': 'success',
            'email_log_id': str(email_log_id),
            'recipient': email_log.recipient
        }
        
    except EmailLog.DoesNotExist:
        logger.error(f"EmailLog {email_log_id} not found")
        return {'status': 'error', 'message': 'EmailLog not found'}
    
    except Exception as exc:
        logger.error(f"Failed to send email {email_log_id}: {exc}")
        
        # Update log with error
        try:
            email_log = EmailLog.objects.get(id=email_log_id)
            email_log.retry_count += 1
            email_log.error_message = str(exc)
            
            if email_log.retry_count >= email_log.max_retries:
                email_log.status = 'FAILED'
                logger.error(f"Email {email_log_id} failed after {email_log.retry_count} retries")
            else:
                email_log.status = 'PENDING'
            
            email_log.save()
        except:
            pass
        
        # Retry task
        raise self.retry(exc=exc)


@shared_task
def send_template_email(recipient, template_type, context, user_id=None):
    """
    Send an email using a template.
    
    Args:
        recipient: Email address
        template_type: Type of email template to use
        context: Dictionary of template variables
        user_id: Optional user ID (for preference checking)
    """
    from apps.notifications.models import EmailTemplate, EmailLog, EmailNotificationPreference
    from django.contrib.auth import get_user_model
    
    CustomUser = get_user_model()
    
    try:
        # Check user preferences if user_id provided
        if user_id:
            try:
                user = CustomUser.objects.get(id=user_id)
                prefs, _ = EmailNotificationPreference.objects.get_or_create(user=user)
                
                # Check if notifications are globally disabled
                if not prefs.email_notifications_enabled:
                    logger.info(f"Email notifications disabled for user {user.email}")
                    return {'status': 'skipped', 'reason': 'notifications_disabled'}
                
                # Check specific preference based on template type
                preference_map = {
                    'ORCID_CONNECTED': 'email_on_orcid_connected',
                    'ORCID_DISCONNECTED': 'email_on_orcid_disconnected',
                    'VERIFICATION_SUBMITTED': 'email_on_verification_submitted',
                    'VERIFICATION_APPROVED': 'email_on_verification_approved',
                    'VERIFICATION_REJECTED': 'email_on_verification_rejected',
                    'VERIFICATION_INFO_REQUESTED': 'email_on_verification_info_requested',
                }
                
                pref_field = preference_map.get(template_type)
                if pref_field and not getattr(prefs, pref_field, True):
                    logger.info(f"Email type {template_type} disabled for user {user.email}")
                    return {'status': 'skipped', 'reason': 'preference_disabled'}
                    
            except CustomUser.DoesNotExist:
                pass
        
        # Get template
        template = EmailTemplate.objects.get(
            template_type=template_type,
            is_active=True
        )
        
        # Render subject and body
        from django.template import Template, Context
        
        subject_template = Template(template.subject)
        subject = subject_template.render(Context(context))
        
        html_template = Template(template.html_body)
        html_body = html_template.render(Context(context))
        
        # Generate text body if not provided
        if template.text_body:
            text_template = Template(template.text_body)
            text_body = text_template.render(Context(context))
        else:
            # Strip HTML for text version
            from django.utils.html import strip_tags
            text_body = strip_tags(html_body)
        
        # Create email log
        email_log = EmailLog.objects.create(
            recipient=recipient,
            user_id=user_id,
            template_type=template_type,
            subject=subject,
            body_html=html_body,
            body_text=text_body,
            context_data=context,
            status='PENDING'
        )
        
        # Try to queue email for sending with Celery, fallback to direct send
        try:
            send_email_task.delay(str(email_log.id))
            logger.info(f"Email queued: {template_type} to {recipient}")
            return {
                'status': 'queued',
                'email_log_id': str(email_log.id),
                'recipient': recipient,
                'template_type': template_type
            }
        except Exception as celery_exc:
            # Celery not available (Redis not running), send directly
            logger.warning(f"Celery not available, sending email directly: {celery_exc}")
            try:
                from django.core.mail import send_mail
                send_mail(
                    subject,
                    text_body,
                    settings.DEFAULT_FROM_EMAIL,
                    [recipient],
                    html_message=html_body,
                    fail_silently=False,
                )
                email_log.status = 'SENT'
                email_log.save()
                logger.info(f"Email sent directly: {template_type} to {recipient}")
                return {
                    'status': 'sent',
                    'email_log_id': str(email_log.id),
                    'recipient': recipient,
                    'template_type': template_type
                }
            except Exception as send_exc:
                email_log.status = 'FAILED'
                email_log.error_message = str(send_exc)
                email_log.save()
                logger.error(f"Failed to send email directly: {send_exc}")
                raise
        
    except EmailTemplate.DoesNotExist:
        logger.error(f"Email template {template_type} not found")
        return {'status': 'error', 'message': f'Template {template_type} not found'}
    
    except Exception as exc:
        logger.error(f"Error sending template email: {exc}")
        return {'status': 'error', 'message': str(exc)}


@shared_task
def send_verification_submitted_email(user_id, verification_request_id):
    """Send email when verification request is submitted."""
    from django.contrib.auth import get_user_model
    from apps.users.models import VerificationRequest
    
    CustomUser = get_user_model()
    
    try:
        user = CustomUser.objects.get(id=user_id)
        verification_request = VerificationRequest.objects.get(id=verification_request_id)
        
        context = {
            'user_name': user.profile.display_name or user.email,
            'requested_role': verification_request.get_requested_role_display(),
            'auto_score': verification_request.auto_score,
            'request_id': str(verification_request.id),
            'site_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://127.0.0.1:8000',
        }
        
        return send_template_email(
            recipient=user.email,
            template_type='VERIFICATION_SUBMITTED',
            context=context,
            user_id=str(user_id)
        )
    
    except Exception as exc:
        logger.error(f"Error sending verification submitted email: {exc}")
        return {'status': 'error', 'message': str(exc)}


@shared_task
def send_verification_approved_email(user_id, verification_request_id):
    """Send email when verification is approved."""
    from django.contrib.auth import get_user_model
    from apps.users.models import VerificationRequest
    
    CustomUser = get_user_model()
    
    try:
        user = CustomUser.objects.get(id=user_id)
        verification_request = VerificationRequest.objects.get(id=verification_request_id)
        
        context = {
            'user_name': user.profile.display_name or user.email,
            'requested_role': verification_request.get_requested_role_display(),
            'approved_date': verification_request.reviewed_at.strftime('%B %d, %Y') if verification_request.reviewed_at else 'today',
            'site_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://127.0.0.1:8000',
        }
        
        return send_template_email(
            recipient=user.email,
            template_type='VERIFICATION_APPROVED',
            context=context,
            user_id=str(user_id)
        )
    
    except Exception as exc:
        logger.error(f"Error sending verification approved email: {exc}")
        return {'status': 'error', 'message': str(exc)}


@shared_task
def send_verification_rejected_email(user_id, verification_request_id):
    """Send email when verification is rejected."""
    from django.contrib.auth import get_user_model
    from apps.users.models import VerificationRequest
    
    CustomUser = get_user_model()
    
    try:
        user = CustomUser.objects.get(id=user_id)
        verification_request = VerificationRequest.objects.get(id=verification_request_id)
        
        context = {
            'user_name': user.profile.display_name or user.email,
            'requested_role': verification_request.get_requested_role_display(),
            'rejection_reason': verification_request.rejection_reason,
            'site_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://127.0.0.1:8000',
        }
        
        return send_template_email(
            recipient=user.email,
            template_type='VERIFICATION_REJECTED',
            context=context,
            user_id=str(user_id)
        )
    
    except Exception as exc:
        logger.error(f"Error sending verification rejected email: {exc}")
        return {'status': 'error', 'message': str(exc)}


@shared_task
def send_verification_info_requested_email(user_id, verification_request_id):
    """Send email when admin requests additional information."""
    from django.contrib.auth import get_user_model
    from apps.users.models import VerificationRequest
    
    CustomUser = get_user_model()
    
    try:
        user = CustomUser.objects.get(id=user_id)
        verification_request = VerificationRequest.objects.get(id=verification_request_id)
        
        context = {
            'user_name': user.profile.display_name or user.email,
            'requested_role': verification_request.get_requested_role_display(),
            'additional_info_requested': verification_request.additional_info_requested,
            'request_id': str(verification_request.id),
            'site_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://127.0.0.1:8000',
        }
        
        return send_template_email(
            recipient=user.email,
            template_type='VERIFICATION_INFO_REQUESTED',
            context=context,
            user_id=str(user_id)
        )
    
    except Exception as exc:
        logger.error(f"Error sending verification info requested email: {exc}")
        return {'status': 'error', 'message': str(exc)}


@shared_task
def send_orcid_connected_email(user_id, orcid_id):
    """Send email when ORCID is connected."""
    from django.contrib.auth import get_user_model
    
    CustomUser = get_user_model()
    
    try:
        user = CustomUser.objects.get(id=user_id)
        
        context = {
            'user_name': user.profile.display_name or user.email,
            'orcid_id': orcid_id,
            'orcid_url': f'https://orcid.org/{orcid_id}',
            'site_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://127.0.0.1:8000',
        }
        
        return send_template_email(
            recipient=user.email,
            template_type='ORCID_CONNECTED',
            context=context,
            user_id=str(user_id)
        )
    
    except Exception as exc:
        logger.error(f"Error sending ORCID connected email: {exc}")
        return {'status': 'error', 'message': str(exc)}


@shared_task
def send_email_verification_email(user_id, verification_url):
    """Send email verification link to new user."""
    from django.contrib.auth import get_user_model
    
    CustomUser = get_user_model()
    
    try:
        user = CustomUser.objects.get(id=user_id)
        
        context = {
            'user_name': user.get_full_name() or user.email,
            'user_email': user.email,
            'verification_url': verification_url,
            'site_name': 'Journal Publication Portal',
            'site_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://127.0.0.1:8000',
        }
        
        return send_template_email(
            recipient=user.email,
            template_type='EMAIL_VERIFICATION',
            context=context,
            user_id=str(user_id)
        )
    
    except Exception as exc:
        logger.error(f"Error sending email verification email: {exc}")
        return {'status': 'error', 'message': str(exc)}


@shared_task
def send_password_reset_email(user_id, reset_url):
    """Send password reset link to user."""
    from django.contrib.auth import get_user_model
    
    CustomUser = get_user_model()
    
    try:
        user = CustomUser.objects.get(id=user_id)
        
        context = {
            'user_name': user.get_full_name() or user.email,
            'user_email': user.email,
            'reset_url': reset_url,
            'site_name': 'Journal Publication Portal',
            'site_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://127.0.0.1:8000',
        }
        
        return send_template_email(
            recipient=user.email,
            template_type='PASSWORD_RESET',
            context=context,
            user_id=str(user_id)
        )
    
    except Exception as exc:
        logger.error(f"Error sending password reset email: {exc}")
        return {'status': 'error', 'message': str(exc)}


# Phase 4: Review System Email Tasks

@shared_task
def send_review_invitation_email(assignment_id):
    """Send review invitation email to reviewer."""
    from apps.reviews.models import ReviewAssignment
    
    try:
        assignment = ReviewAssignment.objects.select_related(
            'reviewer__user', 'submission', 'assigned_by'
        ).get(id=assignment_id)
        
        reviewer = assignment.reviewer.user
        submission = assignment.submission
        
        # Format author list
        authors = [submission.corresponding_author.user.get_full_name()]
        authors += [co.user.get_full_name() for co in submission.coauthors.all()]
        submission_authors = ', '.join(authors)
        
        context = {
            'reviewer_name': reviewer.get_full_name() or reviewer.email,
            'journal_name': 'Journal Publication Portal',
            'submission_title': submission.title,
            'submission_authors': submission_authors,
            'submission_keywords': '',  # Keywords not stored in Submission model
            'submission_abstract': submission.abstract[:300] + '...' if len(submission.abstract) > 300 else submission.abstract,
            'due_date': assignment.due_date.strftime('%B %d, %Y') if assignment.due_date else 'TBD',
            'accept_url': f"{settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://127.0.0.1:8000'}/api/v1/reviews/assignments/{assignment.id}/accept/",
            'decline_url': f"{settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://127.0.0.1:8000'}/api/v1/reviews/assignments/{assignment.id}/decline/",
            'editor_name': assignment.assigned_by.get_full_name() if assignment.assigned_by else 'Editorial Team',
        }
        
        return send_template_email(
            recipient=reviewer.email,
            template_type='REVIEW_INVITATION',
            context=context,
            user_id=str(reviewer.id)
        )
    
    except Exception as exc:
        logger.error(f"Error sending review invitation email: {exc}")
        return {'status': 'error', 'message': str(exc)}


@shared_task
def send_review_reminder_email(assignment_id):
    """Send review deadline reminder email."""
    from apps.reviews.models import ReviewAssignment
    from django.utils import timezone
    
    try:
        assignment = ReviewAssignment.objects.select_related(
            'reviewer__user', 'submission', 'assigned_by'
        ).get(id=assignment_id)
        
        reviewer = assignment.reviewer.user
        submission = assignment.submission
        
        # Calculate days remaining
        days_remaining = (assignment.due_date - timezone.now().date()).days if assignment.due_date else 0
        
        context = {
            'reviewer_name': reviewer.get_full_name() or reviewer.email,
            'journal_name': 'Journal Publication Portal',
            'submission_title': submission.title,
            'due_date': assignment.due_date.strftime('%B %d, %Y') if assignment.due_date else 'TBD',
            'days_remaining': max(0, days_remaining),
            'assigned_date': assignment.invited_at.strftime('%B %d, %Y'),
            'review_url': f"{settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://127.0.0.1:8000'}/api/v1/reviews/reviews/?assignment_id={assignment.id}",
            'editor_name': assignment.assigned_by.get_full_name() if assignment.assigned_by else 'Editorial Team',
            'editor_email': assignment.assigned_by.email if assignment.assigned_by else settings.DEFAULT_FROM_EMAIL,
        }
        
        return send_template_email(
            recipient=reviewer.email,
            template_type='REVIEW_REMINDER',
            context=context,
            user_id=str(reviewer.id)
        )
    
    except Exception as exc:
        logger.error(f"Error sending review reminder email: {exc}")
        return {'status': 'error', 'message': str(exc)}


@shared_task
def send_review_submitted_email(review_id):
    """Send review submission confirmation email."""
    from apps.reviews.models import Review
    from django.utils import timezone
    
    try:
        review = Review.objects.select_related(
            'reviewer__user', 'submission', 'assignment'
        ).get(id=review_id)
        
        reviewer = review.reviewer.user
        submission = review.submission
        
        # Calculate completion time
        if review.assigned_at and review.submitted_at:
            completion_days = (review.submitted_at.date() - review.assigned_at.date()).days
        else:
            completion_days = 0
        
        # Calculate average score
        scores = review.scores if hasattr(review, 'scores') and review.scores else {}
        avg_score = sum(scores.values()) / len(scores) if scores else 0
        
        # Map recommendation to CSS class
        recommendation_classes = {
            'ACCEPT': 'accept',
            'MINOR_REVISION': 'minor',
            'MAJOR_REVISION': 'major',
            'REJECT': 'reject'
        }
        
        context = {
            'reviewer_name': reviewer.get_full_name() or reviewer.email,
            'reviewer_email': reviewer.email,
            'journal_name': 'Journal Publication Portal',
            'submission_title': submission.title,
            'submitted_at': review.submitted_at.strftime('%B %d, %Y at %I:%M %p'),
            'recommendation': review.get_recommendation_display(),
            'recommendation_class': recommendation_classes.get(review.recommendation, 'minor'),
            'confidence_level': review.get_confidence_display(),
            'completion_days': completion_days,
            'average_score': f"{avg_score:.1f}",
            'dashboard_url': f"{settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://127.0.0.1:8000'}/api/v1/reviews/reviews/my_reviews/",
        }
        
        return send_template_email(
            recipient=reviewer.email,
            template_type='REVIEW_SUBMITTED',
            context=context,
            user_id=str(reviewer.id)
        )
    
    except Exception as exc:
        logger.error(f"Error sending review submitted email: {exc}")
        return {'status': 'error', 'message': str(exc)}


@shared_task
def send_editorial_decision_email(submission_id, decision_type, editor_comments, additional_context=None):
    """
    Send editorial decision email to author.
    
    Args:
        submission_id: UUID of the submission
        decision_type: 'ACCEPT', 'REJECT', or 'REVISION'
        editor_comments: Editor's comments
        additional_context: Additional context variables (dict)
    """
    from apps.submissions.models import Submission
    
    try:
        submission = Submission.objects.select_related('author__user').get(id=submission_id)
        author = submission.author.user
        
        # Map decision type to template
        template_map = {
            'ACCEPT': 'EDITORIAL_DECISION_ACCEPT',
            'REJECT': 'EDITORIAL_DECISION_REJECT',
            'REVISION': 'REVISION_REQUESTED',
        }
        
        template_type = template_map.get(decision_type)
        if not template_type:
            raise ValueError(f"Invalid decision type: {decision_type}")
        
        # Base context
        context = {
            'author_name': author.get_full_name() or author.email,
            'author_email': author.email,
            'journal_name': 'Journal Publication Portal',
            'submission_title': submission.title,
            'submission_date': submission.created_at.strftime('%B %d, %Y'),
            'decision_date': timezone.now().strftime('%B %d, %Y'),
            'editor_comments': editor_comments,
            'editor_name': 'Editorial Team',  # TODO: Get from submission or editor
            'manuscript_url': f"{settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://127.0.0.1:8000'}/api/v1/submissions/{submission.id}/",
        }
        
        # Add review statistics
        from apps.reviews.models import Review
        reviews = Review.objects.filter(submission=submission)
        context['review_count'] = reviews.count()
        
        if reviews.exists():
            first_review = reviews.order_by('submitted_at').first()
            review_duration = (timezone.now() - submission.created_at).days
            context['review_duration'] = review_duration
        else:
            context['review_duration'] = 0
        
        # Merge additional context
        if additional_context:
            context.update(additional_context)
        
        return send_template_email(
            recipient=author.email,
            template_type=template_type,
            context=context,
            user_id=str(author.id)
        )
    
    except Exception as exc:
        logger.error(f"Error sending editorial decision email: {exc}")
        return {'status': 'error', 'message': str(exc)}


# Phase 4.3: Editorial Decision Making Email Tasks

@shared_task
def send_decision_letter_email(decision_id):
    """
    Send editorial decision letter to author.
    Uses the rendered decision letter from the decision record.
    """
    from apps.reviews.models import EditorialDecision
    
    try:
        decision = EditorialDecision.objects.select_related(
            'submission__corresponding_author__user',
            'decided_by__user',
            'letter_template'
        ).get(id=decision_id)
        
        author = decision.submission.corresponding_author.user
        
        # Map decision type to template type
        template_map = {
            'ACCEPT': 'DECISION_ACCEPT',
            'REJECT': 'DECISION_REJECT',
            'MINOR_REVISION': 'DECISION_MINOR_REVISION',
            'MAJOR_REVISION': 'DECISION_MAJOR_REVISION',
        }
        
        template_type = template_map.get(decision.decision_type)
        if not template_type:
            logger.error(f"Unknown decision type: {decision.decision_type}")
            return {'status': 'error', 'message': 'Unknown decision type'}
        
        # Calculate review statistics
        from apps.reviews.models import Review
        reviews = Review.objects.filter(submission=decision.submission, is_published=True)
        
        recommendation_counts = {}
        for review in reviews:
            rec = review.get_recommendation_display()
            recommendation_counts[rec] = recommendation_counts.get(rec, 0) + 1
        
        # Format reviews summary
        reviews_summary_text = []
        for rec, count in recommendation_counts.items():
            reviews_summary_text.append(f"{count} reviewer(s) recommended: {rec}")
        
        context = {
            'author_name': author.get_full_name() or author.email,
            'submission_title': decision.submission.title,
            'submission_id': str(decision.submission.id),
            'decision_type': decision.get_decision_type_display(),
            'decision_date': decision.decision_date.strftime('%B %d, %Y'),
            'decision_letter': decision.decision_letter,
            'editor_name': decision.decided_by.user.get_full_name() if decision.decided_by else 'Editorial Team',
            'editor_email': decision.decided_by.user.email if decision.decided_by else settings.DEFAULT_FROM_EMAIL,
            'review_count': reviews.count(),
            'reviews_summary': decision.reviews_summary or {},
            'reviews_summary_text': '\n'.join(reviews_summary_text),
            'revision_deadline': decision.revision_deadline.strftime('%B %d, %Y') if decision.revision_deadline else None,
            'revision_deadline_days': (decision.revision_deadline.date() - timezone.now().date()).days if decision.revision_deadline else 0,
            'dashboard_url': f"{settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://127.0.0.1:8000'}/dashboard/submissions/",
            'submission_url': f"{settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://127.0.0.1:8000'}/api/v1/submissions/{decision.submission.id}/",
        }
        
        return send_template_email(
            recipient=author.email,
            template_type=template_type,
            context=context,
            user_id=str(author.id)
        )
    
    except Exception as exc:
        logger.error(f"Error sending decision letter email: {exc}")
        return {'status': 'error', 'message': str(exc)}


@shared_task
def send_revision_request_email(revision_round_id):
    """
    Send revision request email to author.
    Notifies author that revisions are required.
    """
    from apps.reviews.models import RevisionRound
    
    try:
        revision = RevisionRound.objects.select_related(
            'submission__corresponding_author__user',
            'editorial_decision__decided_by__user',
            'editorial_decision__letter_template'
        ).prefetch_related('reassigned_reviewers__user').get(id=revision_round_id)
        
        author = revision.submission.corresponding_author.user
        decision = revision.editorial_decision
        
        # Determine revision type
        revision_type = 'Major' if decision.decision_type == 'MAJOR_REVISION' else 'Minor'
        
        # Format reassigned reviewers if any
        reassigned_reviewers_list = []
        if revision.reassigned_reviewers.exists():
            for reviewer_profile in revision.reassigned_reviewers.all():
                reassigned_reviewers_list.append(reviewer_profile.user.get_full_name() or reviewer_profile.user.email)
        
        context = {
            'author_name': author.get_full_name() or author.email,
            'submission_title': revision.submission.title,
            'submission_id': str(revision.submission.id),
            'revision_type': revision_type,
            'round_number': revision.round_number,
            'revision_requirements': revision.revision_requirements,
            'deadline': revision.deadline.strftime('%B %d, %Y') if revision.deadline else 'TBD',
            'days_to_deadline': revision.days_remaining() if revision.deadline else 0,
            'editor_name': decision.decided_by.user.get_full_name() if decision.decided_by else 'Editorial Team',
            'editor_email': decision.decided_by.user.email if decision.decided_by else settings.DEFAULT_FROM_EMAIL,
            'decision_letter': decision.decision_letter,
            'reassigned_reviewers': ', '.join(reassigned_reviewers_list) if reassigned_reviewers_list else None,
            'reviewer_comments_included': revision.reviewer_comments_included,
            'revision_url': f"{settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://127.0.0.1:8000'}/api/v1/reviews/revisions/{revision.id}/",
            'dashboard_url': f"{settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://127.0.0.1:8000'}/dashboard/revisions/",
        }
        
        return send_template_email(
            recipient=author.email,
            template_type='REVISION_REQUEST',
            context=context,
            user_id=str(author.id)
        )
    
    except Exception as exc:
        logger.error(f"Error sending revision request email: {exc}")
        return {'status': 'error', 'message': str(exc)}


@shared_task
def send_revision_submitted_notification(revision_round_id):
    """
    Send notification to editor when author submits revised manuscript.
    """
    from apps.reviews.models import RevisionRound
    
    try:
        revision = RevisionRound.objects.select_related(
            'submission__corresponding_author__user',
            'editorial_decision__decided_by__user',
            'revised_manuscript',
            'response_letter'
        ).get(id=revision_round_id)
        
        # Get editor email
        editor = revision.editorial_decision.decided_by
        if not editor:
            logger.warning(f"No editor assigned for revision {revision_round_id}")
            return {'status': 'skipped', 'reason': 'no_editor'}
        
        author = revision.submission.corresponding_author.user
        
        # Calculate submission time
        if revision.requested_at and revision.submitted_at:
            submission_days = (revision.submitted_at.date() - revision.requested_at.date()).days
        else:
            submission_days = 0
        
        context = {
            'editor_name': editor.user.get_full_name() or editor.user.email,
            'author_name': author.get_full_name() or author.email,
            'author_email': author.email,
            'submission_title': revision.submission.title,
            'submission_id': str(revision.submission.id),
            'round_number': revision.round_number,
            'submitted_at': revision.submitted_at.strftime('%B %d, %Y at %I:%M %p') if revision.submitted_at else 'recently',
            'deadline': revision.deadline.strftime('%B %d, %Y') if revision.deadline else 'TBD',
            'submitted_on_time': not revision.is_overdue() if revision.deadline else True,
            'submission_days': submission_days,
            'author_notes': revision.author_notes or 'No notes provided',
            'has_revised_manuscript': revision.revised_manuscript is not None,
            'has_response_letter': revision.response_letter is not None,
            'revision_url': f"{settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://127.0.0.1:8000'}/api/v1/reviews/revisions/{revision.id}/",
            'dashboard_url': f"{settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://127.0.0.1:8000'}/dashboard/editorial/",
        }
        
        return send_template_email(
            recipient=editor.user.email,
            template_type='REVISION_SUBMITTED',
            context=context,
            user_id=str(editor.user.id)
        )
    
    except Exception as exc:
        logger.error(f"Error sending revision submitted notification: {exc}")
        return {'status': 'error', 'message': str(exc)}


@shared_task
def send_revision_approved_email(revision_round_id):
    """
    Send notification to author when revised manuscript is approved.
    """
    from apps.reviews.models import RevisionRound
    
    try:
        revision = RevisionRound.objects.select_related(
            'submission__corresponding_author__user',
            'editorial_decision__decided_by__user'
        ).get(id=revision_round_id)
        
        author = revision.submission.corresponding_author.user
        editor = revision.editorial_decision.decided_by
        
        context = {
            'author_name': author.get_full_name() or author.email,
            'submission_title': revision.submission.title,
            'submission_id': str(revision.submission.id),
            'round_number': revision.round_number,
            'approved_at': timezone.now().strftime('%B %d, %Y'),
            'editor_name': editor.user.get_full_name() if editor else 'Editorial Team',
            'editor_email': editor.user.email if editor else settings.DEFAULT_FROM_EMAIL,
            'next_steps': 'Your revised manuscript will now proceed to the next stage of editorial review.',
            'dashboard_url': f"{settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://127.0.0.1:8000'}/dashboard/submissions/",
        }
        
        return send_template_email(
            recipient=author.email,
            template_type='REVISION_APPROVED',
            context=context,
            user_id=str(author.id)
        )
    
    except Exception as exc:
        logger.error(f"Error sending revision approved email: {exc}")
        return {'status': 'error', 'message': str(exc)}


@shared_task
def send_revision_rejected_email(revision_round_id):
    """
    Send notification to author when revised manuscript is rejected.
    """
    from apps.reviews.models import RevisionRound
    
    try:
        revision = RevisionRound.objects.select_related(
            'submission__corresponding_author__user',
            'editorial_decision__decided_by__user'
        ).get(id=revision_round_id)
        
        author = revision.submission.corresponding_author.user
        editor = revision.editorial_decision.decided_by
        
        context = {
            'author_name': author.get_full_name() or author.email,
            'submission_title': revision.submission.title,
            'submission_id': str(revision.submission.id),
            'round_number': revision.round_number,
            'rejected_at': timezone.now().strftime('%B %d, %Y'),
            'editor_name': editor.user.get_full_name() if editor else 'Editorial Team',
            'editor_email': editor.user.email if editor else settings.DEFAULT_FROM_EMAIL,
            'rejection_reason': 'The revisions did not adequately address the concerns raised during the review process.',
            'dashboard_url': f"{settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://127.0.0.1:8000'}/dashboard/submissions/",
        }
        
        return send_template_email(
            recipient=author.email,
            template_type='REVISION_REJECTED',
            context=context,
            user_id=str(author.id)
        )
    
    except Exception as exc:
        logger.error(f"Error sending revision rejected email: {exc}")
        return {'status': 'error', 'message': str(exc)}
