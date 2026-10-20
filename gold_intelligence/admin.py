"""gold_intelligence/admin.py — the smallest stable observability solution
for the Gold Intelligence vertical, matching the rest of this platform's
Admin-first convention (no second custom dashboard).

Phase 2 (capital_guardian): `save_model`/`save_formset` stash the editing
user on each instance as `_cg_changed_by` before saving, so
capital_guardian/signals.py's Audit History entries can honestly attribute a
change to a real user (never guessed) rather than leaving it blank."""
from django.contrib import admin
from django.utils import timezone

from gold_intelligence.models import (
    CapitalBudgetLine, EquipmentSpec, GoldProject, MineTimelineMilestone, ScenarioAssumption, ProjectMembership,
    GeologicalEvidenceSource, GoldDrillhole, GoldAssayInterval, MineKPIObservation,
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
    """Record the actual internal staff reviewer; not independent certification."""
    readonly_fields = ('reviewer', 'reviewed_at')

    def save_model(self, request, obj, form, change):
        if obj.review_state == 'reviewed':
            if not change or self.model.objects.filter(pk=obj.pk).exclude(review_state='reviewed').exists():
                obj.reviewer = request.user
                obj.reviewed_at = timezone.now()
        elif obj.review_state == 'pending':
            obj.reviewer = None
            obj.reviewed_at = None
        super().save_model(request, obj, form, change)


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
