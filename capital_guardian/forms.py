"""
capital_guardian/forms.py — vertical-slice PR 1: manual project-evidence
intake for the Evidence Centre; PR 3: human-reviewed value-loss
confirmation; PR 6: human-entered implementation monitoring (capital trace,
milestones, implementation evidence, expected-vs-actual outcome recording).
Server-side validation only — the browser form is a convenience, never the
safeguard.
"""
from django import forms

from evidence_memory.models import EvidenceMemory
from gold_intelligence.models import MineTimelineMilestone
from waste_to_value_capital_allocation_engine.models import (
    EVIDENCE_QUALITY_CHOICES, INTERVENTION_TYPE_CHOICES, LOSS_TYPE_CHOICES, READINESS_CHOICES,
    RISK_LEVEL_CHOICES,
)

from capital_guardian.models import CapitalTraceEntry
from capital_guardian.services.execution_monitoring import MONITORING_MRV_STATUS_CHOICES

# 'expired' is a lifecycle outcome (a real expiry date passing), not
# something an intake form should ever assert about brand-new evidence.
INTAKE_VERIFICATION_CHOICES = [
    c for c in EvidenceMemory.VERIFICATION_STATUS_CHOICES if c[0] != 'expired'
]

# Honest classification of what the evidence content IS — stored on
# EvidenceMemory.is_demo (illustrative/demo => True). "Estimated" vs "real"
# is carried by the text itself plus verification_status; this field's job
# is to force the submitter to declare it rather than defaulting silently.
CLASSIFICATION_CHOICES = [
    ('real', 'Real (actual measured/documented data)'),
    ('estimated', 'Estimated (derived or approximate figure)'),
    ('illustrative', 'Illustrative / demo (not real data)'),
]


class ProjectEvidenceIntakeForm(forms.Form):
    title = forms.CharField(max_length=200)
    text = forms.CharField(widget=forms.Textarea, help_text='The evidence text or document summary.')
    source_url = forms.URLField(required=False)
    source_type = forms.ChoiceField(choices=EvidenceMemory.SOURCE_TYPE_CHOICES, initial='manual')
    document_category = forms.ChoiceField(choices=EvidenceMemory.DOCUMENT_CATEGORY_CHOICES, initial='other')
    verification_status = forms.ChoiceField(choices=INTAKE_VERIFICATION_CHOICES, initial='pending')
    review_tier = forms.ChoiceField(choices=EvidenceMemory.REVIEW_TIER_CHOICES, initial='uploaded')
    classification = forms.ChoiceField(choices=CLASSIFICATION_CHOICES, initial='estimated')

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get('verification_status')
        tier = cleaned.get('review_tier')
        classification = cleaned.get('classification')
        if status == 'verified' and tier in ('uploaded', 'system_checked'):
            self.add_error(
                'verification_status',
                'Verified status requires a human-reviewed or independently-verified review tier — '
                'evidence nobody has reviewed cannot be recorded as verified.',
            )
        if classification == 'illustrative' and status == 'verified':
            self.add_error(
                'verification_status',
                'Illustrative/demo evidence cannot be recorded as verified.',
            )
        return cleaned


# Vertical-slice PR 3 — same real/estimated/illustrative discipline as
# evidence intake above, applied to a human-confirmed value-loss record.
LOSS_CLASSIFICATION_CHOICES = CLASSIFICATION_CHOICES


class ValueLossConfirmationForm(forms.Form):
    """
    Human confirmation before creating a real OperationalLoss. Every field
    is either pre-filled from a reviewed default the human can edit, or left
    genuinely blank when no honest default exists — financial_loss_amount in
    particular is REQUIRED and never pre-filled with a guessed number.
    """
    title = forms.CharField(max_length=255)
    loss_type = forms.ChoiceField(choices=LOSS_TYPE_CHOICES)
    financial_loss_amount = forms.FloatField(
        min_value=0, help_text='Required — must be entered or confirmed by the human reviewer. Never pre-filled with a guessed figure.',
    )
    quantity_lost = forms.FloatField(required=False, min_value=0)
    unit = forms.CharField(max_length=40, required=False, help_text='e.g. tonnes coal, MWh, kWh')
    avoidability_score = forms.FloatField(min_value=0, max_value=100, initial=50.0)
    urgency_score = forms.FloatField(min_value=0, max_value=100, initial=50.0)
    classification = forms.ChoiceField(choices=LOSS_CLASSIFICATION_CHOICES, initial='estimated')


