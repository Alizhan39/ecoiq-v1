"""gold_intelligence/admin.py — the smallest stable observability solution
for the Gold Intelligence vertical, matching the rest of this platform's
Admin-first convention (no second custom dashboard).

Phase 2 (capital_guardian): `save_model`/`save_formset` stash the editing
user on each instance as `_cg_changed_by` before saving, so
capital_guardian/signals.py's Audit History entries can honestly attribute a
change to a real user (never guessed) rather than leaving it blank."""
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.utils import timezone

from gold_intelligence.models import (
    CapitalBudgetLine, EquipmentSpec, GoldProject, MineTimelineMilestone, ScenarioAssumption, ProjectMembership,
    GeologicalEvidenceSource, GoldDrillhole, GoldAssayInterval, MineKPIObservation, GoldTarget, GoldCadastreSnapshot,
)


class CapitalBudgetLineInline(admin.TabularInline):
    model = CapitalBudgetLine
    extra = 0


@admin.register(ProjectMembership)
class ProjectMembershipAdmin(admin.ModelAdmin):
    list_display = ('project', 'user', 'role', 'is_active', 'updated_at')
    list_filter = ('role', 'is_active', 'project')
    search_fields = ('project__name', 'user__username')
    readonly_fields = ('created_at', 'updated_at')


class MineTimelineMilestoneInline(admin.TabularInline):
    model = MineTimelineMilestone
    extra = 0


class EquipmentSpecInline(admin.TabularInline):
    model = EquipmentSpec
    extra = 0


class ScenarioAssumptionInline(admin.TabularInline):
    model = ScenarioAssumption
    extra = 0


@admin.register(GoldProject)
class GoldProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'commodity', 'country', 'status', 'is_demo', 'total_capex_usd', 'updated_at')
    list_filter = ('status', 'commodity', 'is_demo', 'country')
    search_fields = ('name', 'region')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [CapitalBudgetLineInline, MineTimelineMilestoneInline, EquipmentSpecInline, ScenarioAssumptionInline]

    def save_model(self, request, obj, form, change):
        obj._cg_changed_by = request.user
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            instance._cg_changed_by = request.user
            instance.save()
        formset.save_m2m()


@admin.register(CapitalBudgetLine)
class CapitalBudgetLineAdmin(admin.ModelAdmin):
    list_display = ('project', 'category', 'label', 'planned_usd', 'committed_usd', 'spent_usd', 'remaining_usd')
    list_filter = ('category', 'project')

    def save_model(self, request, obj, form, change):
        obj._cg_changed_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(MineTimelineMilestone)
class MineTimelineMilestoneAdmin(admin.ModelAdmin):
    list_display = ('project', 'phase', 'status', 'planned_start', 'planned_end', 'verification_status', 'delay_risk')
    list_filter = ('phase', 'status', 'verification_status', 'delay_risk', 'project')

    def save_model(self, request, obj, form, change):
        obj._cg_changed_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(EquipmentSpec)
class EquipmentSpecAdmin(admin.ModelAdmin):
    list_display = ('project', 'equipment_type', 'label', 'capex_usd', 'lead_time_months', 'fat_status', 'delivery_status')
    list_filter = ('equipment_type', 'fat_status', 'delivery_status', 'project')

    def save_model(self, request, obj, form, change):
        obj._cg_changed_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ScenarioAssumption)
class ScenarioAssumptionAdmin(admin.ModelAdmin):
    list_display = ('project', 'name', 'gold_price_usd_per_oz', 'capex_multiplier', 'opex_multiplier')
    list_filter = ('project',)


