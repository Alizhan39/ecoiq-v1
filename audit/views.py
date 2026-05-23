import math
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import Http404, HttpResponse
from django.template.loader import render_to_string

from .models import AuditSession, AuditResponse, Finding, Recommendation, ActionPlan, AuditReport
from .forms import AuditSessionForm
from .questions import QUESTIONS, grouped as grouped_questions
from .ai import run_full_analysis
from core.utils import extract_text  # reuse existing PDF extractor


# ── Index ─────────────────────────────────────────────────────────────────────

def index(request):
    sessions = AuditSession.objects.select_related('report').all()
    return render(request, 'audit/index.html', {'sessions': sessions})


# ── Upload / create session ───────────────────────────────────────────────────

def upload(request):
    if request.method == 'POST':
        form = AuditSessionForm(request.POST, request.FILES)
        if form.is_valid():
            session = form.save(commit=False)
            if session.uploaded_file:
                try:
                    session.extracted_text = extract_text(session.uploaded_file)
                except Exception:
                    session.extracted_text = ''
            session.status = 'ready'
            session.save()
            messages.success(request,
                f'Facility profile created for "{session.facility_name}". '
                'Complete the questionnaire to begin the analysis.')
            return redirect('audit_questionnaire', pk=session.pk)
    else:
        form = AuditSessionForm()
    return render(request, 'audit/upload.html', {'form': form})


# ── Questionnaire ─────────────────────────────────────────────────────────────

def questionnaire(request, pk):
    session = get_object_or_404(AuditSession, pk=pk)
    saved   = {r.question_key: r.answer for r in session.responses.all()}

    if request.method == 'POST':
        answered = 0
        for key, area, color, text, placeholder in QUESTIONS:
            answer = request.POST.get(key, '').strip()
            if answer:
                answered += 1
            AuditResponse.objects.update_or_create(
                session=session, question_key=key,
                defaults={'question_text': text, 'answer': answer},
            )
        if answered == 0:
            messages.warning(request, 'Please answer at least one question before continuing.')
            return redirect('audit_questionnaire', pk=pk)

        session.status = 'processing'
        session.save(update_fields=['status', 'updated_at'])
        messages.success(request, 'Answers saved. Starting AI analysis…')
        return redirect('audit_analyse', pk=pk)

    # Build enriched group data
    raw_groups = grouped_questions()
    q_number   = 1
    groups     = {}
    for area, data in raw_groups.items():
        groups[area] = {'color': data['color'], 'icon': data['icon'], 'questions': []}
        for key, text, placeholder in data['questions']:
            groups[area]['questions'].append({
                'number': q_number, 'key': key,
                'text': text, 'placeholder': placeholder,
                'answer': saved.get(key, ''),
            })
            q_number += 1

    return render(request, 'audit/questionnaire.html', {
        'session': session, 'groups': groups, 'total': len(QUESTIONS),
    })


# ── Analysis trigger ──────────────────────────────────────────────────────────

def analyse(request, pk):
    session = get_object_or_404(AuditSession, pk=pk)

    if session.status == 'complete':
        return redirect('audit_detail', pk=pk)

    if request.method == 'POST':
        try:
            run_full_analysis(session)
            session.status = 'complete'
            session.save(update_fields=['status', 'updated_at'])
            messages.success(request, 'Analysis complete — your report is ready.')
            return redirect('audit_detail', pk=pk)
        except ValueError as exc:
            messages.error(request, str(exc))
            session.status = 'processing'
            session.save(update_fields=['status', 'updated_at'])
            return redirect('audit_detail', pk=pk)
        except Exception as exc:
            messages.error(request, f'Analysis failed: {exc}')
            session.status = 'error'
            session.save(update_fields=['status', 'updated_at'])
            return redirect('audit_detail', pk=pk)

    return render(request, 'audit/analyse.html', {'session': session})


# ── Detail / dashboard ────────────────────────────────────────────────────────

def detail(request, pk):
    session  = get_object_or_404(AuditSession, pk=pk)
    report   = getattr(session, 'report', None)
    findings = session.findings.all()
    recs     = session.recommendations.all()
    phases   = session.action_phases.all()
    return render(request, 'audit/detail.html', {
        'session':  session,
        'report':   report,
        'findings': findings,
        'recs':     recs,
        'phases':   phases,
    })


# ── Report helpers ────────────────────────────────────────────────────────────

AREA_COLORS = {
    'energy':          '#fef3c7',
    'production':      '#dcfce7',
    'maintenance':     '#ede9fe',
    'safety':          '#dbeafe',
    'infrastructure':  '#fee2e2',
    'quality':         '#fce7f3',
    'workforce':       '#f0fdf4',
}

PRIORITY_COLORS = {
    'critical': '#fee2e2',
    'high':     '#fef3c7',
    'medium':   '#ede9fe',
    'low':      '#f0fdf4',
}

PRIORITY_BADGE = {
    'critical': '#dc2626',
    'high':     '#d97706',
    'medium':   '#7c3aed',
    'low':      '#16a34a',
}


