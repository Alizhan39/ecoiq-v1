import logging
from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from .forms import AccessRequestForm, ReviewRequestForm, ReportRequestForm
from .models import AccessRequest, ProfileClaim, ReviewRequest

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
