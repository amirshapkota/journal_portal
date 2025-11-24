"""
Management command to check and update expired review assignments and revision rounds.
This should be run periodically (e.g., daily via cron job or Celery beat).
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.reviews.models import ReviewAssignment, RevisionRound


class Command(BaseCommand):
    help = 'Check and update expired review assignments and revision rounds'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making any changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('Running in DRY RUN mode - no changes will be made'))
        
        # Check review assignments
        expired_assignments = ReviewAssignment.objects.filter(
            status__in=['PENDING', 'ACCEPTED'],
            due_date__lt=timezone.now()
        )
        
        assignment_count = expired_assignments.count()
        self.stdout.write(f'Found {assignment_count} expired review assignments')
        
        if not dry_run and assignment_count > 0:
            for assignment in expired_assignments:
                old_status = assignment.status
                assignment.status = 'EXPIRED'
                assignment.save()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  - Assignment {assignment.id} ({assignment.submission.title[:50]}) '
                        f'status changed from {old_status} to EXPIRED'
                    )
                )
        
        # Check revision rounds
        expired_revisions = RevisionRound.objects.filter(
            status__in=['REQUESTED', 'IN_PROGRESS'],
            deadline__lt=timezone.now()
        )
        
        revision_count = expired_revisions.count()
        self.stdout.write(f'Found {revision_count} expired revision rounds')
        
        if not dry_run and revision_count > 0:
            for revision in expired_revisions:
                old_status = revision.status
                revision.status = 'EXPIRED'
                revision.save()
                
                # Update submission status to REJECTED
                submission = revision.submission
                old_submission_status = submission.status
                submission.status = 'REJECTED'
                submission.save()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  - Revision Round {revision.id} ({revision.submission.title[:50]}) '
                        f'status changed from {old_status} to EXPIRED'
                    )
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f'    Submission status changed from {old_submission_status} to REJECTED'
                    )
                )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY RUN complete: Would have updated {assignment_count} assignments '
                    f'and {revision_count} revision rounds'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully updated {assignment_count} assignments and {revision_count} revision rounds'
                )
            )
