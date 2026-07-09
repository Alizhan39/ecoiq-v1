"""
decision_studio/admin.py — read-only observability. Reuses Django Admin,
same convention as every other Phase 1 module in this platform — no second
observability dashboard.
"""
from django.contrib import admin

from decision_studio.models import DecisionQuery


@admin.register(DecisionQuery)
class DecisionQueryAdmin(admin.ModelAdmin):
    list_display = (
        'question_preview', 'intent', 'data_availability_status', 'confidence_label',
        'confidence_score', 'created_at',
    )
    list_filter = ('intent', 'data_availability_status', 'confidence_label')
    search_fields = ('question_text',)
    readonly_fields = (
        'question_text', 'session_key', 'user', 'intent', 'resolved_entities', 'scope',
        'capability_plan', 'data_availability_status', 'confidence_label', 'confidence_score',
        'result', 'orchestration_run', 'parent_query', 'created_at',
    )

    def has_add_permission(self, request):
        return False

    @admin.display(description='Question')
    def question_preview(self, obj):
        return obj.question_text[:80] + ('…' if len(obj.question_text) > 80 else '')
