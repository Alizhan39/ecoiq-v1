import math
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.template.loader import render_to_string

from .models import Assessment, QuestionnaireResponse, Finding
from .forms import AssessmentUploadForm
from .utils import extract_text
from .questions import QUESTIONS, grouped as grouped_questions
from .ai import run_ecoiq_analysis

PILLARS = [
    ('Environment', '#d8f3dc'),
    ('Social',      '#dde5f4'),
    ('Governance',  '#fef9c3'),
    ('Ethics',      '#fce7f3'),
    ('Innovation',  '#ede9fe'),
]

INDUSTRIES = [
    ('🛢️',  'Oil & Gas / Refining',        'Refineries, upstream, LNG'),
    ('⚙️',  'Manufacturing',               'General heavy industry'),
    ('🚗',  'Automotive',                  'Assembly, stamping, casting'),
    ('🧪',  'Chemicals',                   'Petrochemicals, polymers'),
    ('⚡',  'Utilities & Energy',          'Power gen, grid ops'),
    ('💊',  'Pharmaceuticals',             'API, fill-finish, biotech'),
    ('🥫',  'Food & Beverage',             'Processing, packaging'),
    ('📦',  'Logistics',                   'Warehousing, distribution'),
    ('⛏️',  'Metals & Mining',             'Smelting, rolling, extraction'),
    ('🏗️',  'Infrastructure',              'Cement, glass, building mat.'),
]


CTA_SECTORS = [
    'Oil & Gas', 'Manufacturing', 'Automotive', 'Chemicals',
    'Pharma', 'Logistics', 'Utilities', 'Metals & Mining',
]


CAPABILITY_CHIPS = [
    'AI Operational Diagnostics',
    'ESG Pillar Scoring',
    'Modernization Roadmaps',
    'Compliance Gap Analysis',
    'Sustainability Intelligence',
]

DESIGN_PARTNER_BENEFITS = [
    (
        'Full platform access — no cost',
        'Run unlimited assessments on your facility data throughout the pilot phase.',
    ),
    (
        'Direct product input',
        'Shape the analytical models, questionnaire structure, and report format alongside the EcoIQ team.',
    ),
    (
        'Preferential commercial terms',
        'Design partners receive locked pricing and early-adopter SLA commitments at general release.',
    ),
    (
        'Confidential and secure',
        'All facility data is handled under NDA. No data is shared with third parties.',
    ),
]

PILOT_TIMELINE = [
    (
        'Access Request',
        'Week 0–1',
        'Submit your facility profile via the access request form. EcoIQ reviews within 48 hours.',
    ),
    (
        'Discovery Call',
        'Week 1–2',
        '30-minute call to align on facility scope, data availability, and pilot objectives.',
    ),
    (
        'First Audit Session',
        'Week 2–4',
        'Upload facility documentation, complete the ESG questionnaire, generate your first AI report.',
    ),
    (
        'Feedback Loop',
        'Month 2–3',
        'Iterative refinement of findings and roadmap with EcoIQ team based on your operational reality.',
    ),
    (
        'Design Partner Status',
        'Month 3+',
        'Formalise design partner agreement, shape v2 feature roadmap, receive preferential terms.',
    ),
]


HOW_IT_STEP1 = [
    'PDF / plain-text document extraction',
    'Structured 10-question ESG questionnaire',
    'Facility profile and sector classification',
]
HOW_IT_STEP2 = [
    'Five-pillar ESG scoring (0–100 per pillar)',
    'Root cause and financial impact per finding',
    'Emissions and sustainability consequence',
    'Regulatory compliance gap identification',
]
HOW_IT_STEP3 = [
    'Radar chart score visualization',
    'Executive summary with priority actions',
    'Per-pillar analysis and Q&A transcript',
    'Printable and PDF export',
]
FRAMEWORKS = [
    'ISO 14001', 'GRI Standards', 'TCFD', 'ICMM Principles',
    'TSM Protocol', 'EU ETS', 'SBTi', 'Copper Mark', 'BRC Global Standard',
]
CTA_TRUST_SIGNALS = [
    'No commitment required',
    '48-hour response',
    'NDA available on request',
    'No credit card',
]


