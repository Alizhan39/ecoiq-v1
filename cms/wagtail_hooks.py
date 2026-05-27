"""
EcoIQ CMS — Wagtail hooks.

1. EcoIQDashboardPanel  — live company rankings + data quality snapshot
2. TransitionQueuePanel — companies with urgent transition flags
3. global admin CSS/JS  — EcoIQ dark institutional theme
"""
from django.utils.safestring import mark_safe
from wagtail import hooks
from wagtail.admin.ui.components import Component


# ── Dashboard panels ───────────────────────────────────────────────────────────

class EcoIQDashboardPanel(Component):
    """
    Wagtail admin homepage panel — live EcoIQ rankings and platform stats.
    Shows company count, top-ranked profiles, and data quality overview.
    """
    name          = 'ecoiq_stats'
    template_name = 'cms/admin/ecoiq_panel.html'
    order         = 50

    def get_context_data(self, parent_context):
        from companies.models import CompanyProfile
        from companies.scoring import get_moral_label

        try:
            profiles = list(CompanyProfile.objects.order_by('-ecoiq_score')[:6])
        except Exception:
            profiles = []

        try:
            total_companies = CompanyProfile.objects.count()
        except Exception:
            total_companies = 0

        try:
            # Companies with score > 70 = Responsible Builder tier or above
            high_score_count = CompanyProfile.objects.filter(ecoiq_score__gte=70).count()
        except Exception:
            high_score_count = 0

        try:
            # Companies with high_transition_need flag
            urgent_count = CompanyProfile.objects.filter(high_transition_need=True).count()
        except Exception:
            urgent_count = 0

        return {
            'top_profiles':      profiles,
            'total_companies':   total_companies,
            'high_score_count':  high_score_count,
            'urgent_count':      urgent_count,
        }


class TransitionQueuePanel(Component):
    """
    Shows companies flagged as urgent transition cases.
    Editors can click through to Django admin to review and update.
    """
    name          = 'transition_queue'
    template_name = 'cms/admin/transition_panel.html'
    order         = 60

    def get_context_data(self, parent_context):
        from companies.models import CompanyProfile

        try:
            urgent = (
                CompanyProfile.objects
                .filter(high_transition_need=True)
                .order_by('ecoiq_score')[:8]
            )
            urgent_count = CompanyProfile.objects.filter(high_transition_need=True).count()
        except Exception:
            urgent = []
            urgent_count = 0

        try:
            recent = (
                CompanyProfile.objects
                .order_by('-updated_at')[:5]
            )
        except Exception:
            try:
                recent = CompanyProfile.objects.order_by('-id')[:5]
            except Exception:
                recent = []

        return {
            'urgent_companies': urgent,
            'urgent_count':     urgent_count,
            'recent_updates':   recent,
        }


@hooks.register('construct_homepage_panels')
def add_ecoiq_panels(request, panels):
    panels.append(EcoIQDashboardPanel())
    panels.append(TransitionQueuePanel())


# ── Admin theme CSS — dark institutional ───────────────────────────────────────

