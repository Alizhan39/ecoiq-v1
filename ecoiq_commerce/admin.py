from django.contrib import admin

from .models import (
    AddOn, BillingCustomer, CommercialEvent, Coupon, Entitlement, Feature,
    Invoice, InvoiceLineItem, LicenceAgreement, Organisation, OrganisationMembership,
    OrganisationSubscription, PaymentEvent, Plan, PlanFeature, Product,
    StripeCheckoutRecord, StripeDispute, StripeEvent, Subscription,
    SubscriptionAddOn, UsageLimit, UsageRecord,
)


class OrganisationMembershipInline(admin.TabularInline):
    model = OrganisationMembership
    extra = 0


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'country', 'member_count', 'created_at']
    search_fields = ['name', 'slug', 'billing_email']
    inlines = [OrganisationMembershipInline]

    @admin.display(description='Members')
    def member_count(self, obj):
        return obj.memberships.count()


class PlanInline(admin.TabularInline):
    model = Plan
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'key', 'product_type', 'status', 'sort_order']
    list_filter = ['product_type', 'status']
    search_fields = ['key', 'name']
    inlines = [PlanInline]


class PlanFeatureInline(admin.TabularInline):
    model = PlanFeature
    extra = 0


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'product', 'billing_period', 'price_display', 'is_public', 'api_tier']
    list_filter = ['product', 'billing_period', 'is_public']
    search_fields = ['key', 'name']
    inlines = [PlanFeatureInline]


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ['key', 'name', 'category']
    list_filter = ['category']
    search_fields = ['key', 'name']


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'status', 'current_period_end', 'cancel_at_period_end']
    list_filter = ['status', 'plan__product']
    search_fields = ['user__username']
    autocomplete_fields = []


@admin.register(OrganisationSubscription)
class OrganisationSubscriptionAdmin(admin.ModelAdmin):
    list_display = ['organisation', 'plan', 'status', 'seats', 'current_period_end']
    list_filter = ['status', 'plan__product']
    search_fields = ['organisation__name']


@admin.register(Entitlement)
class EntitlementAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'feature', 'granted_quantity', 'expires_at', 'granted_by']
    list_filter = ['feature']


@admin.register(UsageLimit)
class UsageLimitAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'feature', 'limit_value', 'period']


@admin.register(UsageRecord)
class UsageRecordAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'feature', 'used_quantity', 'period_start', 'period_end']
    list_filter = ['feature']
    readonly_fields = ['user', 'organisation', 'feature', 'period_start', 'period_end', 'used_quantity']

    def has_add_permission(self, request):
        return False  # only ever created by services.entitlements.record_usage()


@admin.register(AddOn)
class AddOnAdmin(admin.ModelAdmin):
    list_display = ['name', 'feature', 'extra_quantity', 'price_amount', 'currency', 'billing_period']


@admin.register(SubscriptionAddOn)
class SubscriptionAddOnAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'addon', 'quantity', 'active']


@admin.register(LicenceAgreement)
class LicenceAgreementAdmin(admin.ModelAdmin):
    list_display = ['organisation', 'product', 'agreement_type', 'status', 'requires_legal_review', 'white_label_allowed']
    list_filter = ['agreement_type', 'status', 'requires_legal_review']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        (None, {'fields': ('organisation', 'product', 'agreement_type', 'status')}),
        ('Scope', {'fields': ('start_date', 'end_date', 'geographical_scope', 'data_modules', 'white_label_allowed')}),
        ('Compliance', {'fields': ('requires_legal_review', 'legal_reviewed_by', 'legal_reviewed_at'),
                         'description': 'A licence involving white-labelling, resale, or transaction-related terms '
                                        'must not be treated as legally cleared until a human reviewer explicitly '
                                        'signs off here.'}),
        ('Admin', {'fields': ('signed_by', 'notes', 'created_at', 'updated_at')}),
    )


@admin.register(BillingCustomer)
class BillingCustomerAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'provider', 'default_currency', 'created_at']
    list_filter = ['provider']


class InvoiceLineItemInline(admin.TabularInline):
    model = InvoiceLineItem
    extra = 0


class PaymentEventInline(admin.TabularInline):
    model = PaymentEvent
    extra = 0


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['pk', 'billing_customer', 'amount_total', 'currency', 'status', 'issued_at', 'paid_at']
    list_filter = ['status', 'currency']
    inlines = [InvoiceLineItemInline, PaymentEventInline]


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_type', 'value', 'active', 'redeemed_count', 'max_redemptions']
    list_filter = ['discount_type', 'active']


@admin.register(CommercialEvent)
class CommercialEventAdmin(admin.ModelAdmin):
    list_display = ['event_type', 'user', 'organisation', 'product', 'plan', 'occurred_at']
    list_filter = ['event_type', 'product']
    readonly_fields = [f.name for f in CommercialEvent._meta.fields]
    date_hierarchy = 'occurred_at'

    def has_add_permission(self, request):
        return False  # only ever created by services.events.track_event()


# ── Stripe ───────────────────────────────────────────────────────────────────
# Both models are read-only in the admin. They are an audit trail of what
# Stripe told us, not something an operator should be able to edit: hand-
# flipping StripeEvent.status would let a real event be re-processed or
# silently skipped, and hand-setting StripeCheckoutRecord.access_granted
# would grant paid access with no payment behind it. Corrections belong in
# Stripe (replay the event from the Dashboard), not in this table.

@admin.register(StripeEvent)
class StripeEventAdmin(admin.ModelAdmin):
    list_display = ['stripe_event_id', 'event_type', 'status', 'livemode',
                    'received_at', 'processed_at']
    list_filter = ['status', 'event_type', 'livemode']
    search_fields = ['stripe_event_id', 'event_type']
    date_hierarchy = 'received_at'
    readonly_fields = [f.name for f in StripeEvent._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(StripeCheckoutRecord)
class StripeCheckoutRecordAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'mode', 'status', 'user', 'organisation',
                    'plan', 'amount_total', 'currency', 'access_granted', 'created_at']
    list_filter = ['mode', 'status', 'access_granted']
    search_fields = ['session_id', 'stripe_customer_id', 'stripe_subscription_id',
                     'stripe_payment_intent_id']
    date_hierarchy = 'created_at'
    readonly_fields = [f.name for f in StripeCheckoutRecord._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(StripeDispute)
class StripeDisputeAdmin(admin.ModelAdmin):
    list_display = ['dispute_id', 'status', 'amount', 'currency', 'access_suspended',
                    'previous_subscription_status', 'opened_at', 'closed_at']
    list_filter = ['status', 'access_suspended']
    search_fields = ['dispute_id', 'charge_id', 'payment_intent_id']
    readonly_fields = [f.name for f in StripeDispute._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
