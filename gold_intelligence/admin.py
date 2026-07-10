"""gold_intelligence/admin.py — the smallest stable observability solution
for the Gold Intelligence vertical, matching the rest of this platform's
Admin-first convention (no second custom dashboard)."""
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
    list_display = ('name', 'country', 'status', 'is_demo', 'total_capex_usd', 'updated_at')
    list_filter = ('status', 'is_demo', 'country')
    search_fields = ('name', 'region')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [CapitalBudgetLineInline, MineTimelineMilestoneInline, EquipmentSpecInline, ScenarioAssumptionInline]


@admin.register(CapitalBudgetLine)
class CapitalBudgetLineAdmin(admin.ModelAdmin):
    list_display = ('project', 'category', 'label', 'planned_usd', 'committed_usd', 'spent_usd', 'remaining_usd')
    list_filter = ('category', 'project')


@admin.register(MineTimelineMilestone)
class MineTimelineMilestoneAdmin(admin.ModelAdmin):
    list_display = ('project', 'phase', 'status', 'planned_start', 'planned_end')
    list_filter = ('phase', 'status', 'project')


@admin.register(EquipmentSpec)
class EquipmentSpecAdmin(admin.ModelAdmin):
    list_display = ('project', 'equipment_type', 'label', 'capex_usd', 'lead_time_months')
    list_filter = ('equipment_type', 'project')


@admin.register(ScenarioAssumption)
class ScenarioAssumptionAdmin(admin.ModelAdmin):
    list_display = ('project', 'name', 'gold_price_usd_per_oz', 'capex_multiplier', 'opex_multiplier')
    list_filter = ('project',)
