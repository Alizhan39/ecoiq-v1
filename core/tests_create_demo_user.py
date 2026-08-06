"""
Tests for the `create_demo_user` management command.

Three concerns:
  1. The demo account is NON-PRIVILEGED. It previously used create_superuser,
     so a demo login carried full Django admin rights.
  2. No default password, and the password is never echoed.
  3. `--reset` is destructive and `--username` is free-form, so an unguarded
     reset could delete a real administrator. It must refuse unless explicitly
     authorised, must never touch a privileged account, and must delete
     nothing when it refuses.
"""
import io
import os
from unittest import mock

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import transaction
from django.test import TestCase, override_settings

# Test-process value only; not a credential for any real environment.
TEST_PASSWORD = 'command-test-only-passphrase'


def run(*args, **kwargs):
    out = io.StringIO()
    call_command('create_demo_user', *args, stdout=out, stderr=out, **kwargs)
    return out.getvalue()


class DemoAccountIsNotPrivilegedTests(TestCase):
    """Requirement 1: a normal demo user is neither staff nor superuser."""

    def test_demo_user_is_not_staff_or_superuser(self):
        run(f'--password={TEST_PASSWORD}')
        user = User.objects.get(username='demo')
        self.assertFalse(user.is_superuser, 'demo account must not be a superuser')
        self.assertFalse(user.is_staff, 'demo account must not be staff')
        self.assertTrue(user.is_active)

    def test_custom_named_demo_user_is_also_unprivileged(self):
        run('--username=investor', f'--password={TEST_PASSWORD}')
        user = User.objects.get(username='investor')
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_staff)

    def test_no_flag_can_grant_privileges(self):
        """There must be no argument that escalates the demo account."""
        for flag in ('--superuser', '--staff', '--admin', '--allow-privileged'):
            with self.subTest(flag=flag):
                with self.assertRaises(Exception):
                    run(flag, f'--password={TEST_PASSWORD}')

    def test_command_never_calls_create_superuser(self):
        """
        AST-based, not a string search: a comment mentioning create_superuser
        must not trip this, but an actual call must.
        """
        import ast
        import inspect
        from core.management.commands import create_demo_user as mod

        called = {
            node.func.attr
            for node in ast.walk(ast.parse(inspect.getsource(mod)))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertNotIn('create_superuser', called)
        self.assertIn('create_user', called)

    def test_demo_user_cannot_reach_the_admin_site(self):
        run(f'--password={TEST_PASSWORD}')
        self.assertTrue(self.client.login(username='demo', password=TEST_PASSWORD))
        response = self.client.get('/admin/', follow=False)
        # Not staff -> Django admin bounces to its own login instead of serving
        # the dashboard, even though the user is authenticated.
        self.assertIn(response.status_code, (301, 302))
        self.assertIn('/admin/login/', response.headers['Location'])


class PasswordHandlingTests(TestCase):
    """Requirement 7: no password appears in command output."""

    def test_no_password_anywhere_raises(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(CommandError) as ctx:
                run()
        self.assertIn('DEMO_USER_PASSWORD', str(ctx.exception))
        self.assertFalse(User.objects.exists())

    def test_password_from_environment_is_accepted(self):
        with mock.patch.dict(os.environ, {'DEMO_USER_PASSWORD': TEST_PASSWORD}, clear=True):
            run()
        self.assertTrue(User.objects.get(username='demo').check_password(TEST_PASSWORD))

    def test_password_is_never_printed_on_creation(self):
        output = run(f'--password={TEST_PASSWORD}')
        self.assertNotIn(TEST_PASSWORD, output)

    def test_password_is_never_printed_on_reset(self):
        User.objects.create_user('plain-user', 'plain@example.invalid', 'old-passphrase')
        output = run('--username=plain-user', f'--password={TEST_PASSWORD}',
                     '--reset', '--confirm')
        self.assertNotIn(TEST_PASSWORD, output)

    def test_password_is_never_printed_in_a_refusal(self):
        User.objects.create_superuser('real-admin', 'a@example.invalid', 'admin-passphrase')
        with self.assertRaises(CommandError) as ctx:
            run('--username=real-admin', f'--password={TEST_PASSWORD}',
                '--reset', '--confirm')
        self.assertNotIn(TEST_PASSWORD, str(ctx.exception))

    def test_password_is_hashed(self):
        run(f'--password={TEST_PASSWORD}')
        user = User.objects.get(username='demo')
        self.assertNotEqual(user.password, TEST_PASSWORD)
        self.assertTrue(user.check_password(TEST_PASSWORD))


class NormalBehaviourPreservedTests(TestCase):

    def test_default_username_and_email(self):
        run(f'--password={TEST_PASSWORD}')
        user = User.objects.get(username='demo')
        self.assertEqual(user.email, 'demo@ecoiq.uk')

    def test_existing_user_is_reported_and_left_alone(self):
        run(f'--password={TEST_PASSWORD}')
        original = User.objects.get(username='demo').password
        output = run(f'--password={TEST_PASSWORD}')
        self.assertIn('already exists', output)
        self.assertEqual(User.objects.get(username='demo').password, original)
        self.assertEqual(User.objects.filter(username='demo').count(), 1)


class ResetRefusalTests(TestCase):
    """Requirements 2, 3, 4, 5 — every refusal leaves the target untouched."""

    def setUp(self):
        self.admin = User.objects.create_superuser(
            'real-admin', 'real-admin@example.invalid', 'admin-passphrase')
        self.staff = User.objects.create_user(
            'real-staff', 'real-staff@example.invalid', 'staff-passphrase',
            is_staff=True)
        self.plain = User.objects.create_user(
            'plain-user', 'plain@example.invalid', 'plain-passphrase')

    def assert_untouched(self, user, raw_password):
        user.refresh_from_db()
        self.assertTrue(user.check_password(raw_password))

    def test_reset_without_confirm_refuses(self):
        with self.assertRaises(CommandError) as ctx:
            run('--username=plain-user', f'--password={TEST_PASSWORD}', '--reset')
        self.assertIn('--confirm', str(ctx.exception))
        self.assert_untouched(self.plain, 'plain-passphrase')

    def test_superuser_cannot_be_reset(self):
        with self.assertRaises(CommandError) as ctx:
            run('--username=real-admin', f'--password={TEST_PASSWORD}',
                '--reset', '--confirm')
        self.assertIn('superuser', str(ctx.exception))
        self.assertTrue(User.objects.filter(username='real-admin').exists())
        self.assert_untouched(self.admin, 'admin-passphrase')

    def test_staff_user_cannot_be_reset(self):
        with self.assertRaises(CommandError) as ctx:
            run('--username=real-staff', f'--password={TEST_PASSWORD}',
                '--reset', '--confirm')
        self.assertIn('staff', str(ctx.exception))
        self.assertTrue(User.objects.filter(username='real-staff').exists())
        self.assert_untouched(self.staff, 'staff-passphrase')

    def test_privileged_refusal_has_no_override_flag(self):
        """There must be no escape hatch that permits a privileged reset."""
        with self.assertRaises(Exception):
            run('--username=real-admin', f'--password={TEST_PASSWORD}',
                '--reset', '--confirm', '--allow-privileged')
        self.assertTrue(User.objects.filter(username='real-admin').exists())
        self.assert_untouched(self.admin, 'admin-passphrase')

    @override_settings(IS_PRODUCTION=True)
    def test_production_reset_is_refused(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(CommandError) as ctx:
                run('--username=plain-user', f'--password={TEST_PASSWORD}',
                    '--reset', '--confirm')
        self.assertIn('production', str(ctx.exception))
        self.assert_untouched(self.plain, 'plain-passphrase')

    @override_settings(IS_PRODUCTION=True)
    def test_production_reset_still_refuses_a_superuser_even_with_override(self):
        env = {'ALLOW_DEMO_USER_RESET': 'true'}
        with mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaises(CommandError) as ctx:
                run('--username=real-admin', f'--password={TEST_PASSWORD}',
                    '--reset', '--confirm')
        self.assertIn('superuser', str(ctx.exception))
        self.assert_untouched(self.admin, 'admin-passphrase')


class ResetSuccessTests(TestCase):
    """Requirement 6: a confirmed development reset works, atomically."""

    def test_confirmed_reset_recreates_a_plain_account(self):
        User.objects.create_user('plain-user', 'plain@example.invalid', 'old-passphrase')
        original_pk = User.objects.get(username='plain-user').pk

        run('--username=plain-user', f'--password={TEST_PASSWORD}',
            '--reset', '--confirm')

        user = User.objects.get(username='plain-user')
        self.assertNotEqual(user.pk, original_pk, 'account should be recreated')
        self.assertTrue(user.check_password(TEST_PASSWORD))
        self.assertFalse(user.check_password('old-passphrase'))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(User.objects.filter(username='plain-user').count(), 1)

    def test_reset_is_atomic_delete_is_rolled_back_if_create_fails(self):
        """A failure mid-reset must not leave the account deleted."""
        User.objects.create_user('plain-user', 'plain@example.invalid', 'old-passphrase')

        with mock.patch.object(User.objects, 'create_user',
                               side_effect=RuntimeError('simulated failure')):
            with self.assertRaises(RuntimeError):
                run('--username=plain-user', f'--password={TEST_PASSWORD}',
                    '--reset', '--confirm')

        # The delete happened inside the same atomic block as the create, so
        # the rollback must have restored the original row.
        self.assertTrue(User.objects.filter(username='plain-user').exists())
        self.assertTrue(
            User.objects.get(username='plain-user').check_password('old-passphrase'))

    def test_command_uses_an_atomic_block(self):
        from core.management.commands import create_demo_user as mod
        import inspect
        self.assertIn('transaction.atomic()', inspect.getsource(mod))

    def test_reset_of_absent_user_still_creates_it(self):
        run('--username=brand-new', f'--password={TEST_PASSWORD}',
            '--reset', '--confirm')
        user = User.objects.get(username='brand-new')
        self.assertFalse(user.is_superuser)
