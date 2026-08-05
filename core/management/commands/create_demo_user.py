"""
Management command: create_demo_user
Creates a superuser account for demo/investor access.

There is no default password: one must be supplied explicitly, either via
--password or via the DEMO_USER_PASSWORD environment variable. The password is
never echoed back to the terminal.

Usage:
    DEMO_USER_PASSWORD=... python manage.py create_demo_user
    python manage.py create_demo_user --username investor --password ...
    python manage.py create_demo_user --reset   # delete and recreate

The user can then sign in at /login/ and access the full ESG platform.
"""
import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError


DEFAULT_USERNAME = 'demo'


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
            default=None,
            help='Password for the demo account. Required — falls back to the '
                 'DEMO_USER_PASSWORD environment variable. No default.',
        )
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete the existing user with this username before creating a fresh one.',
        )

    def handle(self, *args, **options):
        username = options['username']
        password = options['password'] or os.environ.get('DEMO_USER_PASSWORD', '')

        if not password:
            raise CommandError(
                'No password supplied. Pass --password or set the '
                'DEMO_USER_PASSWORD environment variable — this command has '
                'no default password.'
            )

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
            f'     Password : (not shown — the value you supplied)\n'
            f'     Login at : /login/\n'
            f'     Admin at : /admin/\n'
        ))
