from django import forms
from .models import AccessRequest, ReviewRequest

# CSS classes applied to every widget (styles defined in each template's <style> block)
_INPUT = 'form-input'
_SELECT = 'form-select'
_TEXTAREA = 'form-textarea'


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
            'country', 'role',
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
            'country': forms.TextInput(attrs={
                'placeholder': 'e.g. United Kingdom, Kazakhstan, Saudi Arabia',
                'autocomplete': 'country-name',
            }),
            'role': forms.Select(),
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

        # Apply widget CSS classes
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
        self.fields['role'].choices = [('', 'Select your role… (optional)')] + [c for c in self.fields['role'].choices if c[0]]

        # Mark optional fields
        self.fields['message'].required = False
        self.fields['message'].label    = 'Additional context (optional)'
        self.fields['country'].required = False
        self.fields['country'].label    = 'Country (optional)'
        self.fields['role'].required    = False
        self.fields['role'].label       = 'I am a… (optional)'

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


# ── ReviewRequestForm ─────────────────────────────────────────────────────────

_FILE_INPUT = 'form-file-input'

_MAX_UPLOAD_BYTES = 10 * 1024 * 1024   # 10 MB
_ALLOWED_MIMES    = {'application/pdf'}
_ALLOWED_EXTS     = {'.pdf'}


