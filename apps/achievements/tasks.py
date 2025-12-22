"""
Celery tasks for achievements - automatic leaderboard and award updates.
"""
from celery import shared_task
from django.db.models import Count, Avg, F, Q
from django.utils import timezone
from datetime import date, timedelta
import logging

logger = logging.getLogger(__name__)


def _generate_certificate_for_award(award):
    """
    Helper function to generate certificate for an award.
    """
    from apps.achievements.models import Certificate
    
    # Check if certificate already exists
    if Certificate.objects.filter(award=award).exists():
        logger.info(f'Certificate already exists for award {award.id}')
        return
    
    try:
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
                'award_type_display': award.get_award_type_display(),
                'year': award.year,
                'citation': award.citation,
                'metrics': award.metrics
            }
        )
        
        # Mark award as having certificate
        award.certificate_generated = True
        award.save(update_fields=['certificate_generated'])
        
        logger.info(f'Generated certificate {certificate.certificate_number} for award {award.id}')
        return certificate
        
    except Exception as e:
        logger.error(f'Failed to generate certificate for award {award.id}: {e}')
        return None


@shared_task
def update_leaderboards():
    """
    Update all leaderboards - runs daily.
    Calculates rankings for reviewers and authors.
    """
    from apps.achievements.models import Leaderboard
    from apps.reviews.models import ReviewAssignment
    from apps.submissions.models import Submission
    from apps.users.models import Profile
    
    logger.info('Starting automatic leaderboard update...')
    
    # Clear existing leaderboards
    deleted_count = Leaderboard.objects.all().delete()[0]
    logger.info(f'Cleared {deleted_count} existing leaderboard entries')
    
    current_year = timezone.now().year
    year_start = date(current_year, 1, 1)
    year_end = date(current_year, 12, 31)
    
    # Calculate reviewer leaderboards
    reviewer_stats = ReviewAssignment.objects.filter(
        status='COMPLETED',
        completed_at__year=current_year
    ).values('reviewer').annotate(
        reviews_count=Count('id'),
    ).order_by('-reviews_count')
    
    reviewer_count = 0
    for idx, stats in enumerate(reviewer_stats[:100], start=1):  # Top 100
        try:
            profile = Profile.objects.get(id=stats['reviewer'])
            
            Leaderboard.objects.create(
                profile=profile,
                category='REVIEWER',
                period='YEARLY',
                rank=idx,
                score=float(stats['reviews_count'] * 10),
                metrics={
                    'reviews_completed': stats['reviews_count'],
                },
                period_start=year_start,
                period_end=year_end
            )
            reviewer_count += 1
        except Profile.DoesNotExist:
            logger.warning(f"Profile not found for reviewer ID: {stats['reviewer']}")
            continue
    
    logger.info(f'Created {reviewer_count} reviewer leaderboard entries')
    
    # Calculate author leaderboards
    author_stats = Submission.objects.filter(
        status__in=['ACCEPTED', 'PUBLISHED'],
        created_at__year=current_year
    ).values('corresponding_author').annotate(
        publications_count=Count('id'),
    ).order_by('-publications_count')
    
    author_count = 0
    for idx, stats in enumerate(author_stats[:100], start=1):  # Top 100
        if not stats['corresponding_author']:
            continue
            
        try:
            profile = Profile.objects.get(id=stats['corresponding_author'])
            
            Leaderboard.objects.create(
                profile=profile,
                category='AUTHOR',
                period='YEARLY',
                rank=idx,
                score=float(stats['publications_count'] * 20),
                metrics={
                    'publications': stats['publications_count'],
                },
                period_start=year_start,
                period_end=year_end
            )
            author_count += 1
        except Profile.DoesNotExist:
            logger.warning(f"Profile not found for author ID: {stats['corresponding_author']}")
            continue
    
    logger.info(f'Created {author_count} author leaderboard entries')
    logger.info(f'Leaderboard update complete. Total entries: {reviewer_count + author_count}')
    
    return {
        'reviewer_leaderboards': reviewer_count,
        'author_leaderboards': author_count,
        'total': reviewer_count + author_count
    }


