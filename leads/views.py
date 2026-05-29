import logging
from datetime import timedelta

from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from .forms import AccessRequestForm
from .models import AccessRequest, ProfileClaim

logger = logging.getLogger(__name__)


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
            subject='Your EcoIQ access request — we\'ll be in touch',
            message=confirm_body,
            from_email=from_email,
            recipient_list=[instance.work_email],
            fail_silently=True,
        )

    except Exception as exc:  # pragma: no cover
        logger.exception('Email send failed for AccessRequest pk=%s: %s', instance.pk, exc)


# ── Views ─────────────────────────────────────────────────────────────────────

def request_access(request):
    form = AccessRequestForm()

    if request.method == 'POST':
        form = AccessRequestForm(request.POST)

        # Honeypot: if the hidden `website` field has any value, silently redirect
        # to success so bots get no feedback about detection.
        if request.POST.get('website', '').strip():
            return redirect('leads:success')

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

            return redirect('leads:success')

    return render(request, 'leads/request_access.html', {
        'form': form,
    })


def success(request):
    calendly_url = getattr(settings, 'CALENDLY_URL', '')
    return render(request, 'leads/success.html', {
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
