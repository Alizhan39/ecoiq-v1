"""
EcoIQ Commercial Platform — shared foundation for every monetisation channel
(Data API, EcoIQ Lite/Professional, Project Marketplace, Research, Academy).

This is Phase 1 of the commercial architecture (see PART 15 of the spec this
was built against): products, plans, features, entitlements, usage metering,
organisations, and a provider-neutral billing skeleton. It deliberately does
NOT implement Marketplace/Academy/Report domain models yet — those get a
`Product` catalogue row with status='coming_soon' so the rest of the system
(entitlements, feature keys, the /products/ page) already knows about them,
without pretending they're operational.

Nothing here talks to a payment gateway. See services/billing.py for the
provider-neutral interface and its NullBillingProvider default.
"""
from django.conf import settings
from django.db import models


# ── Organisation ─────────────────────────────────────────────────────────────
# No Organisation model existed anywhere in the repo (confirmed by inspection
# before writing this file) — this is the first one, used by every B2B/B2B2C
# concept below (organisation subscriptions, API key ownership, licences).

class Organisation(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    billing_email = models.EmailField(blank=True)
    country = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


ORG_ROLE_CHOICES = [
    ('owner', 'Owner'),
    ('admin', 'Admin'),
    ('billing', 'Billing Contact'),
    ('member', 'Member'),
]


class OrganisationMembership(models.Model):
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='org_memberships')
    role = models.CharField(max_length=10, choices=ORG_ROLE_CHOICES, default='member')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('organisation', 'user')]
        ordering = ['organisation', 'role']

    def __str__(self):
        return f'{self.user.get_username()} @ {self.organisation.name} ({self.role})'


# ── Product catalogue ────────────────────────────────────────────────────────

PRODUCT_TYPE_CHOICES = [
    ('data_api', 'EcoIQ Data API'),
    ('lite', 'EcoIQ Lite'),
    ('professional', 'EcoIQ Professional'),
    ('marketplace', 'EcoIQ Project Marketplace'),
    ('academy', 'EcoIQ Academy'),
    ('research', 'EcoIQ Research'),
]

PRODUCT_STATUS_CHOICES = [
    ('active', 'Active'),            # fully operational — real entitlements/data behind it
    ('coming_soon', 'Coming Soon'),  # catalogued, no operational backend yet — never linked as if live
    ('disabled', 'Disabled'),
]


class Product(models.Model):
    key = models.SlugField(max_length=50, unique=True)
    product_type = models.CharField(max_length=20, choices=PRODUCT_TYPE_CHOICES)
    name = models.CharField(max_length=150)
    tagline = models.CharField(max_length=250, blank=True)
    description = models.TextField(blank=True)
    target_audience = models.TextField(blank=True, help_text='Who this product is for — shown on /products/')
    status = models.CharField(max_length=15, choices=PRODUCT_STATUS_CHOICES, default='coming_soon')
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name

    @property
    def is_operational(self) -> bool:
        return self.status == 'active'


BILLING_PERIOD_CHOICES = [
    ('monthly', 'Monthly'),
    ('annual', 'Annual'),
    ('one_time', 'One-Time'),
    ('usage', 'Usage-Based'),
    ('custom', 'Custom / Contact Sales'),
]


