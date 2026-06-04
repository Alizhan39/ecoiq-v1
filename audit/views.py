import json as _json
import math
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.template.loader import render_to_string

from .models import (
    AuditSession, AuditResponse, Finding, Recommendation, ActionPlan, AuditReport,
    AIAnalysisJob, AIFinding, AIScoreEstimate,
)
from .forms import AuditSessionForm
from .questions import QUESTIONS, grouped as grouped_questions
# run_full_analysis is imported lazily inside the view that calls it — keeps
# the anthropic SDK (~40 MB) out of Django startup memory.
from core.utils import extract_text  # reuse existing PDF extractor


# ── Index ─────────────────────────────────────────────────────────────────────

@login_required
def index(request):
    sessions = AuditSession.objects.select_related('report').order_by('-created_at')[:50]
    return render(request, 'audit/index.html', {'sessions': sessions})


# ── Upload / create session ───────────────────────────────────────────────────

@login_required
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

@login_required
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

@login_required
def analyse(request, pk):
    session = get_object_or_404(AuditSession, pk=pk)

    if session.status == 'complete':
        return redirect('audit_detail', pk=pk)

    if request.method == 'POST':
        try:
            from .ai import run_full_analysis  # lazy — avoids loading anthropic at startup
            run_full_analysis(session)
            session.status = 'complete'
            session.save(update_fields=['status', 'updated_at'])
            messages.success(request, 'Analysis complete — your report is ready.')
            return redirect('audit_detail', pk=pk)
        except ValueError as exc:
            messages.error(request, str(exc))
            session.status = 'ready'   # reset so the user can retry
            session.save(update_fields=['status', 'updated_at'])
            return redirect('audit_detail', pk=pk)
        except Exception as exc:
            messages.error(request, f'Analysis failed: {exc}')
            session.status = 'error'
            session.save(update_fields=['status', 'updated_at'])
            return redirect('audit_detail', pk=pk)

    return render(request, 'audit/analyse.html', {'session': session})


# ── Detail / dashboard ────────────────────────────────────────────────────────

@login_required
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

    # ── Chart.js JSON ────────────────────────────────────────────────────
    # Projected improvements radar / bar
    chart_projections = _json.dumps({
        'labels': [p['label'] for p in projections],
        'pcts':   [float(p['pct']) for p in projections],
        'colors': [p['color'] for p in projections],
    })

    # Phase investment vs savings grouped bar
    chart_phases = _json.dumps({
        'labels':      [f'Phase {ph.phase}: {ph.label[:24]}' for ph in phases],
        'investments': [float(ph.investment) for ph in phases],
        'savings':     [float(ph.savings)    for ph in phases],
    }) if phases else _json.dumps({'labels': [], 'investments': [], 'savings': []})

    # Top-8 recommendations savings bar
    chart_recs = _json.dumps([
        {
            'label':   r.title[:30] + ('…' if len(r.title) > 30 else ''),
            'savings': float(r.savings_usd),
            'cost':    float(r.cost_usd),
            'roi':     r.roi_months,
            'score':   r.computed_score,
        }
        for r in recs[:8]
    ])

    # Findings severity distribution
    from collections import Counter
    sev_counts = Counter(f.severity for f in findings)
    _sev_order  = ['Critical', 'High', 'Medium', 'Low']
    _sev_colors = {'Critical': '#dc2626', 'High': '#f97316', 'Medium': '#f59e0b', 'Low': '#22c55e'}
    chart_severity = _json.dumps({
        'labels': [s for s in _sev_order if s in sev_counts],
        'counts': [sev_counts[s] for s in _sev_order if s in sev_counts],
        'colors': [_sev_colors[s] for s in _sev_order if s in sev_counts],
    })
    # ─────────────────────────────────────────────────────────────────────

    return {
        'session':           session,
        'report':            rep,
        'findings':          findings,
        'recs':              recs,
        'phases':            phases,
        'ba_rows':           ba_rows,
        'gauges':            gauges,
        'eff_now':           eff_now,
        'eff_proj':          eff_proj,
        'projections':       projections,
        'area_colors':       AREA_COLORS,
        'priority_badge':    PRIORITY_BADGE,
        'quick_wins':        [r for r in recs if r.is_quick_win],
        'chart_projections': chart_projections,
        'chart_phases':      chart_phases,
        'chart_recs':        chart_recs,
        'chart_severity':    chart_severity,
    }


