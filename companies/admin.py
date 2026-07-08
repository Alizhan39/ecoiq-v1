"""
EcoIQ Company Intelligence — Django Admin.

Rich admin for CompanyProfile, CompanyGuidanceVideo, CompanySource.
Includes colour-coded badges, inline editing, admin actions for:
  - Recalculate EcoIQ scores
  - Generate AI company profile
  - Generate guidance video script
"""
import logging
from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html, mark_safe

from .models import (CompanyProfile, CompanyGuidanceVideo, CompanySource,
                     CompanyScoreSnapshot, DataIngestionLog)

logger = logging.getLogger(__name__)


# ── Inlines ────────────────────────────────────────────────────────────────────

class CompanySourceInline(admin.TabularInline):
    model   = CompanySource
    extra   = 1
    fields  = ('source_type', 'title', 'url', 'date_accessed')


class CompanyGuidanceVideoInline(admin.StackedInline):
    model   = CompanyGuidanceVideo
    extra   = 0
    fields  = ('title', 'video_type', 'status', 'visibility', 'video_url',
                'current_score_snapshot', 'target_score')
    readonly_fields = ('created_at',)
    show_change_link = True


# ── CompanyProfile Admin ───────────────────────────────────────────────────────

@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display  = (
        'company_link', 'status', 'tier_badge', 'verified_badge',
        'score_badge', 'moral_badge', 'pollution_badge', 'funding_badge',
        'video_count', 'updated_at',
    )
    list_filter   = (
        'status', 'subscription_tier', 'is_verified', 'moral_label',
        'pollution_level', 'funding_status',
        'company__sector', 'company__country',
    )
    search_fields = ('company__name', 'company__country', 'ai_summary')
    list_editable = ('status',)
    readonly_fields = (
        'ecoiq_total_score', 'moral_label', 'ecoiq_category',
        'public_benefit_score', 'environmental_responsibility_score',
        'modernization_score', 'transparency_anti_corruption_score',
        'ethical_alignment_score', 'harm_penalty',
        'created_at', 'updated_at',
        'score_preview_widget', 'company_page_link',
    )
    inlines = [CompanySourceInline, CompanyGuidanceVideoInline]
    ordering = ('-ecoiq_total_score',)
    save_on_top = True

    actions = [
        'action_recalculate_scores',
        'action_generate_ai_profile',
        'action_mark_verified',
        'action_mark_public',
    ]

    fieldsets = (
        ('Company Link', {
            'fields': ('company', 'company_page_link'),
        }),
        ('Status & Subscription', {
            'fields': (
                ('status', 'subscription_tier', 'is_verified'),
            ),
        }),
        ('EcoIQ Scores (Computed — read-only)', {
            'fields': (
                'score_preview_widget',
                ('ecoiq_total_score', 'moral_label', 'ecoiq_category'),
                ('public_benefit_score', 'environmental_responsibility_score'),
                ('modernization_score', 'transparency_anti_corruption_score'),
                ('ethical_alignment_score', 'harm_penalty'),
                ('profit_extraction_score', 'profit_extraction_risk_score'),
            ),
            'description': (
                '⚠ These are computed fields. Use the "Recalculate EcoIQ Scores" action '
                'or save sub-scores below then recalculate to update them. '
                'harm_penalty is auto-calculated and capped at 30 pts.'
            ),
        }),
        ('Financials', {
            'fields': (
                ('annual_revenue', 'profit', 'taxes_paid'),
                ('employees', 'ownership_type', 'state_owned_percentage'),
            ),
            'classes': ('collapse',),
        }),
        ('Environmental', {
            'fields': (
                ('estimated_emissions', 'pollution_level', 'emissions_reduction_target'),
                'pollution_notes',
                ('renewable_energy_share',),
                ('waste_management_score', 'water_impact_score', 'biodiversity_impact_score'),
            ),
        }),
        ('Social / Public Benefit', {
            'fields': (
                ('jobs_created_score', 'regional_development_score'),
                ('infrastructure_contribution_score', 'national_value_score'),
                'community_investment',
            ),
        }),
        ('Modernization', {
            'fields': (
                ('energy_transition_score', 'digitalization_score'),
                ('infrastructure_upgrade_score', 'future_readiness_score'),
                'modernization_investment',
                'modernization_projects',
            ),
        }),
        ('Transparency & Governance', {
            'fields': (
                ('transparency_score_detail', 'audit_quality_score'),
                ('procurement_transparency_score', 'anti_corruption_score'),
                ('controversy_risk_score',),
                'governance_notes',
            ),
        }),
        ('Funding & Investment', {
            'fields': (
                ('funding_status', 'investor_visibility', 'funding_needed'),
                'project_pipeline',
            ),
        }),
        ('AI Content', {
            'fields': (
                'ai_summary',
                'ai_modernization_report',
                'ai_investment_opportunity',
                'ai_risk_notes',
                'ai_recommendations',
            ),
            'classes': ('wide',),
        }),
        ('Source Documents', {
            'fields': (
                ('annual_report_url', 'sustainability_report_url'),
                'public_sources',
            ),
            'classes': ('collapse',),
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    # ── Display columns ────────────────────────────────────────────────────────

    def company_link(self, obj):
        url = reverse('admin:league_company_change', args=[obj.company_id])
        pub = reverse('companies:detail', kwargs={'slug': obj.company.slug})
        return format_html(
            '<a href="{}">{}</a> <a href="{}" target="_blank" style="font-size:.75em;color:#888;">↗</a>',
            url, obj.company.name, pub
        )
    company_link.short_description = 'Company'
    company_link.admin_order_field = 'company__name'

    def company_page_link(self, obj):
        if not obj.pk:
            return '—'
        url = reverse('companies:detail', kwargs={'slug': obj.company.slug})
        return format_html('<a href="{}" target="_blank">View Public Page ↗</a>', url)
    company_page_link.short_description = 'Public Profile'

    def status_badge(self, obj):
        c = {'draft': '#888', 'public': '#58a6ff',
             'verified': '#00e89a', 'archived': '#555'}.get(obj.status, '#888')
        return format_html(
            '<span style="background:{}22;color:{};padding:2px 8px;border-radius:4px;'
            'font-size:.72rem;font-weight:700;">{}</span>',
            c, c, obj.get_status_display()
        )
    status_badge.short_description = 'Status'

    def tier_badge(self, obj):
        c = {'free': '#888', 'verified': '#58a6ff', 'enterprise': '#f4a261'}.get(
            obj.subscription_tier, '#888')
        return format_html(
            '<span style="color:{};font-weight:700;">{}</span>',
            c, obj.get_subscription_tier_display()
        )
    tier_badge.short_description = 'Tier'

    def verified_badge(self, obj):
        if obj.is_verified:
            return format_html('<span style="color:#00e89a;">✓ Verified</span>')
        return format_html('<span style="color:#888;">Unverified</span>')
    verified_badge.short_description = 'Verified'

    def score_badge(self, obj):
        s = obj.ecoiq_total_score
        c = '#00e89a' if s >= 70 else '#f4a261' if s >= 50 else '#e63946'
        return format_html(
            '<span style="font-size:1.1rem;font-weight:800;color:{};">{}</span>',
            c, f'{s:.1f}'
        )
    score_badge.short_description = 'EcoIQ'
    score_badge.admin_order_field = 'ecoiq_total_score'

    def moral_badge(self, obj):
        c = obj.moral_label_color
        return format_html(
            '<span style="background:{}22;color:{};padding:2px 8px;border-radius:4px;'
            'font-size:.7rem;font-weight:700;white-space:nowrap;">{}</span>',
            c, c, obj.moral_label_display
        )
    moral_badge.short_description = 'Moral Label'

    def pollution_badge(self, obj):
        c = obj.pollution_color
        return format_html(
            '<span style="background:{}22;color:{};padding:2px 8px;border-radius:4px;'
            'font-size:.7rem;font-weight:700;">{}</span>',
            c, c, obj.get_pollution_level_display()
        )
    pollution_badge.short_description = 'Pollution'

    def funding_badge(self, obj):
        c = obj.funding_color
        return format_html(
            '<span style="color:{};font-size:.75rem;">{}</span>',
            c, obj.get_funding_status_display()
        )
    funding_badge.short_description = 'Funding'

    def video_count(self, obj):
        n = obj.guidance_videos.count()
        c = '#00e89a' if n > 0 else '#888'
        return format_html('<span style="color:{};font-weight:700;">📹 {}</span>', c, n)
    video_count.short_description = 'Videos'

    def score_preview_widget(self, obj):
        if not obj.pk:
            return '—'
        bars = [
            ('Public Benefit ×25%',      obj.public_benefit_score,               '#00e89a'),
            ('Environmental ×25%',       obj.environmental_responsibility_score,  '#58a6ff'),
            ('Modernization ×20%',       obj.modernization_score,                 '#8b5cf6'),
            ('Transparency ×15%',        obj.transparency_anti_corruption_score,  '#f4a261'),
            ('Anti-Corruption ×10%',     obj.anti_corruption_score,               '#f4a261'),
            ('Ethical Alignment ×5%',    obj.ethical_alignment_score,             '#94a3b8'),
        ]
        html = (
            '<div style="font-family:-apple-system,monospace;font-size:.78rem;'
            'background:#0d1117;border:1px solid rgba(255,255,255,.08);'
            'border-radius:8px;padding:.75rem 1rem;">'
        )
        for label, val, color in bars:
            pct = min(100, max(0, int(val)))
            html += (
                f'<div style="margin:.3rem 0;display:flex;gap:.6rem;align-items:center;">'
                f'<span style="min-width:170px;color:#64748b;font-size:.72rem;">{label}</span>'
                f'<div style="flex:1;height:6px;background:rgba(255,255,255,.05);border-radius:3px;">'
                f'<div style="width:{pct}%;height:100%;background:{color};border-radius:3px;opacity:.8;"></div></div>'
                f'<span style="color:{color};min-width:32px;text-align:right;font-weight:700;">{pct}</span>'
                f'</div>'
            )
        # Harm penalty row
        penalty = obj.harm_penalty or 0
        if penalty > 0:
            html += (
                f'<div style="margin:.4rem 0 .3rem;display:flex;gap:.6rem;align-items:center;">'
                f'<span style="min-width:170px;color:#e63946;font-size:.72rem;">⚠ Harm Penalty</span>'
                f'<div style="flex:1;height:6px;background:rgba(255,255,255,.05);border-radius:3px;">'
                f'<div style="width:{min(100,int(penalty/30*100))}%;height:100%;background:#e63946;border-radius:3px;opacity:.8;"></div></div>'
                f'<span style="color:#e63946;min-width:32px;text-align:right;font-weight:700;">−{penalty:.0f}</span>'
                f'</div>'
            )
        total_color = '#00e89a' if obj.ecoiq_total_score >= 70 else '#f4a261' if obj.ecoiq_total_score >= 50 else '#e63946'
        html += (
            f'<div style="margin-top:.6rem;padding-top:.6rem;border-top:1px solid rgba(255,255,255,.08);'
            f'font-weight:800;font-size:.9rem;color:{total_color};">'
            f'EcoIQ Total: {obj.ecoiq_total_score:.1f} / 100 &nbsp;·&nbsp; '
            f'<span style="font-weight:500;font-size:.75rem;color:#64748b;">'
            f'{obj.moral_label_display} · {obj.get_pollution_level_display()} Pollution</span>'
            f'</div>'
        )
        html += '</div>'
        return mark_safe(html)
    score_preview_widget.short_description = 'Live Score Preview'

    # ── Admin actions ──────────────────────────────────────────────────────────

    def action_recalculate_scores(self, request, queryset):
        from companies.scoring import recalculate_and_save
        updated = 0
        for profile in queryset:
            try:
                recalculate_and_save(profile)
                updated += 1
            except Exception as exc:
                self.message_user(request,
                    f'Error recalculating {profile.company.name}: {exc}',
                    level=messages.ERROR)
        self.message_user(request,
            f'✓ EcoIQ scores recalculated for {updated} company/companies.',
            level=messages.SUCCESS)
    action_recalculate_scores.short_description = '🔄 Recalculate EcoIQ Scores'

    def action_generate_ai_profile(self, request, queryset):
        from companies.ai_helpers import generate_ai_company_profile
        generated = 0
        for profile in queryset:
            try:
                generate_ai_company_profile(profile)
                generated += 1
            except Exception as exc:
                self.message_user(request,
                    f'AI profile failed for {profile.company.name}: {exc}',
                    level=messages.ERROR)
        self.message_user(request,
            f'✓ AI profile generated for {generated} company/companies.',
            level=messages.SUCCESS)
    action_generate_ai_profile.short_description = '🤖 Generate AI Company Profile'

    def action_mark_verified(self, request, queryset):
        queryset.update(is_verified=True, status='verified', subscription_tier='verified')
        self.message_user(request, f'Marked {queryset.count()} companies as Verified.')
    action_mark_verified.short_description = '✓ Mark as Verified'

    def action_mark_public(self, request, queryset):
        queryset.update(status='public')
        self.message_user(request, f'Marked {queryset.count()} companies as Public.')
    action_mark_public.short_description = '🌐 Mark as Public'


# ── CompanyGuidanceVideo Admin ─────────────────────────────────────────────────

@admin.register(CompanyGuidanceVideo)
class CompanyGuidanceVideoAdmin(admin.ModelAdmin):
    list_display  = (
        'company_name', 'title', 'type_badge', 'status_badge_col',
        'visibility', 'script_length', 'has_video_badge', 'allow_download', 'updated_at',
    )
    list_filter   = ('status', 'visibility', 'video_type', 'allow_download')
    search_fields = ('company__company__name', 'title', 'script')
    list_editable = ('visibility', 'allow_download')
    readonly_fields = ('created_at', 'updated_at', 'slug', 'script_stats', 'video_url_hint')
    ordering      = ('-created_at',)
    save_on_top   = True

    actions = [
        'action_generate_script',
        'action_mark_script_generated',
        'action_publish',
        'action_unpublish',
        'action_set_video_created',
    ]

    fieldsets = (
        ('Video Identity', {
            'fields': ('company', 'title', 'slug', 'video_type'),
        }),
        ('Status & Visibility', {
            'fields': (
                ('status', 'visibility'),
                ('allow_download', 'company_can_request_update'),
            ),
        }),
        ('🎬 Paste Video URL Here (after Higgsfield / Vimeo / YouTube upload)', {
            'fields': ('video_url', 'video_url_hint', 'thumbnail'),
            'description': (
                'STEP 3: After generating the video in Higgsfield (or uploading to Vimeo/YouTube), '
                'paste the URL in the field above and set status → Video Created.'
            ),
        }),
        ('Score Context (snapshot at generation time)', {
            'fields': (
                ('current_score_snapshot', 'target_score', 'target_score_improvement'),
            ),
        }),
        ('✍ Script (60-90 second narration)', {
            'fields': ('script_stats', 'executive_summary', 'script'),
            'classes': ('wide',),
            'description': (
                'STEP 1: Use the "Generate Script + Higgsfield Prompt" action to auto-generate, '
                'or write/edit manually. Target: 150-200 words for a 60-90 second read.'
            ),
        }),
        ('🎞 Higgsfield Visual Prompt (paste into Higgsfield AI)', {
            'fields': ('higgsfield_prompt',),
            'classes': ('wide',),
            'description': (
                'STEP 2: Copy this prompt into Higgsfield.ai to generate the video. '
                'Describe the visual scene, camera style, mood, and overlays.'
            ),
        }),
        ('Recommended Actions (JSON list)', {
            'fields': ('recommended_actions',),
            'classes': ('collapse',),
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def get_form(self, request, obj=None, **kwargs):
        """Make script and higgsfield_prompt use larger textareas."""
        form = super().get_form(request, obj, **kwargs)
        if 'script' in form.base_fields:
            form.base_fields['script'].widget.attrs.update({
                'rows': 18,
                'style': (
                    'font-family: -apple-system, monospace; font-size: .85rem; '
                    'line-height: 1.65; width: 100%; resize: vertical;'
                )
            })
        if 'higgsfield_prompt' in form.base_fields:
            form.base_fields['higgsfield_prompt'].widget.attrs.update({
                'rows': 8,
                'style': (
                    'font-family: -apple-system, monospace; font-size: .82rem; '
                    'line-height: 1.6; width: 100%; resize: vertical;'
                )
            })
        if 'executive_summary' in form.base_fields:
            form.base_fields['executive_summary'].widget.attrs.update({
                'rows': 4,
                'style': 'width: 100%; resize: vertical;'
            })
        return form

    def company_name(self, obj):
        url = reverse('admin:companies_companyprofile_change', args=[obj.company_id])
        pub = reverse('companies:detail', kwargs={'slug': obj.company.company.slug})
        return format_html(
            '<a href="{}">{}</a> <a href="{}" target="_blank" style="font-size:.72em;color:#888;">↗</a>',
            url, obj.company.company.name, pub
        )
    company_name.short_description = 'Company'
    company_name.admin_order_field = 'company__company__name'

    def type_badge(self, obj):
        return format_html(
            '<span style="font-size:.72rem;color:#58a6ff;">{}</span>',
            obj.get_video_type_display()
        )
    type_badge.short_description = 'Type'

    def status_badge_col(self, obj):
        c = obj.status_color
        return format_html(
            '<span style="background:{}22;color:{};padding:2px 8px;border-radius:4px;'
            'font-size:.7rem;font-weight:700;">{}</span>',
            c, c, obj.get_status_display()
        )
    status_badge_col.short_description = 'Status'

    def has_video_badge(self, obj):
        if obj.has_video:
            return format_html(
                '<a href="{}" target="_blank" style="color:#00e89a;">▶ View Video ↗</a>',
                obj.video_url
            )
        return format_html('<span style="color:#888;">No Video Yet</span>')
    has_video_badge.short_description = 'Video'

    def script_length(self, obj):
        if not obj.script:
            return format_html('<span style="color:#888;">—</span>')
        words = len(obj.script.split())
        c = '#00e89a' if 130 <= words <= 220 else '#f4a261'
        return format_html('<span style="color:{};font-weight:700;">{} w</span>', c, words)
    script_length.short_description = '📝 Words'

    def script_stats(self, obj):
        if not obj.script:
            return format_html(
                '<span style="color:#888;">No script yet. '
                'Use the "Generate Script" action or write manually below.</span>'
            )
        words = len(obj.script.split())
        chars = len(obj.script)
        approx_sec = round(words / 2.5)
        c = '#00e89a' if 130 <= words <= 220 else '#f4a261'
        return format_html(
            '<div style="font-size:.78rem;padding:.4rem .6rem;'
            'background:rgba(0,232,154,.04);border:1px solid rgba(0,232,154,.12);'
            'border-radius:6px;display:inline-block;">'
            '<strong style="color:{};">{} words</strong> · {} chars · '
            '<span style="color:#94a3b8;">~{} seconds read</span> · '
            '<span style="color:{};">{}</span>'
            '</div>',
            c, words, chars, approx_sec, c,
            '✓ Good length' if 130 <= words <= 220 else '⚠ Adjust length (target 150-200 words)'
        )
    script_stats.short_description = 'Script Stats'

    def video_url_hint(self, obj):
        if obj.has_video:
            return format_html(
                '<div style="font-size:.78rem;">'
                '<a href="{}" target="_blank" style="color:#00e89a;font-weight:700;">'
                '▶ {}</a></div>',
                obj.video_url, obj.video_url
            )
        return format_html(
            '<div style="font-size:.75rem;color:#64748b;padding:.35rem .6rem;'
            'background:rgba(244,162,97,.04);border:1px solid rgba(244,162,97,.15);'
            'border-radius:5px;">'
            '⏳ No video URL yet — paste the Higgsfield / Vimeo / YouTube link above '
            'after generating the video, then set status → <strong>Video Created</strong>.</div>'
        )
    video_url_hint.short_description = 'Video Status'

    # ── Actions ────────────────────────────────────────────────────────────────

    def action_generate_script(self, request, queryset):
        from companies.ai_helpers import generate_guidance_video_script
        ok = err = 0
        for video in queryset:
            try:
                generate_guidance_video_script(video)
                ok += 1
            except Exception as exc:
                self.message_user(request, f'Script failed for {video.title}: {exc}',
                                  level=messages.ERROR)
                err += 1
        if ok:
            self.message_user(request,
                f'✓ Scripts + Higgsfield prompts generated for {ok} video(s).',
                level=messages.SUCCESS)
    action_generate_script.short_description = '🤖 Generate Script + Higgsfield Prompt (AI)'

    def action_mark_script_generated(self, request, queryset):
        queryset.update(status='script_generated')
        self.message_user(request, f'Marked {queryset.count()} video(s) as Script Generated.')
    action_mark_script_generated.short_description = '✍ Mark as Script Generated'

    def action_set_video_created(self, request, queryset):
        queryset.update(status='video_created')
        self.message_user(request, f'Marked {queryset.count()} video(s) as Video Created.')
    action_set_video_created.short_description = '🎬 Mark as Video Created (after Higgsfield)'

    def action_publish(self, request, queryset):
        queryset.update(status='published')
        self.message_user(request, f'✓ Published {queryset.count()} video(s).')
    action_publish.short_description = '✅ Publish Video(s)'

    def action_unpublish(self, request, queryset):
        queryset.update(status='reviewed')
        self.message_user(request, f'Unpublished {queryset.count()} video(s). → Reviewed status.')
    action_unpublish.short_description = '🔒 Unpublish Video(s) (→ Reviewed)'


# ── CompanySource Admin ────────────────────────────────────────────────────────

@admin.register(CompanySource)
class CompanySourceAdmin(admin.ModelAdmin):
    list_display  = ('company', 'title', 'source_type', 'url_link', 'date_accessed')
    list_filter   = ('source_type',)
    search_fields = ('company__company__name', 'title', 'url')
    ordering      = ('company', 'source_type')

    def url_link(self, obj):
        return format_html('<a href="{}" target="_blank">↗ Open</a>', obj.url)
    url_link.short_description = 'Link'


# ── CompanyScoreSnapshot Admin ─────────────────────────────────────────────────

class CompanyScoreSnapshotInline(admin.TabularInline):
    model      = CompanyScoreSnapshot
    extra      = 0
    fields     = ('date', 'trigger', 'total_score', 'moral_label', 'notes')
    readonly_fields = ('created_at',)


@admin.register(CompanyScoreSnapshot)
class CompanyScoreSnapshotAdmin(admin.ModelAdmin):
    list_display  = ('company_name', 'total_score_display', 'tier_label',
                     'intelligence_score', 'trigger', 'date', 'notes_short')
    list_filter   = ('trigger',)
    search_fields = ('profile__company__name',)
    ordering      = ('-date',)
    readonly_fields = ('created_at', 'intelligence_score_explanation')
    actions       = ['action_snapshot_selected']

    def company_name(self, obj):
        return obj.profile.company.name
    company_name.short_description = 'Company'

    def total_score_display(self, obj):
        color = obj.tier_color
        return format_html(
            '<strong style="color:{}">{}</strong>', color, f'{obj.total_score:.1f}'
        )
    total_score_display.short_description = 'EcoIQ Score'

    def tier_label(self, obj):
        return obj.tier_label
    tier_label.short_description = 'Tier'

    def notes_short(self, obj):
        return (obj.notes[:60] + '…') if len(obj.notes) > 60 else obj.notes
    notes_short.short_description = 'Notes'

    def action_snapshot_selected(self, request, queryset):
        """Re-snapshot selected companies from their current live profile scores."""
        ok = 0
        for snap in queryset:
            CompanyScoreSnapshot.create_from_profile(
                snap.profile, trigger='manual',
                notes='Re-snapshotted via admin action',
            )
            ok += 1
        self.message_user(request, f'✓ Created {ok} new snapshots from current live scores.')
    action_snapshot_selected.short_description = '📸 Re-snapshot (new record from current live scores)'


# ── DataIngestionLog admin ────────────────────────────────────────────────────

@admin.register(DataIngestionLog)
class DataIngestionLogAdmin(admin.ModelAdmin):
    list_display   = ['ingested_at', 'source_badge', 'company', 'fields_updated_short', 'success_badge']
    list_filter    = ['source', 'success', 'ingested_at']
    search_fields  = ['company__name', 'error_msg']
    ordering       = ['-ingested_at']
    date_hierarchy = 'ingested_at'
    readonly_fields = ['raw_data', 'fields_updated', 'ingested_at', 'source', 'company', 'success', 'error_msg']

    SOURCE_COLORS = {
        'companies_house': ('#0c3a6b', '#dde5f4'),
        'sec_edgar':       ('#1b4332', '#d8f3dc'),
        'cdp':             ('#4a1d8a', '#ede9fe'),
        'yfinance':        ('#854d0e', '#fef9c3'),
        'rss':             ('#333',    '#e5e7eb'),
        'manual':          ('#333',    '#f9fafb'),
    }

    @admin.display(description='Source', ordering='source')
    def source_badge(self, obj):
        fg, bg = self.SOURCE_COLORS.get(obj.source, ('#333', '#eee'))
        return format_html(
            '<span style="background:{};color:{};padding:2px 9px;border-radius:10px;'
            'font-size:11px;font-weight:600;white-space:nowrap;">{}</span>',
            bg, fg, obj.get_source_display()
        )

    @admin.display(description='Fields', ordering=None)
    def fields_updated_short(self, obj):
        fields = obj.fields_updated or []
        if not fields:
            return '—'
        return ', '.join(fields[:4]) + ('…' if len(fields) > 4 else '')

    @admin.display(description='OK', ordering='success', boolean=True)
    def success_badge(self, obj):
        return obj.success
