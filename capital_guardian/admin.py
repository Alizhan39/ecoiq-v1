"""capital_guardian/admin.py — the smallest stable observability solution for
Capital Guardian, matching this platform's Admin-first convention.

Phase 2: `save_model` is overridden wherever a real person edits a tracked
field through this admin, stashing `request.user` on the instance as
`_cg_changed_by` before saving so capital_guardian/signals.py's Audit
History entries can honestly attribute the change to a real user instead of
leaving `changed_by` blank."""
from django.contrib import admin, messages

from capital_guardian.models import (
    AuditLogEntry, CapitalTraceEntry, OperationalSnapshot, ProjectGovernance, RedFlag, RedFlagRuleConfig,
)


class ChangedByAdminMixin:
    def save_model(self, request, obj, form, change):
        obj._cg_changed_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ProjectGovernance)
class ProjectGovernanceAdmin(ChangedByAdminMixin, admin.ModelAdmin):
    list_display = ('project', 'founder_holdco_pct', 'investor_spv_pct', 'active_controls_count', 'is_demo')
    list_filter = ('is_demo',)


@admin.register(CapitalTraceEntry)
class CapitalTraceEntryAdmin(admin.ModelAdmin):
    list_display = (
        'trace_id', 'project', 'date', 'amount_usd', 'purpose', 'approval_status',
        'investor_approval_status', 'verification_status', 'payment_status',
    )
    list_filter = ('approval_status', 'investor_approval_status', 'verification_status', 'payment_status', 'project')
    search_fields = ('trace_id', 'purpose', 'supplier')
    readonly_fields = ('trace_id',)


@admin.register(RedFlag)
class RedFlagAdmin(admin.ModelAdmin):
    list_display = (
        'project', 'category', 'severity', 'resolution_status', 'actual_value', 'threshold_value',
        'capital_exposure_usd', 'detected_at',
    )
    list_filter = ('severity', 'category', 'resolution_status', 'project')
    search_fields = ('description', 'category')
    readonly_fields = ('rule_key', 'detected_at')
    actions = ['acknowledge_selected', 'resolve_selected', 'mark_under_review_selected', 'mark_false_positive_selected']

    def has_add_permission(self, request):
        # Rows are only ever created by the deterministic rule engine
        # (services/red_flag_engine.py), never by hand.
        return False

    def _bulk_transition(self, request, queryset, resolution_status, verb):
        # Iterates and calls .save() (rather than queryset.update()) so
        # capital_guardian/signals.py's Audit History instrumentation — which
        # only observes real model saves — sees every one of these changes.
        updated = 0
        for flag in queryset:
            flag.resolution_status = resolution_status
            flag.acknowledged_by = request.user
            flag._cg_changed_by = request.user
            flag.save()
            updated += 1
        self.message_user(request, f'{verb} {updated} red flag(s).', level=messages.SUCCESS)

    @admin.action(description='Acknowledge selected red flags')
    def acknowledge_selected(self, request, queryset):
        self._bulk_transition(request, queryset, 'acknowledged', 'Acknowledged')

    @admin.action(description='Mark selected red flags resolved')
    def resolve_selected(self, request, queryset):
        self._bulk_transition(request, queryset, 'resolved', 'Resolved')

    @admin.action(description='Mark selected red flags under review')
    def mark_under_review_selected(self, request, queryset):
        self._bulk_transition(request, queryset, 'under_review', 'Marked under review')

    @admin.action(description='Mark selected red flags as false positive')
    def mark_false_positive_selected(self, request, queryset):
        self._bulk_transition(request, queryset, 'false_positive', 'Marked false positive')


@admin.register(OperationalSnapshot)
class OperationalSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        'project', 'date', 'ore_mined_tonnes', 'plant_throughput_tph', 'recovery_rate_pct',
        'equipment_availability_pct', 'water_recycled_pct', 'confidence', 'environmental_status',
    )
    list_filter = ('environmental_status', 'project')


@admin.register(RedFlagRuleConfig)
class RedFlagRuleConfigAdmin(ChangedByAdminMixin, admin.ModelAdmin):
    list_display = ('rule_key', 'project', 'enabled', 'warning_threshold', 'critical_threshold', 'updated_at')
    list_filter = ('rule_key', 'enabled')

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(AuditLogEntry)
class AuditLogEntryAdmin(admin.ModelAdmin):
    list_display = ('project', 'event_type', 'object_description', 'field_name', 'previous_value', 'new_value', 'changed_by', 'created_at')
    list_filter = ('event_type', 'project')
    search_fields = ('object_description', 'field_name', 'reason')
    readonly_fields = [f.name for f in AuditLogEntry._meta.fields]

    def has_add_permission(self, request):
        # Rows are only ever created automatically by signals.py — never by hand.
        return False

    def has_change_permission(self, request, obj=None):
        return False
