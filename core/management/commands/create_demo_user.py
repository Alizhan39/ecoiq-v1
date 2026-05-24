"""
Management command: create_demo_user
Creates a superuser account for demo/investor access.

Usage:
    python manage.py create_demo_user
    python manage.py create_demo_user --username investor --password Demo2025!
    python manage.py create_demo_user --reset   # delete and recreate

The user can then sign in at /login/ and access the full ESG platform.
"""
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


DEFAULT_USERNAME = 'demo'
DEFAULT_PASSWORD = 'EcoIQ-Demo-2025!'


class Command(BaseCommand):
    help = 'Create (or reset) a demo superuser for investor / pilot access.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            default=DEFAULT_USERNAME,
            help=f'Username for the demo account (default: {DEFAULT_USERNAME})',
        )
        parser.add_argument(
            '--password',
            default=DEFAULT_PASSWORD,
            help=f'Password for the demo account (default: {DEFAULT_PASSWORD})',
        )
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete the existing user with this username before creating a fresh one.',
        )

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']

        if options['reset']:
            deleted, _ = User.objects.filter(username=username).delete()
            if deleted:
                self.stdout.write(self.style.WARNING(
                    f'Deleted existing user "{username}".'
                ))

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(
                f'User "{username}" already exists. '
                f'Use --reset to recreate, or --username to choose a different name.'
            ))
            return

        User.objects.create_superuser(
            username=username,
            email=f'{username}@ecoiq.uk',
            password=password,
        )

        self.stdout.write(self.style.SUCCESS(
            f'\n  ✓  Demo superuser created\n'
            f'     Username : {username}\n'
            f'     Password : {password}\n'
            f'     Login at : /login/\n'
            f'     Admin at : /admin/\n'
        ))
        if password == DEFAULT_PASSWORD:
            self.stdout.write(self.style.WARNING(
                '  ⚠  Using the default password — change it in production.'
            ))