def landing(request):
    from django.conf import settings as _s
    return render(request, 'landing.html', {
        'industries':              INDUSTRIES,
        'cta_sectors':             CTA_SECTORS,
        'capability_chips':        CAPABILITY_CHIPS,
        'design_partner_benefits': DESIGN_PARTNER_BENEFITS,
        'pilot_timeline':          PILOT_TIMELINE,
        'step1_items':             HOW_IT_STEP1,
        'step2_items':             HOW_IT_STEP2,
        'step3_items':             HOW_IT_STEP3,
        'frameworks':              FRAMEWORKS,
        'cta_trust_signals':       CTA_TRUST_SIGNALS,
        'site_url':                _s.SITE_URL,
    })


HOW_IT_WORKS = [
    ('Upload a document',    'PDF or plain-text company report — or skip and answer the questionnaire directly.'),
    ('Answer 10 questions',  'Two questions per pillar (Environment, Social, Governance, Ethics, Innovation).'),
    ('AI generates findings', 'Claude analyses your responses and scores each pillar 0–100 with detailed notes.'),
    ('Download your report', 'View the HTML report or save as PDF — ready for board, investor, or audit use.'),
]


@login_required
def index(request):
    assessments = Assessment.objects.all()
    return render(request, 'core/index.html', {
        'pillars':     PILLARS,
        'assessments': assessments,
        'steps':       HOW_IT_WORKS,
    })


@login_required
def upload(request):
    if request.method == 'POST':
        form = AssessmentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            assessment = form.save(commit=False)
            if assessment.uploaded_file:
                try:
                    assessment.extracted_text = extract_text(assessment.uploaded_file)
                except Exception:
                    assessment.extracted_text = ''
            assessment.status = Assessment.STATUS_READY
            assessment.save()
            messages.success(request, f'Document uploaded for "{assessment.company_name}". Now complete the questionnaire.')
            return redirect('questionnaire', pk=assessment.pk)
    else:
        form = AssessmentUploadForm()

    return render(request, 'core/upload.html', {'form': form})


@login_required
def questionnaire(request, pk):
    assessment = get_object_or_404(Assessment, pk=pk)

    # Pre-load any saved answers so the form re-fills on revisit
    saved = {r.question_key: r.answer
             for r in assessment.responses.all()}

    if request.method == 'POST':
        # Validate at least one answer was given
        answered = 0
        for key, pillar, color, text, placeholder in QUESTIONS:
            answer = request.POST.get(key, '').strip()
            if answer:
                answered += 1
            QuestionnaireResponse.objects.update_or_create(
                assessment=assessment,
                question_key=key,
                defaults={
                    'question_text': text,
                    'answer': answer,
                },
            )

        if answered == 0:
            messages.warning(request, 'Please answer at least one question before continuing.')
            return redirect('questionnaire', pk=pk)

        assessment.status = Assessment.STATUS_PROCESSING
        assessment.save(update_fields=['status', 'updated_at'])
        messages.success(request, 'Answers saved. Generating your EcoIQ findings…')
        return redirect('run_analysis', pk=pk)

    # Enrich group data with question numbers and saved answers
    raw_groups = grouped_questions()
    q_number = 1
    groups = {}
    for pillar, data in raw_groups.items():
        groups[pillar] = {'color': data['color'], 'questions': []}
        for key, text, placeholder in data['questions']:
            groups[pillar]['questions'].append({
                'number':      q_number,
                'key':         key,
                'text':        text,
                'placeholder': placeholder,
                'answer':      saved.get(key, ''),
            })
            q_number += 1

    return render(request, 'core/questionnaire.html', {
        'assessment': assessment,
        'groups':     groups,
        'total':      len(QUESTIONS),
    })


