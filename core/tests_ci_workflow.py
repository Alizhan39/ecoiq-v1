"""
Regression tests for the CI workflow definition itself.

The Django CI job carried `continue-on-error: true` on its test step, so a
failing suite still produced a green workflow. Two stale assertions in
good_agents therefore sat broken on main for eleven days without anyone being
told. These tests keep the enforcement in place: if someone re-adds
continue-on-error to silence a red suite, this suite goes red too.

Deliberately kept in its own module rather than folded into deployment or
settings tests: this asserts on CI configuration, which is a separate concern
from the deploy scripts and has a different owner.
"""
from pathlib import Path

import yaml
from django.test import SimpleTestCase

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_DIR = REPO_ROOT / '.github' / 'workflows'


def load_workflow(name):
    return yaml.safe_load((WORKFLOW_DIR / name).read_text())


class DjangoWorkflowEnforcementTests(SimpleTestCase):

    def setUp(self):
        self.workflow = load_workflow('django.yml')

    def test_no_job_ignores_its_own_failure(self):
        for job_name, job in self.workflow['jobs'].items():
            self.assertNotIn(
                'continue-on-error', job,
                f'job {job_name!r} ignores its own failure')

    def test_no_step_ignores_its_own_failure(self):
        """A red test suite must turn the workflow red."""
        for job_name, job in self.workflow['jobs'].items():
            for step in job.get('steps', []):
                self.assertNotIn(
                    'continue-on-error', step,
                    f"step {step.get('name')!r} in job {job_name!r} ignores "
                    f"failures — fix the test or the code, do not silence CI")

    def test_ci_actually_runs_the_test_suite(self):
        commands = [
            step.get('run', '')
            for job in self.workflow['jobs'].values()
            for step in job.get('steps', [])
        ]
        self.assertTrue(
            any('manage.py test' in c for c in commands),
            'CI must run the Django test suite')

    def test_ci_runs_the_system_and_migration_checks(self):
        commands = ' '.join(
            step.get('run', '')
            for job in self.workflow['jobs'].values()
            for step in job.get('steps', [])
        )
        self.assertIn('manage.py check', commands)
        self.assertIn('makemigrations --check', commands)

    def test_test_step_does_not_run_with_production_debug(self):
        """
        The job-level DEBUG=False is correct for the `check` steps, but at
        settings-import time it also enables SECURE_SSL_REDIRECT, which makes
        every test-client request 301 and fails ~1400 tests. The test step must
        therefore override it.
        """
        job = self.workflow['jobs']['django-check']
        job_debug = str(job.get('env', {}).get('DEBUG', '')).lower()
        for step in job['steps']:
            if 'manage.py test' not in step.get('run', ''):
                continue
            step_debug = str(step.get('env', {}).get('DEBUG', job_debug)).lower()
            self.assertEqual(
                step_debug, 'true',
                'the test step must run with DEBUG=True, otherwise '
                'SECURE_SSL_REDIRECT turns every request into a 301')
            break
        else:
            self.fail('no step runs manage.py test')

    def test_workflow_triggers_on_pull_request_and_main(self):
        # PyYAML parses the bare `on:` key as the boolean True.
        triggers = self.workflow.get(True, self.workflow.get('on'))
        self.assertIn('pull_request', triggers)
        self.assertIn('push', triggers)


class AllWorkflowsAreEnforcingTests(SimpleTestCase):
    """No workflow in the repository may silently swallow a failure."""

    def test_no_workflow_has_a_continue_on_error_step(self):
        offenders = []
        for path in sorted(WORKFLOW_DIR.glob('*.yml')) + sorted(WORKFLOW_DIR.glob('*.yaml')):
            workflow = yaml.safe_load(path.read_text())
            if not isinstance(workflow, dict):
                continue
            for job_name, job in (workflow.get('jobs') or {}).items():
                if 'continue-on-error' in job:
                    offenders.append(f'{path.name}:{job_name} (job)')
                for step in job.get('steps', []):
                    if 'continue-on-error' in step:
                        offenders.append(
                            f'{path.name}:{job_name}:{step.get("name")!r} (step)')
        self.assertEqual(offenders, [], f'workflows ignoring failures: {offenders}')

    def test_every_workflow_parses(self):
        for path in sorted(WORKFLOW_DIR.glob('*.yml')) + sorted(WORKFLOW_DIR.glob('*.yaml')):
            with self.subTest(workflow=path.name):
                workflow = yaml.safe_load(path.read_text())
                self.assertIn('jobs', workflow)
                for job_name, job in workflow['jobs'].items():
                    self.assertIn('runs-on', job, f'{path.name}:{job_name}')
                    for step in job.get('steps', []):
                        self.assertTrue(
                            ('uses' in step) ^ ('run' in step),
                            f'{path.name}:{job_name}: step needs exactly one '
                            f'of uses/run')


