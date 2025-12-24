"""
Management command to manually update leaderboards.
"""
from django.core.management.base import BaseCommand
from apps.achievements.tasks import update_leaderboards


class Command(BaseCommand):
    help = 'Manually update leaderboards for reviewers and authors'

    def handle(self, *args, **options):
        self.stdout.write('Starting leaderboard update...')
        
        try:
            result = update_leaderboards()
            
            self.stdout.write(self.style.SUCCESS(
                f'\nLeaderboard update completed successfully!'
            ))
            self.stdout.write(f'  - Reviewer leaderboard entries: {result["reviewer_leaderboards"]}')
            self.stdout.write(f'  - Author leaderboard entries: {result["author_leaderboards"]}')
            self.stdout.write(f'  - Total entries: {result["total"]}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f'Failed to update leaderboards: {str(e)}'
            ))
            raise