@login_required
def run_analysis(request, pk):
    assessment = get_object_or_404(Assessment, pk=pk)

    # Already done — skip straight to results
    if assessment.status == Assessment.STATUS_COMPLETE:
        return redirect('assessment_detail', pk=pk)

    if request.method == 'POST':
        try:
            result = run_ecoiq_analysis(assessment)
            Finding.objects.update_or_create(
                assessment=assessment,
                defaults=result,
            )
            assessment.status = Assessment.STATUS_COMPLETE
            assessment.save(update_fields=['status', 'updated_at'])
            messages.success(request, 'EcoIQ analysis complete.')
            return redirect('assessment_detail', pk=pk)

        except ValueError as exc:
            # Missing API key or config error
            messages.error(request, str(exc))
            assessment.status = Assessment.STATUS_READY
            assessment.save(update_fields=['status', 'updated_at'])
            return redirect('assessment_detail', pk=pk)

        except Exception as exc:
            messages.error(request, f'Analysis failed: {exc}')
            assessment.status = Assessment.STATUS_ERROR
            assessment.save(update_fields=['status', 'updated_at'])
            return redirect('assessment_detail', pk=pk)

    # GET — render spinner; page auto-POSTs to trigger the AI call
    return render(request, 'core/run_analysis.html', {'assessment': assessment})


@login_required
def assessment_detail(request, pk):
    assessment = get_object_or_404(Assessment, pk=pk)
    scores = []
    pillar_notes = []
    if hasattr(assessment, 'finding'):
        f = assessment.finding
        scores = [
            ('Environment', f.score_environment, '#d8f3dc'),
            ('Social',      f.score_social,      '#dde5f4'),
            ('Governance',  f.score_governance,  '#fef9c3'),
            ('Ethics',      f.score_ethics,      '#fce7f3'),
            ('Innovation',  f.score_innovation,  '#ede9fe'),
            ('Overall',     f.score_overall,     '#1b4332'),
        ]
        notes = f.pillar_notes or {}
        pillar_notes = [
            ('Environment', notes.get('environment', ''), '#d8f3dc'),
            ('Social',      notes.get('social', ''),      '#dde5f4'),
            ('Governance',  notes.get('governance', ''),  '#fef9c3'),
            ('Ethics',      notes.get('ethics', ''),      '#fce7f3'),
            ('Innovation',  notes.get('innovation', ''),  '#ede9fe'),
        ]
    return render(request, 'core/assessment_detail.html', {
        'assessment':   assessment,
        'scores':       scores,
        'pillar_notes': pillar_notes,
    })


# ── Helpers ──────────────────────────────────────────────────────────────────

def _radar_polygon(scores_dict, cx=150, cy=150, r=110):
    """
    Return SVG polygon points for a 5-axis radar chart.
    Axes start at top (270°) and go clockwise.
    scores_dict: {'environment': 74, 'social': 61, ...}  values 0–100
    """
    keys   = ['environment', 'social', 'governance', 'ethics', 'innovation']
    points = []
    for i, key in enumerate(keys):
        angle_deg = 270 + i * 72          # top first, clockwise
        angle_rad = math.radians(angle_deg)
        score     = scores_dict.get(key, 0) / 100
        x = cx + r * score * math.cos(angle_rad)
        y = cy + r * score * math.sin(angle_rad)
        points.append(f"{x:.1f},{y:.1f}")
    return ' '.join(points)


def _radar_grid(cx=150, cy=150, r=110, steps=5):
    """Return list of SVG polygon point-strings for the background grid rings."""
    keys = ['environment', 'social', 'governance', 'ethics', 'innovation']
    rings = []
    for step in range(1, steps + 1):
        frac = step / steps
        pts = []
        for i in range(5):
            angle_rad = math.radians(270 + i * 72)
            x = cx + r * frac * math.cos(angle_rad)
            y = cy + r * frac * math.sin(angle_rad)
            pts.append(f"{x:.1f},{y:.1f}")
        rings.append(' '.join(pts))
    return rings


