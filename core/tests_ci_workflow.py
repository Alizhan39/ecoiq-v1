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
