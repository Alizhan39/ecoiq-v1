from django.contrib import admin

from evidence_memory.models import EvidenceMemory


@admin.register(EvidenceMemory)
class EvidenceMemoryAdmin(admin.ModelAdmin):
    list_display = (
        'text_preview', 'source_type', 'company', 'country', 'agent_name',
        'confidence', 'embedding_status', 'is_demo', 'created_at',
    )
    list_filter = ('source_type', 'embedding_status', 'is_demo', 'company', 'country')
    search_fields = ('text_chunk', 'source_reference', 'agent_name')
    readonly_fields = ('created_at', 'updated_at', 'embedding_status')

    @admin.display(description='Text')
    def text_preview(self, obj):
        return obj.text_chunk[:80] + ('…' if len(obj.text_chunk) > 80 else '')
