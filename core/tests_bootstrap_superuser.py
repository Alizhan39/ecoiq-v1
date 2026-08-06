"""
Security tests for the `bootstrap_superuser` management command.

The command must never create an administrator from built-in defaults, never
overwrite an existing account, and never print the password. These tests are a
regression fence around a real incident — see
docs/security/admin-credential-rotation.md.
"""
import inspect
import io
import os
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from core.management.commands import bootstrap_superuser

User = get_user_model()

# A complete, valid environment. These values exist only inside the test
# process; they are not credentials for any real environment.
VALID_ENV = {
    'BOOTSTRAP_ADMIN_USERNAME': 'test-operator',
    'BOOTSTRAP_ADMIN_EMAIL': 'test-operator@example.invalid',
    'BOOTSTRAP_ADMIN_PASSWORD': 'unit-test-only-passphrase',
}


def env(**overrides):
    """VALID_ENV with overrides applied; a None value drops the variable."""
    merged = {**VALID_ENV, **overrides}
    return {k: v for k, v in merged.items() if v is not None}


class BootstrapSuperuserMissingConfigTests(TestCase):
    """The command must refuse to run on incomplete configuration."""

    def _assert_refuses(self, environ, expected_var):
        # clear=True so the ambient environment can never satisfy a variable
        # the test intends to be missing.
        with mock.patch.dict(os.environ, environ, clear=True):
            with self.assertRaises(CommandError) as ctx:
                call_command('bootstrap_superuser', stdout=io.StringIO())
        self.assertIn(expected_var, str(ctx.exception))
        self.assertFalse(User.objects.exists(), 'No user may be created')

    def test_all_variables_missing_raises(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(CommandError) as ctx:
                call_command('bootstrap_superuser', stdout=io.StringIO())
        message = str(ctx.exception)
        for name in bootstrap_superuser.REQUIRED_ENV_VARS:
            self.assertIn(name, message)
        self.assertFalse(User.objects.exists())

    def test_missing_username_raises(self):
        self._assert_refuses(
            env(BOOTSTRAP_ADMIN_USERNAME=None), 'BOOTSTRAP_ADMIN_USERNAME')

    def test_missing_email_raises(self):
        self._assert_refuses(
            env(BOOTSTRAP_ADMIN_EMAIL=None), 'BOOTSTRAP_ADMIN_EMAIL')

    def test_missing_password_raises(self):
        self._assert_refuses(
            env(BOOTSTRAP_ADMIN_PASSWORD=None), 'BOOTSTRAP_ADMIN_PASSWORD')

    def test_empty_string_username_is_treated_as_missing(self):
        self._assert_refuses(
            env(BOOTSTRAP_ADMIN_USERNAME=''), 'BOOTSTRAP_ADMIN_USERNAME')

    def test_whitespace_only_username_is_treated_as_missing(self):
        self._assert_refuses(
            env(BOOTSTRAP_ADMIN_USERNAME='   '), 'BOOTSTRAP_ADMIN_USERNAME')

    def test_whitespace_only_email_is_treated_as_missing(self):
        self._assert_refuses(
            env(BOOTSTRAP_ADMIN_EMAIL='  \t '), 'BOOTSTRAP_ADMIN_EMAIL')

    def test_empty_password_is_treated_as_missing(self):
        self._assert_refuses(
            env(BOOTSTRAP_ADMIN_PASSWORD=''), 'BOOTSTRAP_ADMIN_PASSWORD')

    def test_error_message_never_contains_the_password(self):
        with mock.patch.dict(os.environ, env(BOOTSTRAP_ADMIN_EMAIL=None), clear=True):
            with self.assertRaises(CommandError) as ctx:
                call_command('bootstrap_superuser', stdout=io.StringIO())
        self.assertNotIn(VALID_ENV['BOOTSTRAP_ADMIN_PASSWORD'], str(ctx.exception))


class BootstrapSuperuserCreationTests(TestCase):
    """Happy path, idempotency, and password preservation."""

    def _run(self):
        out = io.StringIO()
        with mock.patch.dict(os.environ, env(), clear=True):
            call_command('bootstrap_superuser', stdout=out)
        return out.getvalue()

    def test_creates_exactly_one_superuser(self):
        self._run()
        self.assertEqual(User.objects.count(), 1)
        user = User.objects.get()
        self.assertEqual(user.username, VALID_ENV['BOOTSTRAP_ADMIN_USERNAME'])
        self.assertEqual(user.email, VALID_ENV['BOOTSTRAP_ADMIN_EMAIL'])
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)

    def test_username_and_email_are_stripped(self):
        stripped_env = env(
            BOOTSTRAP_ADMIN_USERNAME='  padded-operator  ',
            BOOTSTRAP_ADMIN_EMAIL=' padded@example.invalid ',
        )
        with mock.patch.dict(os.environ, stripped_env, clear=True):
            call_command('bootstrap_superuser', stdout=io.StringIO())
        user = User.objects.get()
        self.assertEqual(user.username, 'padded-operator')
        self.assertEqual(user.email, 'padded@example.invalid')

    def test_password_is_hashed_and_verifies(self):
        self._run()
        user = User.objects.get()
        self.assertTrue(user.check_password(VALID_ENV['BOOTSTRAP_ADMIN_PASSWORD']))
        # Stored as a hash, not as the plaintext value.
        self.assertNotEqual(user.password, VALID_ENV['BOOTSTRAP_ADMIN_PASSWORD'])
        self.assertNotIn(VALID_ENV['BOOTSTRAP_ADMIN_PASSWORD'], user.password)

    def test_running_twice_does_not_create_a_duplicate(self):
        self._run()
        second_output = self._run()
        self.assertEqual(User.objects.count(), 1)
        self.assertIn('already exists', second_output)

    def test_second_run_does_not_overwrite_the_existing_password(self):
        self._run()
        original_hash = User.objects.get().password

        rerun_env = env(BOOTSTRAP_ADMIN_PASSWORD='a-different-passphrase')
        with mock.patch.dict(os.environ, rerun_env, clear=True):
            call_command('bootstrap_superuser', stdout=io.StringIO())

        user = User.objects.get()
        self.assertEqual(user.password, original_hash)
        self.assertTrue(user.check_password(VALID_ENV['BOOTSTRAP_ADMIN_PASSWORD']))
        self.assertFalse(user.check_password('a-different-passphrase'))

    def test_second_run_does_not_overwrite_an_externally_created_user(self):
        User.objects.create_user(
            username=VALID_ENV['BOOTSTRAP_ADMIN_USERNAME'],
            email='someone-else@example.invalid',
            password='pre-existing-passphrase',
        )
        output = self._run()
        self.assertIn('already exists', output)
        user = User.objects.get()
        self.assertTrue(user.check_password('pre-existing-passphrase'))
        self.assertEqual(user.email, 'someone-else@example.invalid')

    def test_output_never_contains_the_password(self):
        output = self._run()
        self.assertNotIn(VALID_ENV['BOOTSTRAP_ADMIN_PASSWORD'], output)
        self.assertIn(VALID_ENV['BOOTSTRAP_ADMIN_USERNAME'], output)


