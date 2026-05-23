from django import forms
from .models import Assessment

ALLOWED_EXTENSIONS = ('.pdf', '.txt', '.md')


class AssessmentUploadForm(forms.ModelForm):
    class Meta:
        model  = Assessment
        fields = ['company_name', 'uploaded_file', 'notes']
        labels = {
            'company_name':  'Company / Organisation name',
            'uploaded_file': 'Upload document (PDF or plain text)',
            'notes':         'Additional context (optional)',
        }
        widgets = {
            'company_name': forms.TextInput(attrs={'placeholder': 'e.g. Acme Corp'}),
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Any extra context for the analysis…'}),
        }

    def clean_uploaded_file(self):
        f = self.cleaned_data.get('uploaded_file')
        if f:
            name = f.name.lower()
            if not any(name.endswith(ext) for ext in ALLOWED_EXTENSIONS):
                raise forms.ValidationError('Only PDF, TXT, or MD files are accepted.')
            if f.size > 10 * 1024 * 1024:
                raise forms.ValidationError('File must be smaller than 10 MB.')
        return f
