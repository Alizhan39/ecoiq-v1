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

    # Stripe Price id (`price_…`) this plan is sold as. NOT a secret — a public
    # catalogue identifier. Blank means the plan is not self-serve purchasable
    # through Stripe (enterprise/contact-sales plans, or a plan whose price has
    # not been created in the Stripe Dashboard yet). Populate with
    # `manage.py sync_stripe_prices`, which copies the STRIPE_PRICE_* env vars
    # onto the matching plans rather than hard-coding ids in source.
    stripe_price_id = models.CharField(
        max_length=120, blank=True, db_index=True,
        help_text='Stripe Price id (price_…) — public identifier, never a secret')

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

    # Suffix shown after the price, e.g. "GBP 99.00/month". An explicit map,
    # not string surgery: `billing_period.rstrip("ly")` strips every trailing
    # "l"/"y" CHARACTER rather than the suffix, so "annual" became "annua".
    # It happened to be correct for "monthly" only, which is why it survived.
    _PERIOD_SUFFIXES = {
        'monthly': 'month',
        'annual': 'year',
        'usage': 'unit',
    }

    @property
    def price_display(self) -> str:
        if self.price_amount is None:
            return 'Contact Sales'
        if self.billing_period == 'one_time':
            return f'{self.currency} {self.price_amount:,.2f}'
        suffix = self._PERIOD_SUFFIXES.get(self.billing_period)
        if suffix is None:
            return f'{self.currency} {self.price_amount:,.2f}'
        return f'{self.currency} {self.price_amount:,.2f}/{suffix}'


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

    # Non-sensitive Stripe identifiers only (see StripeEvent's docstring for
    # the full "what we may and may not store" rule). No card data, no PII
    # beyond what the user already gave EcoIQ directly.
    stripe_subscription_id = models.CharField(max_length=120, blank=True, db_index=True)
    stripe_price_id = models.CharField(max_length=120, blank=True)

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

    stripe_subscription_id = models.CharField(max_length=120, blank=True, db_index=True)
    stripe_price_id = models.CharField(max_length=120, blank=True)

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
    # For provider='stripe' this holds the Stripe Customer id (`cus_…`).
    # Indexed because every inbound webhook resolves its owner through it.
    external_customer_id = models.CharField(max_length=120, blank=True, db_index=True)
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

    # Provider invoice id (`in_…` for Stripe). Blank for manually-issued
    # NullBillingProvider invoices. Not unique at the DB level because blank
    # is the common case; the webhook path upserts on this value explicitly.
    external_invoice_id = models.CharField(max_length=120, blank=True, db_index=True)
    # The PaymentIntent that settled this invoice. Recorded because a dispute
    # payload carries only a charge/payment_intent — this is the link back from
    # a chargeback to the subscription whose access must be suspended.
    external_payment_intent_id = models.CharField(max_length=120, blank=True, db_index=True)
    # Stripe's own hosted invoice/receipt page. Safe to show a customer — it is
    # a capability URL Stripe issues for exactly this purpose, and it means
    # EcoIQ never has to render or store invoice PDFs itself.
    hosted_invoice_url = models.URLField(max_length=500, blank=True)

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


COUPON_SCOPE_CHOICES = [
    ('manual', 'Manual / invoiced billing only'),
]


class Coupon(models.Model):
    """
    Discounts for NON-Stripe payment flows only.

    EcoIQ has two payment paths and they must not share a discount system,
    because two systems mean two answers to "what does this customer owe".
    The split is:

        Stripe Checkout      -> Stripe promotion codes (allow_promotion_codes)
        Manual / invoiced    -> this model

    Stripe is authoritative for anything it charges: a local Coupon row can
    neither reduce a Stripe price nor be redeemed against a Checkout session,
    and nothing in services/stripe_gateway.py reads this table. `scope` records
    that constraint in the schema rather than only in a comment, so the
    restriction survives someone adding a new code path later.
    """
    scope = models.CharField(
        max_length=10, choices=COUPON_SCOPE_CHOICES, default='manual',
        help_text='Manual/invoiced billing only. Stripe Checkout uses Stripe '
                   'promotion codes — create those in the Stripe Dashboard.')
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


# ── Stripe ───────────────────────────────────────────────────────────────────
# Two models back the Stripe integration. Everything else it needs already
# existed (BillingCustomer.external_customer_id, Subscription,
# OrganisationSubscription, Invoice, PaymentEvent) — see
# services/stripe_gateway.py, stripe_sync.py and stripe_webhooks.py.
#
# WHAT MAY BE STORED HERE: opaque Stripe identifiers (cus_/sub_/price_/in_/
# cs_/pi_/evt_), subscription status, period boundaries, cancellation state,
# and amounts. WHAT MAY NOT: card numbers, CVCs, expiry dates, raw payment
# method details of any kind. Stripe holds those; EcoIQ never receives them,
# because every card entry happens on Stripe-hosted Checkout and Portal pages.

STRIPE_EVENT_STATUS_CHOICES = [
    ('received', 'Received'),     # signature verified, handler not finished yet
    ('processed', 'Processed'),   # handler completed — never run again
    ('ignored', 'Ignored'),       # verified but not a type/owner we act on
    ('failed', 'Failed'),         # handler raised; safe for Stripe to retry
]


