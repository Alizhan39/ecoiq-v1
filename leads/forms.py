from django import forms
from .models import AccessRequest

# Tailwind classes applied to every widget
_INPUT = (
    'w-full px-4 py-3 rounded-xl text-sm text-slate-200 placeholder-slate-600 '
    'bg-white/[.045] border border-white/[.09] transition-colors duration-150 '
    'focus:outline-none focus:border-emerald-500/60 focus:ring-2 focus:ring-emerald-500/10'
)
_SELECT = _INPUT + ' cursor-pointer'
_TEXTAREA = _INPUT + ' resize-none leading-relaxed'


class AccessRequestForm(forms.ModelForm):
    # Honeypot — must remain empty on genuine submissions
    website = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'tabindex': '-1', 'autocomplete': 'off'}),
    )

    class Meta:
        model  = AccessRequest
        fields = [
            'full_name', 'company', 'work_email',
            'industry', 'facility_type', 'company_size',
            'challenge', 'message',
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={
                'placeholder': 'Jane Smith',
                'autocomplete': 'name',
            }),
            'company': forms.TextInput(attrs={
                'placeholder': 'Acme Chemicals Ltd',
                'autocomplete': 'organization',
            }),
            'work_email': forms.EmailInput(attrs={
                'placeholder': 'jane@acmechem.com',
                'autocomplete': 'email',
            }),
            'industry': forms.Select(),
            'facility_type': forms.TextInput(attrs={
                'placeholder': 'e.g. Continuous process refinery, Cold-chain warehouse',
            }),
            'company_size': forms.Select(),
            'challenge': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Describe your main operational challenge — energy losses, unplanned downtime, maintenance gaps, compliance pressure…',
            }),
            'message': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': "Anything else you'd like us to know? (optional)",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Apply Tailwind classes to every widget
        for name, field in self.fields.items():
            if name == 'website':
                continue
            if isinstance(field.widget, forms.Select):
                field.widget.attrs.setdefault('class', _SELECT)
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.setdefault('class', _TEXTAREA)
            else:
                field.widget.attrs.setdefault('class', _INPUT)

        # Blank choice for selects
        self.fields['industry'].choices    = [('', 'Select your industry…')]    + list(self.fields['industry'].choices)[1:]
        self.fields['company_size'].choices = [('', 'Select company size…')] + list(self.fields['company_size'].choices)[1:]

        # Mark optional fields
        self.fields['message'].required = False
        self.fields['message'].label    = 'Additional context (optional)'

    def clean_work_email(self):
        return self.cleaned_data['work_email'].strip().lower()

    def clean_challenge(self):
        challenge = self.cleaned_data['challenge'].strip()
        if len(challenge) < 30:
            raise forms.ValidationError(
                'Please provide at least a sentence describing your main challenge.'
            )
        return challenge

    def clean_full_name(self):
        name = self.cleaned_data['full_name'].strip()
        if len(name) < 2:
            raise forms.ValidationError('Please enter your full name.')
        return name
