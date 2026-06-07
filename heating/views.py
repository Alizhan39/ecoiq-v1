"""Khalifa Heat — public views."""
from django.shortcuts import render

from .models import HeatingPackage, HeatingApplication, HomeAssessment, CompanySponsorshipLead
from .forms import (
    CalculatorForm, HouseholdInquiryForm, CompanySponsorshipForm, AkimatPartnershipForm,
)
from .calculator import recommend, PACKAGE_PRICES, PACKAGE_LABELS


COMPANY_PACKAGES = [
    {'key': 'sponsor_10',  'name': 'Sponsor 10 Homes', 'budget': '24M–30M KZT',
     'desc': '10 verified retrofits, logo on materials, one EcoIQ impact report.', 'accent': 'green'},
    {'key': 'clean_street', 'name': 'Clean Street Pilot', 'budget': '65M–150M KZT',
     'desc': '25–50 homes on one street, launch event, media kit, two reports.', 'accent': 'blue'},
    {'key': 'coal_free',   'name': 'Coal-Free Village Pilot', 'budget': '260M–320M KZT',
     'desc': '100 homes, akimat co-launch, full impact study with winter monitoring.', 'accent': 'gold'},
    {'key': 'esg_partner', 'name': 'ESG Heat Partnership', 'budget': '300M+ KZT / year',
     'desc': 'Multi-year co-branded program with audited annual impact reporting.', 'accent': 'purple'},
]


def _client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR') or None


def _is_bot(request):
    # Honeypot may be unprefixed (hp_field) or form-prefixed (hh-hp_field, ak-hp_field).
    return any(k.endswith('hp_field') and v.strip() for k, v in request.POST.items())


def overview(request):
    packages = HeatingPackage.objects.filter(is_active=True)
    return render(request, 'heating/overview.html', {
        'packages': packages,
        'company_packages': COMPANY_PACKAGES,
    })


def packages(request):
    return render(request, 'heating/packages.html', {
        'packages': HeatingPackage.objects.filter(is_active=True),
        'company_packages': COMPANY_PACKAGES,
    })


def calculator(request):
    form = CalculatorForm(request.POST or None)
    result = None
    if request.method == 'POST' and form.is_valid():
        cd = form.cleaned_data
        result = recommend(
            area_m2=cd['area_m2'], insulation=cd['insulation'], rooms=cd['rooms'],
            has_radiators=(cd['has_radiators'] == 'yes'), electricity=cd['electricity'],
            available_kw=cd['available_kw'], package=cd['package'], install_type=cd['install_type'],
        )
        # Persist anonymous assessment for pipeline analytics.
        HomeAssessment.objects.create(
            area_m2=cd['area_m2'], insulation=cd['insulation'], rooms=cd['rooms'],
            has_radiators=(cd['has_radiators'] == 'yes'), electricity=cd['electricity'],
            available_kw=cd['available_kw'], selected_package=cd['package'],
            install_type=cd['install_type'], recommended_kw=result['recommended_kw'],
            estimated_cost_min=result['estimated_cost_min'] or None,
            estimated_cost_max=result['estimated_cost_max'] or None,
            hp_ready_recommended=result['hp_ready_recommended'],
            warnings='\n'.join(result['warnings']),
        )
        result['package_label'] = PACKAGE_LABELS.get(cd['package'], cd['package'])
    return render(request, 'heating/calculator.html', {'form': form, 'result': result})


def company_sponsorship(request):
    form = CompanySponsorshipForm(request.POST or None)
    submitted = False
    if request.method == 'POST':
        if _is_bot(request):
            return render(request, 'heating/company_sponsorship.html',
                          {'form': CompanySponsorshipForm(), 'company_packages': COMPANY_PACKAGES, 'submitted': True})
        if form.is_valid():
            lead = form.save(commit=False)
            lead.ip_address = _client_ip(request)
            lead.save()
            form = CompanySponsorshipForm()
            submitted = True
    return render(request, 'heating/company_sponsorship.html', {
        'form': form, 'company_packages': COMPANY_PACKAGES, 'submitted': submitted,
    })


def pilot_application(request):
    which = request.POST.get('form_type', '')
    household_form = HouseholdInquiryForm(prefix='hh')
    akimat_form = AkimatPartnershipForm(prefix='ak')
    submitted = ''

    if request.method == 'POST' and not _is_bot(request):
        if which == 'household':
            household_form = HouseholdInquiryForm(request.POST, prefix='hh')
            if household_form.is_valid():
                obj = household_form.save(commit=False)
                obj.lead_type = 'household'
                obj.ip_address = _client_ip(request)
                obj.save()
                household_form = HouseholdInquiryForm(prefix='hh')
                submitted = 'household'
        elif which == 'akimat':
            akimat_form = AkimatPartnershipForm(request.POST, prefix='ak')
            if akimat_form.is_valid():
                obj = akimat_form.save(commit=False)
                obj.lead_type = 'akimat'
                obj.ip_address = _client_ip(request)
                obj.save()
                akimat_form = AkimatPartnershipForm(prefix='ak')
                submitted = 'akimat'
    elif request.method == 'POST' and _is_bot(request):
        submitted = which or 'household'

    return render(request, 'heating/pilot_application.html', {
        'household_form': household_form, 'akimat_form': akimat_form, 'submitted': submitted,
    })