class MobileGateEnforcementTests(SimpleTestCase):
    """
    `mobile-gate` is the single required status check that covers the Flutter
    platform on main.

    The four real mobile jobs cannot be required directly: mobile.yml used to
    carry a trigger-level `paths:` filter, so on a non-mobile PR those contexts
    were never created at all, and GitHub treats a required check that never
    reports as permanently pending. Requiring them would have made every
    unrelated PR unmergeable.

    The gate replaces that with one always-present context. These tests pin the
    two properties that make it trustworthy: it must ALWAYS appear, and it must
    NEVER be able to go green while a required mobile job did not succeed.
    """

    REQUIRED_MOBILE_JOBS = [
        'analyze-and-test',
        'build-android',
        'build-ios',
        'build-windows',
    ]

    def setUp(self):
        self.workflow = load_workflow('mobile.yml')
        self.jobs = self.workflow['jobs']
        # PyYAML parses a bare `on:` key as the boolean True.
        self.triggers = self.workflow.get('on') or self.workflow.get(True)
        self.gate = self.jobs['mobile-gate']
        # The verification shell script, as it will actually execute. Read from
        # the parsed step rather than re-dumping the YAML: a dump re-escapes
        # quotes, so assertions against it would test PyYAML's serialiser
        # rather than the script.
        self.gate_script = '\n'.join(
            step.get('run', '') for step in self.gate['steps']
        )
        self.gate_env = {
            k: v
            for step in self.gate['steps']
            for k, v in (step.get('env') or {}).items()
        }

    # ── the gate must always be present ────────────────────────────────────

    def test_mobile_gate_job_exists(self):
        self.assertIn('mobile-gate', self.jobs)

    def test_workflow_has_no_trigger_level_path_filter(self):
        # This is the whole point: a `paths:` filter here would stop the
        # workflow entirely on unrelated PRs, so `mobile-gate` would never
        # report and every non-mobile PR would block forever.
        for event in ('push', 'pull_request'):
            self.assertNotIn(
                'paths', self.triggers[event] or {},
                f'{event} must not filter by path — it would make the required '
                f'mobile-gate context vanish on unrelated PRs',
            )

    def test_gate_runs_on_pull_requests_targeting_main(self):
        self.assertIn('pull_request', self.triggers)
        self.assertIn('main', self.triggers['pull_request']['branches'])

    def test_gate_is_not_itself_conditional(self):
        # A gate with `if: <some condition>` could be skipped, and a skipped
        # required check never reports success -> permanent block. It must run
        # unconditionally.
        self.assertEqual(self.gate.get('if'), 'always()')

    # ── the gate must not be able to pass falsely ──────────────────────────

    def test_gate_depends_on_every_required_mobile_job(self):
        needs = self.gate['needs']
        self.assertIn('changes', needs)
        for job in self.REQUIRED_MOBILE_JOBS:
            self.assertIn(
                job, needs,
                f'{job} missing from mobile-gate needs — its failure would not '
                f'block the gate',
            )

    def test_gate_inspects_the_result_of_every_dependency(self):
        # `if: always()` on its own is a trap: the job runs even when upstream
        # jobs were skipped BECAUSE something failed. The gate must therefore
        # read each result explicitly rather than relying on job ordering.
        wired = ' '.join(self.gate_env.values())
        for job in self.REQUIRED_MOBILE_JOBS:
            self.assertIn(
                f"needs['{job}'].result", wired,
                f'mobile-gate does not read the result of {job}',
            )
        self.assertIn('needs.changes.result', wired)

    def test_gate_requires_success_not_merely_non_failure(self):
        # Two distinct success comparisons must exist and both must be real:
        #   1. the change-detection guard, and
        #   2. the per-job loop that inspects each required mobile job.
        # Asserting only that the string appears somewhere is not enough — a
        # mutation that weakened the per-job comparison while leaving the
        # change-detection guard intact previously slipped past this test.
        self.assertGreaterEqual(
            self.gate_script.count('!= "success"'), 2,
            'the gate must compare BOTH change-detection and each required '
            'mobile job against success',
        )
        self.assertIn(
            'if [ "$res" != "success" ]', self.gate_script,
            'the per-job loop must fail any result that is not success '
            '(failure, cancelled and skipped are all non-success)',
        )
        self.assertIn(
            'if [ "$CHANGES_RESULT" != "success" ]', self.gate_script,
            'the gate must refuse to trust a change-detection job that did '
            'not succeed',
        )

    def test_gate_fails_closed_on_unexpected_state(self):
        # Every branch that is not a recognised good state must exit non-zero.
        self.assertGreaterEqual(
            self.gate_script.count('exit 1'), 4,
            'mobile-gate must exit non-zero on: bad change-detection, '
            'unexpected job state when no mobile change, a non-successful '
            'required job, and an unrecognised detector output',
        )

    def test_gate_does_not_trust_change_detection_blindly(self):
        self.assertIn('CHANGES_RESULT', self.gate_script)
        self.assertIn('refusing to pass', self.gate_script)

    # ── the expensive jobs stay conditional, and stay strong ───────────────

    def test_expensive_jobs_are_conditional_on_change_detection(self):
        for job in self.REQUIRED_MOBILE_JOBS:
            self.assertEqual(
                self.jobs[job].get('if'),
                "needs.changes.outputs.mobile == 'true'",
                f'{job} must be skipped when no mobile-relevant path changed',
            )

    def test_change_detection_job_is_unconditional(self):
        self.assertNotIn('if', self.jobs['changes'])

    def test_mobile_relevant_paths_include_the_whole_platform(self):
        detect = yaml.dump(self.jobs['changes'])
        for path in ('mobile/', 'mobile_auth/', 'api/app_views',
                     'api/commercial_views', 'api/logging_mixin',
                     'workflows/mobile'):
            self.assertIn(
                path, detect,
                f'{path} is part of the mobile platform but would not trigger '
                f'mobile validation',
            )

    def test_flutter_validation_steps_are_still_present(self):
        # The gate must not become a substitute for the real checks.
        steps = yaml.dump(self.jobs['analyze-and-test'])
        for command in ('flutter pub get', 'dart format', 'flutter analyze',
                        'flutter test'):
            self.assertIn(command, steps)

    def test_native_builds_are_still_present(self):
        for job, command in (
            ('build-android', 'flutter build appbundle'),
            ('build-ios', 'flutter build ios'),
            ('build-windows', 'flutter build windows'),
        ):
            self.assertIn(command, yaml.dump(self.jobs[job]))

    def test_no_mobile_job_ignores_its_own_failure(self):
        for name, job in self.jobs.items():
            self.assertNotEqual(
                job.get('continue-on-error'), True,
                f'{name} would hide its own failure from the gate',
            )
            for step in job.get('steps', []):
                self.assertNotEqual(
                    step.get('continue-on-error'), True,
                    f'a step in {name} would hide its own failure',
                )


