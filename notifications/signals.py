"""
Connect existing lead/form models to the Admin Notification Hub.

Each public submission creates an AdminNotification on first save (created=True).
Handlers are defensive — any failure is logged and swallowed so a notification
problem can never break a real form submission.

Adding a future form is a one-liner: add an entry to SOURCES (model-backed) or
call notifications.models.create_notification(...) directly from the view.
"""
import logging

from django.apps import apps as django_apps
from django.db.models.signals import post_save

from .models import create_notification

logger = logging.getLogger(__name__)


def _g(obj, attr):
    """Safe getattr returning '' for missing/None."""
    if not attr:
        return ''
    return getattr(obj, attr, '') or ''


# Model-backed sources: 'app.Model' → config.
#   title:    callable(obj) -> str
#   summary:  callable(obj) -> str   (optional)
#   name/email/phone: attribute names on the instance (optional)
SOURCES = {
    'leads.AccessRequest': dict(
        type='access_request', priority='high',
        title=lambda o: f'Investor Readiness / Access — {o.full_name}',
        summary=lambda o: (getattr(o, 'target_entity', '') or getattr(o, 'message', '') or ''),
        name='full_name', email='work_email', phone=None,
    ),
    'leads.ReviewRequest': dict(
        type='review_request', priority='high',
        title=lambda o: f'Review request — {o.name} ({o.organisation})',
        summary=lambda o: getattr(o, 'message', ''),
        name='name', email='email', phone=None,
    ),
    'leads.ProfileClaim': dict(
        type='profile_claim', priority='normal',
        title=lambda o: f'Profile claim — {o.full_name}',
        summary=lambda o: (getattr(o, 'company_name_reported', '') or getattr(o, 'company_slug', '')),
        name='full_name', email='work_email', phone='phone',
    ),
    'leads.NewsletterSignup': dict(
        type='newsletter', priority='low',
        title=lambda o: f'Newsletter signup — {o.email}',
        summary=lambda o: getattr(o, 'organisation', ''),
        name='name', email='email', phone=None,
    ),
    'heating.CompanySponsorshipLead': dict(
        type='heating_company', priority='high',
        title=lambda o: f'Heating sponsorship — {o.company_name}',
        summary=lambda o: (o.get_package_display() if getattr(o, 'package', '') else ''),
        name='contact_name', email='email', phone='phone',
    ),
    'heating.HomeAssessment': dict(
        type='home_assessment', priority='low',
        title=lambda o: f'Home assessment — {o.area_m2} m² · {o.recommended_kw} kW',
        summary=lambda o: getattr(o, 'selected_package', ''),
        name=None, email=None, phone=None,
    ),
}


def _make_handler(cfg):
    def handler(sender, instance, created, **kwargs):
        if not created:
            return
        try:
            create_notification(
                cfg['title'](instance),
                source_type=cfg['type'],
                priority=cfg.get('priority', 'normal'),
                message=(cfg['summary'](instance) if cfg.get('summary') else ''),
                instance=instance,
                contact_name=_g(instance, cfg.get('name')),
                contact_email=_g(instance, cfg.get('email')),
                phone=_g(instance, cfg.get('phone')),
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception('notification handler failed for %s: %s', sender, exc)
    return handler


def _heating_application_handler(sender, instance, created, **kwargs):
    """HeatingApplication routes to a source_type based on lead_type."""
    if not created:
        return
    try:
        lead_type = getattr(instance, 'lead_type', 'household')
        mapping = {
            'household': ('heating_household', 'normal', 'Heating household application'),
            'akimat':    ('heating_akimat', 'high', 'Akimat / partnership lead'),
            'company':   ('heating_company', 'high', 'Heating company lead'),
        }
        stype, priority, label = mapping.get(lead_type, ('heating_household', 'normal', 'Heating application'))
        create_notification(
            f'{label} — {instance.full_name}',
            source_type=stype,
            priority=priority,
            message=(getattr(instance, 'message', '') or getattr(instance, 'location', '') or ''),
            instance=instance,
            contact_name=_g(instance, 'full_name'),
            contact_email=_g(instance, 'email'),
            phone=_g(instance, 'phone'),
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception('heating application notification failed: %s', exc)


def connect():
    """Wire post_save signals for every available source model."""
    for path, cfg in SOURCES.items():
        app_label, model_name = path.split('.')
        try:
            model = django_apps.get_model(app_label, model_name)
        except Exception:
            continue  # app/model not installed — skip safely
        post_save.connect(_make_handler(cfg), sender=model,
                          dispatch_uid=f'notif_{path}', weak=False)

    try:
        ha = django_apps.get_model('heating', 'HeatingApplication')
        post_save.connect(_heating_application_handler, sender=ha,
                          dispatch_uid='notif_heating_application', weak=False)
    except Exception:
        pass