# Vertical-slice PR 4 — same real/estimated/illustrative discipline, applied
# to a human-reviewed InterventionOption.
INTERVENTION_CLASSIFICATION_CHOICES = CLASSIFICATION_CHOICES


class InterventionOptionForm(forms.Form):
    """
    Human-reviewed creation of one candidate intervention against an
    OperationalLoss. Every financial field defaults to 0/blank rather than a
    guessed figure — the human reviewer enters what's actually known.
    """
    title = forms.CharField(max_length=255)
    intervention_type = forms.ChoiceField(choices=INTERVENTION_TYPE_CHOICES)
    description = forms.CharField(widget=forms.Textarea, required=False)

    capex_estimate = forms.FloatField(min_value=0, initial=0)
    opex_change = forms.FloatField(initial=0, help_text='Positive = OPEX increases, negative = OPEX decreases.')
    estimated_loss_avoided = forms.FloatField(min_value=0, initial=0)
    estimated_value_recovered = forms.FloatField(min_value=0, initial=0)
    estimated_annual_savings = forms.FloatField(min_value=0, initial=0)
    estimated_payback_months = forms.FloatField(required=False, min_value=0)
    implementation_time = forms.CharField(max_length=60, required=False, help_text='e.g. "3-6 months"')

    technical_readiness = forms.ChoiceField(choices=READINESS_CHOICES, initial='not_ready')
    finance_readiness = forms.ChoiceField(choices=READINESS_CHOICES, initial='not_ready')
    mrv_readiness = forms.ChoiceField(choices=READINESS_CHOICES, initial='not_ready')
    risk_level = forms.ChoiceField(choices=RISK_LEVEL_CHOICES, initial='medium')
    classification = forms.ChoiceField(choices=INTERVENTION_CLASSIFICATION_CHOICES, initial='estimated')


# Vertical-slice PR 6 — human-entered implementation monitoring. Same
# real/estimated/illustrative discipline; every status field defaults to the
# least-claimed honest state (pending/not_started/unverified), never to an
# optimistic default.

class CapitalTraceEntryForm(forms.Form):
    """Staff-entered capital movement. Adapted to CapitalTraceEntry's actual
    fields — trace_id is server-generated (never user input), and
    related_equipment is intentionally omitted: EquipmentSpec.equipment_type
    has no generic/'other' choice (see PR6 audit), so equipment purchases for
    a non-mining project are tracked through `purpose`/`supplier` here
    instead of a mis-labelled EquipmentSpec row."""
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    amount_usd = forms.FloatField(min_value=0)
    currency = forms.CharField(max_length=10, initial='USD')
    purpose = forms.CharField(max_length=250, help_text='e.g. "Heat pump units — 50 homes", "Insulation contractor deposit".')
    supplier = forms.CharField(max_length=200, required=False)
    related_milestone = forms.ModelChoiceField(queryset=MineTimelineMilestone.objects.none(), required=False)

    approval_status = forms.ChoiceField(choices=CapitalTraceEntry.APPROVAL_STATUS_CHOICES, initial='pending')
    investor_approval_status = forms.ChoiceField(choices=CapitalTraceEntry.INVESTOR_APPROVAL_STATUS_CHOICES, initial='not_required')
    verification_status = forms.ChoiceField(choices=CapitalTraceEntry.VERIFICATION_STATUS_CHOICES, initial='unverified')
    insurance_status = forms.ChoiceField(choices=CapitalTraceEntry.INSURANCE_STATUS_CHOICES, initial='not_applicable')
    payment_status = forms.ChoiceField(choices=CapitalTraceEntry.PAYMENT_STATUS_CHOICES, initial='pending')
    is_demo = forms.BooleanField(required=False, initial=False, help_text='Check if this is illustrative/demo data, not a real capital movement.')

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        if project is not None:
            self.fields['related_milestone'].queryset = project.timeline_milestones.all()