class MobileBackendContractCITests(SimpleTestCase):
    """
    The mobile<->Django contract E2E job.

    The Dart suite mocks its HTTP transport and the Django suite exercises
    views without a client, so both stay green while the agreement between them
    breaks -- a renamed field, a changed status code, a moved path. The
    `mobile-backend-e2e` job is the only place a real client talks to a real
    server, and `mobile-gate` refuses to pass without it.

    These tests pin that wiring so it cannot be quietly removed.
    """

    E2E_JOB = 'mobile-backend-e2e'

    def setUp(self):
        self.workflow = load_workflow('mobile.yml')
        self.jobs = self.workflow['jobs']
        self.e2e = self.jobs[self.E2E_JOB]
        self.gate = self.jobs['mobile-gate']
        self.gate_script = '\n'.join(
            s.get('run', '') for s in self.gate['steps']
        )
        self.gate_env = {
            k: v
            for s in self.gate['steps']
            for k, v in (s.get('env') or {}).items()
        }
        self.e2e_script = '\n'.join(
            s.get('run', '') for s in self.e2e['steps']
        )

    # ── the job must exist and be reachable ────────────────────────────────

    def test_e2e_job_exists(self):
        self.assertIn(self.E2E_JOB, self.jobs)

    def test_e2e_runs_on_contract_relevant_changes(self):
        self.assertEqual(
            self.e2e.get('if'),
            "needs.changes.outputs.contract == 'true'",
            'the E2E job must be gated on contract-relevant changes',
        )

    def test_change_detection_exposes_a_contract_output(self):
        self.assertIn('contract', self.jobs['changes'].get('outputs', {}))

    def test_every_contract_bearing_path_triggers_the_e2e(self):
        # Extracted from the `contract=` regex specifically, not from the whole
        # job: the native regex is a different (narrower) set, and asserting
        # against the combined text would let a path be dropped from the
        # contract list while still appearing in a comment or the other regex.
        detect = '\n'.join(
            s.get('run', '') for s in self.jobs['changes']['steps']
        )
        contract_line = next(
            (ln for ln in detect.splitlines() if ln.strip().startswith('contract=')),
            None,
        )
        self.assertIsNotNone(
            contract_line, 'the changes job must define a contract path set')
        # The line is a regex, so literal dots are backslash-escaped. Compare
        # against the unescaped form so the assertions read as real paths.
        contract_line = contract_line.replace('\\.', '.')
        for path in (
            'mobile/lib/core/api/',      # the client itself
            'mobile/lib/core/auth/',     # token/session models
            'mobile/lib/data/models/',   # response parsers
            'mobile/test_e2e/',          # the contract test
            'mobile_auth/',              # login/refresh/logout/sessions
            'api/app_views.py',          # /me/ and /app-config/
            'api/commercial_views.py',
            'api/logging_mixin.py',
            'api/urls.py',               # the paths themselves
            'api/authentication.py',     # auth semantics
            'api/permissions.py',
            'api/throttles.py',
            'entitlements.py',           # the entitlements map /me/ returns
        ):
            self.assertIn(
                path, contract_line,
                f'{path} can change the client<->server contract but would not '
                f'trigger the E2E test',
            )

    # ── mobile-gate must enforce it ────────────────────────────────────────

    def test_gate_depends_on_the_e2e_job(self):
        self.assertIn(
            self.E2E_JOB, self.gate['needs'],
            'mobile-gate must depend on the contract test, or an E2E failure '
            'would not block merge',
        )

    def test_gate_reads_the_e2e_result(self):
        self.assertIn(
            f"needs['{self.E2E_JOB}'].result",
            ' '.join(self.gate_env.values()),
        )

    def test_gate_fails_when_the_contract_test_fails(self):
        self.assertIn(
            'if [ "$E2E_RESULT" != "success" ]', self.gate_script,
            'a non-successful contract test must fail the gate',
        )

    def test_gate_rejects_a_skipped_e2e_when_the_contract_changed(self):
        # The dangerous case: contract files changed but the job did not run.
        # Treating that as a pass would silently disable the whole check.
        self.assertIn('CONTRACT_TOUCHED', self.gate_script)
        self.assertIn(
            'if [ "$E2E_RESULT" != "skipped" ]', self.gate_script,
            'when no contract change is detected the E2E job must be skipped, '
            'not merely non-failing',
        )

    # ── the test must be a REAL end-to-end test ────────────────────────────

    def test_e2e_starts_a_real_django_server(self):
        self.assertIn('manage.py runserver', self.e2e_script)
        self.assertIn('manage.py migrate', self.e2e_script)

    def test_e2e_waits_for_server_readiness(self):
        self.assertIn('app-config', self.e2e_script)
        self.assertIn('curl', self.e2e_script)

    def test_e2e_runs_the_real_flutter_client(self):
        self.assertIn('flutter test test_e2e/', self.e2e_script)
        self.assertIn('--dart-define=ECOIQ_ENV=dev', self.e2e_script)

    def test_e2e_uses_a_throwaway_database(self):
        env = ' '.join(
            str(v)
            for s in self.e2e['steps']
            for v in (s.get('env') or {}).values()
        )
        self.assertIn('e2e.sqlite3', env)
        self.assertNotIn('ecoiq.uk', self.e2e_script + env)

    def test_e2e_generates_credentials_rather_than_hardcoding_them(self):
        self.assertIn('openssl rand', self.e2e_script)
        self.assertIn('::add-mask::', self.e2e_script)

    def test_e2e_disables_only_external_side_effects(self):
        env = ' '.join(
            str(v)
            for s in self.e2e['steps']
            for v in (s.get('env') or {}).values()
        )
        # Mail captured in memory, Celery inline, billing unconfigured -- the
        # Django API behaviour under test stays real.
        self.assertIn('locmem.EmailBackend', env)
        self.assertIn('ECOIQ_BILLING_PROVIDER', str(self.e2e))

    def test_e2e_job_does_not_ignore_its_own_failure(self):
        self.assertNotEqual(self.e2e.get('continue-on-error'), True)
        for step in self.e2e['steps']:
            self.assertNotEqual(step.get('continue-on-error'), True)

    def test_the_load_bearing_commands_cannot_be_softened(self):
        # `|| true` is legitimate in this job three times -- polling for
        # readiness, tailing the log on failure, and killing the server -- so a
        # blanket ban would be both wrong and brittle. What must never be
        # softened are the commands whose failure IS the signal.
        for command in ('manage.py migrate --no-input',
                        'manage.py shell < .github/scripts/e2e_seed.py',
                        'flutter test test_e2e/'):
            for line in self.e2e_script.splitlines():
                if command in line:
                    self.assertNotIn(
                        '|| true', line,
                        f'{command!r} must fail the job when it fails',
                    )
                    self.assertNotIn('|| exit 0', line)

    def test_readiness_check_fails_the_job_when_the_server_never_starts(self):
        # The poll loop ends in a hard failure rather than proceeding to run
        # tests against a server that is not there.
        self.assertIn('Django did not become ready', self.e2e_script)
        self.assertIn('exit 1', self.e2e_script)


