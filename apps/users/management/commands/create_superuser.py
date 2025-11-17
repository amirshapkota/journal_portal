"""
Django management command to create the initial superuser.

Usage: python manage.py create_superuser
"""

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from decouple import config

User = get_user_model()


class Command(BaseCommand):
    help = 'Create initial superuser for the Journal Portal'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            default=config('SUPERUSER_EMAIL', default='superadmin@journal-portal.com'),
            help='Superuser email address'
        )
        parser.add_argument(
            '--password',
            type=str,
            default=config('SUPERUSER_PASSWORD', default='admin123123'),
            help='Superuser password'
        )
        parser.add_argument(
            '--first-name',
            type=str,
            default='Admin',
            help='Superuser first name'
        )
        parser.add_argument(
            '--last-name',
            type=str,
            default='User',
            help='Superuser last name'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force creation even if user already exists (will update password)'
        )

    def handle(self, *args, **options):
        email = options['email']
        password = options['password']
        first_name = options['first_name']
        last_name = options['last_name']
        force = options['force']

        self.stdout.write(f'Creating superuser with email: {email}')

        try:
            # Check if user already exists
            if User.objects.filter(email=email).exists():
                if not force:
                    raise CommandError(
                        f'User with email {email} already exists. '
                        'Use --force to update the existing user.'
                    )
                
                # Update existing user
                user = User.objects.get(email=email)
                user.set_password(password)
                user.first_name = first_name
                user.last_name = last_name
                user.is_staff = True
                user.is_superuser = True
                user.is_active = True
                user.save()
                
                self.stdout.write(
                    self.style.WARNING(f'Updated existing superuser: {email}')
                )
            else:
                # Create new superuser
                user = User.objects.create_superuser(
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name
                )
                
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully created superuser: {email}')
                )

            # Display user info
            self.stdout.write('')
            self.stdout.write('Superuser Details:')
            self.stdout.write(f'  Email: {user.email}')
            self.stdout.write(f'  Name: {user.first_name} {user.last_name}')
            self.stdout.write(f'  ID: {user.id}')
            self.stdout.write(f'  Active: {user.is_active}')
            self.stdout.write(f'  Staff: {user.is_staff}')
            self.stdout.write(f'  Superuser: {user.is_superuser}')

        except Exception as e:
            raise CommandError(f'Error creating superuser: {str(e)}')