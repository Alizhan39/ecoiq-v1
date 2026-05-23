from django.contrib import admin
from .models import Assessment, QuestionnaireResponse, Finding


class QuestionnaireResponseInline(admin.TabularInline):
    model = QuestionnaireResponse
    extra = 0


class FindingInline(admin.StackedInline):
    model = Finding
    extra = 0


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display  = ('company_name', 'status', 'created_at')
    list_filter   = ('status',)
    search_fields = ('company_name',)
    inlines       = [QuestionnaireResponseInline, FindingInline]
    readonly_fields = ('created_at', 'updated_at', 'extracted_text')


@admin.register(Finding)
class FindingAdmin(admin.ModelAdmin):
    list_display = ('assessment', 'score_overall', 'score_environment',
                    'score_social', 'score_governance', 'score_ethics',
                    'score_innovation', 'created_at')
    readonly_fields = ('created_at',)

