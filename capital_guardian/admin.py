"""capital_guardian/admin.py — the smallest stable observability solution for
Capital Guardian, matching this platform's Admin-first convention."""
from django.contrib import admin, messages

from capital_guardian.models import CapitalTraceEntry, OperationalSnapshot, ProjectGovernance, RedFlag


@admin.register(ProjectGovernance)
class ProjectGovernanceAdmin(admin.ModelAdmin):
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
    list_display = ('project', 'category', 'severity', 'resolution_status', 'capital_exposure_usd', 'detected_at')
    list_filter = ('severity', 'category', 'resolution_status', 'project')
    search_fields = ('description', 'category')
    readonly_fields = ('rule_key', 'detected_at')
    actions = ['acknowledge_selected', 'resolve_selected']

    def has_add_permission(self, request):
        # Rows are only ever created by the deterministic rule engine
        # (services/red_flag_engine.py), never by hand.
        return False

    @admin.action(description='Acknowledge selected red flags')
    def acknowledge_selected(self, request, queryset):
        updated = queryset.update(resolution_status='acknowledged', acknowledged_by=request.user)
        self.message_user(request, f'Acknowledged {updated} red flag(s).', level=messages.SUCCESS)

    @admin.action(description='Mark selected red flags resolved')
    def resolve_selected(self, request, queryset):
        updated = queryset.update(resolution_status='resolved', acknowledged_by=request.user)
        self.message_user(request, f'Resolved {updated} red flag(s).', level=messages.SUCCESS)


@admin.register(OperationalSnapshot)
class OperationalSnapshotAdmin(admin.ModelAdmin):
    list_display = ('project', 'date', 'ore_mined_tonnes', 'plant_throughput_tph', 'recovery_rate_pct', 'environmental_status')
    list_filter = ('environmental_status', 'project')
