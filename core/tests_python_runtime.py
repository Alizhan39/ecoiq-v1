"""
One Python version, declared in three places, asserted to agree.

WHY THIS TEST EXISTS
--------------------
Production drifted onto a different interpreter than CI tested, and nothing
noticed. `render.yaml` declared 3.11.0, CI resolved "3.11" to 3.11.16, the
Celery worker ran 3.11, and the web service — which had no `PYTHON_VERSION` at
all — fell through to Render's default and ran **3.14.3**. Every dependency was
therefore installed and exercised on an interpreter no test had ever seen.

None of that was visible from the repository, because the repository's own
declarations disagreed with each other and no check compared them.

RENDER'S PRECEDENCE, WHICH IS WHY THESE THREE
---------------------------------------------
    1. the service's PYTHON_VERSION environment variable   (highest)
    2. .python-version in the repository root
    3. Render's default for the service's creation date    (lowest)

So `.python-version` is the repository's canonical declaration, and
`render.yaml` sets the env var that overrides it — they must agree or the
blueprint silently wins. CI is the third, because a version CI does not run is
a version nothing tests.

`runtime.txt` used to be a fourth declaration. It was removed rather than
corrected: Render does not read it, so it could drift indefinitely without ever
taking effect — the worst kind of configuration, one that looks authoritative
and is inert.

WHAT THIS DOES NOT CHECK
------------------------
The env var actually set on a Render service. That is dashboard state, not
repository state, and no test can see it. This pins what the repository claims;
`docs/architecture/reliability.md` records how to verify the running services.
"""
from __future__ import annotations

import re
from pathlib import Path

from django.test import SimpleTestCase

REPO_ROOT = Path(__file__).resolve().parent.parent

#: The single canonical runtime version. Changing Python means changing this
#: line and letting the assertions below tell you what else must move.
CANONICAL_PYTHON = '3.11.16'


def _python_version_file() -> str:
    return (REPO_ROOT / '.python-version').read_text().strip()


def _render_yaml_versions() -> list[str]:
    """Every PYTHON_VERSION value in the blueprint, commented blocks included."""
    text = (REPO_ROOT / 'render.yaml').read_text()
    return re.findall(r'key:\s*PYTHON_VERSION\s*\n\s*#?\s*value:\s*"([^"]+)"', text)


def _ci_versions() -> list[str]:
    text = (REPO_ROOT / '.github' / 'workflows' / 'django.yml').read_text()
    return re.findall(r'python-version:\s*"([^"]+)"', text)


class PythonRuntimeDeclarationTests(SimpleTestCase):

    def test_python_version_file_is_canonical(self):
        self.assertEqual(_python_version_file(), CANONICAL_PYTHON)

    def test_version_is_fully_qualified(self):
        """
        Render requires a fully qualified version for PYTHON_VERSION, and a
        bare "3.11" in CI resolves to whatever patch the runner happens to
        cache — which is how CI ended up on a different patch from the
        blueprint without anyone choosing it.
        """
        self.assertRegex(CANONICAL_PYTHON, r'^\d+\.\d+\.\d+$')

    def test_render_blueprint_agrees(self):
        versions = _render_yaml_versions()
        self.assertTrue(versions, 'no PYTHON_VERSION found in render.yaml')
        for found in versions:
            self.assertEqual(found, CANONICAL_PYTHON)

    def test_every_render_service_block_is_covered(self):
        """
        The blueprint carries commented-out worker and cron blocks. They are
        checked too: a block that is uncommented later must not resurrect an
        old interpreter.
        """
        self.assertGreaterEqual(len(_render_yaml_versions()), 4)

    def test_ci_pins_the_same_version(self):
        versions = _ci_versions()
        self.assertTrue(versions, 'no python-version found in django.yml')
        for found in versions:
            self.assertEqual(found, CANONICAL_PYTHON)

    def test_ci_pins_every_job(self):
        """A job left on a floating version tests a different interpreter."""
        self.assertGreaterEqual(len(_ci_versions()), 3)

    def test_runtime_txt_has_not_come_back(self):
        """
        Render does not read it. Reintroducing it adds a declaration that can
        disagree with the others while having no effect at all.
        """
        self.assertFalse((REPO_ROOT / 'runtime.txt').exists())

    def test_all_declarations_agree_with_each_other(self):
        """
        The property that actually matters, asserted directly rather than
        implied by the tests above.
        """
        declared = {
            '.python-version': [_python_version_file()],
            'render.yaml': _render_yaml_versions(),
            'django.yml': _ci_versions(),
        }
        flat = {v for values in declared.values() for v in values}
        self.assertEqual(
            flat, {CANONICAL_PYTHON},
            f'python runtime declarations disagree: {declared}')

    def test_the_interpreter_running_the_tests_matches(self):
        """
        Closes the loop: CI installs what django.yml pins, so if this passes in
        CI the pinned version is the one the suite actually ran on. Skipped
        locally, where a developer may reasonably be on another patch.
        """
        import os
        import sys

        if not os.environ.get('CI'):
            self.skipTest('local run — patch version is not pinned for developers')
        running = f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}'
        self.assertEqual(running, CANONICAL_PYTHON)
