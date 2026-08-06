"""
ecoiq_commerce/billing_urls.py — mounted at /billing/ from the root urls.py.

Separate from urls.py (the /products/ catalogue) because these routes have a
different trust model: authenticated, owner-scoped billing actions plus one
public, signature-authenticated webhook.

The webhook path is fixed at exactly `/billing/webhook/` — it is configured
by hand in the Stripe Dashboard, so renaming it silently breaks payment
provisioning in production with no local test failure to warn you.
"""
from django.urls import path

from . import billing_views

app_name = 'billing'

urlpatterns = [
    path('plans/', billing_views.plans, name='plans'),
    path('manage/', billing_views.manage, name='manage'),

    path('checkout/subscription/', billing_views.checkout_subscription,
         name='checkout_subscription'),
    path('checkout/one-time/<slug:plan_key>/', billing_views.checkout_one_time,
         name='checkout_one_time'),

    path('portal/', billing_views.portal, name='portal'),

    path('success/', billing_views.success, name='success'),
    path('cancelled/', billing_views.cancelled, name='cancelled'),

    # Configured in the Stripe Dashboard — do NOT rename. See module docstring.
    path('webhook/', billing_views.webhook, name='webhook'),
]