class MobileContractTestContentTests(SimpleTestCase):
    """
    The E2E test file itself. A contract test that stopped logging in, or that
    quietly reintroduced a mocked transport, would still pass CI while proving
    nothing.
    """

    def setUp(self):
        self.path = REPO_ROOT / 'mobile' / 'test_e2e' / 'contract_test.dart'
        self.source = self.path.read_text()

    def test_contract_test_exists(self):
        self.assertTrue(self.path.exists())

    def test_it_uses_the_production_api_client(self):
        self.assertIn('DioEcoIqApiClient', self.source)

    def test_it_does_not_mock_the_transport(self):
        # The whole value of this test is that nothing between the client and
        # Django is faked.
        for banned in ('MockEcoIqApiClient', 'DioAdapter', 'MockAdapter',
                       'http_mock', 'when(', 'registerFallbackValue'):
            self.assertNotIn(
                banned, self.source,
                f'{banned} would replace the real transport and make this a '
                f'unit test again',
            )

    def test_it_actually_logs_in(self):
        self.assertIn('client.login(', self.source)

    def test_it_exercises_the_authenticated_contract(self):
        for call in ('getMe(', 'listSessions(', 'refresh(', 'logout('):
            self.assertIn(call, self.source)

    def test_it_asserts_authentication_is_enforced(self):
        # A revoked/absent token must be rejected -- otherwise the test would
        # pass against a server that had accidentally become public.
        self.assertIn('401', self.source)
        self.assertIn('unauthorized', self.source)

    def test_it_refuses_to_run_against_production(self):
        self.assertIn("contains('localhost')", self.source)
        self.assertIn("isNot(contains('ecoiq.uk'))", self.source)

    def test_it_does_not_hardcode_credentials(self):
        self.assertIn('E2E_USERNAME', self.source)
        self.assertIn('E2E_PASSWORD', self.source)
        self.assertIn('Platform.environment', self.source)

    def test_the_seed_script_is_not_a_management_command(self):
        # A management command would be a permanent, callable path in the
        # deployed application. This must stay a CI-only script.
        self.assertFalse(
            (REPO_ROOT / 'core' / 'management' / 'commands' /
             'e2e_seed.py').exists(),
        )
        self.assertTrue((REPO_ROOT / '.github' / 'scripts' /
                         'e2e_seed.py').exists())

    def test_the_seed_script_refuses_a_non_e2e_database(self):
        seed = (REPO_ROOT / '.github' / 'scripts' / 'e2e_seed.py').read_text()
        self.assertIn("'e2e' not in db_name", seed)
        self.assertIn('refusing to seed', seed)