class ReviewRequestForm(forms.ModelForm):
    # Honeypot — must stay empty on real submissions
    website = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'tabindex': '-1', 'autocomplete': 'off'}),
    )

    class Meta:
        model  = ReviewRequest
        fields = [
            'name', 'organisation', 'email', 'country',
            'sector', 'request_type', 'message', 'sustainability_report',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Jane Smith',
                'autocomplete': 'name',
            }),
            'organisation': forms.TextInput(attrs={
                'placeholder': 'Acme Capital / Ministry of Energy',
                'autocomplete': 'organization',
            }),
            'email': forms.EmailInput(attrs={
                'placeholder': 'jane@acmecapital.com',
                'autocomplete': 'email',
            }),
            'country': forms.TextInput(attrs={
                'placeholder': 'e.g. Kazakhstan, United Arab Emirates, United Kingdom',
                'autocomplete': 'country-name',
            }),
            'sector': forms.Select(),
            'request_type': forms.Select(),
            'message': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': (
                    "Describe the company, country, or project you'd like us to review "
                    "and any specific questions or focus areas."
                ),
            }),
            'sustainability_report': forms.ClearableFileInput(attrs={
                'accept': '.pdf,application/pdf',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Apply widget CSS classes
        for name, f in self.fields.items():
            if name in ('website', 'sustainability_report'):
                continue
            if isinstance(f.widget, forms.Select):
                f.widget.attrs.setdefault('class', _SELECT)
            elif isinstance(f.widget, forms.Textarea):
                f.widget.attrs.setdefault('class', _TEXTAREA)
            else:
                f.widget.attrs.setdefault('class', _INPUT)

        self.fields['sustainability_report'].widget.attrs['class'] = _FILE_INPUT

        # Blank choices for selects
        self.fields['sector'].choices = [('', 'Select sector…')] + list(self.fields['sector'].choices)[1:]
        self.fields['request_type'].choices = [('', 'Select review type…')] + list(self.fields['request_type'].choices)[1:]

        # Optional fields
        self.fields['message'].required = False
        self.fields['message'].label    = 'Context or focus areas (optional)'
        self.fields['sustainability_report'].required = False
        self.fields['sustainability_report'].label    = 'Sustainability report (optional · PDF · max 10 MB)'

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if len(name) < 2:
            raise forms.ValidationError('Please enter your full name.')
        return name

    def clean_sustainability_report(self):
        f = self.cleaned_data.get('sustainability_report')
        if not f:
            return f
        # Size guard
        if f.size > _MAX_UPLOAD_BYTES:
            raise forms.ValidationError(
                f'File too large ({f.size // 1024 // 1024:.0f} MB). '
                'Maximum allowed size is 10 MB.'
            )
        # Extension guard
        import os as _os
        ext = _os.path.splitext(f.name)[1].lower()
        if ext not in _ALLOWED_EXTS:
            raise forms.ValidationError('Only PDF files are accepted.')
        return f


# ── ReportRequestForm ─────────────────────────────────────────────────────────
# Simplified, investor-facing form that reuses the AccessRequest model for the
# "Request EcoIQ Investor Readiness Report" workflow.

class ReportRequestForm(forms.ModelForm):
    # Honeypot — must stay empty on real submissions.
    # NOTE: do NOT name this 'website'/'url'/'email' etc. Browser autofill and
    # password managers ignore autocomplete="off" and will fill semantic names
    # like "website", which silently drops genuine leads. Use a neutral,
    # non-vocabulary name so autofill leaves it empty.
    hp_field = forms.CharField(
        required=False,
        label='',
        widget=forms.TextInput(attrs={
            'tabindex': '-1',
            'autocomplete': 'off',
            'aria-hidden': 'true',
        }),
    )

    class Meta:
        model  = AccessRequest
        fields = [
            'full_name', 'work_email', 'company', 'country',
            'target_entity', 'sector', 'role', 'product_interest',
            'message',
        ]
        labels = {
            'full_name':        'Name',
            'work_email':       'Email',
            'company':          'Organisation',
            'country':          'Country',
            'target_entity':    'Company or project to assess',
            'sector':           'Sector',
            'role':             'Your role',
            'product_interest': 'Product interest',
            'message':          'Message',
        }
        widgets = {
            'full_name':   forms.TextInput(attrs={'placeholder': 'Jane Smith', 'autocomplete': 'name'}),
            'work_email':  forms.EmailInput(attrs={'placeholder': 'jane@organisation.com', 'autocomplete': 'email'}),
            'company':     forms.TextInput(attrs={'placeholder': 'Acme Capital / Ministry of Energy', 'autocomplete': 'organization'}),
            'country':     forms.TextInput(attrs={'placeholder': 'e.g. United Kingdom, Kazakhstan, Saudi Arabia', 'autocomplete': 'country-name'}),
            'target_entity': forms.TextInput(attrs={'placeholder': 'e.g. KazMunayGas, or a named transition project'}),
            'sector':      forms.TextInput(attrs={'placeholder': 'e.g. Oil & Gas, Renewables, Manufacturing'}),
            'role':        forms.Select(),
            'product_interest': forms.Select(),
            'message':     forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Tell us what you would like assessed, your timeline, and any specific questions.',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Apply widget CSS classes
        for name, f in self.fields.items():
            if name == 'hp_field':
                continue
            if isinstance(f.widget, forms.Select):
                f.widget.attrs.setdefault('class', _SELECT)
            elif isinstance(f.widget, forms.Textarea):
                f.widget.attrs.setdefault('class', _TEXTAREA)
            else:
                f.widget.attrs.setdefault('class', _INPUT)

        # Blank prompts for selects
        self.fields['role'].choices = [('', 'Select your role…')] + [c for c in self.fields['role'].choices if c[0]]
        self.fields['product_interest'].choices = (
            [('', 'Select product interest…')] + [c for c in self.fields['product_interest'].choices if c[0]]
        )

        # Required vs optional
        self.fields['full_name'].required        = True
        self.fields['work_email'].required       = True
        self.fields['company'].required          = True
        self.fields['target_entity'].required    = True
        self.fields['country'].required          = False
        self.fields['sector'].required           = False
        self.fields['role'].required             = False
        self.fields['product_interest'].required = False
        self.fields['message'].required          = False

    def clean_work_email(self):
        return self.cleaned_data['work_email'].strip().lower()

    def clean_full_name(self):
        name = self.cleaned_data['full_name'].strip()
        if len(name) < 2:
            raise forms.ValidationError('Please enter your full name.')
        return name