@hooks.register('insert_global_admin_css')
def ecoiq_admin_css():
    """Dark institutional EcoIQ theme for Wagtail admin — Bloomberg × Palantir."""
    return mark_safe("""
<style>
/* ═══════════════════════════════════════════════════════════════════════════
   EcoIQ Admin Theme — Dark Institutional
   Bloomberg × Palantir aesthetic for investor-grade credibility
   ═══════════════════════════════════════════════════════════════════════════ */

/* ── CSS custom properties ─────────────────────────────────────────────── */
:root {
    --eiq-bg:       #070b0f;
    --eiq-surface:  #0d1117;
    --eiq-surface2: #161b22;
    --eiq-border:   rgba(255,255,255,.07);
    --eiq-acc:      #00e89a;
    --eiq-acc-dim:  rgba(0,232,154,.12);
    --eiq-text:     rgba(255,255,255,.88);
    --eiq-muted:    rgba(255,255,255,.45);
    --eiq-warn:     #f4a261;
    --eiq-danger:   #e63946;
    --eiq-info:     #58a6ff;
}

/* ── Sidebar ────────────────────────────────────────────────────────────── */
.sidebar,
.sidebar__inner,
[data-controller="w-sidebar"],
.sidebar-nav {
    background: var(--eiq-surface) !important;
    border-right: 1px solid var(--eiq-border) !important;
}

.sidebar-menu-item__link,
.sidebar-sub-menu-item__link {
    color: var(--eiq-muted) !important;
    border-radius: 6px !important;
    margin: 1px 6px !important;
}
.sidebar-menu-item__link:hover,
.sidebar-sub-menu-item__link:hover {
    background: rgba(255,255,255,.05) !important;
    color: var(--eiq-text) !important;
}
.sidebar-menu-item--active > .sidebar-menu-item__link,
.sidebar-sub-menu-item--active > .sidebar-sub-menu-item__link {
    background: var(--eiq-acc-dim) !important;
    color: var(--eiq-acc) !important;
    font-weight: 600 !important;
}

/* Sidebar footer / account area */
.sidebar__account,
.sidebar-account {
    background: var(--eiq-bg) !important;
    border-top: 1px solid var(--eiq-border) !important;
}

/* ── Top header bar ─────────────────────────────────────────────────────── */
header.header,
.w-header,
[data-controller="w-header"],
.breadcrumb,
.w-breadcrumb {
    background: var(--eiq-surface) !important;
    border-bottom: 1px solid var(--eiq-border) !important;
    box-shadow: 0 1px 0 var(--eiq-border) !important;
}
.header__title,
.w-header__title {
    color: var(--eiq-text) !important;
    letter-spacing: -0.02em;
}

/* ── Main content area ──────────────────────────────────────────────────── */
body,
.content-wrapper,
[data-controller="w-body"],
.dashboard {
    background: var(--eiq-bg) !important;
    color: var(--eiq-text) !important;
}

/* ── Panels / cards ─────────────────────────────────────────────────────── */
.panel,
.w-panel,
.dashboard__panel,
.listing,
.listing__item {
    background: var(--eiq-surface) !important;
    border: 1px solid var(--eiq-border) !important;
    border-radius: 10px !important;
    color: var(--eiq-text) !important;
}
.panel:hover { border-color: rgba(255,255,255,.12) !important; }

/* ── Buttons ────────────────────────────────────────────────────────────── */
.button.button-primary,
.button.yes,
a.button.button-primary {
    background: var(--eiq-acc) !important;
    border-color: var(--eiq-acc) !important;
    color: #070b0f !important;
    font-weight: 700 !important;
}
.button.button-primary:hover { filter: brightness(1.1) !important; }

.button.button-secondary,
a.button.button-secondary {
    background: transparent !important;
    border-color: var(--eiq-border) !important;
    color: var(--eiq-text) !important;
}
.button.button-secondary:hover {
    background: rgba(255,255,255,.06) !important;
    border-color: rgba(255,255,255,.2) !important;
}

/* ── Form fields ────────────────────────────────────────────────────────── */
input[type="text"],
input[type="email"],
input[type="password"],
input[type="search"],
textarea,
select,
.w-field__input,
[data-field] input,
[data-field] textarea,
[data-field] select {
    background: var(--eiq-surface2) !important;
    border-color: var(--eiq-border) !important;
    color: var(--eiq-text) !important;
    border-radius: 6px !important;
}
input:focus, textarea:focus, select:focus {
    border-color: var(--eiq-acc) !important;
    outline: none !important;
    box-shadow: 0 0 0 2px var(--eiq-acc-dim) !important;
}

/* ── Tables ─────────────────────────────────────────────────────────────── */
table,
.listing table {
    background: var(--eiq-surface) !important;
    color: var(--eiq-text) !important;
}
th {
    background: var(--eiq-surface2) !important;
    color: var(--eiq-muted) !important;
    font-size: 0.72rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}
tr:hover td { background: rgba(255,255,255,.025) !important; }
td, th { border-color: var(--eiq-border) !important; }

/* ── Dropdown menus ─────────────────────────────────────────────────────── */
.dropdown-menu,
.w-dropdown,
[data-tippy-root] {
    background: var(--eiq-surface2) !important;
    border: 1px solid var(--eiq-border) !important;
    border-radius: 8px !important;
}
.dropdown-menu a,
.w-dropdown a {
    color: var(--eiq-text) !important;
}
.dropdown-menu a:hover,
.w-dropdown a:hover {
    background: rgba(255,255,255,.06) !important;
}

/* ── Status tags ────────────────────────────────────────────────────────── */
.status-tag { border-radius: 4px !important; font-size: 0.68rem !important; }

/* ── Tabs ───────────────────────────────────────────────────────────────── */
.tab-nav { border-bottom-color: var(--eiq-border) !important; }
.tab-nav__tab--active {
    border-bottom-color: var(--eiq-acc) !important;
    color: var(--eiq-acc) !important;
}

/* ── Page editor StreamField ────────────────────────────────────────────── */
.c-sf-block,
.c-sf-container {
    background: var(--eiq-surface2) !important;
    border-color: var(--eiq-border) !important;
}
.c-sf-block__header {
    background: var(--eiq-surface) !important;
    border-bottom-color: var(--eiq-border) !important;
}
.c-sf-block__header__title { color: var(--eiq-acc) !important; font-weight: 600 !important; }

/* ── Notifications ──────────────────────────────────────────────────────── */
.messages .success { background: rgba(0,232,154,.15) !important; border-color: var(--eiq-acc) !important; }
.messages .error   { background: rgba(230,57,70,.15) !important; border-color: var(--eiq-danger) !important; }
.messages .warning { background: rgba(244,162,97,.15) !important; border-color: var(--eiq-warn) !important; }

/* ── Focus ring ─────────────────────────────────────────────────────────── */
*:focus-visible { outline-color: var(--eiq-acc) !important; }

/* ── Scrollbar ──────────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--eiq-bg); }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,.12); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,.22); }
</style>
""")