@login_required
def report(request, pk):
    session = get_object_or_404(AuditSession, pk=pk)
    ctx = _report_context(session)
    return render(request, 'audit/report.html', ctx)


@login_required
def report_pdf(request, pk):
    session = get_object_or_404(AuditSession, pk=pk)
    ctx = _report_context(session)
    try:
        import gc
        import weasyprint
        html_str  = render_to_string('audit/report_pdf.html', ctx, request=request)
        _html_doc = weasyprint.HTML(
            string=html_str,
            base_url=request.build_absolute_uri('/'),
        )
        try:
            pdf_bytes = _html_doc.write_pdf()
        finally:
            del _html_doc
            gc.collect()
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


# ══════════════════════════════════════════════════════════════════════════════
# AI FINDINGS ENGINE VIEWS
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def ai_jobs(request):
    """
    Job queue + upload form.
    GET  → list all jobs
    POST → create a new job from uploaded PDF
    """
    from league.models import Company

    if request.method == 'POST':
        pdf = request.FILES.get('pdf_file')
        if not pdf:
            messages.error(request, 'Please select a PDF file to upload.')
            return redirect('ai_jobs')

        if not pdf.name.lower().endswith('.pdf'):
            messages.error(request, 'Only PDF files are accepted.')
            return redirect('ai_jobs')

        company_id = request.POST.get('company_id') or None
        company    = None
        if company_id:
            try:
                company = Company.objects.get(pk=company_id)
            except Company.DoesNotExist:
                pass

        job = AIAnalysisJob.objects.create(
            pdf_file=pdf,
            original_filename=pdf.name[:255],
            company=company,
            submitted_by=request.user,
        )
        messages.success(request, f'"{pdf.name}" uploaded. Click Analyse to start.')
        return redirect('ai_job_detail', pk=job.pk)

    jobs      = AIAnalysisJob.objects.select_related('company', 'submitted_by') \
                                      .prefetch_related('findings')
    companies = Company.objects.all().order_by('name')
    return render(request, 'audit/ai_jobs.html', {
        'jobs': jobs, 'companies': companies,
    })


@login_required
def ai_job_detail(request, pk):
    """Review findings for one job."""
    from league.models import Company

    job      = get_object_or_404(AIAnalysisJob, pk=pk)
    findings = job.findings.all()
    score_estimate = getattr(job, 'score_estimate', None)
    companies      = Company.objects.all().order_by('name')

    # Group findings by type for the template
    GROUPS = [
        ('Pollution Metrics', [
            'co2_metric','methane_metric','pm25_metric','so2_metric',
            'nox_metric','water_metric','waste_metric','pollution_other',
        ], '🌫️', '#e63946'),
        ('Projects & Investments', [
            'project','coal_replacement','investment',
        ], '🔨', '#40916c'),
        ('Greenwashing Signals', ['greenwashing'], '⚠️', '#f4a261'),
        ('Transparency', ['transparency'], '📋', '#2980b9'),
        ('Recommendations', ['recommendation'], '💡', '#8e44ad'),
        ('Other', ['other'], '📌', '#7f8c8d'),
    ]

    grouped = []
    for label, types, icon, color in GROUPS:
        group_findings = [f for f in findings if f.finding_type in types]
        if group_findings:
            grouped.append({
                'label': label, 'icon': icon, 'color': color,
                'findings': group_findings,
                'pending':  sum(1 for f in group_findings if f.status == 'pending'),
                'approved': sum(1 for f in group_findings if f.status == 'approved'),
                'rejected': sum(1 for f in group_findings if f.status == 'rejected'),
            })

    import json as _json
    # Chart data for analytics panel
    findings_chart = _json.dumps([
        {'label': g['label'], 'count': len(g['findings']), 'color': g['color']}
        for g in grouped
    ])
    score_chart = _json.dumps({
        'pillars':    ['Pollution', 'Reduction', 'Investment', 'Transparency', 'Community'],
        'estimated':  [
            score_estimate.est_pollution    if score_estimate else None,
            score_estimate.est_reduction    if score_estimate else None,
            score_estimate.est_investment   if score_estimate else None,
            score_estimate.est_transparency if score_estimate else None,
            score_estimate.est_community    if score_estimate else None,
        ],
        'benchmark':  [60, 60, 60, 60, 60],
        'gw_score':   score_estimate.greenwashing_score if score_estimate else None,
    } if score_estimate else {})

    return render(request, 'audit/ai_job_detail.html', {
        'job':             job,
        'findings':        findings,
        'grouped':         grouped,
        'score_estimate':  score_estimate,
        'companies':       companies,
        'total':           findings.count(),
        'pending_count':   findings.filter(status='pending').count(),
        'approved_count':  findings.filter(status='approved').count(),
        'rejected_count':  findings.filter(status='rejected').count(),
        'findings_chart':  findings_chart,
        'score_chart':     score_chart,
    })