class MilestoneForm(forms.Form):
    """Staff-entered project milestone. MineTimelineMilestone has no
    discrete title field (see PR6 audit) — the specific milestone name (e.g.
    "Household survey completed") belongs in `notes`; `phase` is the closest
    honest mining-lifecycle bucket it maps onto. Never defaults to a
    completed/verified status."""
    phase = forms.ChoiceField(choices=MineTimelineMilestone.PHASE_CHOICES)
    notes = forms.CharField(widget=forms.Textarea, help_text='The specific milestone, e.g. "Heat pump equipment delivered".')
    status = forms.ChoiceField(choices=MineTimelineMilestone.STATUS_CHOICES, initial='not_started')
    planned_start = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    planned_end = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    actual_start = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    actual_end = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    completion_pct_override = forms.FloatField(required=False, min_value=0, max_value=100)
    capital_required_usd = forms.FloatField(required=False, min_value=0)
    capital_released_usd = forms.FloatField(required=False, min_value=0)
    verification_required = forms.BooleanField(required=False, initial=False)
    verification_status = forms.ChoiceField(choices=MineTimelineMilestone.VERIFICATION_STATUS_CHOICES, initial='not_required')
    delay_risk = forms.ChoiceField(choices=[('', '—')] + list(MineTimelineMilestone.DELAY_RISK_CHOICES), required=False)
    responsible_party = forms.CharField(max_length=200, required=False)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('status') == 'complete' and not cleaned.get('actual_end'):
            self.add_error(
                'actual_end',
                'A milestone cannot be marked complete without a real actual completion date.',
            )
        return cleaned


# Reuses the exact same real/estimated/illustrative discipline as
# ProjectEvidenceIntakeForm above — implementation evidence is stored as an
# ordinary EvidenceMemory row (see evidence_memory.services.memory.
# create_memory_from_manual_project_evidence), never a second evidence model.
IMPLEMENTATION_DOCUMENT_CATEGORY_CHOICES = [
    c for c in EvidenceMemory.DOCUMENT_CATEGORY_CHOICES
    if c[0] in ('contract', 'inspection_report', 'fat_certificate', 'payment_confirmation', 'technical_report', 'other')
]


class ImplementationEvidenceForm(forms.Form):
    title = forms.CharField(max_length=200)
    text = forms.CharField(widget=forms.Textarea, help_text='Invoice detail, supplier record, inspection/commissioning note, measurement report, etc.')
    source_url = forms.URLField(required=False)
    document_category = forms.ChoiceField(choices=IMPLEMENTATION_DOCUMENT_CATEGORY_CHOICES, initial='other')
    verification_status = forms.ChoiceField(choices=INTAKE_VERIFICATION_CHOICES, initial='pending')
    review_tier = forms.ChoiceField(choices=EvidenceMemory.REVIEW_TIER_CHOICES, initial='uploaded')
    classification = forms.ChoiceField(choices=CLASSIFICATION_CHOICES, initial='estimated')

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get('verification_status')
        tier = cleaned.get('review_tier')
        classification = cleaned.get('classification')
        if status == 'verified' and tier in ('uploaded', 'system_checked'):
            self.add_error(
                'verification_status',
                'Verified status requires a human-reviewed or independently-verified review tier.',
            )
        if classification == 'illustrative' and status == 'verified':
            self.add_error('verification_status', 'Illustrative/demo evidence cannot be recorded as verified.')
        return cleaned


class OutcomeMonitoringForm(forms.Form):
    """
    Human-entered actual implementation results for one CapitalAllocationDecision.
    mrv_status deliberately EXCLUDES 'verified' (see capital_guardian.services.
    execution_monitoring.MONITORING_MRV_STATUS_CHOICES) — independent
    verification is a separate, later action taken through the existing
    VerifiedCapitalOutcome admin change form, never through this form.
    """
    capex_actual = forms.FloatField(min_value=0, help_text='Required — the real actual CAPEX spent so far.')
    opex_actual = forms.FloatField(required=False, min_value=0, initial=0)
    loss_avoided_actual = forms.FloatField(min_value=0, help_text='Required — the real actual loss avoided observed so far.')
    savings_actual = forms.FloatField(required=False, min_value=0, initial=0)
    mrv_status = forms.ChoiceField(choices=MONITORING_MRV_STATUS_CHOICES, initial='baseline_only')
    evidence_quality = forms.ChoiceField(choices=EVIDENCE_QUALITY_CHOICES, initial='medium')
    reviewer_note = forms.CharField(widget=forms.Textarea, required=False)
