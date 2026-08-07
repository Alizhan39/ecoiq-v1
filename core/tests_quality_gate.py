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


class MypyConfigTests(SimpleTestCase):

    def test_mypy_is_configured_with_the_django_plugin(self):
        mypy = load_pyproject()['tool']['mypy']
        self.assertIn('mypy_django_plugin.main', mypy['plugins'])
        self.assertEqual(
            load_pyproject()['tool']['django-stubs']['django_settings_module'],
            'ecoiq.settings')

    def test_no_global_error_suppression(self):
        mypy = load_pyproject()['tool']['mypy']
        # Either of these makes the baseline look better without changing what
        # is true, which is the opposite of the point.
        self.assertNotIn('ignore_errors', mypy)
        self.assertNotEqual(mypy.get('follow_imports'), 'skip')
        for override in mypy.get('overrides', []):
            with self.subTest(override.get('module')):
                self.assertNotIn('ignore_errors', override)

    def test_the_correctness_flags_stay_on(self):
        mypy = load_pyproject()['tool']['mypy']
        for flag in ('check_untyped_defs', 'no_implicit_optional',
                     'warn_unused_ignores', 'warn_redundant_casts',
                     'warn_unreachable', 'strict_equality'):
            with self.subTest(flag):
                self.assertIs(mypy.get(flag), True)

    def test_the_stage_1_surface_must_stay_fully_annotated(self):
        overrides = load_pyproject()['tool']['mypy']['overrides']
        strict = [o for o in overrides if o.get('disallow_untyped_defs')]
        self.assertTrue(strict, 'no module is held to full annotation')
        modules = {m for o in strict for m in o['module']}
        for module in ('core.client_origin', 'notifications.antispam.*'):
            with self.subTest(module):
                self.assertIn(module, modules)


class MypyCiTests(SimpleTestCase):

    def test_ci_runs_mypy_as_its_own_blocking_job(self):
        jobs = load_workflow()['jobs']
        self.assertIn('mypy', jobs)
        self.assertNotIn('continue-on-error', jobs['mypy'])
        for step in jobs['mypy']['steps']:
            with self.subTest(step.get('name')):
                self.assertNotIn('continue-on-error', step)

    def test_the_mypy_command_does_not_suppress_errors(self):
        runs = ' '.join((s.get('run') or '') for s in load_workflow()['jobs']['mypy']['steps'])
        self.assertIn('mypy', runs)
        for forbidden in ('--ignore-errors', '--follow-imports=skip', '--no-error-summary'):
            with self.subTest(forbidden):
                self.assertNotIn(forbidden, runs)

    def test_both_static_gates_precede_the_expensive_suite(self):
        needs = load_workflow()['jobs']['django-check'].get('needs')
        self.assertIn('ruff', needs)
        self.assertIn('mypy', needs)

    def test_mypy_and_stubs_are_pinned(self):
        text = (ROOT / 'requirements-dev.txt').read_text()
        for package in ('mypy==', 'django-stubs[compatible-mypy]=='):
            with self.subTest(package):
                self.assertEqual(
                    len([l for l in text.splitlines() if l.strip().startswith(package)]), 1)


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
        self.assertIn('ruff', load_workflow()['jobs']['django-check'].get('needs'))

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
