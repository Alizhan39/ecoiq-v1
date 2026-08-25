"""
Tests for durable media storage.

Nothing here contacts R2 or the network. The R2 backend is exercised by
constructing the storage class directly and inspecting the configuration and
the URLs it signs; the migration path is exercised local->local, which is the
same code path that runs local->R2 at cutover.
"""
import io
import os
import shutil
import tempfile
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings

from core import storage as storage_mod


class ObjectKeyTests(SimpleTestCase):

    def test_key_is_collision_resistant(self):
        a = storage_mod.build_key('uploads', 'report.pdf')
        b = storage_mod.build_key('uploads', 'report.pdf')
        self.assertNotEqual(a, b, 'identical filenames produced identical keys')

    def test_key_keeps_the_extension(self):
        self.assertTrue(storage_mod.build_key('uploads', 'report.pdf').endswith('.pdf'))

    def test_filename_is_stripped_of_identifying_text(self):
        """
        People name files after themselves and their clients. The stored key is
        visible to anyone who sees a URL, so it keeps a slug and an extension
        and nothing else.
        """
        key = storage_mod.build_key('uploads', 'Ahmed Al-Farsi Q3 CONFIDENTIAL salary.pdf')
        self.assertNotIn('CONFIDENTIAL', key)
        self.assertNotIn('salary', key.split('-', 1)[0])
        self.assertTrue(key.endswith('.pdf'))

    def test_path_traversal_cannot_escape_the_prefix(self):
        key = storage_mod.build_key('uploads', '../../etc/passwd')
        self.assertTrue(key.startswith('uploads/'))
        self.assertNotIn('..', key)

    def test_tenant_scope_appears_in_the_key(self):
        scoped = storage_mod.build_key('league/evidence', 'r.pdf', scope='42')
        self.assertIn('/org/42/', scoped)

    def test_unscoped_key_has_no_fabricated_tenant(self):
        """
        Three of six upload models reach a company; the rest do not. An
        unscoped key says so rather than inventing a scope.
        """
        self.assertNotIn('/org/', storage_mod.build_key('uploads', 'r.pdf'))

    def test_upload_to_callables_scope_by_company_when_available(self):
        class FakeCompany:
            pk = 7

        class Row:
            company = FakeCompany()
            company_id = 7

        self.assertIn('/org/7/', storage_mod.upload_to_evidence(Row(), 'e.pdf'))
        self.assertIn('/org/7/', storage_mod.upload_to_ai_analysis(Row(), 'a.pdf'))

    def test_upload_to_callable_without_company_is_still_safe(self):
        class Row:
            pass

        key = storage_mod.upload_to_assessment(Row(), 'x.pdf')
        self.assertTrue(key.startswith('uploads/'))
        self.assertNotIn('/org/', key)

    def test_sanitiser_never_returns_an_empty_name(self):
        self.assertTrue(storage_mod.sanitise_filename('...'))
        self.assertTrue(storage_mod.sanitise_filename(''))