class Plan(models.Model):
    """
    A purchasable tier of a Product. Price is configurable here, never
    hard-coded in a template — see PART 2 of the spec.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='plans')
    key = models.SlugField(max_length=50)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    billing_period = models.CharField(max_length=10, choices=BILLING_PERIOD_CHOICES, default='monthly')
    price_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                        help_text='Null = "Contact Sales" / custom enterprise pricing')
    currency = models.CharField(max_length=8, default='USD')
    trial_days = models.PositiveIntegerField(default=0)
    is_public = models.BooleanField(default=True, help_text='Shown on /products/ and self-serve signup')
    sort_order = models.PositiveIntegerField(default=0)

    # Only meaningful for product_type='data_api' — maps this plan to the
    # existing api.APIKey.TIER_CHOICES so a subscription determines which
    # rate-limit tier a key gets, without duplicating the throttle config.
    api_tier = models.CharField(max_length=20, blank=True,
                                 help_text='Matches api.APIKey TIER_CHOICES (explorer/professional/enterprise)')

    requires_legal_review = models.BooleanField(
        default=False,
        help_text='Set True for any plan whose commercial terms involve transaction-based fees '
                   '(success fees, % introduction fees, etc.) — such a plan must never be sold or '
                   'activated for real customers until legal/compliance review clears it. See PART 2.')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['product', 'sort_order']
        unique_together = [('product', 'key')]

    def __str__(self):
        return f'{self.product.name} — {self.name}'

    @property
    def price_display(self) -> str:
        if self.price_amount is None:
            return 'Contact Sales'
        if self.billing_period == 'one_time':
            return f'{self.currency} {self.price_amount:,.2f}'
        return f'{self.currency} {self.price_amount:,.2f}/{self.billing_period.rstrip("ly")}'


# ── Features & entitlements ──────────────────────────────────────────────────

FEATURE_CATEGORY_CHOICES = [
    ('company_data', 'Company Data'),
    ('portfolio', 'Portfolio Intelligence'),
    ('screening', 'Ethical / Islamic Screening'),
    ('api', 'API Access'),
    ('reports', 'Research & Reports'),
    ('marketplace', 'Project Marketplace'),
    ('academy', 'Academy'),
]


class Feature(models.Model):
    """
    A gate-able capability. Referenced everywhere by its `key` string (e.g.
    'evidence_access') rather than by FK, so views/templates/API permission
    classes can check has_entitlement(user, 'evidence_access') without
    importing this model — mirrors how companies.investment_report already
    references classification keys as plain strings.
    """
    key = models.SlugField(max_length=60, unique=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=20, choices=FEATURE_CATEGORY_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['category', 'key']

    def __str__(self):
        return self.key


LIMIT_PERIOD_CHOICES = [
    ('monthly', 'Monthly'),
    ('annual', 'Annual'),
    ('unlimited', 'Unlimited'),
]


class PlanFeature(models.Model):
    """One row per (plan, feature): is it included, and with what quantity limit."""
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='plan_features')
    feature = models.ForeignKey(Feature, on_delete=models.CASCADE, related_name='plan_features')
    is_included = models.BooleanField(default=True)
    quantity_limit = models.PositiveIntegerField(null=True, blank=True,
                                                   help_text='Null = unlimited (when is_included and limit_period=unlimited)')
    limit_period = models.CharField(max_length=10, choices=LIMIT_PERIOD_CHOICES, default='unlimited')

    class Meta:
        unique_together = [('plan', 'feature')]
        ordering = ['plan', 'feature']

    def __str__(self):
        return f'{self.plan} — {self.feature.key} ({"included" if self.is_included else "excluded"})'


SUBSCRIPTION_STATUS_CHOICES = [
    ('trialing', 'Trialing'),
    ('active', 'Active'),
    ('past_due', 'Past Due'),
    ('cancelled', 'Cancelled'),
    ('expired', 'Expired'),
]


class Subscription(models.Model):
    """A user's subscription to a Plan. See OrganisationSubscription for the B2B equivalent."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name='subscriptions')
    status = models.CharField(max_length=10, choices=SUBSCRIPTION_STATUS_CHOICES, default='active')

    started_at = models.DateTimeField(auto_now_add=True)
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    trial_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    canceled_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f'{self.user.get_username()} — {self.plan} ({self.status})'

    @property
    def is_active(self) -> bool:
        return self.status in ('trialing', 'active')


class OrganisationSubscription(models.Model):
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name='organisation_subscriptions')
    status = models.CharField(max_length=10, choices=SUBSCRIPTION_STATUS_CHOICES, default='active')
    seats = models.PositiveIntegerField(null=True, blank=True)

    started_at = models.DateTimeField(auto_now_add=True)
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    trial_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    canceled_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f'{self.organisation.name} — {self.plan} ({self.status})'

    @property
    def is_active(self) -> bool:
        return self.status in ('trialing', 'active')


