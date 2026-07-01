from django import forms

from legacy_safe.models import LegacyProject, SourceDocument

DEFAULT_QUESTION = 'What is the full modernisation plan?'


class AskAgentForm(forms.Form):
    project = forms.ModelChoiceField(queryset=LegacyProject.objects.all())
    question = forms.CharField(initial=DEFAULT_QUESTION, widget=forms.TextInput)


class PermissionDemoForm(forms.Form):
    project = forms.ModelChoiceField(queryset=LegacyProject.objects.all())
    question = forms.CharField(initial=DEFAULT_QUESTION, widget=forms.TextInput)


class RevokeDocumentForm(forms.Form):
    source_document = forms.ModelChoiceField(
        queryset=SourceDocument.objects.filter(is_revoked=False),
    )