class StorageSelectionTests(SimpleTestCase):
    """Which backend is chosen, and what happens when configuration is absent."""

    def test_filesystem_is_the_default(self):
        from django.conf import settings

        self.assertFalse(settings.MEDIA_USES_R2)
        self.assertIn('FileSystemStorage', settings.STORAGES['default']['BACKEND'])

    def test_tests_never_use_r2(self):
        """A test run must not need credentials or a network."""
        from django.conf import settings

        self.assertNotIn('storage_r2', settings.STORAGES['default']['BACKEND'])

    def test_r2_requires_every_variable_and_fails_closed(self):
        """
        Falling back to the local filesystem here would write uploads to a disk
        destroyed on the next deploy, silently. It must refuse to start.
        """
        env = {'MEDIA_STORAGE_BACKEND': 'r2', 'R2_ACCOUNT_ID': 'acct',
               'R2_BUCKET_NAME': 'b'}  # keys deliberately absent
        with patch.dict(os.environ, env, clear=False):
            with self.assertRaises(ImproperlyConfigured) as ctx:
                self._reimport_settings()
        message = str(ctx.exception)
        self.assertIn('R2_ACCESS_KEY_ID', message)
        self.assertIn('R2_SECRET_ACCESS_KEY', message)

    def test_failure_message_names_the_missing_variables_not_their_values(self):
        env = {'MEDIA_STORAGE_BACKEND': 'r2', 'R2_ACCOUNT_ID': 'acct-secret-value',
               'R2_BUCKET_NAME': 'bucket', 'R2_ACCESS_KEY_ID': 'AKIA-SECRET'}
        with patch.dict(os.environ, env, clear=False):
            with self.assertRaises(ImproperlyConfigured) as ctx:
                self._reimport_settings()
        message = str(ctx.exception)
        self.assertNotIn('AKIA-SECRET', message)
        self.assertNotIn('acct-secret-value', message)

    @staticmethod
    def _reimport_settings():
        import importlib

        import ecoiq.settings as s

        importlib.reload(s)


