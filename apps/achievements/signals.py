"""
Signals for achievements app - auto-award badges based on user activities.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Count
from django.utils import timezone

from apps.reviews.models import ReviewAssignment
from apps.submissions.models import Submission
from .models import Badge, UserBadge


@receiver(post_save, sender=ReviewAssignment)
def check_reviewer_badges(sender, instance, created, **kwargs):
    """Check and award reviewer badges when a review is completed."""
    if instance.status != 'COMPLETED':
        return
    
    # Only process if completed_at was recently set (within last 10 seconds)
    # This prevents re-processing when updating other fields of completed assignments
    if instance.completed_at:
        time_since_completion = (timezone.now() - instance.completed_at).total_seconds()
        if time_since_completion > 10:
            return
    
    reviewer_profile = instance.reviewer
    current_year = timezone.now().year
    
    # Count total completed reviews for this reviewer this year
    reviews_this_year = ReviewAssignment.objects.filter(
        reviewer=reviewer_profile,
        status='COMPLETED',
        completed_at__year=current_year
    ).count()
    
    # Define badge thresholds
    badge_thresholds = [
        (1, 'BRONZE', '1st Review Complete'),
        (5, 'BRONZE', '5 Reviews Complete'),
        (10, 'SILVER', '10 Reviews Complete'),
        (25, 'GOLD', '25 Reviews Complete'),
        (50, 'PLATINUM', '50 Reviews Complete'),
        (100, 'DIAMOND', '100 Reviews Complete'),
    ]
    
    # Award appropriate badges
    for threshold, level, badge_name in badge_thresholds:
        if reviews_this_year >= threshold:
            # Try to find or create the badge
            badge, _ = Badge.objects.get_or_create(
                name=badge_name,
                badge_type='REVIEWER',
                defaults={
                    'description': f'Awarded for completing {threshold} review(s)',
                    'level': level,
                    'criteria': {'reviews_completed': threshold},
                    'points': threshold * 10,
                }
            )
            
            # Award to user if not already awarded this year
            UserBadge.objects.get_or_create(
                profile=reviewer_profile,
                badge=badge,
                year=current_year,
                journal=instance.submission.journal,
                defaults={
                    'achievement_data': {
                        'reviews_completed': reviews_this_year,
                        'awarded_for': f'Completing {threshold} reviews'
                    }
                }
            )


@receiver(post_save, sender=Submission)
def check_author_badges(sender, instance, created, **kwargs):
    """Check and award author badges when a submission is accepted/published."""
    if instance.status not in ['ACCEPTED', 'PUBLISHED']:
        return
    
    # Skip if no corresponding author (e.g., OJS imports or null author cases)
    if not instance.corresponding_author:
        return
    
    author_profile = instance.corresponding_author
    current_year = timezone.now().year
    
    # Count total published submissions for this author this year
    publications_this_year = Submission.objects.filter(
        corresponding_author=author_profile,
        status__in=['ACCEPTED', 'PUBLISHED'],
        created_at__year=current_year
    ).count()
    
    # Define badge thresholds
    badge_thresholds = [
        (1, 'BRONZE', '1st Publication'),
        (3, 'SILVER', '3 Publications'),
        (5, 'GOLD', '5 Publications'),
        (10, 'PLATINUM', '10 Publications'),
        (20, 'DIAMOND', '20 Publications'),
    ]
    
    # Award appropriate badges
    for threshold, level, badge_name in badge_thresholds:
        if publications_this_year >= threshold:
            # Try to find or create the badge
            badge, _ = Badge.objects.get_or_create(
                name=badge_name,
                badge_type='AUTHOR',
                defaults={
                    'description': f'Awarded for {threshold} publication(s)',
                    'level': level,
                    'criteria': {'publications': threshold},
                    'points': threshold * 20,
                }
            )
            
            # Award to user if not already awarded this year
            UserBadge.objects.get_or_create(
                profile=author_profile,
                badge=badge,
                year=current_year,
                journal=instance.journal,
                defaults={
                    'achievement_data': {
                        'publications': publications_this_year,
                        'awarded_for': f'{threshold} publication(s)'
                    }
                }
            )