@login_required
def ai_job_run(request, pk):
    """POST → trigger AI analysis synchronously."""
    if request.method != 'POST':
        return redirect('ai_job_detail', pk=pk)

    job = get_object_or_404(AIAnalysisJob, pk=pk)

    if job.status == 'processing':
        messages.warning(request, 'Analysis is already running.')
        return redirect('ai_job_detail', pk=pk)

    try:
        from .ai_engine import run_ai_analysis
        run_ai_analysis(job)
        messages.success(
            request,
            f'Analysis complete — {job.finding_count} findings extracted '
            f'({job.input_tokens + job.output_tokens:,} tokens used).'
        )
    except Exception as exc:
        job.status        = 'failed'
        job.error_message = str(exc)
        job.save(update_fields=['status', 'error_message'])
        messages.error(request, f'Analysis failed: {exc}')

    return redirect('ai_job_detail', pk=pk)


@login_required
def ai_finding_action(request, pk):
    """POST: approve or reject a single AIFinding, optionally add analyst note."""
    from django.utils import timezone as tz

    if request.method != 'POST':
        return redirect('ai_jobs')

    finding = get_object_or_404(AIFinding, pk=pk)
    action  = request.POST.get('action')  # 'approve' | 'reject'
    note    = request.POST.get('analyst_notes', '').strip()

    if action in ('approve', 'reject'):
        finding.status      = 'approved' if action == 'approve' else 'rejected'
        finding.reviewed_by = request.user
        finding.reviewed_at = tz.now()
        if note:
            finding.analyst_notes = note
        finding.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'analyst_notes'])
        messages.success(request, f'Finding {finding.status}.')

    return redirect('ai_job_detail', pk=finding.job_id)


@login_required
def ai_bulk_action(request, pk):
    """POST: approve-all or reject-all pending findings for a job."""
    if request.method != 'POST':
        return redirect('ai_job_detail', pk=pk)

    from django.utils import timezone as tz

    job    = get_object_or_404(AIAnalysisJob, pk=pk)
    action = request.POST.get('action')  # 'approve_all' | 'reject_all'

    if action == 'approve_all':
        count = job.findings.filter(status='pending').update(
            status='approved',
            reviewed_by=request.user,
            reviewed_at=tz.now(),
        )
        messages.success(request, f'{count} findings approved.')

    elif action == 'reject_all':
        types = request.POST.getlist('types') or None
        qs    = job.findings.filter(status='pending')
        if types:
            qs = qs.filter(finding_type__in=types)
        count = qs.update(
            status='rejected',
            reviewed_by=request.user,
            reviewed_at=tz.now(),
        )
        messages.success(request, f'{count} findings rejected.')

    return redirect('ai_job_detail', pk=pk)