class Entitlement(models.Model):
    """
    A manual entitlement grant OUTSIDE the normal plan resolution — comp
    accounts, beta testers, a one-off unlock for a support case, etc.
    has_entitlement() checks these in addition to plan-derived access.
    Exactly one of user / organisation must be set (enforced in save()).
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                              on_delete=models.CASCADE, related_name='manual_entitlements')
    organisation = models.ForeignKey(Organisation, null=True, blank=True,
                                      on_delete=models.CASCADE, related_name='manual_entitlements')
    feature = models.ForeignKey(Feature, on_delete=models.CASCADE, related_name='manual_entitlements')
    granted_quantity = models.PositiveIntegerField(null=True, blank=True, help_text='Null = unlimited')
    expires_at = models.DateTimeField(null=True, blank=True)
    reason = models.CharField(max_length=250, blank=True)
    granted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        holder = self.user.get_username() if self.user else self.organisation.name
        return f'{holder} — {self.feature.key} (manual grant)'

    def save(self, *args, **kwargs):
        if bool(self.user_id) == bool(self.organisation_id):
            raise ValueError('Entitlement must have exactly one of user or organisation set.')
        super().save(*args, **kwargs)


class UsageLimit(models.Model):
    """
    A custom quota override for a specific subscription/organisation
    subscription — e.g. an enterprise deal negotiated 10,000 evidence
    lookups/month instead of the plan default. When absent, PlanFeature's
    quantity_limit is authoritative.
    """
    subscription = models.ForeignKey(Subscription, null=True, blank=True,
                                      on_delete=models.CASCADE, related_name='usage_limit_overrides')
    organisation_subscription = models.ForeignKey(OrganisationSubscription, null=True, blank=True,
                                                    on_delete=models.CASCADE, related_name='usage_limit_overrides')
    feature = models.ForeignKey(Feature, on_delete=models.CASCADE, related_name='usage_limit_overrides')
    limit_value = models.PositiveIntegerField(null=True, blank=True, help_text='Null = unlimited')
    period = models.CharField(max_length=10, choices=LIMIT_PERIOD_CHOICES, default='monthly')

    class Meta:
        ordering = ['feature']

    def __str__(self):
        return f'Custom limit — {self.feature.key}: {self.limit_value or "unlimited"}/{self.period}'

    def save(self, *args, **kwargs):
        if bool(self.subscription_id) == bool(self.organisation_subscription_id):
            raise ValueError('UsageLimit must have exactly one of subscription or organisation_subscription set.')
        super().save(*args, **kwargs)


class UsageRecord(models.Model):
    """
    Consumption counter for one (holder, feature, period). Incremented by
    services.entitlements.record_usage(). One row per period so history is
    preserved rather than reset in place.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                              on_delete=models.CASCADE, related_name='usage_records')
    organisation = models.ForeignKey(Organisation, null=True, blank=True,
                                      on_delete=models.CASCADE, related_name='usage_records')
    feature = models.ForeignKey(Feature, on_delete=models.CASCADE, related_name='usage_records')
    period_start = models.DateField()
    period_end = models.DateField()
    used_quantity = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-period_start']
        indexes = [models.Index(fields=['user', 'feature', 'period_start'])]

    def __str__(self):
        holder = self.user.get_username() if self.user else (self.organisation.name if self.organisation else '—')
        return f'{holder} — {self.feature.key}: {self.used_quantity} ({self.period_start})'


class AddOn(models.Model):
    key = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=150)
    feature = models.ForeignKey(Feature, on_delete=models.CASCADE, related_name='addons')
    extra_quantity = models.PositiveIntegerField(help_text='Additional quantity granted per period on top of the plan limit')
    price_amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=8, default='USD')
    billing_period = models.CharField(max_length=10, choices=BILLING_PERIOD_CHOICES, default='monthly')

    def __str__(self):
        return self.name


