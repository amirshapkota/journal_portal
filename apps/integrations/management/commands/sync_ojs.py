"""Management command to manually sync OJS data for multiple journals."""
from django.core.management.base import BaseCommand
from django.db import models
from apps.journals.models import Journal
from apps.integrations.tasks import (
    sync_all_journals,
    sync_single_journal,
    sync_journal_submissions,
    sync_journal_users,
    sync_journal_issues,
    sync_journal_reviews,
    sync_journal_comments,
    check_journal_sync_health,
)


class Command(BaseCommand):
    help = 'Manually trigger OJS synchronization tasks for journals'

    def add_arguments(self, parser):
        parser.add_argument(
            '--journal',
            type=str,
            help='Journal short_name or ID to sync (default: all journals)'
        )
        parser.add_argument(
            '--type',
            type=str,
            default='all',
            choices=['all', 'submissions', 'users', 'issues', 'reviews', 'comments'],
            help='Type of sync to perform (default: all)'
        )
        parser.add_argument(
            '--async',
            action='store_true',
            help='Run tasks asynchronously (requires Celery worker running)'
        )
        parser.add_argument(
            '--health-check',
            action='store_true',
            help='Check health of journal syncs'
        )

    def handle(self, *args, **options):
        # Health check
        if options['health_check']:
            self.stdout.write(self.style.WARNING('Checking journal sync health...'))
            result = check_journal_sync_health()
            
            self.stdout.write(f"Journals checked: {result['journals_checked']}")
            self.stdout.write(f"Issues found: {result['issues_found']}")
            
            if result['issues']:
                for issue in result['issues']:
                    self.stdout.write(self.style.ERROR(f"  ⚠ {issue['journal']}: {issue['issue']}"))
            else:
                self.stdout.write(self.style.SUCCESS('✓ All journals healthy'))
            
            return
        
        sync_type = options['type']
        run_async = options['async']
        journal_filter = options.get('journal')

        # Get journals to sync
        if journal_filter:
            try:
                journal = Journal.objects.get(
                    models.Q(short_name=journal_filter) | models.Q(id=journal_filter),
                    ojs_enabled=True
                )
                journals = [journal]
                self.stdout.write(self.style.SUCCESS(f'Syncing journal: {journal.title}'))
            except Journal.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Journal not found or OJS not enabled: {journal_filter}'))
                return
        else:
            journals = Journal.objects.filter(ojs_enabled=True, is_active=True)
            self.stdout.write(self.style.SUCCESS(f'Syncing {journals.count()} journals'))

        # Sync journals
        if not journal_filter:
            # Sync all journals at once
            if run_async:
                result = sync_all_journals.delay()
                self.stdout.write(self.style.SUCCESS(f'Sync task queued: {result.id}'))
            else:
                result = sync_all_journals()
                self.stdout.write(self.style.SUCCESS(f'Result: {result}'))
        else:
            # Sync specific journal
            journal = journals[0]
            journal_id = str(journal.id)
            
            if sync_type == 'all':
                if run_async:
                    result = sync_single_journal.delay(journal_id)
                    self.stdout.write(self.style.SUCCESS(f'Full sync task queued: {result.id}'))
                else:
                    result = sync_single_journal(journal_id)
                    self.stdout.write(self.style.SUCCESS(f'Result: {result}'))
            
            elif sync_type == 'submissions':
                if run_async:
                    result = sync_journal_submissions.delay(journal_id)
                    self.stdout.write(self.style.SUCCESS(f'Submissions sync task queued: {result.id}'))
                else:
                    result = sync_journal_submissions(journal_id)
                    self.stdout.write(self.style.SUCCESS(f'Result: {result}'))
            
            elif sync_type == 'users':
                if run_async:
                    result = sync_journal_users.delay(journal_id)
                    self.stdout.write(self.style.SUCCESS(f'Users sync task queued: {result.id}'))
                else:
                    result = sync_journal_users(journal_id)
                    self.stdout.write(self.style.SUCCESS(f'Result: {result}'))
            
            elif sync_type == 'issues':
                if run_async:
                    result = sync_journal_issues.delay(journal_id)
                    self.stdout.write(self.style.SUCCESS(f'Issues sync task queued: {result.id}'))
                else:
                    result = sync_journal_issues(journal_id)
                    self.stdout.write(self.style.SUCCESS(f'Result: {result}'))
            
            elif sync_type == 'reviews':
                if run_async:
                    result = sync_journal_reviews.delay(journal_id)
                    self.stdout.write(self.style.SUCCESS(f'Reviews sync task queued: {result.id}'))
                else:
                    result = sync_journal_reviews(journal_id)
                    self.stdout.write(self.style.SUCCESS(f'Result: {result}'))
            
            elif sync_type == 'comments':
                if run_async:
                    result = sync_journal_comments.delay(journal_id)
                    self.stdout.write(self.style.SUCCESS(f'Comments sync task queued: {result.id}'))
                else:
                    result = sync_journal_comments(journal_id)
                    self.stdout.write(self.style.SUCCESS(f'Result: {result}'))

        self.stdout.write(self.style.SUCCESS('✓ Sync command completed'))