def _radar_axes(cx=150, cy=150, r=110):
    """Return list of (x1,y1,x2,y2) line coords for 5 axes."""
    axes = []
    for i in range(5):
        angle_rad = math.radians(270 + i * 72)
        x2 = cx + r * math.cos(angle_rad)
        y2 = cy + r * math.sin(angle_rad)
        axes.append((cx, cy, round(x2, 1), round(y2, 1)))
    return axes


def _radar_labels(cx=150, cy=150, r=110, offset=22):
    """Return list of (x, y, label) for the five pillar labels."""
    labels_text = ['Environment', 'Social', 'Governance', 'Ethics', 'Innovation']
    result = []
    for i, text in enumerate(labels_text):
        angle_rad = math.radians(270 + i * 72)
        x = cx + (r + offset) * math.cos(angle_rad)
        y = cy + (r + offset) * math.sin(angle_rad)
        result.append((round(x, 1), round(y, 1), text))
    return result


def _build_report_ctx(assessment):
    """Shared context builder for report() and share_report()."""
    f = assessment.finding
    scores_dict = {
        'environment': f.score_environment,
        'social':      f.score_social,
        'governance':  f.score_governance,
        'ethics':      f.score_ethics,
        'innovation':  f.score_innovation,
    }
    notes = f.pillar_notes or {}
    pillar_map = {
        'Environment': ('#d8f3dc', scores_dict['environment'], notes.get('environment', '')),
        'Social':      ('#dde5f4', scores_dict['social'],      notes.get('social', '')),
        'Governance':  ('#fef9c3', scores_dict['governance'],  notes.get('governance', '')),
        'Ethics':      ('#fce7f3', scores_dict['ethics'],      notes.get('ethics', '')),
        'Innovation':  ('#ede9fe', scores_dict['innovation'],  notes.get('innovation', '')),
    }
    saved_answers = {r.question_key: r.answer for r in assessment.responses.all()}
    raw_groups    = grouped_questions()
    q_number      = 1
    pillars       = []
    for pillar_name, data in raw_groups.items():
        color, score, note = pillar_map[pillar_name]
        qs = []
        for key, text, _ in data['questions']:
            answer = saved_answers.get(key, '').strip()
            if answer:
                qs.append({'number': q_number, 'text': text, 'answer': answer})
            q_number += 1
        pillars.append({
            'name':      pillar_name,
            'color':     color,
            'score':     score,
            'note':      note,
            'questions': qs,
        })
    return {
        'assessment':    assessment,
        'finding':       f,
        'pillars':       pillars,
        'radar_polygon': _radar_polygon(scores_dict),
        'radar_grid':    _radar_grid(),
        'radar_axes':    _radar_axes(),
        'radar_labels':  _radar_labels(),
    }


@login_required
def report(request, pk):
    assessment = get_object_or_404(Assessment, pk=pk)
    if not hasattr(assessment, 'finding'):
        raise Http404("No findings yet for this assessment.")
    ctx = _build_report_ctx(assessment)
    return render(request, 'core/report.html', ctx)


def share_report(request, token):
    """Public read-only report via share token. No login required."""
    assessment = get_object_or_404(Assessment, share_token=token)
    if not hasattr(assessment, 'finding'):
        raise Http404("Report not available.")
    ctx = _build_report_ctx(assessment)
    ctx['shared'] = True   # hides internal toolbar buttons in template
    return render(request, 'core/report.html', ctx)


@login_required
def report_pdf(request, pk):
    assessment = get_object_or_404(Assessment, pk=pk)
    if not hasattr(assessment, 'finding'):
        raise Http404("No findings yet for this assessment.")

    ctx = _build_report_ctx(assessment)

    try:
        import weasyprint
        html_string = render_to_string('core/report_pdf.html', ctx, request=request)
        pdf_bytes   = weasyprint.HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
        filename    = f"ecoiq-report-{assessment.pk}-{assessment.company_name[:30].replace(' ', '-').lower()}.pdf"
        response    = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    except Exception as exc:
        messages.error(request, f'PDF generation failed: {exc}')
        return redirect('report', pk=pk)
