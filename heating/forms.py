"""Khalifa Heat — public forms (calculator, household, company, akimat)."""
from django import forms

from .models import (
    HeatingApplication, CompanySponsorshipLead, HeatingPackage,
    INSULATION_CHOICES, ELECTRICITY_CHOICES, INSTALL_TYPE_CHOICES,
)
from .calculator import PACKAGE_LABELS

_INPUT = 'kh-input'
_SELECT = 'kh-input kh-select'
_TEXTAREA = 'kh-input kh-textarea'

# Calculator package choices (slugs used by calculator.PACKAGE_PRICES)
CALC_PACKAGE_CHOICES = [(k, v) for k, v in PACKAGE_LABELS.items()]


def _style(fields, skip=('hp_field',)):
    for name, f in fields.items():
        if name in skip:
            continue
        if isinstance(f.widget, forms.Textarea):
            f.widget.attrs.setdefault('class', _TEXTAREA)
        elif isinstance(f.widget, (forms.Select,)):
            f.widget.attrs.setdefault('class', _SELECT)
        else:
            f.widget.attrs.setdefault('class', _INPUT)


class CalculatorForm(forms.Form):
    """Boiler-sizing / package calculator inputs (not persisted directly)."""
    area_m2       = forms.IntegerField(min_value=10, max_value=2000, label='House area (m²)')
    insulation    = forms.ChoiceField(choices=INSULATION_CHOICES, label='Insulation quality')
    rooms         = forms.IntegerField(min_value=1, max_value=40, label='Number of rooms')
    has_radiators = forms.ChoiceField(choices=[('yes', 'Yes'), ('no', 'No')], label='Existing radiators')
    electricity   = forms.ChoiceField(choices=ELECTRICITY_CHOICES, label='Electricity type')
    available_kw  = forms.DecimalField(min_value=0, max_value=200, decimal_places=1, max_digits=5, label='Available power (kW)')
    package       = forms.ChoiceField(choices=CALC_PACKAGE_CHOICES, label='Package')
    install_type  = forms.ChoiceField(choices=INSTALL_TYPE_CHOICES, label='Installation type')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields)


class HouseholdInquiryForm(forms.ModelForm):
    """Household package inquiry."""
    hp_field = forms.CharField(required=False, widget=forms.TextInput(
        attrs={'tabindex': '-1', 'autocomplete': 'off', 'aria-hidden': 'true'}))

    class Meta:
        model = HeatingApplication
        fields = ['full_name', 'phone', 'email', 'location', 'package', 'install_type', 'message']
        widgets = {
            'full_name':   forms.TextInput(attrs={'placeholder': 'Your name', 'autocomplete': 'name'}),
            'phone':       forms.TextInput(attrs={'placeholder': '+7 …', 'autocomplete': 'tel'}),
            'email':       forms.EmailInput(attrs={'placeholder': 'you@email.com (optional)', 'autocomplete': 'email'}),
            'location':    forms.TextInput(attrs={'placeholder': 'City / village / district'}),
            'message':     forms.Textarea(attrs={'rows': 3, 'placeholder': 'Tell us about your home (optional)'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['package'].queryset = HeatingPackage.objects.filter(is_active=True)
        self.fields['package'].required = False
        self.fields['email'].required = False
        self.fields['phone'].required = True
        self.fields['message'].required = False
        self.fields['location'].required = False
        _style(self.fields)

    def clean_full_name(self):
        name = self.cleaned_data['full_name'].strip()
        if len(name) < 2:
            raise forms.ValidationError('Please enter your name.')
        return name


class CompanySponsorshipForm(forms.ModelForm):
    """Corporate / CSR / ESG sponsorship inquiry."""
    hp_field = forms.CharField(required=False, widget=forms.TextInput(
        attrs={'tabindex': '-1', 'autocomplete': 'off', 'aria-hidden': 'true'}))

    class Meta:
        model = CompanySponsorshipLead
        fields = ['company_name', 'contact_name', 'email', 'phone', 'package', 'budget_band', 'message']
        widgets = {
            'company_name': forms.TextInput(attrs={'placeholder': 'Company name', 'autocomplete': 'organization'}),
            'contact_name': forms.TextInput(attrs={'placeholder': 'Contact name', 'autocomplete': 'name'}),
            'email':        forms.EmailInput(attrs={'placeholder': 'you@company.com', 'autocomplete': 'email'}),
            'phone':        forms.TextInput(attrs={'placeholder': '+7 … (optional)', 'autocomplete': 'tel'}),
            'budget_band':  forms.TextInput(attrs={'placeholder': 'Indicative budget (optional)'}),
            'message':      forms.Textarea(attrs={'rows': 3, 'placeholder': 'What would you like to sponsor? (optional)'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['package'].required = False
        self.fields['phone'].required = False
        self.fields['budget_band'].required = False
        self.fields['message'].required = False
        _style(self.fields)


class AkimatPartnershipForm(forms.ModelForm):
    """Akimat / government partnership inquiry (reuses HeatingApplication)."""
    hp_field = forms.CharField(required=False, widget=forms.TextInput(
        attrs={'tabindex': '-1', 'autocomplete': 'off', 'aria-hidden': 'true'}))

    class Meta:
        model = HeatingApplication
        fields = ['organisation', 'full_name', 'email', 'phone', 'location', 'message']
        labels = {
            'organisation': 'Akimat / organisation',
            'full_name':    'Contact name',
            'location':     'Region / district',
        }
        widgets = {
            'organisation': forms.TextInput(attrs={'placeholder': 'Akimat / organisation'}),
            'full_name':    forms.TextInput(attrs={'placeholder': 'Contact name', 'autocomplete': 'name'}),
            'email':        forms.EmailInput(attrs={'placeholder': 'you@org.kz', 'autocomplete': 'email'}),
            'phone':        forms.TextInput(attrs={'placeholder': '+7 … (optional)', 'autocomplete': 'tel'}),
            'location':     forms.TextInput(attrs={'placeholder': 'Region / district'}),
            'message':      forms.Textarea(attrs={'rows': 3, 'placeholder': 'Scope and goals (optional)'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['organisation'].required = True
        self.fields['phone'].required = False
        self.fields['location'].required = False
        self.fields['message'].required = False
        _style(self.fields)