@login_required
def ai_score_action(request, pk):
    """POST: approve or reset score estimate."""
    from django.utils import timezone as tz

    if request.method != 'POST':
        return redirect('ai_job_detail', pk=pk)

    job = get_object_or_404(AIAnalysisJob, pk=pk)
    se  = get_object_or_404(AIScoreEstimate, job=job)

    action = request.POST.get('action')  # 'approve' | 'revoke'
    note   = request.POST.get('analyst_notes', '').strip()

    if action == 'approve':
        se.approved    = True
        se.approved_by = request.user
        if note:
            se.analyst_notes = note
        se.save(update_fields=['approved', 'approved_by', 'analyst_notes'])
        messages.success(request, 'Score estimate approved.')

    elif action == 'revoke':
        se.approved    = False
        se.approved_by = None
        se.save(update_fields=['approved', 'approved_by'])
        messages.info(request, 'Score estimate approval revoked.')

    return redirect('ai_job_detail', pk=pk)


@login_required
def ai_job_apply(request, pk):
    """POST: apply all approved findings to the linked company."""
    if request.method != 'POST':
        return redirect('ai_job_detail', pk=pk)

    from league.models import Company
    from .ai_engine import apply_approved_findings

    job = get_object_or_404(AIAnalysisJob, pk=pk)

    # Allow overriding company from POST
    company_id = request.POST.get('company_id') or None
    if company_id:
        try:
            job.company = Company.objects.get(pk=company_id)
            job.save(update_fields=['company'])
        except Company.DoesNotExist:
            messages.error(request, 'Selected company not found.')
            return redirect('ai_job_detail', pk=pk)

    if not job.company:
        messages.error(request, 'Please link a company before applying findings.')
        return redirect('ai_job_detail', pk=pk)

    approved = job.findings.filter(status='approved').count()
    if approved == 0:
        messages.warning(request, 'No approved findings to apply. Approve some findings first.')
        return redirect('ai_job_detail', pk=pk)

    try:
        result = apply_approved_findings(job, job.company)
        parts  = [
            f"{result['projects_created']} project(s) created",
            f"{result['evidence_created']} evidence record(s) created",
        ]
        if result['score_applied']:
            parts.append('company scores updated from AI estimate')
        if result['errors']:
            messages.warning(request, 'Applied with warnings: ' + '; '.join(result['errors']))
        messages.success(
            request,
            f'Applied to {job.company.name}: {", ".join(parts)}.'
        )
    except Exception as exc:
        messages.error(request, f'Apply failed: {exc}')

    return redirect('ai_job_detail', pk=pk)


@login_required
def ai_job_save_note(request, pk):
    """POST: save analyst note on a job (used by sidebar auto-save)."""
    from django.http import JsonResponse
    if request.method != 'POST':
        return JsonResponse({'ok': False}, status=405)
    job = get_object_or_404(AIAnalysisJob, pk=pk)
    note = request.POST.get('analyst_notes', '')
    job.analyst_notes = note
    job.save(update_fields=['analyst_notes'])
    return JsonResponse({'ok': True})


@login_required
def ai_job_set_company(request, pk):
    """POST: set or change the company linked to a job."""
    if request.method != 'POST':
        return redirect('ai_job_detail', pk=pk)

    from league.models import Company

    job        = get_object_or_404(AIAnalysisJob, pk=pk)
    company_id = request.POST.get('company_id') or None

    if company_id:
        try:
            job.company = Company.objects.get(pk=company_id)
        except Company.DoesNotExist:
            messages.error(request, 'Company not found.')
            return redirect('ai_job_detail', pk=pk)
    else:
        job.company = None

    job.save(update_fields=['company'])
    messages.success(request, f'Job linked to {job.company.name}.' if job.company else 'Company link removed.')
    return redirect('ai_job_detail', pk=pk)
