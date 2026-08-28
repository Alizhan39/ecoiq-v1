"""
What the repository says about production, held to what can be checked here.

WHY
---
`docs/operations/PRODUCTION_RUNBOOK.md` stated "Redis and Celery are NOT
deployed" and "that is the entire production estate. One web service and one
database." Both were false for four days: `ecoiq-keyvalue` and
`ecoiq-celery-worker` were created by hand in the Render dashboard on
2026-08-24, so `render.yaml` — which still carries them commented out — never
learned, and every document citing the blueprint as evidence inherited the
error. `ecoiq/settings.py` and the engineering backlog carried it too.

An operator reads the runbook when something is broken. Telling them a service
does not exist is worse than saying nothing about it.

WHAT THIS CAN AND CANNOT ASSERT
-------------------------------
A unit test cannot reach the Render API, and should not: a suite whose result
depends on a network is a suite that goes red for reasons unrelated to the
change under test — see company_intelligence's DNS flake for what that costs.

So this pins the two things that ARE local facts:

  * the repository does not repeat the claim that Redis and Celery are absent
    from production, in any of the four places it used to;
  * the claim that nothing runs on a SCHEDULE — which is still true, and is the
    one the product's public copy depends on — matches the code.
"""
import pathlib
import re

from django.conf import settings
from django.test import SimpleTestCase

ROOT = pathlib.Path(settings.BASE_DIR)
RUNBOOK = ROOT / 'docs/operations/PRODUCTION_RUNBOOK.md'

#: The sentences that were false. Each names a service as absent from
#: production; production runs all of them.
RETRACTED_CLAIMS = (
    'Redis and Celery are NOT deployed',
    'That is the entire production estate',
    'no Redis service is deployed',
    'Do not claim Redis or Celery as production infrastructure',
)

SEARCHED = (
    'docs/operations/PRODUCTION_RUNBOOK.md',
    'docs/engineering/django-improvement-backlog.md',
    'ecoiq/settings.py',
    'render.yaml',
)


def text(relative_path):
    return (ROOT / relative_path).read_text(encoding='utf-8')


class RetractedClaimsTests(SimpleTestCase):

    def test_no_file_still_asserts_redis_and_celery_are_absent(self):
        """
        Quoting the old claim to retract it is fine — the runbook does exactly
        that — so this looks for the claim asserted, not merely mentioned. A
        line that also says "used to", "was false", "until", "no longer" or
        "retained for the record" is a retraction, not a repetition.
        """
        retraction = re.compile(
            r'used to|was false|were false|until 2026|no longer|stopped being '
            r'true|retained for the record|premise now false|now wrong',
            re.I)
        offenders = []
        for relative_path in SEARCHED:
            lines = text(relative_path).splitlines()
            for number, line in enumerate(lines, 1):
                for claim in RETRACTED_CLAIMS:
                    if claim.lower() not in line.lower():
                        continue
                    # Prose wraps, so the retraction may sit on a neighbouring
                    # line. Judge the sentence, not the line.
                    window = '\n'.join(lines[max(0, number - 3):number + 2])
                    if not retraction.search(window):
                        offenders.append(
                            f'{relative_path}:{number}  {line.strip()[:80]}')
        self.assertEqual(
            offenders, [],
            'A file still states that Redis or Celery is absent from '
            'production. Both run there:\n  ' + '\n  '.join(offenders))

    def test_the_runbook_names_the_services_that_actually_run(self):
        body = text('docs/operations/PRODUCTION_RUNBOOK.md')
        for name in ('ecoiq-keyvalue', 'ecoiq-celery-worker'):
            self.assertIn(
                name, body,
                f'{name} runs in production and the runbook does not mention it.')

    def test_the_blueprint_says_it_is_not_the_inventory(self):
        """
        render.yaml cannot be fixed by a comment — closing the gap costs money
        and is the owner's call. It can at least stop being read as complete.
        """
        self.assertIn('DOES NOT DESCRIBE THE RUNNING ESTATE', text('render.yaml'))


class NothingRunsOnAScheduleTests(SimpleTestCase):
    """
    The claim the PUBLIC copy depends on. `/pricing/` says monitoring is
    "scheduler-ready rather than running", and that has to stay true in the
    code, not just in the runbook.
    """

    def test_there_is_no_celery_beat_schedule(self):
        skip = {'.venv', 'node_modules', '.git', '__pycache__', 'static', 'docs'}
        offenders = []
        for path in ROOT.rglob('*.py'):
            if any(part in skip or part.startswith('.') for part in path.parts):
                continue
            if path.name.startswith('tests'):
                continue
            body = path.read_text(encoding='utf-8', errors='replace')
            if 'beat_schedule' in body or 'CELERYBEAT_SCHEDULE' in body:
                offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(
            offenders, [],
            'A Celery beat schedule appeared in ' + ', '.join(offenders) +
            '. Periodic execution would make the public claim that monitoring '
            'is "scheduler-ready rather than running" false — update the '
            'pricing copy and the runbook in the same change.')

    def test_the_runbook_still_says_nothing_is_scheduled(self):
        self.assertIn('Nothing runs on a schedule',
                      text('docs/operations/PRODUCTION_RUNBOOK.md'))
