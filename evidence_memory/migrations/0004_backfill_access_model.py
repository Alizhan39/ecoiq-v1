"""
feat/evidence-memory-hardening — classify existing EvidenceMemory rows into
the new structured access model. Additive-only: no row is deleted or has its
text/verification state rewritten; only the new project/originating_*/
visibility fields are populated.

Classification rules (safest-first, never optimistic):

- `gold_intelligence.GoldProject:<pk>` source_reference → project FK set
  directly from the pk (the reference IS the project). Stays
  'project_private' (the schema default already applied by 0003).

- `waste_to_value_capital_allocation_engine.VerifiedCapitalOutcome:<pk>`
  source_reference → originating_outcome + originating_decision FKs set from
  the real outcome row; project resolved via the same exact-name,
  ambiguity-refusing match used everywhere else
  (capital_guardian_handoff.find_matching_gold_project's semantics,
  re-implemented here against historical state because migrations must not
  import live service code). Unresolvable/ambiguous → project stays NULL and
  visibility becomes 'restricted_unresolved' — hidden from all cross-project
  retrieval until a human resolves it (MANUAL REVIEW NEEDED: admin filter
  visibility='restricted_unresolved').

- Every other row (harvester/company/country/agent/hikma/league memories)
  keeps the 'project_private' default with project NULL. These are
  company/country-scoped memories, not project evidence; project_private +
  no project simply means "not retrievable through the project evidence
  policy", which is exactly their current behaviour.

Reversal is a no-op on data (fields are dropped by reversing 0003).
"""
from django.db import migrations

PROJECT_PREFIX = 'gold_intelligence.GoldProject:'
OUTCOME_PREFIX = 'waste_to_value_capital_allocation_engine.VerifiedCapitalOutcome:'


def classify_existing_rows(apps, schema_editor):
    EvidenceMemory = apps.get_model('evidence_memory', 'EvidenceMemory')
    GoldProject = apps.get_model('gold_intelligence', 'GoldProject')
    VerifiedCapitalOutcome = apps.get_model('waste_to_value_capital_allocation_engine', 'VerifiedCapitalOutcome')

    for memory in EvidenceMemory.objects.exclude(source_reference='').iterator():
        ref = memory.source_reference

        if ref.startswith(PROJECT_PREFIX):
            pk = ref[len(PROJECT_PREFIX):]
            project = GoldProject.objects.filter(pk=pk).first() if pk.isdigit() else None
            if project is not None:
                memory.project = project
                memory.save(update_fields=['project'])
            continue

        if ref.startswith(OUTCOME_PREFIX):
            pk = ref[len(OUTCOME_PREFIX):]
            outcome = (
                VerifiedCapitalOutcome.objects.select_related('decision').filter(pk=pk).first()
                if pk.isdigit() else None
            )
            if outcome is None:
                # The outcome this memory was derived from no longer exists —
                # provenance is unresolvable, so it must never surface in
                # cross-project retrieval.
                memory.visibility = 'restricted_unresolved'
                memory.save(update_fields=['visibility'])
                continue
            memory.originating_outcome = outcome
            memory.originating_decision = outcome.decision
            project_name = (outcome.decision.project or '').strip()
            matches = list(GoldProject.objects.filter(name__iexact=project_name)[:2]) if project_name else []
            if len(matches) == 1:
                memory.project = matches[0]
                memory.save(update_fields=['originating_outcome', 'originating_decision', 'project'])
            else:
                # No match or ambiguous match — never guessed.
                memory.visibility = 'restricted_unresolved'
                memory.save(update_fields=['originating_outcome', 'originating_decision', 'visibility'])


class Migration(migrations.Migration):

    dependencies = [
        ('evidence_memory', '0003_evidencememory_organisation_and_more'),
        ('gold_intelligence', '0005_goldproject_organisation'),
    ]

    operations = [
        migrations.RunPython(classify_existing_rows, migrations.RunPython.noop),
    ]
