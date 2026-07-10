"""gold_intelligence/admin.py — the smallest stable observability solution
for the Gold Intelligence vertical, matching the rest of this platform's
Admin-first convention (no second custom dashboard).

Phase 2 (capital_guardian): `save_model`/`save_formset` stash the editing
user on each instance as `_cg_changed_by` before saving, so
capital_guardian/signals.py's Audit History entries can honestly attribute a
change to a real user (never guessed) rather than leaving it blank."""
from django.contrib import admin

from gold_intelligence.models import (
    CapitalBudgetLine, EquipmentSpec, GoldProject, MineTimelineMilestone, ScenarioAssumption,
)


class CapitalBudgetLineInline(admin.TabularInline):
    model = CapitalBudgetLine
    extra = 0


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