class GoldEvidenceReviewAdmin(admin.ModelAdmin):
    """Review via explicit staff action after full form/model validation.

    Never silently approve a newly entered record: the form keeps the review
    fields read-only and reviewed changes require reopening first.
    """
    readonly_fields = ('review_state', 'reviewer', 'reviewed_at')
    actions = ('mark_internally_reviewed', 'reopen_for_review')

    @admin.action(description='Internally review selected records (not external certification)')
    def mark_internally_reviewed(self, request, queryset):
        if not self.has_change_permission(request):
            self.message_user(request, 'Permission denied.', level=messages.ERROR)
            return
        accepted = 0
        for obj in queryset:
            obj.review_state = 'reviewed'
            obj.reviewer = request.user
            obj.reviewed_at = timezone.now()
            try:
                obj.save()
                accepted += 1
            except ValidationError as exc:
                self.message_user(request, f'{obj.pk}: {exc}', level=messages.WARNING)
        if accepted:
            self.message_user(request, f'{accepted} record(s) internally reviewed.')

    @admin.action(description='Return selected records to pending for correction')
    def reopen_for_review(self, request, queryset):
        if not self.has_change_permission(request):
            self.message_user(request, 'Permission denied.', level=messages.ERROR)
            return
        reopened = 0
        for obj in queryset:
            obj.review_state = 'pending'
            obj.reviewer = None
            obj.reviewed_at = None
            try:
                obj.save()
                reopened += 1
            except ValidationError as exc:
                self.message_user(request, f'{obj.pk}: {exc}', level=messages.WARNING)
        if reopened:
            self.message_user(request, f'{reopened} record(s) returned to pending.')


@admin.register(GeologicalEvidenceSource)
class GeologicalEvidenceSourceAdmin(GoldEvidenceReviewAdmin):
    list_display = ('project', 'source_id', 'kind', 'issuer', 'is_synthetic', 'review_state')
    list_filter = ('kind', 'review_state', 'is_synthetic', 'project')
    search_fields = ('source_id', 'title', 'issuer', 'citation', 'project__name')


@admin.register(GoldDrillhole)
class GoldDrillholeAdmin(GoldEvidenceReviewAdmin):
    list_display = ('project', 'hole_id', 'latitude', 'longitude', 'total_depth_m', 'review_state')
    list_filter = ('review_state', 'project')
    search_fields = ('hole_id', 'project__name')


@admin.register(GoldAssayInterval)
class GoldAssayIntervalAdmin(GoldEvidenceReviewAdmin):
    list_display = ('project', 'sample_id', 'drillhole', 'from_m', 'to_m',
                    'au_g_per_t', 'sample_type', 'review_state')
    list_filter = ('review_state', 'sample_type', 'project')
    search_fields = ('sample_id', 'certificate_id', 'drillhole__hole_id')


@admin.register(MineKPIObservation)
class MineKPIObservationAdmin(GoldEvidenceReviewAdmin):
    list_display = ('project', 'metric_key', 'period_start', 'period_end',
                    'numerator', 'denominator', 'review_state')
    list_filter = ('metric_key', 'review_state', 'project')
    search_fields = ('source__source_id', 'project__name')



@admin.register(GoldTarget)
class GoldTargetAdmin(admin.ModelAdmin):
    """Staff-only source review; review is internal, not geological certification."""
    list_display = ('target_id', 'name', 'feature_kind', 'region', 'review_state', 'rights_status', 'is_demo', 'updated_at')
    list_filter = ('feature_kind', 'review_state', 'rights_status', 'is_demo', 'region')
    search_fields = ('target_id', 'name', 'region', 'source_reference')
    readonly_fields = ('created_at', 'updated_at')



@admin.register(GoldCadastreSnapshot)
class GoldCadastreSnapshotAdmin(admin.ModelAdmin):
    """Read-only audit metadata with explicit human review; no live licence claims."""
    list_display = ('parcel_id', 'snapshot_on', 'recorded_status', 'review_state', 'project')
    list_filter = ('recorded_status', 'review_state', 'snapshot_on')
    search_fields = ('parcel_id', 'source_reference')
    # A snapshot is immutable in the admin: correcting source geometry/status
    # requires a fresh dated import; only review and project access can change.
    readonly_fields = (
        'parcel_id', 'snapshot_on', 'geometry', 'recorded_status',
        'official_status_text', 'source_name', 'source_url',
        'source_reference', 'reuse_terms', 'source_sha256', 'created_at',
    )

    def has_add_permission(self, request):
        return False  # Operator-controlled import only.

    def has_delete_permission(self, request, obj=None):
        return False  # Preserve historical source snapshots.
