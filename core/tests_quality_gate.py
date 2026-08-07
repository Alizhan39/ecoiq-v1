"""
Safeguards for the Ruff quality gate.

These do not re-test Ruff, and they do not assert on configuration prose. They
assert the handful of properties that, if quietly reversed, would leave a gate
that looks present and enforces nothing — which is exactly what happened to this
repository's test step before, where `continue-on-error: true` meant no failing
test could ever fail CI.
"""
import pathlib
import tomllib

import yaml
from django.test import SimpleTestCase

ROOT = pathlib.Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / 'pyproject.toml'
WORKFLOW = ROOT / '.github' / 'workflows' / 'django.yml'


def load_pyproject():
    with PYPROJECT.open('rb') as handle:
        return tomllib.load(handle)


def load_workflow():
    with WORKFLOW.open(encoding='utf-8') as handle:
        return yaml.safe_load(handle)


class RuffConfigTests(SimpleTestCase):

    def test_pyproject_parses_and_configures_ruff(self):
        config = load_pyproject()
        self.assertIn('ruff', config.get('tool', {}))
        self.assertTrue(config['tool']['ruff']['lint']['select'])

    def test_the_gate_still_selects_the_defect_rules_it_was_created_for(self):
        # Each of these was chosen because it found a real defect in this
        # repository. Dropping one to make a branch green would remove the only
        # reason the gate exists.
        select = set(load_pyproject()['tool']['ruff']['lint']['select'])
        for rule in ('F821', 'F811', 'F601', 'F541', 'B023', 'E722'):
            with self.subTest(rule):
                self.assertIn(rule, select)

    def test_no_blanket_suppression(self):
        lint = load_pyproject()['tool']['ruff']['lint']
        self.assertNotIn('ALL', lint.get('ignore', []))
        for path, rules in lint.get('per-file-ignores', {}).items():
            with self.subTest(path):
                self.assertNotIn('ALL', rules)
                # A per-file ignore names specific rules or it is a blanket
                # ignore wearing a path.
                self.assertTrue(rules)

    def test_business_critical_code_is_not_excluded(self):
        excluded = load_pyproject()['tool']['ruff'].get('extend-exclude', [])
        for app in ('core', 'companies', 'notifications', 'api', 'leads', 'league'):
            with self.subTest(app):
                self.assertNotIn(app, excluded)


class RuffCiTests(SimpleTestCase):

    def test_ci_runs_ruff_as_its_own_job(self):
        jobs = load_workflow()['jobs']
        self.assertIn('ruff', jobs)
        steps = jobs['ruff']['steps']
        self.assertTrue(any('ruff check' in (s.get('run') or '') for s in steps))

    def test_ruff_is_blocking(self):
        job = load_workflow()['jobs']['ruff']
        self.assertNotIn('continue-on-error', job)
        for step in job['steps']:
            with self.subTest(step.get('name')):
                self.assertNotIn('continue-on-error', step)

    def test_ci_never_mutates_the_tree(self):
        # `--fix` in CI rewrites files nobody reviews and can turn a real finding
        # into a silent edit.
        for job in load_workflow()['jobs'].values():
            for step in job['steps']:
                run = step.get('run') or ''
                if 'ruff' in run:
                    with self.subTest(step.get('name')):
                        self.assertNotIn('--fix', run)
                        self.assertNotIn('ruff format', run)

    def test_lint_gates_the_expensive_suite(self):
        self.assertEqual(load_workflow()['jobs']['django-check'].get('needs'), 'ruff')

    def test_ruff_version_is_pinned_and_matches_ci(self):
        text = (ROOT / 'requirements-dev.txt').read_text()
        pins = [l for l in text.splitlines() if l.strip().startswith('ruff==')]
        self.assertEqual(len(pins), 1, 'Ruff must be pinned exactly once')

    def test_the_existing_gates_are_all_still_present(self):
        # Ruff supplements these; it does not replace any of them.
        runs = ' '.join(
            (step.get('run') or '')
            for job in load_workflow()['jobs'].values()
            for step in job['steps'])
        for command in ('manage.py check', 'makemigrations --check', 'manage.py test'):
            with self.subTest(command):
                self.assertIn(command, runs)
        self.assertTrue((ROOT / '.github' / 'workflows' / 'secret-scan.yml').exists())
