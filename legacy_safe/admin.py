from django.contrib import admin

from legacy_safe.models import (
    AuditLog, ChangeProposal, DerivedMemory, LegacyProject, MemoryChunk, SourceDocument,
)


@admin.register(LegacyProject)
class LegacyProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'organisation', 'sector', 'created_at')
    search_fields = ('name', 'organisation', 'sector')


@admin.register(SourceDocument)
class SourceDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'document_type', 'access_level', 'is_revoked', 'created_at')
    list_filter = ('access_level', 'document_type', 'is_revoked', 'project')
    search_fields = ('title', 'text_content')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(MemoryChunk)
class MemoryChunkAdmin(admin.ModelAdmin):
    list_display = ('source_document', 'chunk_index', 'access_level', 'is_revoked', 'created_at')
    list_filter = ('access_level', 'is_revoked')
    readonly_fields = ('created_at',)


@admin.register(DerivedMemory)
class DerivedMemoryAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'access_level', 'is_revoked', 'created_at')
    list_filter = ('access_level', 'is_revoked', 'project')
    readonly_fields = ('created_at',)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'decision', 'user', 'created_at')
    list_filter = ('action', 'decision')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)


@admin.register(ChangeProposal)
class ChangeProposalAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'status', 'created_at')
    list_filter = ('status', 'project')
    readonly_fields = ('created_at',)
