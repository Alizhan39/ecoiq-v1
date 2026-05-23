from django import forms
from .models import AuditSession

ALLOWED_EXTENSIONS = ('.pdf', '.txt', '.md', '.docx')


class AuditSessionForm(forms.ModelForm):
    class Meta:
        model  = AuditSession
        fields = ['facility_name', 'sector', 'location', 'facility_age',
                  'headcount', 'annual_revenue', 'uploaded_file', 'notes']
        labels = {
            'facility_name':  'Facility / Company name',
            'sector':         'Industry sector',
            'location':       'Location (city, country)',
            'facility_age':   'Facility age (years)',
            'headcount':      'Total headcount',
            'annual_revenue': 'Annual revenue (USD, optional)',
            'uploaded_file':  'Upload documents (PDF, TXT, DOCX)',
            'notes':          'Additional context for the auditor',
        }
        widgets = {
            'facility_name':  forms.TextInput(attrs={'placeholder': 'e.g. Acme Manufacturing — Plant 2'}),
            'location':       forms.TextInput(attrs={'placeholder': 'e.g. Detroit, MI, USA'}),
            'facility_age':   forms.NumberInput(attrs={'placeholder': '25', 'min': 0}),
            'headcount':      forms.NumberInput(attrs={'placeholder': '450', 'min': 1}),
            'annual_revenue': forms.NumberInput(attrs={'placeholder': '50000000', 'min': 0}),
            'notes':          forms.Textarea(attrs={'rows': 3,
                              'placeholder': 'Any specific concerns, prior audit findings, or focus areas…'}),
        }

    def clean_uploaded_file(self):
        f = self.cleaned_data.get('uploaded_file')
        if f:
            name = f.name.lower()
            if not any(name.endswith(ext) for ext in ALLOWED_EXTENSIONS):
                raise forms.ValidationError('Only PDF, TXT, MD, or DOCX files are accepted.')
            if f.size > 10 * 1024 * 1024:
                raise forms.ValidationError('File must be smaller than 10 MB.')
        return f
