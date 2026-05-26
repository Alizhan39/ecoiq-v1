"""
EcoIQ Ingestion — Django Admin.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse

from .models import IngestionJob, IngestionSource


class IngestionSourceInline(admin.TabularInline):
    model  = IngestionSource
    extra  = 0
    fields = ('source_type', 'title', 'url_short', 'downloaded',
              'used_in_analysis', 'content_chars', 'confidence')
    readonly_fields = ('url_short', 'downloaded', 'used_in_analysis',
                       'content_chars', 'confidence')
    can_delete = False

    @admin.display(description='URL')
    def url_short(self, obj):
        url = obj.url or ''
        label = url[:60] + ('…' if len(url) > 60 else '')
        return format_html('<a href="{}" target="_blank">{}</a>', url, label)


@admin.register(IngestionJob)
class IngestionJobAdmin(admin.ModelAdmin):
    list_display  = ('company_name', 'status_badge', 'progress_pct',
                     'result_link', 'created_at', 'duration_col')
    list_filter   = ('status',)
    search_fields = ('company_name',)
    readonly_fields = ('status', 'progress_pct', 'progress_message',
                       'result_company', 'error_message',
                       'search_result', 'extraction_result', 'score_result',
                       'created_at', 'started_at', 'completed_at')
    ordering      = ('-created_at',)
    inlines       = [IngestionSourceInline]

    fieldsets = (
        ('Job', {
            'fields': ('company_name', 'status', 'progress_pct', 'progress_message'),
        }),
        ('Result', {
            'fields': ('result_company', 'error_message'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'started_at', 'completed_at'),
        }),
        ('Raw AI Output', {
            'classes': ('collapse',),
            'fields': ('search_result', 'extraction_result', 'score_result'),
        }),
    )

    @admin.display(description='Status')
    def status_badge(self, obj):
        colours = {
            'pending':     '#888',
            'searching':   '#f4a261',
            'downloading': '#f4a261',
            'extracting':  '#52b788',
            'scoring':     '#40916c',
            'saving':      '#2d6a4f',
            'done':        '#00e89a',
            'failed':      '#e63946',
        }
        colour = colours.get(obj.status, '#888')
        return format_html(
            '<span style="background:{c};color:#fff;padding:2px 8px;'
            'border-radius:10px;font-size:11px;font-weight:700;">{s}</span>',
            c=colour, s=obj.status.upper(),
        )

    @admin.display(description='Company')
    def result_link(self, obj):
        if obj.result_company:
            url = reverse('admin:league_company_change', args=[obj.result_company.pk])
            return format_html('<a href="{}">{}</a>', url, obj.result_company.name)
        return '—'

    @admin.display(description='Duration')
    def duration_col(self, obj):
        d = obj.duration_seconds
        if d is None:
            return '—'
        if d < 60:
            return f'{d}s'
        return f'{d // 60}m {d % 60}s'


@admin.register(IngestionSource)
class IngestionSourceAdmin(admin.ModelAdmin):
    list_display  = ('title_col', 'job', 'source_type', 'downloaded',
                     'content_chars', 'confidence')
    list_filter   = ('source_type', 'downloaded', 'used_in_analysis')
    search_fields = ('title', 'url', 'job__company_name')
    ordering      = ('-confidence',)
    readonly_fields = ('job', 'url', 'source_type', 'title', 'snippet',
                       'downloaded', 'content_chars', 'used_in_analysis',
                       'confidence', 'created_at')

    @admin.display(description='Title')
    def title_col(self, obj):
        label = obj.title or obj.url[:60]
        return format_html('<a href="{}" target="_blank">{}</a>', obj.url, label)