class SubscriptionAddOn(models.Model):
    subscription = models.ForeignKey(Subscription, null=True, blank=True,
                                      on_delete=models.CASCADE, related_name='addons')
    organisation_subscription = models.ForeignKey(OrganisationSubscription, null=True, blank=True,
                                                    on_delete=models.CASCADE, related_name='addons')
    addon = models.ForeignKey(AddOn, on_delete=models.PROTECT, related_name='subscription_addons')
    quantity = models.PositiveIntegerField(default=1)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if bool(self.subscription_id) == bool(self.organisation_subscription_id):
            raise ValueError('SubscriptionAddOn must have exactly one of subscription or organisation_subscription set.')
        super().save(*args, **kwargs)


LICENCE_TYPE_CHOICES = [
    ('standard', 'Standard'),
    ('enterprise', 'Enterprise'),
    ('white_label', 'White-Label'),
    ('api_data', 'API Data Licence'),
]

LICENCE_STATUS_CHOICES = [
    ('draft', 'Draft'),
    ('active', 'Active'),
    ('expired', 'Expired'),
    ('terminated', 'Terminated'),
]


class LicenceAgreement(models.Model):
    """
    Governs how an organisation may use EcoIQ data/branding beyond a plain
    subscription (white-label rights, geographic scope, which data modules
    are licensed). `requires_legal_review` defaults True and is never
    auto-cleared by application code — see PART 2's explicit instruction not
    to make unverified legal claims about monetisation activity.
    """
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE, related_name='licence_agreements')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='licence_agreements')
    agreement_type = models.CharField(max_length=15, choices=LICENCE_TYPE_CHOICES, default='standard')
    status = models.CharField(max_length=12, choices=LICENCE_STATUS_CHOICES, default='draft')

    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    geographical_scope = models.JSONField(default=list, blank=True, help_text='List of country codes, or [] = worldwide')
    data_modules = models.JSONField(default=list, blank=True, help_text='Which data modules are licensed')
    white_label_allowed = models.BooleanField(default=False)

    requires_legal_review = models.BooleanField(
        default=True,
        help_text='Must be explicitly cleared by a human reviewer before this licence can move to active status '
                   'if it involves white-labelling, resale, or transaction-related terms.')
    legal_reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                           on_delete=models.SET_NULL, related_name='+')
    legal_reviewed_at = models.DateTimeField(null=True, blank=True)

    signed_by = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.organisation.name} — {self.product.name} ({self.agreement_type})'


# ── Billing (provider-neutral — see services/billing.py) ────────────────────

BILLING_PROVIDER_CHOICES = [
    ('none', 'No Provider (Manual)'),
    ('stripe', 'Stripe'),
]