class StripeEvent(models.Model):
    """
    The idempotency ledger for inbound Stripe webhooks.

    Stripe guarantees at-least-once delivery, retries on any non-2xx, and can
    deliver the same event concurrently. Provisioning must therefore be keyed
    on the event id, not on the fact that a request arrived. The webhook view
    takes a row lock on this table before doing any work, so a duplicate
    delivery finds status='processed' and returns 200 without provisioning a
    second time.

    `payload_summary` deliberately stores a small allow-listed set of scalar
    identifiers rather than the full event body — same privacy stance as
    CommercialEvent.metadata (see services/events.py). The full payload is
    always retrievable from the Stripe Dashboard by event id if needed.
    """
    stripe_event_id = models.CharField(max_length=120, unique=True)
    event_type = models.CharField(max_length=80, db_index=True)
    api_version = models.CharField(max_length=40, blank=True)
    livemode = models.BooleanField(default=False)

    status = models.CharField(max_length=10, choices=STRIPE_EVENT_STATUS_CHOICES, default='received')
    payload_summary = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True)

    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-received_at']
        indexes = [models.Index(fields=['event_type', 'received_at'])]

    def __str__(self):
        return f'{self.stripe_event_id} ({self.event_type}, {self.status})'


STRIPE_CHECKOUT_MODE_CHOICES = [
    ('subscription', 'Subscription'),
    ('payment', 'One-Time Payment'),
]

STRIPE_CHECKOUT_STATUS_CHOICES = [
    ('created', 'Created'),      # session opened, customer may still abandon it
    ('completed', 'Completed'),  # checkout.session.completed received and verified
    ('expired', 'Expired'),      # Stripe expired the session unpaid
]


class StripeCheckoutRecord(models.Model):
    """
    A checkout session EcoIQ itself created, written BEFORE the customer is
    redirected to Stripe.

    Two jobs:

    1. It ties the session back to the authenticated user (and organisation)
       that started it, so an inbound `checkout.session.completed` provisions
       for the right owner even though the webhook arrives on a separate,
       unauthenticated connection. `client_reference_id` and session metadata
       carry the same ids, and the two are cross-checked on arrival.

    2. `access_granted` is the single flag the rest of the app reads to decide
       whether a one-time purchase was actually paid for. It is set ONLY by
       the verified webhook handler — never by the browser success redirect,
       which a customer can reach (or forge) without having paid.
    """
    session_id = models.CharField(max_length=200, unique=True)
    mode = models.CharField(max_length=12, choices=STRIPE_CHECKOUT_MODE_CHOICES)
    status = models.CharField(max_length=10, choices=STRIPE_CHECKOUT_STATUS_CHOICES, default='created')

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                              related_name='stripe_checkouts')
    organisation = models.ForeignKey(Organisation, null=True, blank=True, on_delete=models.CASCADE,
                                      related_name='stripe_checkouts')
    plan = models.ForeignKey(Plan, null=True, blank=True, on_delete=models.SET_NULL,
                              related_name='stripe_checkouts')

    stripe_price_id = models.CharField(max_length=120, blank=True)
    stripe_customer_id = models.CharField(max_length=120, blank=True)
    stripe_subscription_id = models.CharField(max_length=120, blank=True)
    stripe_payment_intent_id = models.CharField(max_length=120, blank=True)

    amount_total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=8, blank=True)

    access_granted = models.BooleanField(
        default=False,
        help_text='Set only by the verified webhook handler — never by the browser success redirect.')
    # Why access was taken away, so a dispute resolved in EcoIQ's favour can
    # restore only what a dispute removed — and never resurrect a refund.
    revocation_reason = models.CharField(
        max_length=10, blank=True,
        choices=[('refund', 'Refunded'), ('dispute', 'Disputed')])

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['user', 'created_at'])]

    def __str__(self):
        return f'{self.session_id} ({self.mode}, {self.status})'


DISPUTE_STATUS_CHOICES = [
    ('open', 'Open — funds withheld'),
    ('won', 'Won — funds returned to EcoIQ'),
    ('lost', 'Lost — funds returned to the cardholder'),
]


class StripeDispute(models.Model):
    """
    A chargeback, and the record of what EcoIQ suspended because of it.

    A dispute is not a refund. The cardholder's bank has pulled the funds
    pending an investigation that can take weeks and can go either way, so the
    right response is to *suspend* access, not delete the subscription — and
    then to restore exactly what was suspended if the dispute is won.

    `previous_subscription_status` is what makes that restoration honest.
    Without it, "won" would have to guess a status to restore to, and would
    happily reactivate a subscription that had independently been cancelled or
    had gone past_due for an unrelated failed payment. With it, a won dispute
    puts the subscription back precisely where it was and nowhere else.

    Keyed on `dispute_id` (unique), so the create/closed pair and any duplicate
    delivery of either converge on one row.
    """
    dispute_id = models.CharField(max_length=120, unique=True)
    charge_id = models.CharField(max_length=120, blank=True, db_index=True)
    payment_intent_id = models.CharField(max_length=120, blank=True, db_index=True)

    status = models.CharField(max_length=6, choices=DISPUTE_STATUS_CHOICES, default='open')
    reason = models.CharField(max_length=80, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=8, blank=True)

    checkout_record = models.ForeignKey(StripeCheckoutRecord, null=True, blank=True,
                                         on_delete=models.SET_NULL, related_name='disputes')
    subscription = models.ForeignKey(Subscription, null=True, blank=True,
                                      on_delete=models.SET_NULL, related_name='disputes')
    organisation_subscription = models.ForeignKey(OrganisationSubscription, null=True, blank=True,
                                                   on_delete=models.SET_NULL, related_name='disputes')

    # Captured at suspension time so a won dispute restores the exact prior
    # state instead of assuming 'active'.
    previous_subscription_status = models.CharField(max_length=10, blank=True)
    # And what we moved it TO. Restoration only proceeds when the subscription
    # is still sitting in this state — if anything else has changed it since
    # (an unrelated cancellation, a renewal failure), that newer fact wins.
    suspended_to_status = models.CharField(max_length=10, blank=True)
    access_suspended = models.BooleanField(default=False)

    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-opened_at']

    def __str__(self):
        return f'Dispute {self.dispute_id} ({self.status})'