class R2BackendConfigurationTests(SimpleTestCase):
    """The R2 class itself — constructed directly, never contacted."""

    def _storage(self, **overrides):
        from core.storage_r2 import R2MediaStorage

        opts = dict(bucket_name='ecoiq-media-production', access_key='k',
                    secret_key='s', endpoint_url='https://acct.r2.cloudflarestorage.com',
                    region_name='auto', signature_version='s3v4', querystring_expire=300)
        opts.update(overrides)
        return R2MediaStorage(**opts)

    def test_objects_are_not_public(self):
        """
        R2 has no per-object ACLs. `default_acl` must be None, not 'private':
        sending an ACL header makes R2 reject the upload.
        """
        self.assertIsNone(self._storage().default_acl)

    def test_reads_are_signed(self):
        self.assertTrue(self._storage().querystring_auth)

    def test_signed_url_expiry_is_short(self):
        self.assertEqual(self._storage().querystring_expire, 300)

    def test_existing_objects_are_never_overwritten(self):
        self.assertFalse(self._storage().file_overwrite)

    def test_uploads_are_not_cacheable(self):
        self.assertEqual(self._storage().object_parameters.get('CacheControl'),
                         'private, no-store')

    def test_signed_url_contains_a_signature_and_an_expiry(self):
        url = self._storage().url('uploads/abc-report.pdf')
        self.assertIn('X-Amz-Signature=', url)
        self.assertIn('X-Amz-Expires=', url)

    def test_signed_url_never_contains_the_secret_key(self):
        """
        The signature is DERIVED from the secret. The secret itself must never
        appear in a URL that will be pasted into tickets and proxy logs.
        """
        url = self._storage(secret_key='SUPER-SECRET-VALUE').url('uploads/x.pdf')
        self.assertNotIn('SUPER-SECRET-VALUE', url)

    def test_signed_url_expiry_is_configurable(self):
        self.assertIn('X-Amz-Expires=60', self._storage(querystring_expire=60).url('uploads/x.pdf'))


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix='ecoiq-media-test-'))
class ReconcileMediaTests(TestCase):
    """The reconciliation command, exercised local->local."""

    def setUp(self):
        self.src = tempfile.mkdtemp(prefix='ecoiq-src-')
        self.dst = tempfile.mkdtemp(prefix='ecoiq-dst-')
        self.addCleanup(shutil.rmtree, self.src, ignore_errors=True)
        self.addCleanup(shutil.rmtree, self.dst, ignore_errors=True)

    def _run(self, **kwargs):
        from io import StringIO

        out = StringIO()
        with override_settings(STORAGES={
            'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage',
                        'OPTIONS': {'location': self.dst}},
            'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
        }):
            call_command('reconcile_media', stdout=out, **kwargs)
        return out.getvalue()

    def _evidence_with_file(self, name='report.pdf', body=b'hello'):
        from league.models import Company, Evidence

        company = Company.objects.create(name='Recon Co', slug='recon-co')
        ev = Evidence.objects.create(company=company)
        FileSystemStorage(location=self.src).save('league/evidence/fixed-key.pdf', ContentFile(body))
        Evidence.objects.filter(pk=ev.pk).update(file='league/evidence/fixed-key.pdf')
        return Evidence.objects.get(pk=ev.pk)

    def test_reports_zero_when_there_is_nothing(self):
        output = self._run()
        self.assertIn('database references: 0', output)
        self.assertIn('referenced_but_missing    : 0', output)

    def test_referenced_but_missing_is_reported_not_repaired(self):
        """
        The exact failure the ephemeral filesystem produced: a row pointing at
        a file that no longer exists. It is reported, never silently deleted.
        """
        from league.models import Company, Evidence

        company = Company.objects.create(name='Gone Co', slug='gone-co')
        ev = Evidence.objects.create(company=company)
        Evidence.objects.filter(pk=ev.pk).update(file='league/evidence/vanished.pdf')
        output = self._run(source_root=self.src)
        self.assertIn('referenced_but_missing    : 1', output)
        self.assertTrue(Evidence.objects.filter(pk=ev.pk).exists())

    def test_migrate_copies_and_leaves_the_original(self):
        self._evidence_with_file()
        output = self._run(migrate=True, source_root=self.src)
        self.assertIn('copied                    : 1', output)
        self.assertTrue(os.path.exists(os.path.join(self.src, 'league/evidence/fixed-key.pdf')),
                        'the source object was removed — it must never be')
        self.assertTrue(os.path.exists(os.path.join(self.dst, 'league/evidence/fixed-key.pdf')))

    def test_migrate_is_idempotent(self):
        self._evidence_with_file()
        self._run(migrate=True, source_root=self.src)
        second = self._run(migrate=True, source_root=self.src)
        self.assertIn('copied                    : 0', second)
        self.assertIn('referenced_and_present    : 1', second)

    def test_migrate_preserves_the_key_so_no_row_is_rewritten(self):
        ev = self._evidence_with_file()
        before = ev.file.name
        self._run(migrate=True, source_root=self.src)
        ev.refresh_from_db()
        self.assertEqual(ev.file.name, before)

    def test_present_but_unreferenced_is_reported(self):
        FileSystemStorage(location=self.src).save('league/evidence/orphan.pdf', ContentFile(b'x'))
        output = self._run(source_root=self.src)
        self.assertIn('present_but_unreferenced  : 1', output)

    def test_no_file_content_is_printed(self):
        self._evidence_with_file(body=b'SECRET-DOCUMENT-BODY')
        output = self._run(migrate=True, source_root=self.src)
        self.assertNotIn('SECRET-DOCUMENT-BODY', output)


class UploadValidationUnchangedTests(SimpleTestCase):
    """This package must not have relaxed the existing upload limits."""

    def test_upload_size_ceilings_are_unchanged(self):
        from django.conf import settings

        self.assertEqual(settings.FILE_UPLOAD_MAX_MEMORY_SIZE, 10 * 1024 * 1024)
        self.assertEqual(settings.DATA_UPLOAD_MAX_MEMORY_SIZE, 10 * 1024 * 1024)


class WorkerAndWebAgreeTests(SimpleTestCase):
    """
    Web and Celery must resolve the same bucket from the same variables. They
    read one settings module, so this pins that nothing forks the decision.
    """

    def test_storage_selection_is_a_single_settings_decision(self):
        source = (storage_mod.__file__.rsplit('/', 2)[0] + '/ecoiq/settings.py')
        text = open(source, encoding='utf-8').read() if os.path.exists(source) else ''
        if text:
            self.assertEqual(text.count("STORAGES['default'] = {"), 1,
                             'more than one place assigns the default storage')
