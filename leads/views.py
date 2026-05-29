import logging
from datetime import timedelta

from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings

from .forms import AccessRequestForm
from .models import AccessRequest

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
