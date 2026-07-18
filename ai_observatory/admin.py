from django.contrib import admin

from ai_observatory.models import AnalysisSession, ModelInvocation, PipelineStageExecution


class PipelineStageInline(admin.TabularInline):
    model = PipelineStageExecution
    extra = 0
    can_delete = False
    readonly_fields = [f.name for f in PipelineStageExecution._meta.fields]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(AnalysisSession)
class AnalysisSessionAdmin(admin.ModelAdmin):
    """Read-only — telemetry is written only by the recorder at real
    pipeline run time; hand-edited telemetry would be fabricated data."""
    list_display = ('project', 'kind', 'status', 'user', 'started_at', 'duration_ms', 'blocked_recommendation_count')
    list_filter = ('kind', 'status', 'human_review_required')
    readonly_fields = [f.name for f in AnalysisSession._meta.fields]
    inlines = [PipelineStageInline]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ModelInvocation)
class ModelInvocationAdmin(admin.ModelAdmin):
    list_display = ('provider', 'model_name', 'session', 'input_tokens', 'output_tokens', 'cached_tokens', 'retry_count', 'created_at')
    list_filter = ('provider', 'model_name')
    readonly_fields = [f.name for f in ModelInvocation._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