class BillingCustomer(models.Model):
    """
    One row per (user or organisation) that has ever been billed. Provider-
    specific IDs live here so swapping providers later doesn't touch
    Subscription/Invoice at all.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                              on_delete=models.CASCADE, related_name='billing_customer')
    organisation = models.ForeignKey(Organisation, null=True, blank=True,
                                      on_delete=models.CASCADE, related_name='billing_customer')
    provider = models.CharField(max_length=10, choices=BILLING_PROVIDER_CHOICES, default='none')
    external_customer_id = models.CharField(max_length=120, blank=True)
    default_currency = models.CharField(max_length=8, default='USD')
    tax_id = models.CharField(max_length=60, blank=True, help_text='VAT/GST/Tax ID, when applicable')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        holder = self.user.get_username() if self.user else (self.organisation.name if self.organisation else '—')
        return f'BillingCustomer({holder}, {self.provider})'

    def save(self, *args, **kwargs):
        if bool(self.user_id) == bool(self.organisation_id):
            raise ValueError('BillingCustomer must have exactly one of user or organisation set.')
        super().save(*args, **kwargs)


INVOICE_STATUS_CHOICES = [
    ('draft', 'Draft'),
    ('open', 'Open'),
    ('paid', 'Paid'),
    ('void', 'Void'),
    ('uncollectible', 'Uncollectible'),
]


class Invoice(models.Model):
    billing_customer = models.ForeignKey(BillingCustomer, on_delete=models.CASCADE, related_name='invoices')
    subscription = models.ForeignKey(Subscription, null=True, blank=True,
                                      on_delete=models.SET_NULL, related_name='invoices')
    organisation_subscription = models.ForeignKey(OrganisationSubscription, null=True, blank=True,
                                                    on_delete=models.SET_NULL, related_name='invoices')
    description = models.CharField(max_length=250, blank=True)
    amount_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=8, default='USD')
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=15, choices=INVOICE_STATUS_CHOICES, default='draft')

    issued_at = models.DateTimeField(null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Invoice #{self.pk} — {self.currency} {self.amount_total} ({self.status})'


class InvoiceLineItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='line_items')
    description = models.CharField(max_length=250)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f'{self.description} x{self.quantity}'


COUPON_DISCOUNT_TYPE_CHOICES = [('percent', 'Percent'), ('fixed', 'Fixed Amount')]


class Coupon(models.Model):
    code = models.CharField(max_length=40, unique=True)
    discount_type = models.CharField(max_length=10, choices=COUPON_DISCOUNT_TYPE_CHOICES, default='percent')
    value = models.DecimalField(max_digits=8, decimal_places=2, help_text='Percent (0-100) or fixed amount')
    currency = models.CharField(max_length=8, blank=True, help_text='Only used when discount_type=fixed')
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    max_redemptions = models.PositiveIntegerField(null=True, blank=True)
    redeemed_count = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.code

    @property
    def is_valid(self) -> bool:
        from django.utils import timezone
        if not self.active:
            return False
        now = timezone.now()
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        if self.max_redemptions is not None and self.redeemed_count >= self.max_redemptions:
            return False
        return True


PAYMENT_EVENT_STATUS_CHOICES = [('succeeded', 'Succeeded'), ('failed', 'Failed'), ('refunded', 'Refunded')]


class PaymentEvent(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payment_events')
    status = models.CharField(max_length=10, choices=PAYMENT_EVENT_STATUS_CHOICES)
    provider_reference = models.CharField(max_length=120, blank=True)
    failure_reason = models.CharField(max_length=250, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-occurred_at']

    def __str__(self):
        return f'PaymentEvent(invoice={self.invoice_id}, {self.status})'


# ── Commercial event tracking (PART 13) ─────────────────────────────────────

COMMERCIAL_EVENT_TYPES = [
    'trial_started', 'subscription_started', 'subscription_upgraded', 'subscription_cancelled',
    'report_viewed', 'report_purchased', 'course_enrolled', 'course_completed',
    'api_key_created', 'api_key_revoked', 'api_limit_reached',
    'project_submitted', 'investor_interest_created', 'introduction_approved',
]
COMMERCIAL_EVENT_TYPE_CHOICES = [(k, k.replace('_', ' ').title()) for k in COMMERCIAL_EVENT_TYPES]


class CommercialEvent(models.Model):
    """
    Structured, privacy-conscious commercial event log. `metadata` is
    intentionally constrained by services.events.track_event() to a small
    allow-listed set of scalar fields (plan key, amount, feature key, etc.)
    — never raw report content or private portfolio data. See that module's
    docstring for the retention/privacy rationale.
    """
    event_type = models.CharField(max_length=40, choices=COMMERCIAL_EVENT_TYPE_CHOICES)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                              on_delete=models.SET_NULL, related_name='commercial_events')
    organisation = models.ForeignKey(Organisation, null=True, blank=True,
                                      on_delete=models.SET_NULL, related_name='commercial_events')
    product = models.ForeignKey(Product, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    plan = models.ForeignKey(Plan, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    metadata = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-occurred_at']
        indexes = [models.Index(fields=['event_type', 'occurred_at'])]

    def __str__(self):
        return f'{self.event_type} @ {self.occurred_at:%Y-%m-%d %H:%M}'
