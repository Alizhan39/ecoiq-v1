"""
seed_all_good_agent_definitions — scales GoodAgentDefinition from the 6
hand-tuned lenses (PR2) to all 114 canonical principles (PR3 Phase 23).

For any principle_id NOT already hand-tuned, creates a MINIMAL, validated
definition derived mechanically from core.esg_principles_data.PRINCIPLES:
domains=[category], search_questions=[question], evidence_requirements=
metrics, risk_flags=[signal] — every field copied verbatim from the
canonical source, nothing interpreted or invented. Marked
definition_quality='auto_generated', requires_human_review=True, exactly
as Phase 23 asks: "If canonical meaning is incomplete, mark
REQUIRES_HUMAN_REVIEW. Do not fabricate interpretation."

Idempotent: existing hand_tuned rows (created by seed_good_agent_definitions,
PR2) are never touched by this command. Re-running only refreshes the
auto-generated rows in case core.esg_principles_data.PRINCIPLES changes.
"""
import re

from django.core.management.base import BaseCommand

from core.esg_principles_data import PRINCIPLES
from good_agents.models import GoodAgentDefinition

_STOPWORDS = frozenset({'this', 'that', 'with', 'from', 'does', 'they', 'their', 'have', 'organisation', 'what'})


def _derive_signal_types(principle):
    """Mechanical keyword extraction from the canonical tagline — never interpreted beyond the source text."""
    words = re.findall(r'[a-zA-Z]+', principle['tagline'].lower())
    keywords = [w for w in words if len(w) > 3 and w not in _STOPWORDS]
    seen = []
    for w in keywords:
        if w not in seen:
            seen.append(w)
    return seen[:6]


class Command(BaseCommand):
    help = 'Scales GoodAgentDefinition from the 6 hand-tuned lenses to all 114 canonical principles.'

    def handle(self, *args, **options):
        hand_tuned_ids = set(
            GoodAgentDefinition.objects.filter(definition_quality='hand_tuned').values_list('principle_id', flat=True)
        )
        created = 0
        skipped_hand_tuned = 0
        for principle in PRINCIPLES:
            if principle['id'] in hand_tuned_ids:
                skipped_hand_tuned += 1
                continue
            _, was_created = GoodAgentDefinition.objects.update_or_create(
                principle_id=principle['id'],
                defaults=dict(
                    name=principle['title'],
                    category=principle['category'],
                    mission=principle['question'],
                    domains=[principle['category']],
                    signal_types=_derive_signal_types(principle),
                    search_questions=[principle['question']],
                    evidence_requirements=list(principle['metrics']),
                    risk_flags=[principle['signal']],
                    definition_quality='auto_generated',
                    requires_human_review=True,
                    is_active=True,
                ),
            )
            created += int(was_created)

        total = GoodAgentDefinition.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f'Scaled to {total}/114 GoodAgentDefinitions ({created} auto-generated this run, '
            f'{skipped_hand_tuned} hand-tuned rows preserved untouched).'
        ))
