"""
EcoIQ CMS — Wagtail hooks.

1. LeagueDashboardPanel   — top companies + pending evidence summary
2. EvidenceQueuePanel     — list of evidence records awaiting verification
3. global admin CSS/JS    — EcoIQ green theme override
"""
from django.utils.safestring import mark_safe
from wagtail import hooks
from wagtail.admin.ui.components import Component


# ── Dashboard panels ───────────────────────────────────────────────────────────

class LeagueDashboardPanel(Component):
    """
    Shows key league stats on the Wagtail admin homepage.
    Provides a quick overview without leaving the CMS.
    """
    name          = 'league_stats'
    template_name = 'cms/admin/league_panel.html'
    order         = 50

    def get_context_data(self, parent_context):
        from league.models import Company, EnvironmentalProject, Evidence

        companies = list(Company.objects.order_by('rank')[:6])
        for co in companies:
            from league.scoring import get_tier
            co.tier = get_tier(float(co.ecoiq_score))

        all_cos = Company.objects.prefetch_related('projects')
        total_co2 = sum(c.total_co2_reduced for c in all_cos)

        return {
            'top_companies':          companies,
            'total_companies':        Company.objects.count(),
            'active_projects':        EnvironmentalProject.objects.filter(status='active').count(),
            'completed_projects':     EnvironmentalProject.objects.filter(status='completed').count(),
            'pending_evidence_count': Evidence.objects.filter(verification_status='pending').count(),
            'total_co2_reduced':      total_co2,
        }


class EvidenceQueuePanel(Component):
    """
    Shows pending evidence documents that need verification.
    Editors can click through to Django admin to approve/reject.
    """
    name          = 'evidence_queue'
    template_name = 'cms/admin/evidence_queue.html'
    order         = 60

    def get_context_data(self, parent_context):
        from league.models import Evidence
        pending = (
            Evidence.objects
            .filter(verification_status='pending')
            .select_related('company', 'project')
            .order_by('-created_at')[:8]
        )
        return {
            'pending_evidence':      pending,
            'pending_count':         Evidence.objects.filter(verification_status='pending').count(),
            'verified_count':        Evidence.objects.filter(verification_status='verified').count(),
        }


@hooks.register('construct_homepage_panels')
def add_league_panels(request, panels):
    panels.append(LeagueDashboardPanel())
    panels.append(EvidenceQueuePanel())


# ── Admin theme CSS ────────────────────────────────────────────────────────────

@hooks.register('insert_global_admin_css')
def ecoiq_admin_css():
    """Injects EcoIQ green brand colours into the Wagtail admin."""
    return mark_safe("""
<style>
/* ── EcoIQ Admin Theme — green brand colours ── */

/* Sidebar background */
.sidebar,
.sidebar__inner,
[data-controller="w-sidebar"] {
    background: #1b4332 !important;
    border-right-color: #2d6a4f !important;
}

/* Sidebar nav links */
.sidebar-menu-item__link,
.sidebar-sub-menu-item__link {
    color: rgba(255,255,255,.75) !important;
}
.sidebar-menu-item__link:hover,
.sidebar-sub-menu-item__link:hover {
    background: rgba(255,255,255,.08) !important;
    color: #fff !important;
}
.sidebar-menu-item--active > .sidebar-menu-item__link,
.sidebar-sub-menu-item--active > .sidebar-sub-menu-item__link {
    background: rgba(0,200,150,.18) !important;
    color: #00e89a !important;
}

/* Top header bar */
header.header,
.w-header,
[data-controller="w-header"] {
    background: #2d6a4f !important;
    border-bottom-color: #40916c !important;
}
.header__title,
.w-header__title { color: #fff !important; }

/* Primary action buttons */
.button.button-primary,
.button.yes,
a.button.button-primary {
    background: #2d6a4f !important;
    border-color: #2d6a4f !important;
    color: #fff !important;
}
.button.button-primary:hover { background: #1b4332 !important; }

/* Focus ring */
*:focus-visible { outline-color: #40916c !important; }

/* Page editor tabs active */
.tab-nav__tab--active { border-bottom-color: #2d6a4f !important; }

/* Admin index dashboard panels */
.panel { border-radius: 10px !important; }
</style>
""")


# ── Admin JS — minor UX ────────────────────────────────────────────────────────

@hooks.register('insert_global_admin_js')
def ecoiq_admin_js():
    """Adds a small breadcrumb subtitle showing 'EcoIQ CMS'."""
    return mark_safe("""
<script>
document.addEventListener('DOMContentLoaded', function () {
    const title = document.querySelector('.w-header__title, .header__title');
    if (title && !document.querySelector('.ecoiq-sub')) {
        const sub = document.createElement('small');
        sub.className = 'ecoiq-sub';
        sub.style.cssText = 'font-size:10px;opacity:.55;margin-left:8px;font-weight:400;';
        sub.textContent = 'EcoIQ CMS';
        title.appendChild(sub);
    }
});
</script>
""")
