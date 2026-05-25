"""
Management command: bootstrap_superuser

Creates the production superuser on first deploy.
Idempotent — skips silently if the user already exists.

Called automatically from build.sh on every Render deploy.

Credentials can be overridden via environment variables:
    BOOTSTRAP_ADMIN_USERNAME  (default: alizhan)
    BOOTSTRAP_ADMIN_EMAIL     (default: work.tazabekov@gmail.com)
    BOOTSTRAP_ADMIN_PASSWORD  (default: EcoIQ2026!)
"""
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()

_DEFAULT_USERNAME = 'alizhan'
_DEFAULT_EMAIL    = 'work.tazabekov@gmail.com'
_DEFAULT_PASSWORD = 'EcoIQ2026!'


class Command(BaseCommand):
    help = 'Bootstrap the production superuser if none exists (idempotent).'

    def handle(self, *args, **options):
        username = os.environ.get('BOOTSTRAP_ADMIN_USERNAME', _DEFAULT_USERNAME)
        email    = os.environ.get('BOOTSTRAP_ADMIN_EMAIL',    _DEFAULT_EMAIL)
        password = os.environ.get('BOOTSTRAP_ADMIN_PASSWORD', _DEFAULT_PASSWORD)

        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write('EcoIQ admin bootstrap checked')
            return

        User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'EcoIQ admin bootstrap checked\n'
                f'  ✓  Superuser created: {username} <{email}>'
            )
        )
