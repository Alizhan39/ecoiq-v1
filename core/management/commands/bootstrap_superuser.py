"""
Management command: bootstrap_superuser

Creates the first administrator account for an environment. This is an
EXPLICIT, ONE-TIME, MANUAL operation — it is deliberately NOT wired into any
deploy script, so a routine deploy can never (re)create an administrator.

There are no default credentials. All three values must be supplied through
the environment, and the command refuses to run if any of them is missing:

    BOOTSTRAP_ADMIN_USERNAME
    BOOTSTRAP_ADMIN_EMAIL
    BOOTSTRAP_ADMIN_PASSWORD

If a user with the given username already exists, the command reports that and
exits without touching the account — it never overwrites an existing password.

The password is read from the environment, hashed by Django's user manager, and
is never written to stdout, stderr, or logs. Remove BOOTSTRAP_ADMIN_PASSWORD
from the environment immediately after a successful run — see
docs/security/admin-credential-rotation.md.
"""
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

User = get_user_model()

REQUIRED_ENV_VARS = (
    'BOOTSTRAP_ADMIN_USERNAME',
    'BOOTSTRAP_ADMIN_EMAIL',
    'BOOTSTRAP_ADMIN_PASSWORD',
)


class Command(BaseCommand):
    help = (
        'Create the first administrator from BOOTSTRAP_ADMIN_* environment '
        'variables. Manual, one-time operation — never run automatically. '
        'Refuses to run if any variable is missing; never overwrites an '
        'existing account.'
    )

    def handle(self, *args, **options):
        username = os.environ.get('BOOTSTRAP_ADMIN_USERNAME', '').strip()
        email    = os.environ.get('BOOTSTRAP_ADMIN_EMAIL', '').strip()
        password = os.environ.get('BOOTSTRAP_ADMIN_PASSWORD', '')

        missing = [
            name for name, value in (
                ('BOOTSTRAP_ADMIN_USERNAME', username),
                ('BOOTSTRAP_ADMIN_EMAIL', email),
                ('BOOTSTRAP_ADMIN_PASSWORD', password),
            )
            if not value
        ]
        if missing:
            # Names only — never echo a value back to the caller.
            raise CommandError(
                'Cannot bootstrap an administrator: missing required '
                'environment variables: ' + ', '.join(missing)
            )

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(
                f'Administrator "{username}" already exists — no changes made '
                f'(existing password left untouched).'
            ))
            return

        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )

        self.stdout.write(self.style.SUCCESS(
            f'Administrator created: {username} <{email}>\n'
            f'Now remove BOOTSTRAP_ADMIN_PASSWORD from the environment.'
        ))
