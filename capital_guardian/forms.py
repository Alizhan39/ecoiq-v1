"""
capital_guardian/forms.py — vertical-slice PR 1: manual project-evidence
intake for the Evidence Centre. Server-side validation only — the browser
form is a convenience, never the safeguard.
"""
from django import forms

from evidence_memory.models import EvidenceMemory

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
