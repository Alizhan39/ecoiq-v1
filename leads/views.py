import logging
from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.core.mail import send_mail
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from .forms import AccessRequestForm, EnterpriseEnquiryForm, InvestorEnquiryForm, ReviewRequestForm, ReportRequestForm
from .models import (
    AccessRequest, EnterpriseEnquiry, InvestorEnquiry, ProfileClaim, ReviewRequest,
    INVESTOR_ORGANISATION_TYPE_CHOICES, INVESTOR_INTEREST_TYPE_CHOICES, INVESTOR_SOURCE_COUNTRY_CHOICES,
)

logger = logging.getLogger(__name__)


# ── Starter draft defaults — shown in the preview when draft fields are empty ──

DRAFT_PLACEHOLDERS = {
    'draft_score_summary': (
        'Pending analyst review. EcoIQ will assess public data, governance signals, '
        'sustainability exposure, and Maqasid-aligned value creation.'
    ),
    'draft_risk_summary': (
        'Pending review of climate, governance, reputational, and transition risks.'
    ),
    'draft_recommendations': (
        'Pending preparation of practical actions for investor readiness and ethical transition.'
    ),
    'draft_roadmap': (
        'Pending roadmap across 30, 60, and 90-day implementation windows.'
    ),
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_client_ip(request):
    """Return the real client IP, honouring X-Forwarded-For from proxies."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def _is_rate_limited(ip):
    """True if this IP has submitted ≥ 3 times in the last 60 minutes."""
    if not ip:
        return False
    cutoff = timezone.now() - timedelta(hours=1)
    count = AccessRequest.objects.filter(ip_address=ip, created_at__gte=cutoff).count()
    return count >= 3


def _send_emails(instance, request):
    """
    Send two emails:
      1. Team notification to LEAD_NOTIFY_EMAIL
      2. Confirmation to the submitter

    Both use plain-text templates. Failures are logged but never surface to the user.
    """
    try:
        notify_email = getattr(settings, 'LEAD_NOTIFY_EMAIL', 'alizhan@ecoiq.uk')
        from_email   = getattr(settings, 'DEFAULT_FROM_EMAIL', 'EcoIQ <noreply@ecoiq.uk>')

        # ── Team notification ─────────────────────────────────────────────────
        notify_body = render_to_string('emails/access_request_notify.txt', {
            'instance': instance,
            'admin_url': request.build_absolute_uri(
                f'/admin/leads/accessrequest/{instance.pk}/change/'
            ),
        })
        send_mail(
            subject=f'[EcoIQ] New access request — {instance.full_name} ({instance.company})',
            message=notify_body,
            from_email=from_email,
            recipient_list=[notify_email],
            fail_silently=True,
        )

        # ── Submitter confirmation ────────────────────────────────────────────
        confirm_body = render_to_string('emails/access_request_confirm.txt', {
            'instance': instance,
        })
        send_mail(
            subject='EcoIQ assessment request received',
            message=confirm_body,
            from_email=from_email,
            recipient_list=[instance.work_email],
            fail_silently=True,
        )

    except Exception as exc:  # pragma: no cover
        # Never break the form on email failure — log and continue silently.
        logger.exception('Email send failed for AccessRequest pk=%s: %s', instance.pk, exc)


# ── Views ─────────────────────────────────────────────────────────────────────

def request_access(request):
    """
    GET/POST /request-access/
    "Request EcoIQ Investor Readiness Report" lead-capture form.
    Reuses the AccessRequest model via the simplified ReportRequestForm and
    redirects to the thank-you page on success.
    """
    form = ReportRequestForm()

    if request.method == 'POST':
        form = ReportRequestForm(request.POST)

        # Honeypot: if the hidden `hp_field` has any value, silently redirect
        # to the thank-you page so bots get no feedback about detection.
        # (Named `hp_field` — not `website` — so browser autofill cannot fill it
        # and silently drop genuine submissions.)
        if request.POST.get('hp_field', '').strip():
            return redirect('leads:thank_you')

        ip = _get_client_ip(request)

        if _is_rate_limited(ip):
            return render(request, 'leads/request_access.html', {
                'form':          form,
                'rate_limited':  True,
            })

        if form.is_valid():
            instance = form.save(commit=False)
            instance.ip_address = ip
            instance.save()

            _send_emails(instance, request)

            return redirect('leads:thank_you')

    return render(request, 'leads/request_access.html', {
        'form': form,
    })


def success(request):
    """Legacy success page — kept for backward compatibility / older links."""
    calendly_url = getattr(settings, 'CALENDLY_URL', '')
    return render(request, 'leads/success.html', {
        'calendly_url': calendly_url,
    })


def thank_you(request):
    """
    GET /request-access/thank-you/
    Confirmation page shown after an Investor Readiness Report request.
    """
    calendly_url = getattr(settings, 'CALENDLY_URL', '')
    return render(request, 'leads/thank_you.html', {
        'calendly_url': calendly_url,
    })


# ── Profile Claim ─────────────────────────────────────────────────────────────

def _send_claim_emails(claim, request):
    """
    Send two emails for a new ProfileClaim:
      1. Team notification → LEAD_NOTIFY_EMAIL
      2. Acknowledgement  → claimant's work_email
    Failures are logged and silenced — never shown to the user.
    """
    try:
        notify_email = getattr(settings, 'LEAD_NOTIFY_EMAIL', 'alizhan@ecoiq.uk')
        from_email   = getattr(settings, 'DEFAULT_FROM_EMAIL', 'EcoIQ <noreply@ecoiq.uk>')

        notify_body = render_to_string('emails/claim_notify.txt', {
            'claim':     claim,
            'admin_url': request.build_absolute_uri(
                f'/admin/leads/profileclaim/{claim.pk}/change/'
            ),
        })
        send_mail(
            subject=f'[EcoIQ] New profile claim {claim.ref} — {claim.full_name} ({claim.company_name_reported or claim.company_slug})',
            message=notify_body,
            from_email=from_email,
            recipient_list=[notify_email],
            fail_silently=True,
        )

        confirm_body = render_to_string('emails/claim_confirm.txt', {'claim': claim})
        send_mail(
            subject=f'Your EcoIQ profile claim — {claim.ref}',
            message=confirm_body,
            from_email=from_email,
            recipient_list=[claim.work_email],
            fail_silently=True,
        )
    except Exception as exc:           # pragma: no cover
        logger.exception('Claim email failed for ProfileClaim pk=%s: %s', claim.pk, exc)


@ensure_csrf_cookie
def claim_profile_page(request):
    """
    GET /request-access/claim/
    Renders the standalone claim-your-profile form.
    Accepts ?company=<slug> to pre-populate the company field.
    """
    company_slug = request.GET.get('company', '').strip()

    # Try to resolve a display name from the slug
    company_display = ''
    if company_slug:
        try:
            from league.models import Company
            co = Company.objects.filter(slug=company_slug).only('name').first()
            if co:
                company_display = co.name
        except Exception:
            pass

    return render(request, 'claim_profile.html', {
        'company_slug':    company_slug,
        'company_display': company_display or company_slug.replace('-', ' ').title(),
    })


@require_POST
def claim_profile_submit(request):
    """
    POST /request-access/claim/submit/
    AJAX-only endpoint — returns JSON.
    Validates, saves a ProfileClaim, and fires email notifications.
    """
    # Honeypot: populated → bot, silently accept
    if request.POST.get('website', '').strip():
        return JsonResponse({'success': True})

    ip = _get_client_ip(request)

    # Rate limit: 3 claims per IP per hour
    cutoff = timezone.now() - timedelta(hours=1)
    if ProfileClaim.objects.filter(ip_address=ip, created_at__gte=cutoff).count() >= 3:
        return JsonResponse(
            {'error': 'Too many submissions from this IP. Please try again later.'},
            status=429,
        )

    # Field extraction
    full_name    = request.POST.get('full_name',    '').strip()
    work_email   = request.POST.get('work_email',   '').strip()
    job_title    = request.POST.get('job_title',    '').strip()
    company_slug = request.POST.get('company_slug', '').strip()
    company_name = request.POST.get('company_name', '').strip()
    message      = request.POST.get('message',      '').strip()

    # Validation
    errors = {}
    if not full_name:
        errors['full_name'] = 'Full name is required.'
    if not work_email or '@' not in work_email or '.' not in work_email.split('@')[-1]:
        errors['work_email'] = 'A valid work email address is required.'
    if not job_title:
        errors['job_title'] = 'Job title is required.'
    if not company_slug and not company_name:
        errors['company_name'] = 'Company name is required.'

    if errors:
        return JsonResponse({'errors': errors}, status=400)

    claim = ProfileClaim(
        company_slug=company_slug,
        company_name_reported=company_name,
        full_name=full_name,
        work_email=work_email,
        job_title=job_title,
        message=message,
        ip_address=ip,
    )
    claim.save()   # ref auto-generated in save()

    _send_claim_emails(claim, request)

    return JsonResponse({'success': True, 'ref': claim.ref})


# ── EcoIQ Review Request ───────────────────────────────────────────────────────

def _is_rate_limited_review(ip: str) -> bool:
    """True if this IP has submitted ≥ 5 review requests in the last hour."""
    if not ip:
        return False
    cutoff = timezone.now() - timedelta(hours=1)
    return ReviewRequest.objects.filter(ip_address=ip, created_at__gte=cutoff).count() >= 5


def _send_review_emails(instance: 'ReviewRequest', request) -> None:
    """
    Fire two emails for a new ReviewRequest:
      1. Team notification → LEAD_NOTIFY_EMAIL
      2. Confirmation      → submitter's email
    Failures are logged and silenced — never surfaced to the user.
    """
    try:
        notify_email = getattr(settings, 'LEAD_NOTIFY_EMAIL', 'alizhan@ecoiq.uk')
        from_email   = getattr(settings, 'DEFAULT_FROM_EMAIL', 'EcoIQ <noreply@ecoiq.uk>')

        notify_body = render_to_string('emails/review_notify.txt', {
            'instance':  instance,
            'admin_url': request.build_absolute_uri(
                f'/admin/leads/reviewrequest/{instance.pk}/change/'
            ),
        })
        send_mail(
            subject=(
                f'[EcoIQ] New review request — {instance.get_request_type_display()} '
                f'({instance.name}, {instance.organisation})'
            ),
            message=notify_body,
            from_email=from_email,
            recipient_list=[notify_email],
            fail_silently=True,
        )

        confirm_body = render_to_string('emails/review_confirm.txt', {'instance': instance})
        send_mail(
            subject='Your EcoIQ review request — we\'ll be in touch within 48 hours',
            message=confirm_body,
            from_email=from_email,
            recipient_list=[instance.email],
            fail_silently=True,
        )

    except Exception as exc:   # pragma: no cover
        logger.exception('Email send failed for ReviewRequest pk=%s: %s', instance.pk, exc)


def request_review(request):
    """
    GET/POST /request-access/review/

    Renders the "Request EcoIQ Review" lead-capture form.
    Accepts an optional ?type= query param to pre-select the request type.
    Handles multipart/form-data for the optional sustainability report upload.
    """
    # Pre-select request type from query string (used by CTA deep-links)
    initial = {}
    rt = request.GET.get('type', '').strip()
    if rt:
        initial['request_type'] = rt

    form = ReviewRequestForm(initial=initial)

    if request.method == 'POST':
        # Honeypot check — silently redirect bots
        if request.POST.get('website', '').strip():
            return redirect('leads:review_success')

        ip   = _get_client_ip(request)
        form = ReviewRequestForm(request.POST, request.FILES)

        if _is_rate_limited_review(ip):
            return render(request, 'leads/review_request.html', {
                'form':         form,
                'rate_limited': True,
            })

        if form.is_valid():
            instance            = form.save(commit=False)
            instance.ip_address = ip
            instance.save()
            _send_review_emails(instance, request)
            return redirect('leads:review_success')

    calendly_url = getattr(settings, 'CALENDLY_URL', '')
    return render(request, 'leads/review_request.html', {
        'form':         form,
        'calendly_url': calendly_url,
    })


def review_success(request):
    """GET /request-access/review/success/ — thank-you page after form submission."""
    calendly_url = getattr(settings, 'CALENDLY_URL', '')
    return render(request, 'leads/review_success.html', {
        'calendly_url': calendly_url,
    })


# ── Staff-only draft report preview ────────────────────────────────────────────

@staff_member_required
def admin_report_preview(request, access_request_id):
    """
    GET /admin-report-preview/<access_request_id>/

    Staff-only internal preview of an Investor Readiness Report draft, rendered
    from an AccessRequest. Non-staff users are redirected to the admin login by
    the @staff_member_required decorator.

    Empty draft fields fall back to neutral "starter draft" placeholder text so
    the layout is always complete.
    """
    obj = get_object_or_404(AccessRequest, pk=access_request_id)

    drafts = {
        key: (getattr(obj, key) or '').strip() or placeholder
        for key, placeholder in DRAFT_PLACEHOLDERS.items()
    }

    return render(request, 'leads/admin_report_preview.html', {
        'obj':    obj,
        'drafts': drafts,
    })


# ── Staff-only client-facing report preview ────────────────────────────────────

# Professional placeholder for empty draft fields on the client-facing report.
CLIENT_DRAFT_PLACEHOLDER = 'Pending final analyst review.'

# The draft fields surfaced on the client report (internal_notes is deliberately excluded).
_CLIENT_DRAFT_FIELDS = (
    'draft_score_summary',
    'draft_risk_summary',
    'draft_recommendations',
    'draft_roadmap',
)


@staff_member_required
def client_report_preview(request, access_request_id):
    """
    GET /client-report-preview/<access_request_id>/

    Staff-only, client-facing version of the Investor Readiness Report rendered
    from an AccessRequest. Same source data as the internal draft preview, but
    with no internal notes, warnings, or admin-only language — suitable for
    printing / saving as PDF and sending to the client.

    Non-staff users are redirected to the admin login by @staff_member_required.
    Empty draft fields fall back to a professional "Pending final analyst
    review." placeholder.
    """
    obj = get_object_or_404(AccessRequest, pk=access_request_id)

    drafts = {
        key: (getattr(obj, key) or '').strip() or CLIENT_DRAFT_PLACEHOLDER
        for key in _CLIENT_DRAFT_FIELDS
    }

    return render(request, 'leads/client_report_preview.html', {
        'obj':    obj,
        'drafts': drafts,
    })


# ── Enterprise Enquiry (EcoIQ Enterprise Pricing page) ─────────────────────────

def _is_rate_limited_enterprise(ip: str) -> bool:
    """True if this IP has submitted ≥ 5 enterprise enquiries in the last hour."""
    if not ip:
        return False
    cutoff = timezone.now() - timedelta(hours=1)
    return EnterpriseEnquiry.objects.filter(ip_address=ip, created_at__gte=cutoff).count() >= 5


def _send_enterprise_emails(instance: 'EnterpriseEnquiry', request) -> None:
    """
    Fire two emails for a new EnterpriseEnquiry:
      1. Team notification → LEAD_NOTIFY_EMAIL
      2. Confirmation      → submitter's work email
    Failures are logged and silenced — never surfaced to the user.
    """
    try:
        notify_email = getattr(settings, 'LEAD_NOTIFY_EMAIL', 'alizhan@ecoiq.uk')
        from_email   = getattr(settings, 'DEFAULT_FROM_EMAIL', 'EcoIQ <noreply@ecoiq.uk>')

        notify_body = render_to_string('emails/enterprise_enquiry_notify.txt', {
            'instance':  instance,
            'admin_url': request.build_absolute_uri(
                f'/admin/leads/enterpriseenquiry/{instance.pk}/change/'
            ),
        })
        send_mail(
            subject=(
                f'[EcoIQ] New enterprise enquiry — {instance.get_preferred_engagement_display()} '
                f'({instance.full_name}, {instance.organisation})'
            ),
            message=notify_body,
            from_email=from_email,
            recipient_list=[notify_email],
            fail_silently=True,
        )

        confirm_body = render_to_string('emails/enterprise_enquiry_confirm.txt', {'instance': instance})
        send_mail(
            subject='EcoIQ Enterprise — we have received your enquiry',
            message=confirm_body,
            from_email=from_email,
            recipient_list=[instance.work_email],
            fail_silently=True,
        )

    except Exception as exc:   # pragma: no cover
        logger.exception('Email send failed for EnterpriseEnquiry pk=%s: %s', instance.pk, exc)


def enterprise_enquiry(request):
    """
    GET/POST /request-access/enterprise/

    The single enquiry form every CTA on the EcoIQ Enterprise Pricing page
    (/pricing/) routes to. Accepts an optional ?engagement= query param
    (matching leads.models.ENGAGEMENT_TYPE_CHOICES) to pre-select the
    dropdown — same deep-link convention as request_review's ?type=.
    Never accepts payment; this only opens a scoped commercial conversation.
    """
    initial = {}
    engagement = request.GET.get('engagement', '').strip()
    if engagement:
        initial['preferred_engagement'] = engagement

    form = EnterpriseEnquiryForm(initial=initial)

    if request.method == 'POST':
        # Honeypot: if the hidden `hp_field` has any value, silently redirect
        # to the thank-you page so bots get no feedback about detection.
        if request.POST.get('hp_field', '').strip():
            return redirect('leads:enterprise_enquiry_success')

        ip   = _get_client_ip(request)
        form = EnterpriseEnquiryForm(request.POST)

        if _is_rate_limited_enterprise(ip):
            return render(request, 'leads/enterprise_enquiry.html', {
                'form':         form,
                'rate_limited': True,
            })

        if form.is_valid():
            instance            = form.save(commit=False)
            instance.ip_address = ip
            instance.save()
            _send_enterprise_emails(instance, request)
            return redirect('leads:enterprise_enquiry_success')

    calendly_url = getattr(settings, 'CALENDLY_URL', '')
    return render(request, 'leads/enterprise_enquiry.html', {
        'form':         form,
        'calendly_url': calendly_url,
    })


def enterprise_enquiry_success(request):
    """GET /request-access/enterprise/success/ — confirmation page after an enterprise enquiry."""
    calendly_url = getattr(settings, 'CALENDLY_URL', '')
    return render(request, 'leads/enterprise_enquiry_success.html', {
        'calendly_url': calendly_url,
    })


# ── Investor Enquiry (GCC investor pages) ──────────────────────────────────────

# Query-string keys carried from a GCC investor page's CTA link straight
# through to the form's hidden fields (and, on submit, into InvestorEnquiry).
_INVESTOR_ATTRIBUTION_KEYS = (
    'source_page', 'source_country',
    'utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term',
)


def _is_rate_limited_investor(ip: str) -> bool:
    """True if this IP has submitted ≥ 5 investor enquiries in the last hour."""
    if not ip:
        return False
    cutoff = timezone.now() - timedelta(hours=1)
    return InvestorEnquiry.objects.filter(ip_address=ip, created_at__gte=cutoff).count() >= 5


def _send_investor_emails(instance: 'InvestorEnquiry', request) -> None:
    """
    Fire two emails for a new InvestorEnquiry:
      1. Team notification → LEAD_NOTIFY_EMAIL
      2. Confirmation      → submitter's work email
    Failures are logged and silenced — never surfaced to the user.
    """
    try:
        notify_email = getattr(settings, 'LEAD_NOTIFY_EMAIL', 'alizhan@ecoiq.uk')
        from_email   = getattr(settings, 'DEFAULT_FROM_EMAIL', 'EcoIQ <noreply@ecoiq.uk>')

        notify_body = render_to_string('emails/investor_enquiry_notify.txt', {
            'instance':  instance,
            'admin_url': request.build_absolute_uri(
                f'/admin/leads/investorenquiry/{instance.pk}/change/'
            ),
        })
        send_mail(
            subject=(
                f'[EcoIQ] New investor enquiry — {instance.get_type_of_interest_display()} '
                f'({instance.full_name}, {instance.organisation})'
            ),
            message=notify_body,
            from_email=from_email,
            recipient_list=[notify_email],
            fail_silently=True,
        )

        confirm_body = render_to_string('emails/investor_enquiry_confirm.txt', {'instance': instance})
        send_mail(
            subject='EcoIQ — we have received your investor enquiry',
            message=confirm_body,
            from_email=from_email,
            recipient_list=[instance.work_email],
            fail_silently=True,
        )

    except Exception as exc:   # pragma: no cover
        logger.exception('Email send failed for InvestorEnquiry pk=%s: %s', instance.pk, exc)


def investor_enquiry(request):
    """
    GET/POST /request-access/investors/[?lang=ar]

    The single enquiry form every GCC investor page (EN + AR — /gcc-investors/,
    /qatar/investors/, /saudi-arabia/investors/, /kuwait/investors/, and their
    /ar/ equivalents) routes to. Accepts an optional ?interest= query param
    (matching leads.models.INVESTOR_INTEREST_TYPE_CHOICES) to pre-select the
    dropdown, plus source_page/source_country/utm_* for attribution — see
    _INVESTOR_ATTRIBUTION_KEYS. ?lang=ar renders the form in Arabic/RTL (a
    display concern only — not persisted on InvestorEnquiry). Never accepts
    payment, share purchase, or an investment commitment; this only opens a
    scoped conversation.
    """
    is_arabic = request.GET.get('lang', '').strip().lower() == 'ar'

    initial = {}
    interest = request.GET.get('interest', '').strip()
    if interest:
        initial['type_of_interest'] = interest
    for key in _INVESTOR_ATTRIBUTION_KEYS:
        value = request.GET.get(key, '').strip()
        if value:
            initial[key] = value

    # Non-PII attribution surfaced to the template purely for client-side
    # analytics (investor_form_start) — never persisted separately from the
    # InvestorEnquiry row itself, and never includes name/email/phone/message.
    attribution = {key: initial.get(key, '') for key in _INVESTOR_ATTRIBUTION_KEYS}

    form = InvestorEnquiryForm(initial=initial)

    if request.method == 'POST':
        is_arabic = request.POST.get('lang', '').strip().lower() == 'ar'

        # Honeypot: if the hidden `hp_field` has any value, silently redirect
        # to the thank-you page so bots get no feedback about detection.
        if request.POST.get('hp_field', '').strip():
            return redirect(f"{reverse('leads:investor_enquiry_success')}{'?lang=ar' if is_arabic else ''}")

        ip   = _get_client_ip(request)
        form = InvestorEnquiryForm(request.POST)

        if _is_rate_limited_investor(ip):
            return render(request, 'leads/investor_enquiry.html', {
                'form':         form,
                'rate_limited': True,
                'is_arabic':    is_arabic,
                'attribution':  attribution,
            })

        if form.is_valid():
            instance            = form.save(commit=False)
            instance.ip_address = ip
            instance.save()
            _send_investor_emails(instance, request)
            # Handed to the success view via the session (never the URL) so the
            # investor_form_submit conversion event carries non-PII attribution
            # without leaking it into browser history/referrers, and so a
            # refresh of the success page can't re-fire it (session key is
            # popped exactly once — see investor_enquiry_success()).
            request.session['investor_conversion'] = {
                'source_country_page': instance.source_country,
                'organisation_type':   instance.organisation_type,
                'type_of_interest':    instance.type_of_interest,
                'utm_source':          instance.utm_source,
                'utm_medium':          instance.utm_medium,
                'utm_campaign':        instance.utm_campaign,
                'utm_content':         instance.utm_content,
                'utm_term':            instance.utm_term,
                'landing_page':        instance.source_page,
            }
            return redirect(f"{reverse('leads:investor_enquiry_success')}{'?lang=ar' if is_arabic else ''}")

    calendly_url = getattr(settings, 'CALENDLY_URL', '')
    return render(request, 'leads/investor_enquiry.html', {
        'form':         form,
        'calendly_url': calendly_url,
        'is_arabic':    is_arabic,
        'attribution':  attribution,
    })


def investor_enquiry_success(request):
    """
    GET /request-access/investors/success/[?lang=ar] — confirmation page after
    an investor enquiry.

    request.session.pop() both reads and clears 'investor_conversion' in one
    step, so the investor_form_submit conversion event fires exactly once per
    real submission: present on the redirect that follows a successful POST,
    gone on any subsequent refresh or direct/bookmarked visit to this URL.
    """
    calendly_url = getattr(settings, 'CALENDLY_URL', '')
    is_arabic = request.GET.get('lang', '').strip().lower() == 'ar'
    conversion = request.session.pop('investor_conversion', None)
    return render(request, 'leads/investor_enquiry_success.html', {
        'calendly_url': calendly_url,
        'is_arabic':    is_arabic,
        'conversion':   conversion,
    })


# ── Investor Enquiry — staff-only reporting dashboard ──────────────────────────

_ORG_TYPE_LABELS      = dict(INVESTOR_ORGANISATION_TYPE_CHOICES)
_INTEREST_TYPE_LABELS = dict(INVESTOR_INTEREST_TYPE_CHOICES)
_SOURCE_COUNTRY_LABELS = dict(INVESTOR_SOURCE_COUNTRY_CHOICES)

# How many days of the by-date submission breakdown to show.
_REPORT_WINDOW_DAYS = 30


@staff_member_required
def investor_enquiry_report(request):
    """
    GET /request-access/investors/report/

    Staff-only conversion-reporting dashboard for the GCC investor enquiry
    flow: enquiries by country, organisation type, type of interest, source
    page, UTM campaign, submissions by day (last 30 days), and totals.
    Read-only — no PII beyond what staff already see in the Django admin
    changelist for this same model. Non-staff users are redirected to the
    admin login by @staff_member_required.
    """
    qs = InvestorEnquiry.objects.all()

    by_country = [
        {'key': row['source_country'], 'label': _SOURCE_COUNTRY_LABELS.get(row['source_country'], row['source_country'] or '(not set)'), 'total': row['total']}
        for row in qs.values('source_country').annotate(total=Count('id')).order_by('-total')
    ]
    by_org_type = [
        {'key': row['organisation_type'], 'label': _ORG_TYPE_LABELS.get(row['organisation_type'], row['organisation_type']), 'total': row['total']}
        for row in qs.values('organisation_type').annotate(total=Count('id')).order_by('-total')
    ]
    by_interest = [
        {'key': row['type_of_interest'], 'label': _INTEREST_TYPE_LABELS.get(row['type_of_interest'], row['type_of_interest']), 'total': row['total']}
        for row in qs.values('type_of_interest').annotate(total=Count('id')).order_by('-total')
    ]
    by_source_page = list(
        qs.exclude(source_page='').values('source_page').annotate(total=Count('id')).order_by('-total')
    )
    by_utm_campaign = list(
        qs.exclude(utm_campaign='').values('utm_campaign').annotate(total=Count('id')).order_by('-total')
    )

    window_start = timezone.now() - timedelta(days=_REPORT_WINDOW_DAYS)
    by_date = list(
        qs.filter(created_at__gte=window_start)
          .annotate(day=TruncDate('created_at'))
          .values('day')
          .annotate(total=Count('id'))
          .order_by('-day')
    )

    return render(request, 'leads/investor_enquiry_report.html', {
        'total_conversions':   qs.count(),
        'total_last_30_days':  qs.filter(created_at__gte=window_start).count(),
        'by_country':          by_country,
        'by_org_type':         by_org_type,
        'by_interest':         by_interest,
        'by_source_page':      by_source_page,
        'by_utm_campaign':     by_utm_campaign,
        'by_date':             by_date,
        'report_window_days':  _REPORT_WINDOW_DAYS,
    })
