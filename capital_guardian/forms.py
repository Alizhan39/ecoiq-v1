"""
capital_guardian/forms.py — vertical-slice PR 1: manual project-evidence
intake for the Evidence Centre; PR 3: human-reviewed value-loss
confirmation. Server-side validation only — the browser form is a
convenience, never the safeguard.
"""
from django import forms

from evidence_memory.models import EvidenceMemory
from waste_to_value_capital_allocation_engine.models import (
    INTERVENTION_TYPE_CHOICES, LOSS_TYPE_CHOICES, READINESS_CHOICES, RISK_LEVEL_CHOICES,
)

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
