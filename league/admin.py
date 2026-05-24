"""
EcoIQ Good Deeds League — Django Admin.
Russian-labelled sections per design spec.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Sum

from .models import Company, EnvironmentalProject, Evidence, ScoreHistory
from .scoring import get_tier, rerank_all


# ── Helpers ───────────────────────────────────────────────────────────────────

def _score_chip(score, *, width=60):
    """Coloured pill showing a 0-100 pillar score."""
    if score is None:
        return '—'
    tier = get_tier(score)
    return format_html(
        '<span style="background:{c}22;color:{c};border:1px solid {c}44;'
        'padding:2px 8px;border-radius:12px;font-size:11px;font-weight:700;">{s}</span>',
        c=tier.colour, s=score,
    )


def _ecoiq_chip(score):
    """Larger chip for the composite EcoIQ score."""
    if score is None:
        return '—'
    tier = get_tier(float(score))
    return format_html(
        '<span style="background:{c};color:#fff;'
        'padding:3px 10px;border-radius:12px;font-size:12px;font-weight:700;">'
        '{s} · {label}</span>',
        c=tier.colour, s=score, label=tier.label,
    )


# ── Admin actions ─────────────────────────────────────────────────────────────

@admin.action(description='Пересчитать рейтинг всех компаний')
def action_rerank(modeladmin, request, queryset):
    rerank_all()
    modeladmin.message_user(request, 'Рейтинг пересчитан.')


# ── Inlines ───────────────────────────────────────────────────────────────────

class ProjectInline(admin.TabularInline):
    model  = EnvironmentalProject
    extra  = 1
    fields = ('name', 'project_type', 'status', 'investment_usd',
              'co2_reduction_tonnes', 'households_helped', 'verified')
    show_change_link = True


class EvidenceInline(admin.TabularInline):
    model  = Evidence
    extra  = 1
    fields = ('doc_type', 'title', 'date_issued', 'issuer', 'verification_status')
    show_change_link = True


class ScoreHistoryInline(admin.TabularInline):
    model   = ScoreHistory
    extra   = 0
    fields  = ('date', 'ecoiq_score', 'rank',
               'score_pollution_footprint', 'score_reduction_progress',
               'score_investment', 'score_transparency', 'score_community_impact')
    ordering = ('-date',)
    max_num  = 12


# ── Company ───────────────────────────────────────────────────────────────────

@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display  = (
        'rank_col', 'name', 'sector', 'country',
        'ecoiq_badge', 'poll_badge', 'red_badge', 'inv_badge',
        'trans_badge', 'comm_badge',
        'verified_icon', 'projects_count',
    )
    list_filter   = ('sector', 'country', 'verified', 'is_featured')
    search_fields = ('name', 'city', 'description')
    prepopulated_fields = {'slug': ('name',)}
    ordering      = ('rank', '-ecoiq_score')
    actions       = [action_rerank]
    inlines       = [ProjectInline, EvidenceInline, ScoreHistoryInline]

    fieldsets = (
        ('Компания', {
            'fields': ('name', 'slug', 'sector', 'country', 'city', 'founded_year',
                       'website', 'logo_url', 'description'),
        }),
        ('Масштаб', {
            'fields': ('employee_count', 'annual_revenue_usd', 'is_public'),
        }),
        ('Оценки (0–100)', {
            'fields': (
                ('score_pollution_footprint', 'score_reduction_progress'),
                ('score_investment', 'score_transparency', 'score_community_impact'),
            ),
            'description': (
                'Итоговый EcoIQ = Загрязнение×35% + Снижение×25% + '
                'Инвестиции×20% + Прозрачность×10% + Сообщество×10%'
            ),
        }),
        ('Рейтинг', {
            'fields': ('ecoiq_score', 'rank', 'verified', 'is_featured'),
        }),
    )
    readonly_fields = ('ecoiq_score',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_projects=Count('projects', distinct=True))

    @admin.display(description='#', ordering='rank')
    def rank_col(self, obj):
        r = obj.rank or '—'
        return format_html('<b style="color:#2d6a4f;">{}</b>', r)

    @admin.display(description='EcoIQ', ordering='ecoiq_score')
    def ecoiq_badge(self, obj):
        return _ecoiq_chip(obj.ecoiq_score)

    @admin.display(description='Загрязн.', ordering='score_pollution_footprint')
    def poll_badge(self, obj):
        return _score_chip(obj.score_pollution_footprint)

    @admin.display(description='Снижение', ordering='score_reduction_progress')
    def red_badge(self, obj):
        return _score_chip(obj.score_reduction_progress)

    @admin.display(description='Инвест.', ordering='score_investment')
    def inv_badge(self, obj):
        return _score_chip(obj.score_investment)

    @admin.display(description='Прозрачн.', ordering='score_transparency')
    def trans_badge(self, obj):
        return _score_chip(obj.score_transparency)

    @admin.display(description='Сообщ.', ordering='score_community_impact')
    def comm_badge(self, obj):
        return _score_chip(obj.score_community_impact)

    @admin.display(description='✓', boolean=True, ordering='verified')
    def verified_icon(self, obj):
        return obj.verified

    @admin.display(description='Проекты')
    def projects_count(self, obj):
        return obj._projects


# ── Environmental Project ──────────────────────────────────────────────────────

@admin.register(EnvironmentalProject)
class ProjectAdmin(admin.ModelAdmin):
    list_display  = ('name', 'company', 'project_type', 'status',
                     'investment_usd', 'co2_reduction_tonnes', 'households_helped',
                     'verified', 'start_date')
    list_filter   = ('project_type', 'status', 'verified', 'company')
    search_fields = ('name', 'company__name', 'description', 'location')
    ordering      = ('-start_date',)
    date_hierarchy = 'start_date'

    fieldsets = (
        ('Проект', {
            'fields': ('company', 'name', 'project_type', 'status', 'location', 'description'),
        }),
        ('Даты', {
            'fields': ('start_date', 'completion_date'),
        }),
        ('KPI', {
            'fields': (
                ('investment_usd', 'co2_reduction_tonnes'),
                ('pm25_reduction_kg', 'households_helped'),
            ),
        }),
        ('Верификация', {
            'fields': ('verified',),
        }),
    )


# ── Evidence ──────────────────────────────────────────────────────────────────

@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display  = ('title', 'company', 'project', 'doc_type',
                     'date_issued', 'issuer', 'verification_status')
    list_filter   = ('doc_type', 'verification_status', 'company')
    search_fields = ('title', 'company__name', 'issuer', 'notes')
    ordering      = ('-date_issued',)

    fieldsets = (
        ('Документ', {
            'fields': ('company', 'project', 'doc_type', 'title'),
        }),
        ('Файл / Ссылка', {
            'fields': ('file', 'url'),
        }),
        ('Мета', {
            'fields': ('date_issued', 'issuer', 'verification_status', 'notes'),
        }),
    )


# ── Score History ─────────────────────────────────────────────────────────────

@admin.register(ScoreHistory)
class ScoreHistoryAdmin(admin.ModelAdmin):
    list_display  = ('company', 'date', 'ecoiq_score', 'rank')
    list_filter   = ('company',)
    ordering      = ('-date', 'rank')
    date_hierarchy = 'date'