# ── Admin JS ───────────────────────────────────────────────────────────────────

@hooks.register('insert_global_admin_js')
def ecoiq_admin_js():
    """Adds EcoIQ branding badge and keyboard shortcut hints to Wagtail admin."""
    return mark_safe("""
<script>
document.addEventListener('DOMContentLoaded', function () {
    /* ── EcoIQ brand badge in header ── */
    const title = document.querySelector('.w-header__title, .header__title');
    if (title && !document.querySelector('.ecoiq-badge')) {
        const badge = document.createElement('span');
        badge.className = 'ecoiq-badge';
        badge.style.cssText = [
            'display:inline-flex',
            'align-items:center',
            'gap:4px',
            'margin-left:10px',
            'font-size:10px',
            'font-weight:700',
            'letter-spacing:.06em',
            'text-transform:uppercase',
            'color:#00e89a',
            'opacity:.8',
            'border:1px solid rgba(0,232,154,.3)',
            'border-radius:4px',
            'padding:1px 6px',
            'vertical-align:middle',
        ].join(';');
        badge.textContent = 'Intelligence CMS';
        title.appendChild(badge);
    }

    /* ── Soft entrance animation for panels ── */
    document.querySelectorAll('.panel, .w-panel').forEach(function(el, i) {
        el.style.opacity = '0';
        el.style.transform = 'translateY(6px)';
        el.style.transition = 'opacity .25s ease, transform .25s ease';
        setTimeout(function() {
            el.style.opacity = '';
            el.style.transform = '';
        }, 60 + i * 30);
    });
});
</script>
""")
