"""EcoIQ Intelligence OS — Django Admin."""
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    CountryIntelligence, IntelligenceAlert,
    MonitorWatch, StrategicSignal, ExecutiveBriefing,
)


@admin.register(CountryIntelligence)
class CountryIntelligenceAdmin(admin.ModelAdmin):
    list_display  = ('country_name', 'score_badge', 'company_count',
                     'trend_col', 'reporting_pct', 'last_computed')
    list_filter   = ('trend_direction', 'region')
    search_fields = ('country_name', 'country_code', 'region')
    readonly_fields = ('last_computed',)
    ordering = ('-national_ecoiq_score',)

    @admin.display(description='EcoIQ')
    def score_badge(self, obj):
        from league.scoring import get_tier
        tier = get_tier(float(obj.national_ecoiq_score))
        return format_html(
            '<span style="background:{c};color:#fff;padding:2px 8px;border-radius:8px;'
            'font-weight:700;font-size:11px;">{s}</span>',
            c=tier.colour, s=obj.national_ecoiq_score,
        )

    @admin.display(description='Trend')
    def trend_col(self, obj):
        return format_html(
            '<span style="color:{c};font-weight:700;">{s} {d}</span>',
            c=obj.trend_color, s=obj.trend_symbol,
            d=obj.trend_delta if obj.trend_delta != 0 else '',
        )


@admin.register(IntelligenceAlert)
class IntelligenceAlertAdmin(admin.ModelAdmin):
    list_display  = ('severity_col', 'alert_type', 'title_short',
                     'company', 'is_read', 'created_at')
    list_filter   = ('severity', 'alert_type', 'is_read')
    search_fields = ('title', 'body', 'company__name')
    ordering      = ('-created_at',)
    actions       = ['mark_read']

    @admin.display(description='Severity')
    def severity_col(self, obj):
        return format_html(
            '<span style="color:{c};font-weight:700;">{i} {s}</span>',
            c=obj.severity_color, i=obj.severity_icon, s=obj.severity.upper(),
        )

    @admin.display(description='Alert')
    def title_short(self, obj):
        return obj.title[:60] + ('…' if len(obj.title) > 60 else '')

    @admin.action(description='Mark selected alerts as read')
    def mark_read(self, request, queryset):
        queryset.update(is_read=True)


@admin.register(MonitorWatch)
class MonitorWatchAdmin(admin.ModelAdmin):
    list_display  = ('company', 'check_type', 'label', 'is_active',
                     'last_checked_at', 'change_detected', 'consecutive_errors')
    list_filter   = ('check_type', 'is_active', 'change_detected')
    search_fields = ('company__name', 'url', 'label')
    ordering      = ('-last_checked_at',)


@admin.register(StrategicSignal)
class StrategicSignalAdmin(admin.ModelAdmin):
    list_display  = ('module', 'polarity_col', 'company', 'title_short',
                     'metric_value', 'metric_unit', 'year', 'confidence', 'detected_at')
    list_filter   = ('module', 'polarity')
    search_fields = ('company__name', 'title', 'description')
    ordering      = ('-detected_at',)

    @admin.display(description='Polarity')
    def polarity_col(self, obj):
        return format_html(
            '<span style="color:{c};font-weight:700;">{p}</span>',
            c=obj.polarity_color, p=obj.polarity.upper(),
        )

    @admin.display(description='Signal')
    def title_short(self, obj):
        return obj.title[:55] + ('…' if len(obj.title) > 55 else '')


@admin.register(ExecutiveBriefing)
class ExecutiveBriefingAdmin(admin.ModelAdmin):
    list_display  = ('company', 'scope', 'headline_short', 'model_used',
                     'token_count', 'created_at')
    list_filter   = ('scope',)
    search_fields = ('company__name', 'headline', 'body')
    readonly_fields = ('created_at', 'model_used', 'token_count')
    ordering      = ('-created_at',)

    @admin.display(description='Headline')
    def headline_short(self, obj):
        return obj.headline[:80] + ('…' if len(obj.headline) > 80 else '')