def _priority_score(r):
    """Compute a 0-100 priority score from ROI, complexity, savings, and quick-win status."""
    roi_pts        = max(0, 40 - r.roi_months * 0.5)
    complexity_pts = {'low': 20, 'medium': 12, 'high': 4}.get(r.complexity, 10)
    savings_pts    = min(25, math.log10(max(r.savings_usd, 1000)) * 4.2)
    qw_pts         = 15 if r.is_quick_win else 0
    return min(100, round(roi_pts + complexity_pts + savings_pts + qw_pts))


def _report_context(session):
    if not hasattr(session, 'report'):
        raise Http404('No report available for this session.')
    rep      = session.report
    findings = list(session.findings.all())
    recs     = list(session.recommendations.all())
    phases   = list(session.action_phases.all())

    # Annotate recs with display colours + priority score
    for r in recs:
        r.area_color     = AREA_COLORS.get(r.category, '#f5f5f5')
        r.priority_color = PRIORITY_COLORS.get(r.priority, '#f5f5f5')
        r.priority_badge = PRIORITY_BADGE.get(r.priority, '#666')
        r.impl_steps     = [s.strip() for s in r.implementation.split('|') if s.strip()]
        r.computed_score = _priority_score(r)

    # Sort by computed priority score descending
    recs.sort(key=lambda r: r.computed_score, reverse=True)

    # Annotate findings
    for f in findings:
        f.area_color     = AREA_COLORS.get(f.area, '#f5f5f5')
        f.priority_badge = PRIORITY_BADGE.get(f.severity, '#666')

    # Before/after table rows
    ba = rep.before_after or {}
    ba_rows = []
    for area_key, meta in [
        ('energy',         ('Energy',         '⚡')),
        ('production',     ('Production',     '⚙️')),
        ('maintenance',    ('Maintenance',     '🔧')),
        ('safety',         ('Safety',         '🛡️')),
        ('infrastructure', ('Infrastructure', '🏭')),
    ]:
        if area_key in ba:
            row = ba[area_key]
            ba_rows.append({
                'area':    meta[0],
                'icon':    meta[1],
                'color':   AREA_COLORS.get(area_key, '#f5f5f5'),
                'current': row.get('current', '—'),
                'future':  row.get('future', '—'),
                'pct':     row.get('improvement_pct', 0),
            })

    eff_now  = rep.overall_efficiency_score
    eff_proj = rep.modernization_score

    gauges = [
        ('Current Efficiency',   eff_now,  '#dc2626', '#dc2626'),
        ('Projected Efficiency', eff_proj, '#16a34a', '#16a34a'),
    ]

    # Projected improvements for visualisation — sign indicates direction of improvement
    projections = [
        {'label': 'Energy Reduction',      'pct': rep.energy_reduction_pct,      'sign': '–', 'icon': '⚡', 'color': '#d97706'},
        {'label': 'Downtime Reduction',    'pct': rep.downtime_reduction_pct,     'sign': '–', 'icon': '🔧', 'color': '#dc2626'},
        {'label': 'Production Efficiency', 'pct': rep.production_efficiency_pct,  'sign': '+', 'icon': '⚙️', 'color': '#2563eb'},
        {'label': 'Emissions Reduction',   'pct': rep.emissions_reduction_pct,    'sign': '–', 'icon': '🌿', 'color': '#16a34a'},
    ]

    return {
        'session':        session,
        'report':         rep,
        'findings':       findings,
        'recs':           recs,
        'phases':         phases,
        'ba_rows':        ba_rows,
        'gauges':         gauges,
        'eff_now':        eff_now,
        'eff_proj':       eff_proj,
        'projections':    projections,
        'area_colors':    AREA_COLORS,
        'priority_badge': PRIORITY_BADGE,
        'quick_wins':     [r for r in recs if r.is_quick_win],
    }


def report(request, pk):
    session = get_object_or_404(AuditSession, pk=pk)
    ctx = _report_context(session)
    return render(request, 'audit/report.html', ctx)


def report_pdf(request, pk):
    session = get_object_or_404(AuditSession, pk=pk)
    ctx = _report_context(session)
    try:
        import weasyprint
        html_str  = render_to_string('audit/report_pdf.html', ctx, request=request)
        pdf_bytes = weasyprint.HTML(
            string=html_str,
            base_url=request.build_absolute_uri('/'),
        ).write_pdf()
        name = f"ecoiq-audit-{session.pk}-{session.facility_name[:30].replace(' ', '-').lower()}.pdf"
        resp = HttpResponse(pdf_bytes, content_type='application/pdf')
        resp['Content-Disposition'] = f'attachment; filename="{name}"'
        return resp
    except (ImportError, OSError, Exception) as exc:
        # WeasyPrint requires Cairo/Pango system libraries.
        # On Render free tier these may not be present — PDF export degrades gracefully.
        if 'cairo' in str(exc).lower() or 'pango' in str(exc).lower() or isinstance(exc, OSError):
            messages.error(
                request,
                'PDF export is not available in this environment — '
                'Cairo/Pango system libraries are missing. '
                'Use your browser\'s Print → Save as PDF instead.'
            )
        else:
            messages.error(request, f'PDF generation failed: {exc}')
        return redirect('audit_report', pk=pk)
