from django.contrib import admin

from digital_twin import models as m


@admin.register(m.UnitCategory)
class UnitCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code']


@admin.register(m.Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'category', 'symbol', 'is_base_unit', 'to_base_multiplier']
    list_filter = ['category', 'is_base_unit']


@admin.register(m.AssetType)
class AssetTypeAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'code', 'is_active']


@admin.register(m.IndustrialAsset)
class IndustrialAssetAdmin(admin.ModelAdmin):
    list_display = ['name', 'asset_type', 'company', 'country', 'lifecycle_stage', 'operational_status', 'is_demo']
    list_filter = ['asset_type', 'lifecycle_stage', 'operational_status', 'is_demo']
    search_fields = ['name', 'country', 'region']


class TwinComponentInline(admin.TabularInline):
    model = m.TwinComponent
    extra = 0


class TwinDataGapInline(admin.TabularInline):
    model = m.TwinDataGap
    extra = 0


@admin.register(m.DigitalTwin)
class DigitalTwinAdmin(admin.ModelAdmin):
    list_display = ['name', 'asset', 'version', 'status', 'confidence_score', 'completeness_score', 'data_freshness_score']
    list_filter = ['status']
    inlines = [TwinComponentInline, TwinDataGapInline]


@admin.register(m.TwinComponent)
class TwinComponentAdmin(admin.ModelAdmin):
    list_display = ['name', 'twin', 'component_type', 'condition', 'criticality', 'operational_status']
    list_filter = ['component_type', 'condition', 'criticality']


@admin.register(m.ProcessNode)
class ProcessNodeAdmin(admin.ModelAdmin):
    list_display = ['name', 'twin', 'node_type', 'sequence_order', 'utilisation_pct', 'confidence']
    list_filter = ['node_type']


@admin.register(m.ProcessEdge)
class ProcessEdgeAdmin(admin.ModelAdmin):
    list_display = ['twin', 'source_node', 'target_node', 'label']


@admin.register(m.ResourceFlow)
class ResourceFlowAdmin(admin.ModelAdmin):
    list_display = ['twin', 'resource_type', 'quantity', 'unit', 'confidence']
    list_filter = ['resource_type']


@admin.register(m.MetricDefinition)
class MetricDefinitionAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'unit_category', 'default_unit', 'higher_is_better', 'is_active']


@admin.register(m.OperationalMetric)
class OperationalMetricAdmin(admin.ModelAdmin):
    list_display = ['definition', 'twin', 'value', 'unit', 'verification_status', 'confidence', 'recorded_at']
    list_filter = ['verification_status', 'definition']


@admin.register(m.TwinDataGap)
class TwinDataGapAdmin(admin.ModelAdmin):
    list_display = ['affected_area', 'twin', 'severity', 'status']
    list_filter = ['severity', 'status']


@admin.register(m.LossDetection)
class LossDetectionAdmin(admin.ModelAdmin):
    list_display = ['title', 'twin', 'loss_type', 'estimated_annual_impact', 'confidence', 'status']
    list_filter = ['status', 'loss_type']


@admin.register(m.ModernisationScenario)
class ModernisationScenarioAdmin(admin.ModelAdmin):
    list_display = ['intervention', 'twin', 'scenario_type', 'technology_category', 'confidence']
    list_filter = ['scenario_type']


@admin.register(m.SacredSourceReference)
class SacredSourceReferenceAdmin(admin.ModelAdmin):
    list_display = ['canonical_reference', 'source_tradition', 'review_status', 'version']
    list_filter = ['source_tradition', 'review_status']


@admin.register(m.StewardshipPrinciple)
class StewardshipPrincipleAdmin(admin.ModelAdmin):
    list_display = ['name', 'domain', 'review_status', 'is_approved_for_use', 'version']
    list_filter = ['review_status', 'is_approved_for_use', 'domain']


@admin.register(m.StewardshipKPI)
class StewardshipKPIAdmin(admin.ModelAdmin):
    list_display = ['name', 'principle', 'approval_status', 'is_active', 'version']
    list_filter = ['approval_status', 'is_active']


@admin.register(m.StewardshipAssessment)
class StewardshipAssessmentAdmin(admin.ModelAdmin):
    list_display = ['kpi', 'scenario', 'calculated_score', 'warning', 'blocking']
    list_filter = ['warning', 'blocking']


@admin.register(m.HumanDecision)
class HumanDecisionAdmin(admin.ModelAdmin):
    list_display = ['scenario', 'decision', 'human_approved', 'reviewer', 'decided_at']
    list_filter = ['decision']


@admin.register(m.ImplementationAction)
class ImplementationActionAdmin(admin.ModelAdmin):
    list_display = ['title', 'scenario', 'status', 'planned_start_date', 'planned_end_date']
    list_filter = ['status']


@admin.register(m.MeasuredOutcome)
class MeasuredOutcomeAdmin(admin.ModelAdmin):
    list_display = ['action', 'metric_definition', 'predicted_value', 'actual_value', 'variance_pct', 'measured_at']
