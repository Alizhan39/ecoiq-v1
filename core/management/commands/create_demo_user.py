"""
Management command: create_demo_user

Creates a NON-PRIVILEGED demo account for investor / pilot access
(`is_staff=False`, `is_superuser=False`). It previously created a superuser,
which meant a demo login carried full Django admin rights.

This command can no longer grant administrative privileges by any flag or
argument. If an administrator account is genuinely needed, create it through
the separate authorised bootstrap process —
see docs/security/admin-credential-rotation.md — never through this command.

There is no default password: one must be supplied explicitly, either via
--password or via the DEMO_USER_PASSWORD environment variable. The password is
never echoed back to the terminal.

`--reset` DELETES the named account. Because `--username` is free-form, an
unguarded reset could destroy a real administrator (`--username <admin>
--reset`). It is therefore gated three ways: it requires `--confirm`, it
refuses outright when the target is a staff or superuser account (no override
exists), and it refuses to run in production unless ALLOW_DEMO_USER_RESET is
explicitly set for that single command. The delete and recreate run inside one
transaction.

Usage:
    DEMO_USER_PASSWORD=… python manage.py create_demo_user
    python manage.py create_demo_user --username investor --password …
    python manage.py create_demo_user --reset --confirm

The user can then sign in at /login/. They have no access to /admin/.
"""
import os

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


DEFAULT_USERNAME = 'demo'

# Opt-in required before --reset will delete anything in a production process.
RESET_OVERRIDE_ENV = 'ALLOW_DEMO_USER_RESET'


class Command(BaseCommand):
    help = (
        'Create (or reset) a non-privileged demo account for investor / pilot '
        'access. Never grants staff or superuser rights.'
    )

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
            help='DESTRUCTIVE: delete the existing user with this username '
                 'before creating a fresh one. Requires --confirm, and refuses '
                 'staff/superuser accounts.',
        )
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Required acknowledgement for --reset. Without it, --reset '
                 'refuses to delete anything.',
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
            # Checked before any write, so a refusal deletes nothing.
            self._authorise_reset(username, options)

        with transaction.atomic():
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

            # create_user, NOT create_superuser: a demo login must never carry
            # admin rights. is_staff/is_superuser are pinned explicitly so a
            # future change to Django's defaults cannot silently escalate this.
            User.objects.create_user(
                username=username,
                email=f'{username}@ecoiq.uk',
                password=password,
                is_staff=False,
                is_superuser=False,
            )

        self.stdout.write(self.style.SUCCESS(
            f'\n  ✓  Demo account created (no staff or admin rights)\n'
            f'     Username : {username}\n'
            f'     Password : (not shown — the value you supplied)\n'
            f'     Login at : /login/\n'
        ))

    def _authorise_reset(self, username, options):
        """
        Raise CommandError unless this destructive reset is explicitly
        authorised. Performs no writes.
        """
        if not options['confirm']:
            raise CommandError(
                f'--reset will DELETE the user "{username}". Re-run with '
                f'--confirm if that is genuinely what you intend.'
            )

        if getattr(settings, 'IS_PRODUCTION', False) and \
                os.environ.get(RESET_OVERRIDE_ENV, '').strip().lower() not in ('true', '1', 'yes', 'on'):
            raise CommandError(
                f'Refusing to delete user "{username}": --reset is disabled in '
                f'production. Set {RESET_OVERRIDE_ENV}=true for this single '
                f'command if an authorised operator genuinely intends it.'
            )

        target = User.objects.filter(username=username).first()
        if target is not None and (target.is_superuser or target.is_staff):
            role = 'superuser' if target.is_superuser else 'staff user'
            raise CommandError(
                f'Refusing to delete "{username}": it is a {role}, and this '
                f'command manages non-privileged demo accounts only. There is '
                f'no override. To rotate an administrator password use '
                f'`manage.py changepassword {username}`; to remove a '
                f'privileged account, do it deliberately in the Django admin.'
            )
