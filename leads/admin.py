from django.contrib import admin
from .models import AccessRequest


@admin.register(AccessRequest)
class AccessRequestAdmin(admin.ModelAdmin):
    list_display  = (
        'full_name', 'company', 'work_email',
        'industry', 'company_size', 'status', 'created_at',
    )
    list_filter   = ('status', 'industry', 'company_size', 'created_at')
    search_fields = ('full_name', 'company', 'work_email', 'challenge', 'message')
    list_editable = ('status',)
    readonly_fields = ('ip_address', 'created_at', 'updated_at')
    ordering        = ('-created_at',)
    date_hierarchy  = 'created_at'

    fieldsets = (
        ('Contact', {
            'fields': ('full_name', 'company', 'work_email'),
        }),
        ('Profile', {
            'fields': ('industry', 'facility_type', 'company_size'),
        }),
        ('Qualification', {
            'fields': ('challenge', 'message'),
        }),
        ('CRM', {
            'fields': ('status', 'notes'),
        }),
        ('Meta', {
            'fields': ('ip_address', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