class BootstrapSuperuserNoHardcodedCredentialsTests(TestCase):
    """No default/fallback administrator credentials may reappear."""

    def test_command_source_has_no_credential_defaults(self):
        source = inspect.getsource(bootstrap_superuser)
        # os.environ.get(..., <default>) for a credential is the exact pattern
        # that caused the incident; only the safe empty-string form is allowed.
        for name in bootstrap_superuser.REQUIRED_ENV_VARS:
            self.assertNotIn(f"os.environ.get('{name}', '{name}", source)
        self.assertNotIn('_DEFAULT_PASSWORD', source)
        self.assertNotIn('_DEFAULT_USERNAME', source)
        self.assertNotIn('_DEFAULT_EMAIL', source)

    def test_no_former_fallback_credentials_in_command_or_tests(self):
        # The compromised values are reconstructed here from fragments so the
        # literal strings never appear in this file either.
        former = [
            'EcoIQ' + '2026!',
            'EcoIQ' + '-Demo-' + '2025!',
        ]
        sources = [
            inspect.getsource(bootstrap_superuser),
            inspect.getsource(inspect.getmodule(self)),
        ]
        for source in sources:
            for value in former:
                self.assertNotIn(value, source)

    def test_command_refuses_with_a_completely_empty_environment(self):
        # Belt and braces: with nothing set at all, no user may appear.
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(CommandError):
                call_command('bootstrap_superuser', stdout=io.StringIO())
        self.assertEqual(User.objects.count(), 0)


class DeploymentDoesNotBootstrapTests(TestCase):
    """The deploy path must not create administrators automatically."""

    def test_predeploy_does_not_invoke_bootstrap_superuser(self):
        from pathlib import Path

        repo_root = Path(__file__).resolve().parent.parent
        for script in ('predeploy.sh', 'build.sh', 'start.sh'):
            path = repo_root / script
            if not path.exists():
                continue
            for line in path.read_text().splitlines():
                stripped = line.strip()
                if stripped.startswith('#'):
                    continue  # documentation of the manual procedure is fine
                self.assertNotIn(
                    'bootstrap_superuser', stripped,
                    f'{script} must not run bootstrap_superuser automatically',
                )
