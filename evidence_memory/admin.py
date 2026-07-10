from django.contrib import admin

from evidence_memory.models import EvidenceMemory


@admin.register(EvidenceMemory)
class EvidenceMemoryAdmin(admin.ModelAdmin):
    list_display = (
        'text_preview', 'source_type', 'document_category', 'verification_status', 'review_tier',
        'company', 'country', 'agent_name', 'confidence', 'embedding_status', 'is_demo', 'created_at',
    )
    list_filter = (
        'source_type', 'document_category', 'verification_status', 'review_tier',
        'embedding_status', 'is_demo', 'company', 'country',
    )
    search_fields = ('text_chunk', 'source_reference', 'agent_name')
    readonly_fields = ('created_at', 'updated_at', 'embedding_status', 'integrity_reference')

    @admin.display(description='Text')
    def text_preview(self, obj):
        return obj.text_chunk[:80] + ('…' if len(obj.text_chunk) > 80 else '')

    def save_model(self, request, obj, form, change):
        # Capital Guardian Phase 2 Audit History — see gold_intelligence/admin.py's docstring.
        obj._cg_changed_by = request.user
        super().save_model(request, obj, form, change)