@shared_task
def generate_yearly_awards():
    """
    Generate awards for the previous year - runs annually on January 1st.
    Creates best reviewer and researcher of year awards for each journal.
    """
    from apps.achievements.models import Award
    from apps.reviews.models import ReviewAssignment
    from apps.submissions.models import Submission
    from apps.users.models import Profile
    from apps.journals.models import Journal
    
    logger.info('Starting automatic yearly award generation...')
    
    # Previous year
    previous_year = timezone.now().year - 1
    
    awards_created = 0
    
    # Generate best reviewer awards for each journal
    for journal in Journal.objects.filter(is_active=True):
        try:
            # Find best reviewer for this journal in previous year
            reviewer_stats = ReviewAssignment.objects.filter(
                submission__journal=journal,
                status='COMPLETED',
                completed_at__year=previous_year
            ).values('reviewer').annotate(
                reviews_count=Count('id'),
            ).order_by('-reviews_count').first()
            
            if reviewer_stats and reviewer_stats['reviews_count'] >= 5:  # Minimum 5 reviews
                profile = Profile.objects.get(id=reviewer_stats['reviewer'])
                
                award, created = Award.objects.get_or_create(
                    award_type='BEST_REVIEWER',
                    year=previous_year,
                    journal=journal,
                    defaults={
                        'title': f'Best Reviewer {previous_year}',
                        'description': f'Outstanding contribution to peer review for {journal.title}',
                        'recipient': profile,
                        'citation': f'Recognized for completing {reviewer_stats["reviews_count"]} reviews with excellence',
                        'metrics': {
                            'reviews_completed': reviewer_stats['reviews_count'],
                        }
                    }
                )
                
                if created:
                    awards_created += 1
                    logger.info(f'Created Best Reviewer award for {profile.user.email} at {journal.title}')
                    
                    # Auto-generate certificate for the award
                    _generate_certificate_for_award(award)
        
        except Exception as e:
            logger.error(f'Error creating best reviewer award for {journal.name}: {e}')
            continue
    
    # Generate researcher of year awards for each journal
    for journal in Journal.objects.filter(is_active=True):
        try:
            # Find top author for this journal in previous year
            author_stats = Submission.objects.filter(
                journal=journal,
                status__in=['ACCEPTED', 'PUBLISHED'],
                created_at__year=previous_year
            ).values('corresponding_author').annotate(
                publications_count=Count('id'),
            ).order_by('-publications_count').first()
            
            if author_stats and author_stats['publications_count'] >= 3:  # Minimum 3 publications
                profile = Profile.objects.get(id=author_stats['corresponding_author'])
                
                award, created = Award.objects.get_or_create(
                    award_type='RESEARCHER_OF_YEAR',
                    year=previous_year,
                    journal=journal,
                    defaults={
                        'title': f'Researcher of the Year {previous_year}',
                        'description': f'Most prolific researcher for {journal.title}',
                        'recipient': profile,
                        'citation': f'Recognized for {author_stats["publications_count"]} publications',
                        'metrics': {
                            'publications': author_stats['publications_count'],
                        }
                    }
                )
                
                if created:
                    awards_created += 1
                    logger.info(f'Created Researcher of Year award for {profile.user.email} at {journal.title}')
                    
                    # Auto-generate certificate for the award
                    _generate_certificate_for_award(award)
        
        except Exception as e:
            logger.error(f'Error creating researcher of year award for {journal.name}: {e}')
            continue
    
    logger.info(f'Yearly award generation complete. Created {awards_created} awards')
    
    return {
        'awards_created': awards_created,
        'year': previous_year
    }


@shared_task
def generate_monthly_awards():
    """
    Generate monthly awards - runs on the 1st of each month.
    Awards excellence in review and top contributor badges.
    """
    from apps.achievements.models import Award
    from apps.reviews.models import ReviewAssignment
    from apps.submissions.models import Submission
    from apps.users.models import Profile
    from apps.journals.models import Journal
    
    logger.info('Starting automatic monthly award generation...')
    
    # Previous month
    today = timezone.now().date()
    first_of_this_month = today.replace(day=1)
    last_month = first_of_this_month - timedelta(days=1)
    first_of_last_month = last_month.replace(day=1)
    
    awards_created = 0
    
    # Generate excellence in review awards for outstanding reviewers
    for journal in Journal.objects.filter(is_active=True):
        try:
            # Find reviewers who completed reviews with high quality last month
            reviewer_stats = ReviewAssignment.objects.filter(
                submission__journal=journal,
                status='COMPLETED',
                completed_at__gte=first_of_last_month,
                completed_at__lt=first_of_this_month
            ).values('reviewer').annotate(
                reviews_count=Count('id'),
            ).order_by('-reviews_count').first()
            
            if reviewer_stats and reviewer_stats['reviews_count'] >= 3:  # Minimum 3 reviews in a month
                profile = Profile.objects.get(id=reviewer_stats['reviewer'])
                
                award, created = Award.objects.get_or_create(
                    award_type='EXCELLENCE_REVIEW',
                    year=last_month.year,
                    journal=journal,
                    recipient=profile,
                    defaults={
                        'title': f'Excellence in Review - {last_month.strftime("%B %Y")}',
                        'description': f'Outstanding review performance for {journal.title}',
                        'citation': f'Completed {reviewer_stats["reviews_count"]} exceptional reviews',
                        'metrics': {
                            'reviews_completed': reviewer_stats['reviews_count'],
                            'month': last_month.month,
                        }
                    }
                )
                
                if created:
                    awards_created += 1
                    logger.info(f'Created Excellence Review award for {profile.user.email} at {journal.title}')
                    
                    # Auto-generate certificate for the award
                    _generate_certificate_for_award(award)
        
        except Exception as e:
            logger.error(f'Error creating excellence review award for {journal.name}: {e}')
            continue
    
    logger.info(f'Monthly award generation complete. Created {awards_created} awards')
    
    return {
        'awards_created': awards_created,
        'month': last_month.strftime('%B %Y')
    }
