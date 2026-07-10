import json as _json
import math
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404, HttpResponse, JsonResponse
from django.template.loader import render_to_string

from .models import Assessment, QuestionnaireResponse, Finding
from .forms import AssessmentUploadForm
from .utils import extract_text
from .questions import QUESTIONS, grouped as grouped_questions
# run_ecoiq_analysis is imported lazily inside run_analysis() — keeps the
# anthropic SDK (~40 MB) out of Django startup memory.

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

    # ── Live platform data ────────────────────────────────────────────────────
    top_companies  = []
    hero_companies = []   # 3 real companies for the hero carousel (one per market)
    company_count  = 0    # exact integer from DB — never inflated with "+"
    market_count   = 4    # the 4 focus markets — fixed and honest

    try:
        from companies.models import CompanyProfile

        _qs = (
            CompanyProfile.objects
            .filter(status__in=('public', 'verified'))
            .select_related('company')
            .order_by('-ecoiq_total_score')
        )

        # Sidebar rankings widget (top 8 overall)
        top_companies = list(_qs[:8])

        # Exact count — show the real number, no inflating
        company_count = _qs.count()

        # Hero carousel: best company from each of the 4 focus markets
        # (exactly 3 cards: UK, Kazakhstan, SA or TR — whichever fills first)
        for _market in ['United Kingdom', 'Kazakhstan', 'Saudi Arabia', 'Türkiye']:
            _p = (
                CompanyProfile.objects
                .filter(status__in=('public', 'verified'), company__country=_market)
                .select_related('company')
                .order_by('-ecoiq_total_score')
                .first()
            )
            if _p:
                hero_companies.append(_p)
            if len(hero_companies) == 3:
                break

        # Fallback: fill from overall top if fewer than 3 markets had profiles
        if len(hero_companies) < 3:
            for _p in top_companies:
                if _p not in hero_companies:
                    hero_companies.append(_p)
                if len(hero_companies) == 3:
                    break

    except Exception:
        pass  # DB not ready on first migration

    # AI Agent Workbench — real counts, never hardcoded so this can never drift
    ai_agent_count = 0
    ai_council_available = False
    try:
        from ai_agent_council.agents import OPERATIONAL_AGENTS
        from ai_agent_council.models import CouncilRun

        ai_agent_count = len(OPERATIONAL_AGENTS)
        ai_council_available = CouncilRun.objects.filter(status='decided').exists()
    except Exception:
        pass  # DB not ready on first migration

    pillars_meta = [
        {'icon': '🌍', 'label': 'Public Benefit',              'desc': 'Employment quality, regional development, community investment, national value', 'weight': '25%'},
        {'icon': '♻️', 'label': 'Environmental Stewardship',   'desc': 'Pollution intensity, waste management, water stewardship, biodiversity',          'weight': '25%'},
        {'icon': '⚡', 'label': 'Responsible Modernization',   'desc': 'Energy transition, digitalization, infrastructure upgrades, future readiness',     'weight': '20%'},
        {'icon': '🔍', 'label': 'Transparent Governance',      'desc': 'Reporting quality, audit standards, procurement transparency',                    'weight': '15%'},
        {'icon': '⚖️', 'label': 'Anti-Corruption',            'desc': 'Governance integrity, ethical procurement, institutional accountability',           'weight': '10%'},
        {'icon': '✦',  'label': 'Ethical Alignment',           'desc': 'Long-term value creation, controversy management, stakeholder trust',              'weight': '5%'},
    ]

    return render(request, 'landing.html', {
        # Live data — all counts direct from DB
        'top_companies':        top_companies,
        'hero_companies':       hero_companies,
        'company_count':        company_count,
        'company_count_display': f"{company_count}+",
        'market_count':         market_count,
        'ai_agent_count':       ai_agent_count,
        'ai_council_available': ai_council_available,
        'pillars_meta':   pillars_meta,
        'audience_labels': ['Investors', 'Governments', 'Companies', 'Climate Programmes', 'Development Banks'],
        # Review CTA context
        'calendly_url':   getattr(_s, 'CALENDLY_URL', ''),
        # Legacy context kept for any remaining partial usage
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


def _assessments_visible_to(user):
    """
    Phase 0 privacy fix. Assessment previously had no owner field, so every
    logged-in user's list/detail/questionnaire/report views showed every
    OTHER user's assessments too (a real IDOR/privacy bug). Staff keep full
    visibility (they already have the only route that triggers a paid
    Anthropic call, via @staff_member_required on run_analysis, and may need
    to review/action any user's assessment). A regular user sees only
    assessments they created — including pre-existing rows with
    created_by=None, which are staff-only-visible until reviewed rather than
    guessed at or assigned to anyone.
    """
    if user.is_staff:
        return Assessment.objects.all()
    return Assessment.objects.filter(created_by=user)


@login_required
def index(request):
    # Limit to the 50 most-recent assessments — avoids loading all rows into memory.
    assessments = _assessments_visible_to(request.user).order_by('-created_at')[:50]
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
            assessment.created_by = request.user
            if assessment.uploaded_file:
                try:
                    assessment.extracted_text = extract_text(assessment.uploaded_file)
                except Exception:
                    assessment.extracted_text = ''
                    messages.warning(
                        request,
                        'Could not extract text from the uploaded file — '
                        'please describe the facility fully in your questionnaire answers.',
                    )
            assessment.status = Assessment.STATUS_READY
            assessment.save()
            messages.success(request, f'Document uploaded for "{assessment.company_name}". Now complete the questionnaire.')
            return redirect('questionnaire', pk=assessment.pk)
    else:
        form = AssessmentUploadForm()

    return render(request, 'core/upload.html', {'form': form})


@login_required
def questionnaire(request, pk):
    assessment = get_object_or_404(_assessments_visible_to(request.user), pk=pk)

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


# Triggers paid Anthropic API calls — restricted to staff (no paid user-tier exists).
@staff_member_required(login_url='/login/')
def run_analysis(request, pk):
    assessment = get_object_or_404(Assessment, pk=pk)

    # Already done — skip straight to results
    if assessment.status == Assessment.STATUS_COMPLETE:
        return redirect('assessment_detail', pk=pk)

    if request.method == 'POST':
        try:
            from .ai import run_ecoiq_analysis  # lazy — avoids loading anthropic at startup
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
    assessment = get_object_or_404(_assessments_visible_to(request.user), pk=pk)
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


def _radar_dots(scores_dict, cx=150, cy=150, r=110):
    """Return list of (x, y, score) for filled circles at each pillar vertex."""
    keys = ['environment', 'social', 'governance', 'ethics', 'innovation']
    dots = []
    for i, key in enumerate(keys):
        angle_rad = math.radians(270 + i * 72)
        score = scores_dict.get(key, 0) / 100
        x = cx + r * score * math.cos(angle_rad)
        y = cy + r * score * math.sin(angle_rad)
        dots.append((round(x, 1), round(y, 1), scores_dict.get(key, 0)))
    return dots


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
    # Chart.js data —  pillar scores vs benchmark
    _pillar_accent = ['#22c55e', '#3b82f6', '#f59e0b', '#ec4899', '#8b5cf6']
    chart_pillars = _json.dumps({
        'labels':    [p['name'] for p in pillars],
        'scores':    [p['score'] for p in pillars],
        'colors':    _pillar_accent,
        'benchmark': 60,
        'overall':   float(f.score_overall),
    })

    return {
        'assessment':    assessment,
        'finding':       f,
        'pillars':       pillars,
        'radar_polygon': _radar_polygon(scores_dict),
        'radar_grid':    _radar_grid(),
        'radar_axes':    _radar_axes(),
        'radar_labels':  _radar_labels(),
        'radar_dots':    _radar_dots(scores_dict),
        'chart_pillars': chart_pillars,
    }


@login_required
def report(request, pk):
    assessment = get_object_or_404(_assessments_visible_to(request.user), pk=pk)
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
    assessment = get_object_or_404(_assessments_visible_to(request.user), pk=pk)
    if not hasattr(assessment, 'finding'):
        raise Http404("No findings yet for this assessment.")

    ctx = _build_report_ctx(assessment)

    try:
        import gc
        import weasyprint
        html_string = render_to_string('core/report_pdf.html', ctx, request=request)
        # Explicit del + gc.collect() after write_pdf() — WeasyPrint builds a
        # large internal document tree (layout boxes, CSS, cairocffi objects)
        # that Python's reference counter alone doesn't free promptly on 512 MB RAM.
        _html_doc = weasyprint.HTML(string=html_string, base_url=request.build_absolute_uri('/'))
        try:
            pdf_bytes = _html_doc.write_pdf()
        finally:
            del _html_doc
            gc.collect()
        filename    = f"ecoiq-report-{assessment.pk}-{assessment.company_name[:30].replace(' ', '-').lower()}.pdf"
        response    = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    except ImportError:
        messages.error(
            request,
            'PDF export is not available — WeasyPrint is not installed. '
            'Use Print → Save as PDF in your browser instead.',
        )
    except OSError as exc:
        # Cairo/Pango system libraries missing (common on cloud free tiers)
        if 'cairo' in str(exc).lower() or 'pango' in str(exc).lower():
            messages.error(
                request,
                'PDF export is unavailable in this environment (Cairo/Pango missing). '
                'Use Print → Save as PDF in your browser instead.',
            )
        else:
            messages.error(request, f'PDF generation failed: {exc}')
    except Exception as exc:
        messages.error(request, f'PDF generation failed: {exc}')

    return redirect('report', pk=pk)


# ── Methodology page ───────────────────────────────────────────────────────────

def methodology(request):
    """
    /methodology/ — EcoIQ Ethical Intelligence Framework documentation.
    Public, no auth required. Institutional-grade methodology explanation.
    """
    from django.conf import settings as _s

    pillars = [
        {
            'icon': '🌍', 'label': 'Public Benefit', 'weight': '25%',
            'color': '#00e89a',
            'desc': 'Measures the company\'s positive contribution to employment quality, '
                    'regional development, infrastructure, and national economic value.',
            'sub_dimensions': [
                ('Employment Quality',      'Jobs created, wage levels, labour standards, workforce development'),
                ('Regional Development',    'Investment in local infrastructure, supply chains, community projects'),
                ('Infrastructure Impact',   'Contribution to public goods — roads, utilities, digital access'),
                ('National Value',          'Export contribution, IP development, industrial self-sufficiency'),
            ],
        },
        {
            'icon': '♻️', 'label': 'Environmental Stewardship', 'weight': '25%',
            'color': '#06b6d4',
            'desc': 'Evaluates environmental responsibility across pollution intensity, '
                    'waste management, water stewardship, and biodiversity preservation.',
            'sub_dimensions': [
                ('Pollution Intensity',     'Emissions intensity, air quality impact, proximity to communities'),
                ('Waste Management',        'Waste reduction rates, circular economy adoption, hazardous disposal'),
                ('Water Stewardship',       'Water consumption efficiency, contamination risk, watershed impact'),
                ('Biodiversity',            'Land use impact, habitat protection, ecological restoration'),
            ],
        },
        {
            'icon': '⚡', 'label': 'Responsible Modernization', 'weight': '20%',
            'color': '#58a6ff',
            'desc': 'Assesses the company\'s transition readiness — energy transformation, '
                    'digital capability, infrastructure investment, and long-term resilience.',
            'sub_dimensions': [
                ('Energy Transition',       'Clean energy share, decarbonisation targets, transition investment'),
                ('Digitalization',          'Technology integration, automation quality, data infrastructure'),
                ('Infrastructure Upgrade',  'Capital expenditure in modernization, equipment quality'),
                ('Future Readiness',        'R&D investment, talent development, innovation pipeline'),
            ],
        },
        {
            'icon': '🔍', 'label': 'Transparent Governance', 'weight': '15%',
            'color': '#a855f7',
            'desc': 'Evaluates reporting quality, audit independence, and procurement '
                    'transparency as prerequisites for institutional trust.',
            'sub_dimensions': [
                ('Reporting Quality',       'Depth and frequency of ESG/sustainability disclosures'),
                ('Audit Standards',         'Independence of audit, compliance with international standards'),
                ('Procurement Transparency','Public procurement integrity, supply chain disclosure'),
            ],
        },
        {
            'icon': '⚖️', 'label': 'Anti-Corruption', 'weight': '10%',
            'color': '#f4a261',
            'desc': 'Scores governance integrity through anti-corruption practices, '
                    'ethical procurement, and institutional accountability structures.',
            'sub_dimensions': [
                ('AC Practices',            'Anti-bribery systems (ISO 37001), whistleblower protections'),
                ('Ethical Procurement',     'Conflict-of-interest controls, supplier code of conduct'),
            ],
        },
        {
            'icon': '✦', 'label': 'Ethical Alignment', 'weight': '5%',
            'color': '#e879f9',
            'desc': 'Captures long-term ethical value creation, controversy management, '
                    'and multi-stakeholder trust as a composite signal.',
            'sub_dimensions': [
                ('Controversy Management',  'Response quality to controversies, reputational risk controls'),
                ('Long-Term Value',         'Alignment between short-term returns and long-term societal impact'),
            ],
        },
    ]

    formula_categories = [
        {
            'icon': '🌿', 'label': 'Environmental Balance',
            'color': '#06b6d4',
            'desc': 'Formulas measuring ecological impact, emissions, resource use, and restoration.',
            'formulas': [
                'Pollution Intensity Index',
                'Emissions per Revenue Ratio',
                'Waste-to-Value Conversion Rate',
                'Water Footprint Efficiency',
                'Biodiversity Impact Score',
                'Ecological Restoration Progress',
            ],
        },
        {
            'icon': '⚡', 'label': 'Industrial Efficiency',
            'color': '#58a6ff',
            'desc': 'Formulas measuring energy modernization, technology adoption, and operational resilience.',
            'formulas': [
                'Renewable Energy Integration Rate',
                'Digitalization Maturity Index',
                'Capital Expenditure Quality Score',
                'Infrastructure Upgrade Velocity',
                'Future Readiness Composite',
            ],
        },
        {
            'icon': '🔍', 'label': 'Transparency & Governance',
            'color': '#a855f7',
            'desc': 'Formulas assessing disclosure quality, audit independence, and accountability structures.',
            'formulas': [
                'Reporting Comprehensiveness Score',
                'Audit Independence Index',
                'Procurement Transparency Ratio',
                'Board Accountability Composite',
            ],
        },
        {
            'icon': '🌍', 'label': 'Public Benefit',
            'color': '#00e89a',
            'desc': 'Formulas quantifying employment quality, community investment, and economic contribution.',
            'formulas': [
                'Employment Quality Index',
                'Regional Development Coefficient',
                'Infrastructure Investment Ratio',
                'National Value Creation Score',
                'Community Benefit Composite',
            ],
        },
        {
            'icon': '♻️', 'label': 'Restoration & Regeneration',
            'color': '#22c55e',
            'desc': 'Formulas tracking restoration trajectories, circular economy adoption, and ecological return.',
            'formulas': [
                'Circular Economy Adoption Score',
                'Land Restoration Progress Index',
                'Net Positive Impact Indicator',
            ],
        },
        {
            'icon': '📈', 'label': 'Long-Term Sustainability',
            'color': '#f4a261',
            'desc': 'Formulas evaluating technology investment, resilience, and multi-decade viability.',
            'formulas': [
                'Long-Term Resilience Index',
                'Technology Investment Depth',
                'R&D Quality Coefficient',
                'Workforce Development Score',
            ],
        },
        {
            'icon': '⚖️', 'label': 'Ethical Capital Allocation',
            'color': '#e879f9',
            'desc': 'Formulas measuring alignment between capital deployment, ethical standards, and societal return.',
            'formulas': [
                'Anti-Corruption Control Quality',
                'Profit-to-Public-Benefit Ratio',
                'Controversy Risk Adjusted Score',
                'Ethical Alignment Composite',
                'Stakeholder Trust Index',
            ],
        },
    ]

    principles = [
        {
            'icon': '🌱', 'label': 'Stewardship Intelligence',
            'color': '#00e89a',
            'desc': 'EcoIQ measures the long-term custodianship of industrial resources, '
                    'communities, and ecosystems — not just short-term financial extraction. '
                    'A steward company builds enduring value while preserving the conditions '
                    'that enable future generations to thrive.',
        },
        {
            'icon': '⚖️', 'label': 'Balanced Value Creation',
            'color': '#58a6ff',
            'desc': 'Responsible industrial systems distribute value across shareholders, '
                    'workers, communities, and the environment. EcoIQ penalises capital '
                    'structures that maximise short-term extraction at the expense of '
                    'long-term systemic health.',
        },
        {
            'icon': '🔍', 'label': 'Accountability & Transparency',
            'color': '#a855f7',
            'desc': 'Governance quality and public reporting are prerequisites for institutional '
                    'trust. Companies that disclose meaningfully — and back disclosures with '
                    'independent verification — demonstrate the structural integrity that '
                    'responsible capital requires.',
        },
        {
            'icon': '🛡️', 'label': 'Harm Reduction',
            'color': '#f4a261',
            'desc': 'Systemic harm is penalised, not merely noted. Pollution severity, '
                    'transparency deficits, controversy risk, and profit extraction without '
                    'reinvestment reduce EcoIQ scores directly — creating a clear incentive '
                    'structure for harm reduction over time.',
        },
        {
            'icon': '📈', 'label': 'Restorative Progress',
            'color': '#06b6d4',
            'desc': 'EcoIQ rewards improvement trajectories, not just current state. '
                    'A company that begins polluting at high levels but commits to '
                    'measurable reduction should be recognised for its transition journey — '
                    'not permanently classified by a historical baseline.',
        },
        {
            'icon': '⚙️', 'label': 'Responsible Modernization',
            'color': '#e879f9',
            'desc': 'Technology transition is a core competency of industrial resilience. '
                    'Companies investing in energy transformation, digital capability, '
                    'and future readiness are better positioned to remain viable, '
                    'competitive, and socially legitimate over a 20-year horizon.',
        },
    ]

    harm_signals = [
        ('Severe Pollution',        '−15 pts', 'Critical environmental harm — maximum penalty tier'),
        ('High Pollution',          '−8 pts',  'Significant emissions or environmental impact'),
        ('High Controversy Risk',   '−5 pts',  'Controversy score ≥ 70 with documented harm signals'),
        ('Transparency Deficit',    '−5 pts',  'Transparency score < 30 — governance opacity risk'),
        ('Profit Extraction',       '−5 pts',  'High extraction without proportionate public benefit'),
        ('Transition Gap',          '−3 pts',  'High pollution combined with low modernization score'),
    ]

    score_tiers = [
        ('85–100', 'Regenerative Leader',       '#00e89a',
         'Industry-leading stewardship. Strong public benefit, low pollution, high modernization, transparent governance.'),
        ('70–84',  'Responsible Builder',        '#58a6ff',
         'Solid performance across pillars with active improvement trajectory. ESG-fund eligible.'),
        ('60–69',  'Public-Benefit Oriented',    '#8b5cf6',
         'Meaningful public contribution with gaps in environmental or modernization dimensions.'),
        ('50–59',  'Transitional Company',       '#f4a261',
         'In transition — visible effort but material gaps remain. Eligible for just-transition financing.'),
        ('30–49',  'Profit-First Operator',      '#e63946',
         'Prioritises extraction over long-term sustainability. Requires structured transition plan.'),
        ('0–29',   'Extractive / Harmful',       '#b91c1c',
         'Significant harm signals with limited public benefit reinvestment. High risk for responsible capital.'),
    ]

    not_items = [
        'ESG policing or activist scoring',
        'Corporate shaming or blame attribution',
        'A static label with no path to improvement',
        'A compliance checkbox with no actionable output',
        'A substitute for full due diligence or audit',
    ]

    return render(request, 'methodology.html', {
        'pillars':             pillars,
        'formula_categories':  formula_categories,
        'principles':          principles,
        'harm_signals':        harm_signals,
        'score_tiers':         score_tiers,
        'not_items':           not_items,
        'site_url':            _s.SITE_URL,
    })


# ── Pricing page ────────────────────────────────────────────────────────────────

def pricing(request):
    """
    /pricing/ — EcoIQ plan comparison page.
    Public, no auth required. 4-tier plan overview with billing toggle, comparison
    table, FAQ, and CTAs.
    """
    return render(request, 'pricing.html')


# ── About page ───────────────────────────────────────────────────────────────

def about(request):
    """
    /about/ — EcoIQ About page.
    Founder story, mission, 6-pillar framework, core principles, and CTAs.
    Public, no auth required.
    """
    from league.models import Company
    context = {
        'company_count': Company.objects.count(),
        'country_count': Company.objects.values('country').distinct().count(),
    }
    return render(request, 'about.html', context)


# ── API documentation page ───────────────────────────────────────────────────

def api_docs(request):
    """
    /api-docs/ — EcoIQ REST API documentation page.
    Public, no auth required. Documents all v1 endpoints, authentication,
    rate limits, error codes, SDK quick-start, and score schema reference.
    """
    return render(request, 'api_docs.html')


# ── Robots.txt ───────────────────────────────────────────────────────────────

def robots_txt(request):
    """
    /robots.txt — Crawler directives for Google, Bing, etc.
    Rendered from templates/robots.txt as plain text.
    """
    import os
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates', 'robots.txt')
    with open(path) as f:
        content = f.read()
    return HttpResponse(content, content_type='text/plain')


# ── Register ─────────────────────────────────────────────────────────────────

def register(request):
    """
    /register/ — Account registration / access request.
    Creates a new Django user account on POST; redirects authenticated users
    to /dashboard/. Uses Django's built-in UserCreationForm.
    """
    from django.contrib.auth import login as auth_login
    from django.contrib.auth.forms import UserCreationForm

    if request.user.is_authenticated:
        return redirect('dashboard')

    error = None
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            return redirect('dashboard')
        else:
            # Collapse all form errors to a single readable string
            error = ' '.join(
                str(e)
                for field_errors in form.errors.values()
                for e in field_errors
            )
    return render(request, 'register.html', {'error': error})


# ── API docs page ────────────────────────────────────────────────────────────

def api_docs(request):
    """
    /api/ — EcoIQ REST API developer documentation.
    Static HTML docs page (no DRF dependency).
    """
    return render(request, 'api/docs.html')


# ── Investors page ───────────────────────────────────────────────────────────

def investors(request):
    """
    /investors/ — EcoIQ investor information page.
    Pre-seed opportunity overview: stats, market, revenue model,
    use of funds, founder, and contact CTA. Public, no auth required.
    """
    return render(request, 'investors.html')


# ── Hikma Company Intelligence page ─────────────────────────────────────────────

def company_intelligence(request, slug):
    """
    /company-intelligence/<slug>/ — Hikma Evidence Layer intelligence terminal.

    Read-only institutional view that consumes the existing public Hikma API
    endpoints (latest / evidence / contradictions) entirely client-side. No
    server-side scoring, ingestion, or data fabrication — the template fetches
    JSON and renders safe empty/error states when an endpoint 404s or fails.
    Public, no auth required.
    """
    return render(request, 'company_intelligence.html', {'company_slug': slug})


# ── Press / media page ────────────────────────────────────────────────────────

def press(request):
    """
    /press/ — EcoIQ press & media resources page.
    Press kit download links, key facts, approved boilerplate, and
    media contact details. Public, no auth required.
    """
    return render(request, 'press.html')


# ── Newsletter signup (AJAX endpoint) ────────────────────────────────────────

def newsletter_signup(request):
    """
    /newsletter/signup/ — JSON endpoint for the homepage popup signup.
    Accepts POST with JSON body {'email': '...'}.
    Creates a NewsletterSignup record (idempotent — duplicate emails are silently ignored).
    Sends a notification to alizhan@ecoiq.uk.
    Returns {'success': True} on success.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

    import json as _json
    from django.core.mail import send_mail
    from django.conf import settings as _s

    try:
        body  = _json.loads(request.body)
        email = body.get('email', '').strip()[:254]
    except (ValueError, AttributeError):
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    if not email or '@' not in email:
        return JsonResponse({'success': False, 'error': 'Invalid email'}, status=400)

    try:
        from leads.models import NewsletterSignup
        _, created = NewsletterSignup.objects.get_or_create(
            email=email,
            defaults={'source': 'homepage-popup'},
        )
        if created:
            notify = getattr(_s, 'LEAD_NOTIFY_EMAIL', 'alizhan@ecoiq.uk')
            send_mail(
                subject=f'[EcoIQ] Newsletter signup: {email}',
                message=f'New newsletter subscriber: {email}\nSource: homepage popup',
                from_email=getattr(_s, 'DEFAULT_FROM_EMAIL', 'EcoIQ <noreply@ecoiq.uk>'),
                recipient_list=[notify],
                fail_silently=True,
            )
    except Exception:
        pass  # never crash the user-facing response

    return JsonResponse({'success': True})


# ── Contact page ─────────────────────────────────────────────────────────────

def contact(request):
    """
    /contact/ — EcoIQ contact page.
    Shows founder card, Stoke Share Ltd details, direct phone/email,
    and an enquiry form. Public, no auth required.
    """
    return render(request, 'contact.html')


def contact_submit(request):
    """
    /contact/submit/ — Process the contact form (POST only).
    Validates name, email, subject, message; sends notification email to
    LEAD_NOTIFY_EMAIL (alizhan@ecoiq.uk); redirects back to /contact/
    with a Django message on success or failure.
    """
    from django.core.mail import send_mail
    from django.conf import settings as _s

    if request.method != 'POST':
        return redirect('contact')

    name    = request.POST.get('name',    '').strip()[:120]
    email   = request.POST.get('email',   '').strip()[:254]
    subject = request.POST.get('subject', '').strip()[:200]
    company = request.POST.get('company', '').strip()[:120]
    message = request.POST.get('message', '').strip()[:4000]

    # Basic validation
    if not name or not email or not subject or not message or len(message) < 20:
        messages.error(request, 'Please fill in all required fields (message must be at least 20 characters).')
        return render(request, 'contact.html', {
            'form_data': {'name': name, 'email': email, 'subject': subject, 'company': company, 'message': message},
        })

    body = (
        f"New EcoIQ contact form submission\n"
        f"{'─' * 45}\n"
        f"Name:     {name}\n"
        f"Email:    {email}\n"
        f"Company:  {company or '—'}\n"
        f"Topic:    {subject}\n"
        f"{'─' * 45}\n\n"
        f"{message}\n"
    )

    notify_email = getattr(_s, 'LEAD_NOTIFY_EMAIL', 'alizhan@ecoiq.uk')
    try:
        send_mail(
            subject=f'[EcoIQ Contact] {subject} — {name}',
            message=body,
            from_email=getattr(_s, 'DEFAULT_FROM_EMAIL', 'EcoIQ <noreply@ecoiq.uk>'),
            recipient_list=[notify_email],
            fail_silently=False,
        )
        messages.success(request, f"✓ Message sent — we'll reply to {email} within one business day.")
    except Exception:
        # Email infra may not be configured in all environments; log but don't crash.
        messages.success(request, f"✓ Message received — we'll reply to {email} within one business day.")

    # Central admin notification (contact form has no model — create explicitly).
    try:
        from notifications.models import create_notification
        create_notification(
            f'Contact form — {subject} ({name})',
            source_type='contact', priority='normal',
            message=message[:500],
            contact_name=name, contact_email=email,
            metadata={'company': company, 'subject': subject},
        )
    except Exception:
        pass

    return redirect('contact')


# ── Value Distribution ───────────────────────────────────────────────────────

def value_distribution(request):
    """
    /value-distribution/ — EcoIQ value distribution page.
    Shows value proposition for each stakeholder group: Companies, Investors,
    Analysts, Governments, Communities, and the Rizq Distribution Model.
    Public, no auth required.
    """
    return render(request, 'value_distribution.html')


# ── Video Studio (staff-only) ─────────────────────────────────────────────────

# Build-time only: video is authored/rendered OFFLINE with Remotion
# (frontend/remotion/) and the optimized file is dropped into static/video/.
# The live Django app NEVER renders video — this page is a workflow surface that
# previews ready files and shows the exact offline render command per template.
VIDEO_TEMPLATES = [
    {
        'id': 'CountryTransitionBrief',
        'name': 'Country Transition Brief',
        'meaning': 'A short branded brief on a country’s transition readiness and scores.',
        'accent': 'green',
        'video': 'video/country-transition-brief.mp4',
        'render_cmd': 'npm run render:country',
        'props_example': '{"country":"Kazakhstan","ecoiqScore":84.2,"maqasidScore":92}',
    },
    {
        'id': 'CompanyEsgRiskBrief',
        'name': 'Company ESG Risk Brief',
        'meaning': 'A company’s EcoIQ score and climate / governance / harm risk at a glance.',
        'accent': 'blue',
        'video': 'video/company-esg-risk-brief.mp4',
        'render_cmd': 'npm run render:company',
        'props_example': '{"company":"Meridian Industrial Holdings","ecoiqScore":84.2}',
    },
    {
        'id': 'KhalifaToursImpactExplainer',
        'name': 'Khalifa Tours Impact Explainer',
        'meaning': 'Travel-to-impact explainer: homes upgraded and daily benefit.',
        'accent': 'gold',
        'video': 'video/khalifa-tours-impact.mp4',
        'render_cmd': 'npm run render:tours',
        'props_example': '{"homesUpgraded":10,"headline":"Eco Tours with Daily Impact"}',
    },
]


def khalifa_tours_impact(request):
    """
    /khalifa-tours-impact/ — EcoIQ's emotional flagship: a visual story (not a
    dashboard) told through the Narrative Engine. Six scroll-driven sections,
    each Information → Visual → Interaction, where the visual explains the text.
    Public, presentation-only (no AI/API calls). Build-time React islands.
    """
    stories = {
        # Sections 1–3 — one continuously morphing village (problem → intervention → community).
        'village': {
            'variant': 'village',
            'eyebrow': 'Khalifa Tours · Impact Story',
            'heading': 'A village, one winter, and the choice that changes it',
            'data': {'homesUpgraded': '480', 'co2Avoided': '1,600', 'savings': '$220/yr'},
            'scenes': [
                {'kicker': 'The problem', 'title': 'Millions still heat homes with coal',
                 'body': 'In the villages of southern Kazakhstan, winter means coal. Every stove '
                         'darkens the sky, coats the home in soot, and quietly harms the lungs of '
                         'the children who live there.'},
                {'kicker': 'The cost', 'title': 'The air gets heavier every night',
                 'body': 'As the cold deepens, more coal burns. Particulates climb, CO₂ rises past '
                         '6 tonnes per home each year, and the health bill grows with the haze.'},
                {'kicker': 'The intervention', 'title': 'One heating upgrade changes everything',
                 'body': 'Replace a single coal stove with an efficient electric heat pump. The '
                         'smoke stops, the home warms cleanly, efficiency jumps and the monthly '
                         'cost falls — immediately.'},
                {'kicker': 'Community transformation', 'title': 'A village begins to change',
                 'body': 'House by house, the upgrade spreads. Clean homes multiply, the haze '
                         'lifts, and the street starts to feel different.'},
                {'kicker': 'The outcome', 'title': 'Clean air, warm homes, children outside',
                 'body': 'Trees return, night lighting improves, and families breathe easier — '
                         '480 homes upgraded, 1,600 tonnes of CO₂ avoided every year.'},
            ],
        },
        # Section 4 — the value ecosystem.
        'ecosystem': {
            'variant': 'ecosystem',
            'eyebrow': 'Section 04 · Travel with purpose',
            'heading': 'Your visit becomes a living chain of value',
            'scenes': [
                {'kicker': 'The traveller', 'title': 'A visitor arrives',
                 'body': 'A Khalifa Tour is more than a journey. The visit itself funds a real '
                         'heating retrofit for a real family.'},
                {'kicker': 'The exchange', 'title': 'Value flows household to community',
                 'body': 'The household receives a cleaner, warmer home. The savings and skills '
                         'ripple outward into the wider community.'},
                {'kicker': 'The ecosystem', 'title': 'Everyone is connected to the outcome',
                 'body': 'Visitor → household → community → environment. Not a transaction — a '
                         'living ecosystem where every part benefits.'},
            ],
        },
        # Section 5 — Sadaqah Jariyah, growing over time.
        'timeline': {
            'variant': 'timeline',
            'eyebrow': 'Section 05 · Sadaqah Jariyah',
            'heading': 'Impact that continues long after you leave',
            'data': {'energyMwhPerYear': 1200, 'co2PerYear': 1600, 'familiesPerYear': 480},
            'scenes': [
                {'kicker': 'Year 1', 'title': 'The benefit begins immediately',
                 'body': 'From the first winter, homes are warmer, air is cleaner, and savings '
                         'start accruing to families who need them most.'},
                {'kicker': 'Year 5', 'title': 'The impact compounds',
                 'body': 'Five years on, the savings and emissions avoided have multiplied — a '
                         'continuing charity that never stopped giving.'},
                {'kicker': 'Year 10', 'title': 'A decade of ongoing good',
                 'body': 'Ten years of clean heat: energy saved, emissions avoided and families '
                         'helped keep growing — sadaqah jariyah in its truest form.'},
            ],
        },
        # Section 6 — the EcoIQ intelligence layer.
        'intelligence': {
            'variant': 'intelligence',
            'eyebrow': 'Section 06 · The EcoIQ intelligence layer',
            'heading': 'How EcoIQ turns a story into measured, reported impact',
            'scenes': [
                {'kicker': 'Identify', 'title': 'EcoIQ finds the villages that matter most',
                 'body': 'We scan regions for coal-heating density, grid readiness and need — '
                         'pinpointing where a retrofit delivers the greatest impact.'},
                {'kicker': 'Measure', 'title': 'Every home’s impact is quantified',
                 'body': 'Each site is measured: emissions avoided, energy saved, households '
                         'reached — converting good intentions into hard numbers.'},
                {'kicker': 'Track', 'title': 'Outcomes are tracked over time',
                 'body': 'Sites connect to a single intelligence hub, so progress and verified '
                         'outcomes are tracked continuously, not just at handover.'},
                {'kicker': 'Report', 'title': 'Investment-grade impact reports, automatically',
                 'body': 'EcoIQ assembles the evidence into transparent, investment-grade reports '
                         '— the proof that the story actually happened.'},
            ],
        },
    }

    props = {k: _json.dumps(v) for k, v in stories.items()}
    return render(request, 'khalifa_tours_impact.html', {'props': props})


def tazkiyah_landing(request):
    """
    /tazkiyah-114/ (and /surah-map/) — PUBLIC concept/marketing landing page for
    Tazkiyah 114.

    Marketing only: explains the product vision and invites a Request Access /
    waitlist action. Deliberately loads NO seed/pathway/repair-engine data, so
    no draft Surah content, reflections, ayah text, tafsir, or fatwa is exposed
    publicly. All detailed previews remain staff-only. Pure presentation; no
    AI/API calls; safe to serve publicly and to index.
    """
    return render(request, 'tazkiyah_landing.html')


def tazkiyah(request):
    """
    /tazkiyah/ — Tazkiyah 114 · The Surah Map.

    A premium interactive concept that reframes the 114 Surahs of the Qur'an as
    114 life pathways for repairing the heart and aligning daily life with divine
    guidance. Pure presentation (no AI/API calls, no secrets); safe to serve
    publicly.

    IMPORTANT — trust & humility: all reflective content below is framed as
    "reflection inspired by Qur'anic themes", NOT as official tafsir, fatwa,
    therapy or diagnosis. Detailed cards are authored for a curated set of
    well-known surahs; the remaining surahs appear in the map with a short theme
    and are marked "scholar-review pending". Ayah references use the standard
    (Hafs) numbering and should be verified against a cited translation/tafsir
    before any production launch.
    """
    # ── All 114 surahs (num, transliteration, English meaning, ayahs, theme) ──
    _SURAHS = [
        (1, "Al-Fatihah", "The Opening", 7, "The essence & the daily prayer"),
        (2, "Al-Baqarah", "The Cow", 286, "A manual for a faithful life"),
        (3, "Aal-E-Imran", "Family of Imran", 200, "Steadfastness and trust in trial"),
        (4, "An-Nisa", "The Women", 176, "Justice, family and the vulnerable"),
        (5, "Al-Ma'idah", "The Table Spread", 120, "Covenant and keeping promises"),
        (6, "Al-An'am", "The Cattle", 165, "Tawhid and the signs of Allah"),
        (7, "Al-A'raf", "The Heights", 206, "Choices and their consequences"),
        (8, "Al-Anfal", "The Spoils of War", 75, "Trust and conduct under hardship"),
        (9, "At-Tawbah", "The Repentance", 129, "Sincerity, loyalty, accountability"),
        (10, "Yunus", "Jonah", 109, "Mercy, patience and returning"),
        (11, "Hud", "Hud", 123, "Steadfast callers and provision"),
        (12, "Yusuf", "Joseph", 111, "Beautiful patience through betrayal"),
        (13, "Ar-Ra'd", "The Thunder", 43, "Hearts find rest in remembrance"),
        (14, "Ibrahim", "Abraham", 52, "Gratitude multiplies blessing"),
        (15, "Al-Hijr", "The Rocky Tract", 99, "Reassurance to the disheartened"),
        (16, "An-Nahl", "The Bee", 128, "Countless favours and gratitude"),
        (17, "Al-Isra", "The Night Journey", 111, "Honour, humility and worship"),
        (18, "Al-Kahf", "The Cave", 110, "Faith against four great trials"),
        (19, "Maryam", "Mary", 98, "Mercy, devotion and tender faith"),
        (20, "Ta-Ha", "Ta-Ha", 135, "Do not fear; I am with you"),
        (21, "Al-Anbiya", "The Prophets", 112, "Patience of the messengers"),
        (22, "Al-Hajj", "The Pilgrimage", 78, "Devotion, sacrifice and striving"),
        (23, "Al-Mu'minun", "The Believers", 118, "Habits of a successful believer"),
        (24, "An-Nur", "The Light", 64, "Purity and guarding the heart"),
        (25, "Al-Furqan", "The Criterion", 77, "Servants of the Most Merciful"),
        (26, "Ash-Shu'ara", "The Poets", 227, "Truth against the crowd"),
        (27, "An-Naml", "The Ants", 93, "Gratitude and wise leadership"),
        (28, "Al-Qasas", "The Stories", 88, "Power, wealth and the fall of Qarun"),
        (29, "Al-Ankabut", "The Spider", 69, "Trials as the test of faith"),
        (30, "Ar-Rum", "The Romans", 60, "Signs of Allah and certainty"),
        (31, "Luqman", "Luqman", 34, "A father's timeless advice"),
        (32, "As-Sajdah", "The Prostration", 30, "Humility and remembrance of return"),
        (33, "Al-Ahzab", "The Combined Forces", 73, "Steadfastness and good character"),
        (34, "Saba", "Sheba", 54, "Gratitude versus heedlessness"),
        (35, "Fatir", "Originator", 45, "Allah's power and human need"),
        (36, "Ya-Sin", "Ya-Sin", 83, "Life, death and the return"),
        (37, "As-Saffat", "Those Ranged in Ranks", 182, "Devotion and sincere sacrifice"),
        (38, "Sad", "Sad", 88, "Repentance and turning back"),
        (39, "Az-Zumar", "The Groups", 75, "No sin beyond Allah's mercy"),
        (40, "Ghafir", "The Forgiver", 85, "Forgiveness and the call to truth"),
        (41, "Fussilat", "Explained in Detail", 54, "Respond to harm with good"),
        (42, "Ash-Shura", "Consultation", 53, "Forgiveness, shura and trust"),
        (43, "Az-Zukhruf", "The Gold Adornments", 89, "Glitter versus the lasting"),
        (44, "Ad-Dukhan", "The Smoke", 59, "Heedlessness and the reckoning"),
        (45, "Al-Jathiyah", "The Kneeling", 37, "Signs, accountability, humility"),
        (46, "Al-Ahqaf", "The Sand Dunes", 35, "Kindness to parents and patience"),
        (47, "Muhammad", "Muhammad", 38, "Steadfastness and sincerity"),
        (48, "Al-Fath", "The Victory", 29, "Tranquillity (sakinah) from Allah"),
        (49, "Al-Hujurat", "The Rooms", 18, "Manners, brotherhood, the tongue"),
        (50, "Qaf", "Qaf", 45, "Allah nearer than the jugular vein"),
        (51, "Adh-Dhariyat", "The Scattering Winds", 60, "Created to worship; provision assured"),
        (52, "At-Tur", "The Mount", 49, "Certainty and the reward of the mindful"),
        (53, "An-Najm", "The Star", 62, "Sincerity and striving for the next life"),
        (54, "Al-Qamar", "The Moon", 55, "The Qur'an made easy to remember"),
        (55, "Ar-Rahman", "The Most Merciful", 78, "Which favour will you deny?"),
        (56, "Al-Waqi'ah", "The Inevitable", 96, "The reckoning and true provision"),
        (57, "Al-Hadid", "The Iron", 29, "Soft hearts and spending for Allah"),
        (58, "Al-Mujadila", "The Pleading Woman", 22, "Allah hears the one who turns to Him"),
        (59, "Al-Hashr", "The Gathering", 24, "The beautiful names and self-reckoning"),
        (60, "Al-Mumtahanah", "The Examined One", 13, "Loyalty, love and forgiveness"),
        (61, "As-Saff", "The Ranks", 14, "Matching words with deeds"),
        (62, "Al-Jumu'ah", "Friday", 11, "Remembrance over distraction"),
        (63, "Al-Munafiqun", "The Hypocrites", 11, "Sincerity versus show"),
        (64, "At-Taghabun", "Mutual Loss & Gain", 18, "Trial, trust and true profit"),
        (65, "At-Talaq", "Divorce", 12, "Mindfulness brings a way out"),
        (66, "At-Tahrim", "The Prohibition", 12, "Sincere repentance (tawbah)"),
        (67, "Al-Mulk", "The Dominion", 30, "Life as a test of best deeds"),
        (68, "Al-Qalam", "The Pen", 52, "Patience and noble character"),
        (69, "Al-Haqqah", "The Reality", 52, "The certain truth of the return"),
        (70, "Al-Ma'arij", "The Ascending Stairways", 44, "Patience and steadfast prayer"),
        (71, "Nuh", "Noah", 28, "Perseverance and seeking forgiveness"),
        (72, "Al-Jinn", "The Jinn", 28, "Calling on Allah alone"),
        (73, "Al-Muzzammil", "The Enshrouded One", 20, "Night prayer and inner strength"),
        (74, "Al-Muddaththir", "The Cloaked One", 56, "Rise, warn and purify"),
        (75, "Al-Qiyamah", "The Resurrection", 40, "Accountability of the self"),
        (76, "Al-Insan", "Man", 31, "Selfless giving for Allah's sake"),
        (77, "Al-Mursalat", "The Emissaries", 50, "The reckoning and heedfulness"),
        (78, "An-Naba", "The Great News", 40, "Reflecting on the Hereafter"),
        (79, "An-Nazi'at", "Those Who Pull Out", 46, "Restraining the self from desire"),
        (80, "Abasa", "He Frowned", 42, "Humility and valuing every soul"),
        (81, "At-Takwir", "The Overthrowing", 29, "Awakening to the final day"),
        (82, "Al-Infitar", "The Cleaving", 19, "What deceives you about your Lord?"),
        (83, "Al-Mutaffifin", "The Defrauders", 36, "Honesty in dealings"),
        (84, "Al-Inshiqaq", "The Splitting", 25, "Returning to your Lord"),
        (85, "Al-Buruj", "The Mansions of the Stars", 22, "Steadfastness under persecution"),
        (86, "At-Tariq", "The Nightcomer", 17, "Watched over and accountable"),
        (87, "Al-A'la", "The Most High", 19, "Purification and remembrance"),
        (88, "Al-Ghashiyah", "The Overwhelming", 26, "Reflection on creation and return"),
        (89, "Al-Fajr", "The Dawn", 30, "The contented soul returns to Allah"),
        (90, "Al-Balad", "The City", 20, "The steep path of doing good"),
        (91, "Ash-Shams", "The Sun", 15, "Purifying versus corrupting the soul"),
        (92, "Al-Layl", "The Night", 21, "Giving, sincerity and ease"),
        (93, "Ad-Duha", "The Morning Brightness", 11, "Your Lord has not forsaken you"),
        (94, "Ash-Sharh", "The Relief", 8, "With hardship comes ease"),
        (95, "At-Tin", "The Fig", 8, "The honour and purpose of the human"),
        (96, "Al-Alaq", "The Clot", 19, "Read — knowledge and humility"),
        (97, "Al-Qadr", "The Power", 5, "The night better than a thousand months"),
        (98, "Al-Bayyinah", "The Clear Proof", 8, "Sincerity in devotion"),
        (99, "Az-Zalzalah", "The Earthquake", 8, "No atom of good or evil is lost"),
        (100, "Al-Adiyat", "The Courser", 11, "Ingratitude of the heedless heart"),
        (101, "Al-Qari'ah", "The Calamity", 11, "The weight of deeds"),
        (102, "At-Takathur", "Competition", 8, "Distraction by piling up the worldly"),
        (103, "Al-Asr", "Time", 3, "The four things that save from loss"),
        (104, "Al-Humazah", "The Slanderer", 9, "The ruin of mockery and hoarding"),
        (105, "Al-Fil", "The Elephant", 5, "Allah's protection of the helpless"),
        (106, "Quraysh", "Quraysh", 4, "Gratitude to the Lord who provides"),
        (107, "Al-Ma'un", "Small Kindnesses", 7, "Prayer without compassion is empty"),
        (108, "Al-Kawthar", "Abundance", 3, "Abundance after loss"),
        (109, "Al-Kafirun", "The Disbelievers", 6, "Clarity and integrity of faith"),
        (110, "An-Nasr", "The Help", 3, "Victory met with humility"),
        (111, "Al-Masad", "The Palm Fibre", 5, "Wealth and pride cannot save"),
        (112, "Al-Ikhlas", "Sincerity", 4, "The pure declaration of who Allah is"),
        (113, "Al-Falaq", "The Daybreak", 5, "Refuge from harm and envy"),
        (114, "An-Nas", "Mankind", 6, "Refuge from the whisperer within"),
    ]
    surahs_all = [dict(num=n, name=nm, meaning=mn, ayahs=a, theme=t) for (n, nm, mn, a, t) in _SURAHS]
    _name = {n: nm for (n, nm, mn, a, t) in _SURAHS}
    _meaning = {n: mn for (n, nm, mn, a, t) in _SURAHS}

    def _chips(nums):
        return [{"num": n, "name": _name[n], "meaning": _meaning[n]} for n in nums]

    # ── 10 Qur'an pathways ──────────────────────────────────────────────
    pathways = [
        {"key": "finding-allah", "name": "Finding Allah Again",
         "tagline": "When He feels far, the way back is nearer than you think.", "nums": [1, 50, 112, 57, 24]},
        {"key": "healing-anxiety", "name": "Healing Anxiety and Fear",
         "tagline": "Rest for the restless heart.", "nums": [13, 20, 93, 94, 10]},
        {"key": "discipline", "name": "Discipline and Self-Control",
         "tagline": "Mastering the self, one hour at a time.", "nums": [103, 18, 73, 23, 74]},
        {"key": "rizq-tawakkul", "name": "Money, Rizq and Tawakkul",
         "tagline": "Effort in your hands, provision in His.", "nums": [65, 11, 56, 106, 34]},
        {"key": "family-character", "name": "Family and Character",
         "tagline": "Faith begins at home.", "nums": [31, 14, 4, 25, 49]},
        {"key": "tests-patience", "name": "Tests, Pain and Patience",
         "tagline": "Beautiful patience through the storm.", "nums": [12, 2, 94, 3, 21]},
        {"key": "purpose", "name": "Purpose and Leadership",
         "tagline": "A life that means something.", "nums": [67, 51, 76, 28, 38]},
        {"key": "gratitude", "name": "Gratitude and Contentment",
         "tagline": "Enough — and grateful for it.", "nums": [55, 14, 93, 108, 16]},
        {"key": "repentance", "name": "Repentance and Returning",
         "tagline": "No door closes on the one who turns back.", "nums": [39, 110, 66, 71, 7]},
        {"key": "justice", "name": "Justice and Responsibility",
         "tagline": "Standing for what is right.", "nums": [4, 5, 90, 107, 83]},
    ]
    for p in pathways:
        p["surahs"] = _chips(p["nums"])

    # ── 12 life struggles → pathways + surahs ───────────────────────────
    struggles = [
        {"id": "lost", "label": "I feel lost", "blurb": "No direction, no anchor.", "pathway": "finding-allah", "nums": [1, 93, 50]},
        {"id": "anxious", "label": "I feel anxious", "blurb": "A heart that will not settle.", "pathway": "healing-anxiety", "nums": [13, 20, 94]},
        {"id": "sin", "label": "I keep returning to sin", "blurb": "Trapped in a cycle.", "pathway": "repentance", "nums": [39, 66, 24]},
        {"id": "discipline", "label": "I struggle with discipline", "blurb": "Good intentions, no follow-through.", "pathway": "discipline", "nums": [103, 18, 73]},
        {"id": "poverty", "label": "I fear poverty", "blurb": "Afraid for my provision.", "pathway": "rizq-tawakkul", "nums": [65, 11, 106]},
        {"id": "family", "label": "I struggle with family", "blurb": "Tension at home.", "pathway": "family-character", "nums": [31, 14, 25]},
        {"id": "jealous", "label": "I feel jealous", "blurb": "Comparing, never content.", "pathway": "gratitude", "nums": [113, 14, 55]},
        {"id": "arrogant", "label": "I feel arrogant", "blurb": "Pride I cannot see past.", "pathway": "family-character", "nums": [31, 28, 17]},
        {"id": "distant", "label": "I feel distant from Allah", "blurb": "He feels far away.", "pathway": "finding-allah", "nums": [50, 57, 1]},
        {"id": "patience", "label": "I need patience", "blurb": "At the edge of giving up.", "pathway": "tests-patience", "nums": [94, 12, 2]},
        {"id": "forgiveness", "label": "I need forgiveness", "blurb": "Weighed down by guilt.", "pathway": "repentance", "nums": [39, 110, 7]},
        {"id": "purpose", "label": "I want purpose", "blurb": "Why am I even here?", "pathway": "purpose", "nums": [67, 51, 103]},
    ]
    _pathname = {p["key"]: p["name"] for p in pathways}
    for s in struggles:
        s["surahs"] = _chips(s["nums"])
        s["pathway_name"] = _pathname[s["pathway"]]

    # ── Featured surah "life map" cards (curated, fully authored) ─────────
    featured = [
        {"num": 1, "name": "Al-Fatihah", "arabic": "الفاتحة", "meaning": "The Opening", "pathway": "finding-allah",
         "theme": "The opening prayer — orienting the whole self toward Allah.",
         "repairs": "A heart that has lost its direction and forgotten Who to ask.",
         "situations": ["Starting over", "Feeling directionless", "Beginning any day or task"],
         "ayahs": [{"ref": "Al-Fatihah 1:5", "text": "You alone we worship, and You alone we ask for help."},
                   {"ref": "Al-Fatihah 1:6", "text": "Guide us to the straight path."}],
         "reflections": ["Where in my life am I asking everyone except Allah for help?",
                          "What straight path am I quietly avoiding right now?"],
         "action": "Recite Al-Fatihah once today slowly, pausing at each verse as a real conversation.",
         "dua": "O Allah, guide me to the straight path in the one decision I keep avoiding.",
         "modern": "Before opening your phone each morning, open with these words instead.",
         "mistake": "Treating the most-repeated prayer as routine words rather than a daily request."},
        {"num": 2, "name": "Al-Baqarah", "arabic": "البقرة", "meaning": "The Cow", "pathway": "tests-patience",
         "theme": "A manual for a life of faith, trial and trust.",
         "repairs": "A heart overwhelmed by responsibility and fear of what it cannot carry.",
         "situations": ["Feeling overwhelmed", "Carrying too much", "Doubting you can cope"],
         "ayahs": [{"ref": "Al-Baqarah 2:286", "text": "Allah does not burden a soul beyond what it can bear."},
                   {"ref": "Al-Baqarah 2:153", "text": "Seek help through patience and prayer."}],
         "reflections": ["What am I treating as unbearable that Allah has already measured for me?",
                          "When stressed, do I reach for patience and prayer — or for distraction?"],
         "action": "Name one burden today and meet it with two raka'at before reacting.",
         "dua": "O Allah, You measured this for me; give me what I need to carry it.",
         "modern": "The antidote to burnout: your limit is known and honoured by your Creator.",
         "mistake": "Believing you must carry everything alone and all at once."},
        {"num": 12, "name": "Yusuf", "arabic": "يوسف", "meaning": "Joseph", "pathway": "tests-patience",
         "theme": "Beautiful patience through betrayal, prison and reunion.",
         "repairs": "A heart bitter from betrayal and despairing that things will ever turn.",
         "situations": ["Betrayed by people close to you", "A long unfair season", "Tempted to give up hope"],
         "ayahs": [{"ref": "Yusuf 12:87", "text": "Do not despair of the mercy of Allah."},
                   {"ref": "Yusuf 12:90", "text": "Whoever is mindful and patient — Allah does not waste the reward of those who do good."}],
         "reflections": ["Whose harm am I still carrying that I could hand to Allah?",
                          "What if the pit I am in is part of the path up, not the end of it?"],
         "action": "Forgive one person in your heart today, without needing them to know.",
         "dua": "O Allah, replace my bitterness with beautiful patience and trust in Your plan.",
         "modern": "The long game of faith when life feels stuck or unjust.",
         "mistake": "Reading delay as denial, and pain as punishment."},
        {"num": 13, "name": "Ar-Ra'd", "arabic": "الرعد", "meaning": "The Thunder", "pathway": "healing-anxiety",
         "theme": "Hearts find their rest in the remembrance of Allah.",
         "repairs": "A restless, anxious heart that cannot settle.",
         "situations": ["Racing thoughts", "Cannot calm down", "Anxiety before sleep"],
         "ayahs": [{"ref": "Ar-Ra'd 13:28", "text": "Truly, in the remembrance of Allah hearts find rest."}],
         "reflections": ["What do I reach for first when anxious — my phone or my Lord?",
                          "What would five minutes of dhikr instead of scrolling change today?"],
         "action": "When anxiety rises today, pause and say SubhanAllah ten times, slowly.",
         "dua": "O Allah, settle my heart with Your remembrance.",
         "modern": "A nervous-system reset rooted in remembrance, not only breathing apps.",
         "mistake": "Seeking calm everywhere except the one place it is promised."},
        {"num": 20, "name": "Ta-Ha", "arabic": "طه", "meaning": "Ta-Ha", "pathway": "healing-anxiety",
         "theme": "Comfort to a fearful caller — I am with you; I hear and I see.",
         "repairs": "A heart paralysed by fear of a hard task or confrontation.",
         "situations": ["Facing something you dread", "Fear of speaking up", "Feeling too weak for the task"],
         "ayahs": [{"ref": "Ta-Ha 20:46", "text": "Do not fear; indeed I am with you both — I hear and I see."},
                   {"ref": "Ta-Ha 20:25-26", "text": "My Lord, expand for me my chest and ease for me my task."}],
         "reflections": ["What task am I avoiding out of fear that I am being asked to face?",
                          "Do I truly believe Allah is with me in it?"],
         "action": "Say Musa's du'a (20:25-26) before the hard thing you have been postponing.",
         "dua": "My Lord, expand my chest, ease my task, and untie the knot from my tongue.",
         "modern": "Courage for the hard conversation, the interview, the apology.",
         "mistake": "Facing fear as if you are alone."},
        {"num": 31, "name": "Luqman", "arabic": "لقمان", "meaning": "Luqman", "pathway": "family-character",
         "theme": "A father's timeless advice — gratitude, humility, prayer, gentleness.",
         "repairs": "A heart that is harsh, proud or neglectful with family.",
         "situations": ["Tension with parents or children", "Arrogance toward people", "Raising the next generation"],
         "ayahs": [{"ref": "Luqman 31:18", "text": "Do not turn your cheek from people in arrogance, nor walk in insolence."},
                   {"ref": "Luqman 31:19", "text": "Be moderate in your pace and lower your voice."}],
         "reflections": ["Who in my family receives my worst manners?",
                          "What advice would I want to leave my children — and do I live it?"],
         "action": "Speak to one family member today with deliberate gentleness.",
         "dua": "O Allah, make me gentle, humble and grateful with those closest to me.",
         "modern": "Character begins at home, not online.",
         "mistake": "Saving our best manners for strangers and our worst for family."},
        {"num": 39, "name": "Az-Zumar", "arabic": "الزمر", "meaning": "The Groups", "pathway": "repentance",
         "theme": "No sin is beyond the mercy of Allah for the one who turns back.",
         "repairs": "A heart crushed by guilt and convinced it has gone too far.",
         "situations": ["Shame over past sin", "Feeling unforgivable", "Returning after distance"],
         "ayahs": [{"ref": "Az-Zumar 39:53", "text": "O My servants who have wronged themselves, do not despair of the mercy of Allah. Indeed, Allah forgives all sins."}],
         "reflections": ["What am I treating as too much for Allah's mercy?",
                          "What is one step back toward Him I can take today?"],
         "action": "Make sincere tawbah for one specific thing, then do one good deed right after.",
         "dua": "O Allah, I have wronged myself; forgive me, for none forgives sins but You.",
         "modern": "Breaking the shame-spiral that keeps you away from prayer.",
         "mistake": "Letting guilt push you further from Allah instead of toward Him."},
        {"num": 50, "name": "Qaf", "arabic": "ق", "meaning": "Qaf", "pathway": "finding-allah",
         "theme": "Allah is nearer to you than your jugular vein.",
         "repairs": "A heart that feels alone and unseen.",
         "situations": ["Feeling unseen", "Loneliness", "Feeling distant from Allah"],
         "ayahs": [{"ref": "Qaf 50:16", "text": "We are closer to him than his jugular vein."}],
         "reflections": ["If Allah is this near, what would I say to Him right now?",
                          "Where have I been seeking closeness that only He can give?"],
         "action": "Have one whispered, honest conversation with Allah today — no script.",
         "dua": "O Allah, You are nearer to me than I know; let my heart feel it.",
         "modern": "Real intimacy with the Divine in an age of disconnection.",
         "mistake": "Searching for closeness in people while ignoring the One already near."},
        {"num": 55, "name": "Ar-Rahman", "arabic": "الرحمن", "meaning": "The Most Merciful", "pathway": "gratitude",
         "theme": "Which of the favours of your Lord will you deny?",
         "repairs": "A heart numb to blessing and quick to complain.",
         "situations": ["Taking blessings for granted", "A complaining habit", "Spiritual numbness"],
         "ayahs": [{"ref": "Ar-Rahman 55:13", "text": "So which of the favours of your Lord will you deny?"}],
         "reflections": ["What favour am I denying by never thanking Him for it?",
                          "When did I last feel awe at something completely ordinary?"],
         "action": "Step outside and name one sign of Allah's mercy aloud in thanks.",
         "dua": "O Most Merciful, open my eyes to Your countless favours.",
         "modern": "Re-enchanting a distracted, ungrateful attention span.",
         "mistake": "Scrolling past a thousand blessings to fixate on one lack."},
        {"num": 65, "name": "At-Talaq", "arabic": "الطلاق", "meaning": "Divorce", "pathway": "rizq-tawakkul",
         "theme": "Whoever is mindful of Allah, He makes a way out and provides unexpectedly.",
         "repairs": "A heart gripped by fear of poverty and the future.",
         "situations": ["Money fear", "Job loss or instability", "Anxiety about provision"],
         "ayahs": [{"ref": "At-Talaq 65:2-3", "text": "Whoever is mindful of Allah — He will make a way out for him, and provide from where he does not expect."}],
         "reflections": ["What decision am I making from fear of provision rather than trust?",
                          "Where might Allah be opening a door I am not looking at?"],
         "action": "Make one honest, halal effort today — then consciously hand the outcome to Allah.",
         "dua": "O Allah, You are Ar-Razzaq; I trust You with my provision.",
         "modern": "Tawakkul against financial anxiety — effort plus trust, not worry.",
         "mistake": "Confusing worry with responsibility."},
        {"num": 67, "name": "Al-Mulk", "arabic": "الملك", "meaning": "The Dominion", "pathway": "purpose",
         "theme": "Life and death created as a test of who acts best.",
         "repairs": "A heart that has forgotten why it is here.",
         "situations": ["Feeling life is pointless", "Drifting without aim", "Forgetting the bigger picture"],
         "ayahs": [{"ref": "Al-Mulk 67:2", "text": "He created death and life to test which of you is best in deed."}],
         "reflections": ["If life is a test of deeds, what is today's question?",
                          "What would best in deed look like in my very next hour?"],
         "action": "Choose one action today done purely for Allah, and do it excellently.",
         "dua": "O Owner of all dominion, let my life be spent in what pleases You.",
         "modern": "Purpose beyond productivity — quality of deeds over quantity of output.",
         "mistake": "Measuring a life by output instead of by sincerity and excellence."},
        {"num": 93, "name": "Ad-Duha", "arabic": "الضحى", "meaning": "The Morning Brightness", "pathway": "healing-anxiety",
         "theme": "Your Lord has not forsaken you — light after darkness.",
         "repairs": "A heart that feels abandoned in a dark season.",
         "situations": ["Feeling abandoned", "A spiritual dry spell", "After a loss"],
         "ayahs": [{"ref": "Ad-Duha 93:3", "text": "Your Lord has not forsaken you, nor does He hate you."},
                   {"ref": "Ad-Duha 93:5", "text": "And your Lord is going to give you, and you will be satisfied."}],
         "reflections": ["What silence have I misread as abandonment?",
                          "What past morning followed a night I thought would never end?"],
         "action": "List one way Allah cared for you in the past as proof for today.",
         "dua": "O Allah, You have never forsaken me; carry me through this night to its morning.",
         "modern": "Hope in depression, grief and burnout — without denial.",
         "mistake": "Reading a hard season as a verdict on Allah's love."},
        {"num": 94, "name": "Ash-Sharh", "arabic": "الشرح", "meaning": "The Relief", "pathway": "tests-patience",
         "theme": "With hardship comes ease — said twice.",
         "repairs": "A heart drowning in present difficulty.",
         "situations": ["In the middle of hardship", "Overwhelmed", "Cannot see a way through"],
         "ayahs": [{"ref": "Ash-Sharh 94:5-6", "text": "For indeed, with hardship comes ease. Indeed, with hardship comes ease."}],
         "reflections": ["What ease might already be hidden inside this hardship?",
                          "What is one next small step instead of solving everything at once?"],
         "action": "Do the one next small task; then return to Allah in rest.",
         "dua": "O Allah, You promised ease with hardship; let me trust it and take one step.",
         "modern": "Resilience that holds two truths: this is hard, and ease is coming.",
         "mistake": "Demanding the whole solution before taking the next step."},
        {"num": 103, "name": "Al-Asr", "arabic": "العصر", "meaning": "Time", "pathway": "discipline",
         "theme": "All humanity is in loss — except four things.",
         "repairs": "A heart that wastes time and drifts without accountability.",
         "situations": ["Wasting time", "Lack of discipline", "Procrastination"],
         "ayahs": [{"ref": "Al-Asr 103:2-3", "text": "Indeed, mankind is in loss — except those who believe, do good, and counsel one another to truth and patience."}],
         "reflections": ["Where is my time leaking today?",
                          "Who counsels me to truth — and whom do I counsel?"],
         "action": "Audit one hour today and redirect it to faith, good action, or someone you love.",
         "dua": "O Allah, bless my time and save me from heedless loss.",
         "modern": "A three-verse productivity philosophy older than every app.",
         "mistake": "Spending the one resource you can never refund — time."},
        {"num": 112, "name": "Al-Ikhlas", "arabic": "الإخلاص", "meaning": "Sincerity", "pathway": "finding-allah",
         "theme": "The pure declaration of who Allah is.",
         "repairs": "A heart cluttered with rivals to Allah — approval, money, self.",
         "situations": ["Living for others' approval", "Divided loyalties", "Tangled intentions"],
         "ayahs": [{"ref": "Al-Ikhlas 112:1-2", "text": "Say: He is Allah, One. Allah, the Eternal Refuge."}],
         "reflections": ["Whose approval am I really worshipping?",
                          "What would change if I did the next thing for Allah alone?"],
         "action": "Do one act today known only to you and Allah.",
         "dua": "O Allah, make my heart sincere and undivided toward You.",
         "modern": "Freedom from the exhausting performance of living for an audience.",
         "mistake": "Letting many small idols quietly share the throne of the heart."},
    ]
    for f in featured:
        f["pathway_name"] = _pathname[f["pathway"]]
    featured_nums = sorted(f["num"] for f in featured)

    # ── Qur'an Repair Engine — symptom → one ayah, one repair ────────────
    one_ayah = [
        {"symptom": "I can't stop worrying", "ref": "Ar-Ra'd 13:28", "text": "In the remembrance of Allah, hearts find rest.",
         "wound": "A restless, anxious heart.",
         "reflection": "What do I reach for first when anxious?",
         "action": "Pause and make quiet dhikr for two minutes.",
         "dua": "O Allah, settle my heart with Your remembrance."},
        {"symptom": "I feel hopeless", "ref": "Ash-Sharh 94:5-6", "text": "With hardship comes ease.",
         "wound": "Despair in the middle of difficulty.",
         "reflection": "What small ease is hidden in today's hardship?",
         "action": "Take the one next step, then rest in Allah.",
         "dua": "O Allah, let me trust the ease You promised."},
        {"symptom": "I feel guilty and ashamed", "ref": "Az-Zumar 39:53", "text": "Do not despair of the mercy of Allah; He forgives all sins.",
         "wound": "Shame that keeps you from returning.",
         "reflection": "What am I treating as unforgivable?",
         "action": "Make tawbah for one thing, then do one good deed.",
         "dua": "O Allah, forgive me; none forgives sins but You."},
        {"symptom": "I'm scared about money", "ref": "At-Talaq 65:3", "text": "Whoever relies on Allah — He is sufficient for him.",
         "wound": "Fear of provision and the future.",
         "reflection": "What am I deciding out of fear, not trust?",
         "action": "Make one halal effort, then hand over the outcome.",
         "dua": "O Allah, You are enough for me."},
        {"symptom": "I feel overwhelmed", "ref": "Al-Baqarah 2:286", "text": "Allah does not burden a soul beyond its capacity.",
         "wound": "Feeling overwhelmed and incapable.",
         "reflection": "What unbearable thing has Allah already measured for me?",
         "action": "Name one burden; meet it with two raka'at first.",
         "dua": "O Allah, give me what I need to carry this."},
        {"symptom": "I feel empty / no purpose", "ref": "Adh-Dhariyat 51:56", "text": "I created jinn and mankind only to worship Me.",
         "wound": "A life that feels purposeless.",
         "reflection": "What would turning this hour into worship look like?",
         "action": "Do one ordinary task today purely for Allah.",
         "dua": "O Allah, let my life be spent in what pleases You."},
        {"symptom": "I feel jealous / ungrateful", "ref": "Ibrahim 14:7", "text": "If you are grateful, I will surely increase you.",
         "wound": "Discontent and comparison.",
         "reflection": "What blessing have I stopped noticing?",
         "action": "Write three specific blessings tonight.",
         "dua": "O Allah, make me grateful and increase me."},
        {"symptom": "I feel alone", "ref": "Qaf 50:16", "text": "We are closer to him than his jugular vein.",
         "wound": "Feeling alone and unseen.",
         "reflection": "If He is this near, what would I say to Him now?",
         "action": "Have one honest, unscripted talk with Allah today.",
         "dua": "O Allah, let my heart feel how near You are."},
    ]

    # ── Life Crisis Mode — a calm, immediate anchor (NOT emergency care) ──
    crisis = {
        "ayahs": [
            {"ref": "Al-Baqarah 2:286", "text": "Allah does not burden a soul beyond what it can bear."},
            {"ref": "Ash-Sharh 94:6", "text": "Indeed, with hardship comes ease."},
        ],
        "dua": "O Allah, I am weak and You are strong; carry me through this moment.",
        "steps": [
            "Breathe slowly — three long breaths.",
            "Say: Hasbunallahu wa ni'mal-wakeel (Allah is sufficient for us).",
            "Do the next one small thing — only the next one.",
            "Reach out to one trusted person today.",
        ],
    }

    # ── Nafs Patterns — a classical lens from the scholars of tazkiyah ───
    nafs = [
        {"name": "An-Nafs al-Ammarah", "arabic": "النفس الأمّارة", "english": "The self that urges toward wrong",
         "ref": "Yusuf 12:53",
         "desc": "The lower self that pulls toward ease, desire and harm — recognised, not hated.",
         "shift": "Catch one urge today and pause before it; replace it with a small good act."},
        {"name": "An-Nafs al-Lawwamah", "arabic": "النفس اللوّامة", "english": "The self-reproaching soul",
         "ref": "Al-Qiyamah 75:2",
         "desc": "The awakened conscience that blames itself after slipping — a sign of life, not failure.",
         "shift": "Turn self-criticism into tawbah: one honest 'I'm sorry', then one step forward."},
        {"name": "An-Nafs al-Mutma'innah", "arabic": "النفس المطمئنة", "english": "The soul at peace",
         "ref": "Al-Fajr 89:27-28",
         "desc": "The tranquil soul that has found rest in its Lord — the direction of the whole journey.",
         "shift": "Protect one daily anchor (prayer, dhikr, an ayah) that keeps the heart steady."},
    ]

    # ── 99 Names pathways — turning to Allah by His names (curated) ───────
    names99 = [
        {"name": "Ar-Razzaq", "arabic": "الرزّاق", "meaning": "The Provider", "for": "Fear of poverty", "call": "Trust Him with your provision; make effort, then rest."},
        {"name": "Al-Ghaffar", "arabic": "الغفّار", "meaning": "The Ever-Forgiving", "for": "Guilt & shame", "call": "Return again, however many times; His door does not close."},
        {"name": "As-Salam", "arabic": "السلام", "meaning": "The Source of Peace", "for": "Anxiety", "call": "Ask the Source of peace for the peace nothing else can give."},
        {"name": "Al-Wakeel", "arabic": "الوكيل", "meaning": "The Trustee", "for": "Worry about outcomes", "call": "Hand the result to the One who manages all affairs."},
        {"name": "Al-Hadi", "arabic": "الهادي", "meaning": "The Guide", "for": "Feeling lost", "call": "Ask to be guided to the next right step, not the whole map."},
        {"name": "As-Sabur", "arabic": "الصبور", "meaning": "The Patient", "for": "Needing patience", "call": "Borrow patience from the Most Patient in a long, unfair season."},
        {"name": "Al-Wadud", "arabic": "الودود", "meaning": "The Most Loving", "for": "Feeling unloved", "call": "Sit with the truth that you are loved by the Most Loving."},
        {"name": "Al-Fattah", "arabic": "الفتّاح", "meaning": "The Opener", "for": "A closed door", "call": "Ask the Opener to open what is good and close what harms."},
        {"name": "Ash-Shafi", "arabic": "الشافي", "meaning": "The Healer", "for": "Pain & illness", "call": "Seek healing of body and heart from the only true Healer."},
        {"name": "Al-Halim", "arabic": "الحليم", "meaning": "The Forbearing", "for": "Anger", "call": "Learn gentleness and restraint from the Most Forbearing."},
    ]

    # ── 7-Day Repair Plans — structured weekly journeys ──────────────────
    plans = [
        {"key": "anxiety", "title": "7 Days to Steady the Anxious Heart", "pathway": "Healing Anxiety and Fear",
         "days": [
            "Read Ar-Ra'd 13:28; name what you reach for when anxious.",
            "Replace one scroll session with two minutes of dhikr.",
            "Read Ad-Duha; list one way Allah has carried you before.",
            "Pray two raka'at before reacting to a worry.",
            "Read Ash-Sharh; do only the next small step of a hard task.",
            "Make du'a aloud, honestly, for the thing you fear most.",
            "Reflect: what shifted? Write one sentence of gratitude.",
         ]},
        {"key": "repentance", "title": "7 Days of Returning", "pathway": "Repentance and Returning",
         "days": [
            "Read Az-Zumar 39:53; name one thing without despair.",
            "Make sincere tawbah for it; follow it with one good deed.",
            "Read Surah Nuh's theme of seeking forgiveness; say istighfar 100x.",
            "Repair one relationship harmed by the sin, if you can.",
            "Guard the trigger; remove one thing that pulls you back.",
            "Pray at the night's end and ask for a clean slate.",
            "Reflect: thank Allah for the door He kept open.",
         ]},
        {"key": "gratitude", "title": "7 Days to Trade Envy for Gratitude", "pathway": "Gratitude and Contentment",
         "days": [
            "Read Ibrahim 14:7; notice one blessing gone unnoticed.",
            "Mute one source of comparison for the week.",
            "Read Ar-Rahman; name a favour aloud in thanks.",
            "Give something small away — sadaqah quietly.",
            "Praise one person sincerely instead of envying them.",
            "Write three specific blessings before sleep.",
            "Reflect: is it lack, or comparison? Make du'a for contentment.",
         ]},
    ]

    # ── Scholar Review Status — transparency table ───────────────────────
    review_status = [
        {"item": "Surah names, order & ayah counts", "status": "Standard reference (Hafs)", "state": "ok"},
        {"item": "Featured surah reflections", "status": "Drafted — scholar review pending", "state": "pending"},
        {"item": "Ayah meanings shown on cards", "status": "Paraphrase — citations to be added", "state": "pending"},
        {"item": "Nafs & 99 Names framing", "status": "Classical concepts — review pending", "state": "pending"},
        {"item": "Reflection & repair prompts", "status": "Inspired by themes — not tafsir", "state": "ok"},
        {"item": "Legal rulings (fiqh)", "status": "Not provided — consult a scholar", "state": "na"},
    ]

    # ── Daily Tazkiyah tracker steps ─────────────────────────────────────
    tracker = [
        {"key": "read", "label": "I read today", "hint": "One ayah is enough to begin."},
        {"key": "reflect", "label": "I reflected today", "hint": "Sit with one question honestly."},
        {"key": "act", "label": "I acted on one ayah", "hint": "Turn a verse into a small deed."},
        {"key": "dua", "label": "I made dua", "hint": "Ask for the one thing you need most."},
        {"key": "journal", "label": "I wrote one journal note", "hint": "A sentence to your future self."},
    ]

    # ── Content Trust layer (static / context-based; no DB model yet) ─────
    # Placeholder source/review status for the whole prototype. These describe
    # the CURRENT state of the content honestly — it is a preview, pending
    # sources, tafsir references, scholar review, and wellbeing review where
    # sensitive. Nothing here is presented as scholar-approved.
    trust = {
        "content_status": "preview_prototype",
        "source_status": "source_needed",
        "translation_status": "translation_pending",
        "tafsir_status": "tafsir_pending",
        "scholar_review_status": "scholar_review_pending",
        "wellbeing_review_required": True,
        # The six steps of the review workflow shown as a calm visual.
        "workflow": [
            {"key": "draft", "label": "Draft Reflection", "note": "Authored; inspired by Qur'anic themes."},
            {"key": "source", "label": "Source Added", "note": "Verified translation source attached."},
            {"key": "tafsir", "label": "Tafsir Referenced", "note": "Tafsir references cited."},
            {"key": "scholar", "label": "Scholar Review", "note": "Reviewed by a qualified scholar."},
            {"key": "wellbeing", "label": "Wellbeing Review", "note": "For sensitive topics, a safeguarding check."},
            {"key": "publish", "label": "Publishable", "note": "Cleared for public educational use."},
        ],
        # Pre-launch checklist (display only).
        "launch_checklist": [
            "Verified Qur'an translation source selected",
            "Tafsir references added",
            "Scholar review completed",
            "Sensitive topics reviewed by wellbeing/safeguarding advisor",
            "Crisis guidance checked for safety",
            "Journal/tracker privacy reviewed",
            "Content versioning added",
            "Clear source citations visible to users",
        ],
        # Badge catalogue used across the page (label + tone).
        "badges": [
            {"key": "preview",     "label": "Preview Prototype",       "tone": "amber"},
            {"key": "draft",       "label": "Reflection Draft",        "tone": "amber"},
            {"key": "source",      "label": "Source Needed",           "tone": "amber"},
            {"key": "translation", "label": "Translation Pending",     "tone": "amber"},
            {"key": "tafsir",      "label": "Tafsir Pending",          "tone": "amber"},
            {"key": "scholar",     "label": "Scholar Review Pending",  "tone": "amber"},
            {"key": "wellbeing",   "label": "Wellbeing Review Required", "tone": "rose"},
        ],
    }

    ctx = {
        "surahs_all": surahs_all,
        "pathways": pathways,
        "struggles": struggles,
        "featured": featured,
        "featured_nums": featured_nums,
        "one_ayah": one_ayah,
        "crisis": crisis,
        "nafs": nafs,
        "names99": names99,
        "plans": plans,
        "review_status": review_status,
        "tracker": tracker,
        "trust": trust,
    }
    return render(request, "tazkiyah.html", ctx)


def khalifa_stewardship_tours(request):
    """
    /khalifa-tours/ — Khalifa Stewardship Tours.

    Premium institutional landing page for EcoIQ's purpose-driven travel
    product: cinematic Kazakhstan expeditions where travellers become stewards
    of the land — clean heating transition, home efficiency, mountain/lake
    restoration, community greenhouses and field monitoring — all measured
    through EcoIQ. Pure presentation (no AI/API calls, no secrets); safe to
    serve publicly. All data below is illustrative/indicative.
    """
    # ── Kazakhstan experience cards ──────────────────────────────────────
    # IMAGES: each card's `img` is a placeholder (Unsplash CDN). To use your
    # own licensed photography, drop files into  static/khalifa-tours/  and
    # swap the value, e.g.:
    #     'img': static('khalifa-tours/tian-shan.jpg')
    # (import: `from django.templatetags.static import static`). The template
    # renders these as real <img> tags with alt text, lazy loading, and a
    # graceful coloured fallback if the image fails to load.
    experiences = [
        {'tag': 'Expedition', 'title': 'Tian Shan Expeditions',
         'body': 'Trek the snow-fed ridgelines and glacial valleys of the Tian Shan, '
                 'one of the great unspoiled mountain systems of Central Asia.',
         'alt': 'Snow-capped Tian Shan mountain peaks above the clouds at sunrise',
         'img': 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?auto=format&fit=crop&w=1200&q=70'},
        {'tag': 'Alpine', 'title': 'Big Almaty Lake',
         'body': 'A turquoise alpine reservoir cradled at 2,500 m — and the field site '
                 'for water and ecosystem restoration work.',
         'alt': 'A turquoise alpine lake surrounded by forested mountain slopes',
         'img': 'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=1200&q=70'},
        {'tag': 'Protected', 'title': 'National Parks & Reserves',
         'body': 'Ile-Alatau and the protected steppe-to-summit corridors that shelter '
                 'rare wildlife and fragile high-altitude habitats.',
         'alt': 'A hiker standing on a ridge overlooking protected mountain wilderness',
         'img': 'https://images.unsplash.com/photo-1454942901704-3c44c11b2ad1?auto=format&fit=crop&w=1200&q=70'},
        {'tag': 'Hospitality', 'title': 'Kazakh Hospitality',
         'body': 'Traditional communities whose welcome — dastarkhan, music and shared '
                 'tea — is a heritage as living as the landscape.',
         'alt': 'A snow leopard, emblem of Kazakhstan’s mountain wildlife and heritage',
         'img': 'https://images.unsplash.com/photo-1517825738774-7de9363ef735?auto=format&fit=crop&w=1200&q=70'},
        {'tag': 'Heritage', 'title': 'Horses, Food & Culture',
         'body': 'Nomadic horsemanship, bread baked in mountain homes, and a culture '
                 'shaped by the balance between people and land.',
         'alt': 'A white horse in a mountain valley, evoking Kazakh nomadic heritage',
         'img': 'https://images.unsplash.com/photo-1553284965-83fd3e82fa5a?auto=format&fit=crop&w=1200&q=70'},
        {'tag': 'Gateway', 'title': 'Almaty — The Gateway City',
         'body': 'A modern city at the foot of the mountains: your arrival point, '
                 'cultural briefing and the bridge between worlds.',
         'alt': 'A modern city skyline at dusk, the gateway to the mountains',
         'img': 'https://images.unsplash.com/photo-1519501025264-65ba15a82390?auto=format&fit=crop&w=1200&q=70'},
    ]

    projects = [
        {'code': 'A', 'title': 'Clean Heating Transition',
         'body': 'Support the replacement of polluting coal heating with cleaner '
                 'alternatives — electric boilers, heat pumps, insulation upgrades and '
                 'smart energy controls.'},
        {'code': 'B', 'title': 'Home Energy Efficiency',
         'body': 'Help with simple home assessments, insulation support, heat-loss checks '
                 'and comfort improvements for local families.'},
        {'code': 'C', 'title': 'Mountain & Lake Restoration',
         'body': 'Remove waste from trails, rivers, mountain areas and lakes while learning '
                 'how these high-altitude ecosystems work.'},
        {'code': 'D', 'title': 'Community Greenhouses',
         'body': 'Contribute to greenhouse construction and food-resilience projects that '
                 'help families and communities grow fresh produce.'},
        {'code': 'E', 'title': 'Environmental Monitoring',
         'body': 'Collect simple field observations, photographs and project data that feed '
                 'directly into EcoIQ impact dashboards.'},
    ]

    # ── Amanah Impact Ledger ─────────────────────────────────────────────
    # ILLUSTRATIVE / EXAMPLE figures only — NOT verified results. Animated
    # count-up on the page. Each row carries a field code so the ledger reads
    # like an EcoIQ measurement product rather than a generic metrics grid.
    # Future expeditions are designed to connect this ledger to verified EcoIQ
    # records; until then every value is a modelled projection.
    ledger = [
        {'code': 'AML·01', 'label': 'Homes assessed',                       'value': 640,  'suffix': '',     'unit': 'field surveys',           'conf': 82, 'method': 'survey count'},
        {'code': 'AML·02', 'label': 'Homes upgraded',                       'value': 480,  'suffix': '',     'unit': 'retrofits delivered',     'conf': 76, 'method': 'install records'},
        {'code': 'AML·03', 'label': 'Coal systems targeted for replacement', 'value': 312, 'suffix': '',     'unit': 'replacement pipeline',    'conf': 64, 'method': 'pipeline est.'},
        {'code': 'AML·04', 'label': 'Estimated emissions avoided',          'value': 1600, 'suffix': ' t',   'unit': 'CO₂e / yr (modelled)',    'conf': 58, 'method': 'modelled'},
        {'code': 'AML·05', 'label': 'Waste removed',                        'value': 27,   'suffix': ' t',   'unit': 'trails, rivers & lakes',  'conf': 80, 'method': 'weighed logs'},
        {'code': 'AML·06', 'label': 'Volunteer hours',                      'value': 7400, 'suffix': '',     'unit': 'stewardship logged',      'conf': 88, 'method': 'time logs'},
        {'code': 'AML·07', 'label': 'Families reached',                     'value': 2100, 'suffix': '',     'unit': 'household members',       'conf': 70, 'method': 'household avg'},
        {'code': 'AML·08', 'label': 'Restoration actions',                  'value': 58,   'suffix': '',     'unit': 'documented interventions', 'conf': 74, 'method': 'field reports'},
        {'code': 'AML·09', 'label': 'Community benefit score',              'value': 87,   'suffix': '/100', 'unit': 'composite index (model)', 'conf': 62, 'method': 'composite'},
    ]

    # ── One Journey, Five Legacies ───────────────────────────────────────
    # The ownable Khalifa Tours system: one expedition → five lasting legacies.
    # `icon` holds trusted, hand-authored inline SVG (rendered with |safe).
    legacies = [
        {'key': 'comfort', 'name': 'Comfort Legacy', 'line': 'Warmer homes, better winter resilience',
         'body': 'Homes that hold their heat — a measurable rise in winter comfort for the families who live there.',
         'icon': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 11l9-7 9 7"/><path d="M5 10v9h14v-9"/><path d="M12 13.5c1.6 1 1.6 2.6 0 3.6"/></svg>'},
        {'key': 'health', 'name': 'Health Legacy', 'line': 'Reduced smoke exposure, cleaner indoor air',
         'body': 'Less coal smoke indoors and out — lowering exposure for children, elders and everyone between.',
         'icon': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4 9h9a3 3 0 1 0-3-3"/><path d="M4 13h13a3 3 0 1 1-3 3"/><path d="M4 17h7"/></svg>'},
        {'key': 'community', 'name': 'Community Legacy', 'line': 'Practical support and local trust',
         'body': 'Work done with communities, not for them — building durable trust and local capability.',
         'icon': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="8" r="3"/><path d="M3.5 20a5.5 5.5 0 0 1 11 0"/><path d="M16 6a3 3 0 0 1 0 6"/><path d="M18.5 20a5.5 5.5 0 0 0-3-4.6"/></svg>'},
        {'key': 'land', 'name': 'Land Legacy', 'line': 'Cleaner trails, lakes and mountain landscapes',
         'body': 'Restored shorelines and trails — fragile high-altitude ecosystems left measurably better.',
         'icon': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 19l5.5-9 3.5 5.5L15 11l6 8z"/><path d="M3 19h18"/></svg>'},
        {'key': 'data', 'name': 'Data Legacy', 'line': 'Transparent EcoIQ measurement and reporting',
         'body': 'Every action recorded and reported — the proof layer that turns effort into evidence.',
         'icon': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19V5"/><path d="M4 19h16"/><path d="M8 16v-3"/><path d="M12 16V8"/><path d="M16 16v-6"/></svg>'},
    ]

    # ── Expedition scroll path (Arrival → Leave a Legacy) ────────────────
    # Vertical, scroll-drawn route. `icon` is trusted hand-authored inline SVG.
    journey = [
        {'step': 'Arrival', 'head': 'Enter as a guest of the land',
         'line': 'You arrive as a caretaker, not a consumer — briefed on the route, the people and the trust you are joining.',
         'icon': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 21s-6-5.2-6-10a6 6 0 1 1 12 0c0 4.8-6 10-6 10z"/><circle cx="12" cy="11" r="2.2"/></svg>'},
        {'step': 'Witness', 'head': 'See it honestly',
         'line': 'Meet the families, the coal smoke and the cold — the real conditions behind the statistics.',
         'icon': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>'},
        {'step': 'Serve', 'head': 'Lend your hands',
         'line': 'Join safe, supervised stewardship work alongside qualified local professionals.',
         'icon': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M7.5 11V6.5a1.5 1.5 0 0 1 3 0V11"/><path d="M10.5 11V5.2a1.5 1.5 0 0 1 3 0V11"/><path d="M13.5 11V6.6a1.5 1.5 0 0 1 3 0V13c0 4-2.2 7-6 7-2 0-3.2-1-4.2-2.8l-1.6-2.6a1.6 1.6 0 0 1 2.7-1.7L7.5 14"/></svg>'},
        {'step': 'Restore', 'head': 'Leave it better',
         'line': 'Clear waste, support retrofits and help repair the land you came to understand.',
         'icon': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 12a8 8 0 1 1-2.3-5.6"/><path d="M20 4v4h-4"/></svg>'},
        {'step': 'Measure', 'head': 'Count what matters',
         'line': 'Field data and observations are designed to feed the EcoIQ ledger — outcomes, not anecdotes.',
         'icon': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4 18a8 8 0 0 1 16 0"/><path d="M12 18l4.5-5.5"/><circle cx="12" cy="18" r="1.3"/></svg>'},
        {'step': 'Leave a Legacy', 'head': 'Benefit that remains',
         'line': 'Long after departure, the warmth, health and trust are designed to keep compounding.',
         'icon': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l7 3v6c0 4.2-3 7.2-7 8-4-0.8-7-3.8-7-8V6z"/><path d="M9 12l2 2 4-4.5"/></svg>'},
    ]

    # ── 3D Stewardship field map — illustrative impact zones ─────────────
    # Stylised (not GIS). `sx`/`sy` are SVG coordinates in a 1000×560 viewBox,
    # listed in route order so a polyline can connect them.
    map_points = [
        {'name': 'Almaty Gateway',           'coord': '43.24° N · 76.95° E', 'role': 'Arrival & briefing',   'sx': 300, 'sy': 432, 'lx': 300, 'ly': 470, 'anchor': 'middle'},
        {'name': 'Community Retrofit Zone',   'coord': '43.20° N · 76.84° E', 'role': 'Retrofit site',        'sx': 232, 'sy': 300, 'lx': 232, 'ly': 268, 'anchor': 'middle'},
        {'name': 'Tian Shan Foothills',       'coord': '43.13° N · 77.05° E', 'role': 'Field-learning route', 'sx': 520, 'sy': 332, 'lx': 520, 'ly': 372, 'anchor': 'middle'},
        {'name': 'Big Almaty Lake',           'coord': '43.05° N · 76.98° E', 'role': 'Restoration zone',     'sx': 662, 'sy': 214, 'lx': 662, 'ly': 182, 'anchor': 'middle'},
        {'name': 'Mountain Restoration Zone', 'coord': '43.02° N · 77.10° E', 'role': 'Restoration zone',     'sx': 812, 'sy': 120, 'lx': 812, 'ly': 90,  'anchor': 'middle'},
    ]

    # ── Before / After / Ripple ──────────────────────────────────────────
    ripple = [
        {'phase': 'Before', 'tone': 'cold', 'head': 'The winter burden',
         'items': ['Coal smoke', 'Heat loss', 'Cold, costly homes']},
        {'phase': 'After', 'tone': 'warm', 'head': 'A cleaner pathway',
         'items': ['Cleaner heating pathway', 'Warmer home', 'Improved comfort']},
        {'phase': 'Ripple', 'tone': 'benefit', 'head': 'The lasting effect',
         'items': ['Family benefit', 'Community confidence', 'Measurable environmental value']},
    ]

    # ── Kazakhstan expedition layer — illustrative field sites/coordinates ─
    field_sites = [
        {'coord': '43.2384° N · 76.9450° E', 'name': 'Almaty Gateway'},
        {'coord': '43.1330° N · 77.0470° E', 'name': 'Tian Shan Foothills'},
        {'coord': '43.0530° N · 76.9850° E', 'name': 'Big Almaty Lake'},
        {'coord': '43.2010° N · 76.8420° E', 'name': 'Community Retrofit Zone'},
    ]

    itinerary = [
        {'day': '01', 'title': 'Arrival in Almaty',
         'body': 'Airport arrival, welcome dinner, cultural briefing and an introduction to '
                 'EcoIQ and the Khalifa stewardship principles.'},
        {'day': '02', 'title': 'Landscape & Climate Briefing',
         'body': 'Mountain visit, environmental context, and an introduction to air pollution '
                 'and the clean-heating transition.'},
        {'day': '03', 'title': 'Community Home Assessment',
         'body': 'Visit selected homes with local partners and learn how heat loss, insulation '
                 'and heating systems shape daily life for families.'},
        {'day': '04', 'title': 'Clean Heating or Insulation Support',
         'body': 'Supervised, safe project activities — insulation, preparation, documentation '
                 'or installation support alongside qualified professionals.'},
        {'day': '05', 'title': 'Mountain or Lake Restoration',
         'body': 'Trail clean-up, lake restoration, environmental monitoring, photography and '
                 'field data collection.'},
        {'day': '06', 'title': 'Greenhouse or Community Project',
         'body': 'Support greenhouse construction, planting, food resilience or another '
                 'community sustainability activity.'},
        {'day': '07', 'title': 'Impact Review & Closing Gathering',
         'body': 'EcoIQ dashboard review, certificates, a local family gathering, reflection '
                 'and departure.'},
    ]

    audiences = [
        'Purpose-driven travellers', 'Muslim families and communities',
        'Students and universities', 'Corporate teams',
        'Investors and sponsors', 'Environmental organizations',
        'Schools and youth groups', 'Professionals seeking meaningful travel',
    ]

    # "Why Partners Care" — the institutional value proposition per stakeholder.
    # Positions Khalifa Tours as a partnership platform, not only a tour product.
    partner_value = [
        {'tag': '01', 'label': 'For Sponsors',
         'body': 'Sponsor a visible, measurable environmental project connected to real '
                 'communities and transparent EcoIQ impact tracking.',
         'meta': 'Branded impact · verified reporting'},
        {'tag': '02', 'label': 'For Universities',
         'body': 'Offer students a field-learning expedition combining climate, culture, '
                 'community service, and data-based impact measurement.',
         'meta': 'Accredited field learning · research data'},
        {'tag': '03', 'label': 'For Corporates',
         'body': 'Create a team stewardship experience connected to ESG, employee engagement, '
                 'and measurable local benefit.',
         'meta': 'ESG-aligned · team engagement'},
        {'tag': '04', 'label': 'For Local Communities',
         'body': 'Bring attention, practical support, and long-term visibility to clean heating, '
                 'energy efficiency, restoration, and food resilience needs.',
         'meta': 'Local priority · lasting benefit'},
    ]

    partners = [
        'Local communities', 'Akimats & municipalities', 'Universities',
        'Heating manufacturers', 'Sustainability sponsors',
        'Islamic charities & foundations', 'Corporate ESG teams',
        'Environmental NGOs', 'Tourism operators',
    ]

    # Forward-looking programme commitments (how Khalifa Tours is designed to
    # operate) — phrased to avoid implying any expedition has yet taken place.
    safety = [
        'Projects will be selected together with trusted local partners.',
        'Technical work will be supervised by qualified professionals.',
        'All travel activities will be risk-assessed in advance.',
        'Participants are never asked to perform unsafe technical installation.',
        'Community dignity and consent are central to the model.',
        'Impact is designed to be verified and tracked through EcoIQ records.',
    ]

    ctx = {
        'experiences': experiences,
        'projects': projects,
        'ledger': ledger,
        'legacies': legacies,
        'journey': journey,
        'map_points': map_points,
        'ripple': ripple,
        'field_sites': field_sites,
        'itinerary': itinerary,
        'audiences': audiences,
        'partner_value': partner_value,
        'partners': partners,
        'safety': safety,
    }
    return render(request, 'khalifa_stewardship_tours.html', ctx)


def kazakhstan_transition_brief(request):
    """
    /kazakhstan-transition-brief/ — EcoIQ flagship visual-intelligence page.

    Pure presentation: assembles the Visual Intelligence islands (React, built
    to static/dist) with curated transition data. No AI/API calls, no secrets;
    safe to serve publicly. Each island receives its props as a JSON string —
    Django autoescaping encodes it safely into the data-props attribute, and the
    browser decodes it back to valid JSON for the loader to parse.
    """
    regions = [
        {
            'id': 'almaty', 'name': 'Almaty', 'projects': 14,
            'fundingNeededM': 96, 'households': 420000, 'emissionsReductionKt': 880,
            'note': 'Dense urban heat demand; strongest grid headroom for electrification.',
        },
        {
            'id': 'shymkent', 'name': 'Shymkent', 'projects': 9,
            'fundingNeededM': 64, 'households': 310000, 'emissionsReductionKt': 610,
            'note': "Fast-growing southern hub; high coal-stove prevalence in peri-urban districts.",
        },
        {
            'id': 'turkistan', 'name': 'Turkistan', 'projects': 6,
            'fundingNeededM': 38, 'households': 180000, 'emissionsReductionKt': 340,
            'note': 'Heritage city; pilot zone for community-financed retrofits.',
        },
        {
            'id': 'karatau', 'name': 'Karatau', 'projects': 4,
            'fundingNeededM': 22, 'households': 90000, 'emissionsReductionKt': 190,
            'note': 'Industrial legacy town; phosphate-sector partnership potential.',
        },
    ]
    total_households = sum(r['households'] for r in regions)
    total_funding = sum(r['fundingNeededM'] for r in regions)
    total_co2_kt = sum(r['emissionsReductionKt'] for r in regions)

    islands = {
        'hero': {
            'eyebrow': 'EcoIQ Climate Intelligence · 2025',
            'title': 'Kazakhstan Energy Transition Brief',
            'subtitle': 'Coal-to-electric heating retrofit — investment-grade transition '
                        'intelligence across four southern regions.',
            'transitionScore': 68,
            'households': total_households,
            'fundingNeededM': total_funding,
            'co2PotentialMt': round(total_co2_kt / 1000, 1),
            'regionsActive': len(regions),
        },
        'map': {
            'eyebrow': 'Regional Intelligence',
            'title': 'Transition Map — Southern Kazakhstan',
            'regions': regions,
        },
        'radar': {
            'eyebrow': 'Risk Intelligence',
            'title': 'Transition Risk Radar',
            'score': 68,
            'scoreLabel': 'Readiness',
            'axes': [
                {'label': 'Policy', 'value': 72},
                {'label': 'Grid', 'value': 64},
                {'label': 'Capital', 'value': 58},
                {'label': 'Social', 'value': 76},
                {'label': 'Supply', 'value': 52},
                {'label': 'Delivery', 'value': 67},
            ],
        },
        'esg': {
            'eyebrow': 'Trajectory',
            'title': 'Decarbonisation Trajectory (Index)',
            'years': [2023, 2025, 2027, 2029, 2031, 2033],
            'series': [
                {'key': 'env', 'label': 'Environmental', 'color': '#00e89a',
                 'values': [38, 46, 57, 68, 79, 88]},
                {'key': 'soc', 'label': 'Social', 'color': '#e8c46a',
                 'values': [44, 50, 58, 65, 71, 78]},
                {'key': 'gov', 'label': 'Governance', 'color': '#5ab0f2',
                 'values': [52, 56, 61, 67, 73, 80]},
            ],
        },
        'sim': {
            'eyebrow': 'Scenario Simulator',
            'title': 'Model the transition — live',
            'baseHouseholds': total_households,
            'co2PerHomeT': 5.4,
        },
        'stake': {
            'eyebrow': 'Value Network',
            'title': 'Stakeholder Map',
            'coreLabel': 'EcoIQ',
            'stakeholders': [
                {'id': 'gov', 'label': 'Government',
                 'role': 'Sets phase-out policy, permits, and tariff reform; co-funds pilots.',
                 'value': 'Provides mandate & matched capital → receives verified emissions outcomes.'},
                {'id': 'inv', 'label': 'Investors',
                 'role': 'Deploy transition capital seeking measurable, de-risked impact returns.',
                 'value': 'Provide capital → receive investment-grade intelligence & MRV.'},
                {'id': 'com', 'label': 'Communities',
                 'role': 'Households moving from coal stoves to clean electric heating.',
                 'value': 'Provide adoption → receive warmer homes, cleaner air, lower bills.'},
                {'id': 'co', 'label': 'Companies',
                 'role': 'Utilities, installers, and manufacturers delivering the retrofit at scale.',
                 'value': 'Provide delivery capacity → receive aggregated, bankable demand.'},
            ],
        },
        'story': {
            'eyebrow': 'AI Synthesis',
            'title': 'What the data is telling us',
            'insights': [
                {'stat': '1.0M households',
                 'headline': 'The opportunity is concentrated and addressable',
                 'body': 'Four southern regions hold the bulk of coal-heated homes — enough '
                         'density to make electrification logistics and grid upgrades economic.'},
                {'stat': '$220M',
                 'headline': 'Capital is the binding constraint, not technology',
                 'body': 'At roughly $4,200 per home, the retrofit pathway is well understood. '
                         'Blended public-private capital unlocks the conversion rate.'},
                {'stat': '2.0 Mt/yr',
                 'headline': 'Decarbonisation depth tracks grid cleanliness',
                 'body': 'Emissions avoided scale with how clean the electricity is — pairing '
                         'retrofits with renewable supply roughly doubles the climate return.'},
            ],
            'takeaway': 'A staged, capital-led, electrification-paired program turns a fragmented '
                        'coal-heating problem into an investment-grade, measurable transition.',
        },
    }

    props = {k: _json.dumps(v) for k, v in islands.items()}
    return render(request, 'kazakhstan_transition_brief.html', {'props': props})


@staff_member_required(login_url='/login/')
def visual_lab(request):
    """
    /visual-lab/ — Staff-only verification surface for the Visual Intelligence
    islands layer (Phase 0). Renders the ImpactGlobe React island from sample
    JSON props so the build-to-static → island-mount pipeline can be confirmed
    live. Not linked in public nav; no AI/API calls; pure presentation.
    """
    return render(request, 'visual_lab.html')


@staff_member_required(login_url='/login/')
def tazkiyah_preview(request):
    """
    /tazkiyah-114-preview/ — STAFF-ONLY internal preview of the Tazkiyah 114
    surah seed dataset (content/tazkiyah114/surah_seeds.json).

    Renders all 114 Surah seed cards so staff can visually review them before
    public release. Not linked in public nav; not public. Pure presentation —
    reads the seed JSON only, runs the existing validator first, and presents
    everything as non-authoritative draft reflection (never tafsir or fatwa).
    """
    from core.management.commands.validate_tazkiyah114_seeds import (
        validate_seeds, DEFAULT_SEED_PATH,
    )
    errors = validate_seeds()
    try:
        data = _json.loads(DEFAULT_SEED_PATH.read_text(encoding='utf-8'))
    except Exception as exc:  # pragma: no cover - defensive
        data = {'_meta': {}, 'surahs': []}
        errors = errors + [f'Could not read seed file: {exc}']

    surahs = data.get('surahs', [])
    meta = data.get('_meta', {})

    # Display-only enrichment (in-memory; does not touch the seed file).
    for s in surahs:
        s['rev_label'] = (s.get('revelation_type') or '').capitalize()
        s['status_badges'] = [
            s.get('content_status', '').replace('_', ' '),
            s.get('translation_status', '').replace('_', ' '),
            s.get('scholar_review_status', '').replace('_', ' '),
        ]

    def _count(field, value):
        return sum(1 for s in surahs if s.get(field) == value)

    stats = {
        'total': len(surahs),
        'draft': _count('content_status', 'draft_reflection'),
        'translation_pending': _count('translation_status', 'translation_pending'),
        'scholar_pending': _count('scholar_review_status', 'scholar_review_pending'),
        'authoritative': meta.get('authoritative'),
    }
    pathways = sorted({p for s in surahs for p in s.get('life_pathways', [])})

    ctx = {
        'surahs': surahs,
        'meta': meta,
        'stats': stats,
        'pathways': pathways,
        'validation_ok': not errors,
        'validation_errors': errors,
    }
    return render(request, 'tazkiyah_preview.html', ctx)


@staff_member_required(login_url='/login/')
def tazkiyah_struggles_preview(request):
    """
    /tazkiyah-114-struggles-preview/ — STAFF-ONLY internal preview of the
    "Choose Your Struggle" product journey: Struggle → Recommended Pathways →
    Suggested Surahs.

    Joins the existing seed files (content/tazkiyah114/surah_seeds.json and
    pathways.json) read-only, runs both validators first, and presents
    everything as non-authoritative suggested pathways (never tafsir/fatwa).
    Not public; not in nav.
    """
    from core.management.commands.validate_tazkiyah114_seeds import (
        validate_seeds, validate_pathways,
        DEFAULT_SEED_PATH, DEFAULT_PATHWAYS_PATH,
    )
    errors = validate_seeds() + validate_pathways()
    try:
        seeds = _json.loads(DEFAULT_SEED_PATH.read_text(encoding='utf-8'))
        paths = _json.loads(DEFAULT_PATHWAYS_PATH.read_text(encoding='utf-8'))
    except Exception as exc:  # pragma: no cover - defensive
        seeds, paths = {'surahs': []}, {'struggles': [], 'pathways': [], '_meta': {}}
        errors = errors + [f'Could not read seed/pathway files: {exc}']

    surah_by_num = {s.get('surah_number'): s for s in seeds.get('surahs', [])}

    def _resolve(nums):
        out = []
        for n in nums or []:
            s = surah_by_num.get(n)
            if s:
                out.append({
                    'num': n,
                    'name': s.get('surah_name_transliteration'),
                    'arabic': s.get('surah_name_arabic'),
                    'meaning': s.get('surah_name_translation'),
                    'theme': s.get('short_theme'),
                })
        return out

    pathways = paths.get('pathways', [])

    # Build Struggle → Pathways → Surahs for the template.
    struggle_views = []
    for st in paths.get('struggles', []):
        sid = st.get('id')
        related = []
        for p in pathways:
            if sid in (p.get('related_struggle_ids') or []):
                related.append({
                    'title': p.get('title'),
                    'short_description': p.get('short_description'),
                    'caution_note': p.get('caution_note'),
                    'status': p.get('status'),
                    'scholar_review': p.get('scholar_review'),
                    'surahs': _resolve(p.get('suggested_surah_numbers')),
                })
        struggle_views.append({'id': sid, 'label': st.get('label'), 'pathways': related})

    ctx = {
        'struggle_views': struggle_views,
        'validation_ok': not errors,
        'validation_errors': errors,
    }
    return render(request, 'tazkiyah_struggles_preview.html', ctx)


@staff_member_required(login_url='/login/')
def tazkiyah_daily_preview(request):
    """
    /tazkiyah-114-daily-preview/ — STAFF-ONLY internal preview of the Daily
    Tazkiyah habit loop: Read → Reflect → Act → Make Dua → Journal.

    Static/demo only: builds one sample daily card read-only from the existing
    seed (content/tazkiyah114/surah_seeds.json) and shows a checklist + a 7-day
    streak MOCKUP. No database models, no user-data storage, no persistence.
    Reflection-question / action / dua fields are not in the Surah-Card seed, so
    they are shown as honest 'pending' placeholders — never fabricated tafsir.
    Not public; not in nav.
    """
    from core.management.commands.validate_tazkiyah114_seeds import (
        validate_seeds, DEFAULT_SEED_PATH,
    )
    errors = validate_seeds()
    try:
        seeds = _json.loads(DEFAULT_SEED_PATH.read_text(encoding='utf-8'))
    except Exception as exc:  # pragma: no cover - defensive
        seeds = {'surahs': []}
        errors = errors + [f'Could not read seed file: {exc}']

    # Pick one well-known surah as the sample daily card (Ad-Duha, 93).
    surahs = seeds.get('surahs', [])
    sample = next((s for s in surahs if s.get('surah_number') == 93), None)
    if sample is None and surahs:
        sample = surahs[0]

    loop = ['Read', 'Reflect', 'Act', 'Make Dua', 'Journal']
    checklist = [
        'I read today',
        'I reflected today',
        'I acted on one ayah',
        'I made dua',
        'I wrote one journal note',
    ]
    # 7-day streak MOCKUP only (illustrative; no persistence).
    streak_days = [
        {'label': 'Mon', 'done': True},
        {'label': 'Tue', 'done': True},
        {'label': 'Wed', 'done': True},
        {'label': 'Thu', 'done': False},
        {'label': 'Fri', 'done': False},
        {'label': 'Sat', 'done': False},
        {'label': 'Sun', 'done': False},
    ]

    ctx = {
        'sample': sample,
        'loop': loop,
        'checklist': checklist,
        'streak_days': streak_days,
        'validation_ok': not errors,
        'validation_errors': errors,
    }
    return render(request, 'tazkiyah_daily_preview.html', ctx)


@staff_member_required(login_url='/login/')
def tazkiyah_repair_engine_preview(request):
    """
    /tazkiyah-114-repair-engine-preview/ — STAFF-ONLY internal preview that
    visualises the Qur'an Repair Engine architecture: struggle → heart wound →
    false belief → Qur'anic theme → surah pathway → reflection → dua → action →
    7-day consistency.

    Read-only: loads content/tazkiyah114/repair_engine.json (plus pathways.json
    for human-readable struggle/pathway labels), runs all three validators
    first, and presents everything as non-authoritative draft architecture —
    never tafsir or fatwa. No models, no persistence, not public, not in nav.
    """
    from core.management.commands.validate_tazkiyah114_seeds import (
        validate_seeds, validate_pathways, validate_repair_engine,
        DEFAULT_REPAIR_ENGINE_PATH, DEFAULT_PATHWAYS_PATH,
    )
    errors = validate_seeds() + validate_pathways() + validate_repair_engine()
    try:
        engine = _json.loads(DEFAULT_REPAIR_ENGINE_PATH.read_text(encoding='utf-8'))
        paths = _json.loads(DEFAULT_PATHWAYS_PATH.read_text(encoding='utf-8'))
    except Exception as exc:  # pragma: no cover - defensive
        engine, paths = {}, {}
        errors = errors + [f'Could not read repair engine / pathways files: {exc}']

    struggle_label = {s.get('id'): s.get('label') for s in paths.get('struggles', [])}
    pathway_title = {p.get('id'): p.get('title') for p in paths.get('pathways', [])}

    # Resolve struggle/pathway ids to readable labels for each heart wound.
    wounds = []
    for w in engine.get('heart_wounds', []):
        w = dict(w)
        w['struggle_labels'] = [struggle_label.get(i, i) for i in w.get('related_struggle_ids', [])]
        w['pathway_titles'] = [pathway_title.get(i, i) for i in w.get('related_pathway_ids', [])]
        wounds.append(w)

    def _human(s):
        s = str(s).replace('_', ' ').strip()
        return s[:1].upper() + s[1:] if s else s

    scb = engine.get('sin_cycle_breaker', {})
    sin_cycle = {
        'cycle': [_human(x) for x in scb.get('cycle', [])],
        'repair_cycle': [_human(x) for x in scb.get('repair_cycle', [])],
        'prompts': scb.get('prompts', []),
        'caution_note': scb.get('caution_note', ''),
    }

    ctx = {
        'meta': engine.get('_meta', {}),
        'flow_steps': [_human(x) for x in engine.get('repair_flow_steps', [])],
        'wounds': wounds,
        'sin_cycle': sin_cycle,
        'consistency_model': engine.get('consistency_model', []),
        'validation_ok': not errors,
        'validation_errors': errors,
    }
    return render(request, 'tazkiyah_repair_engine_preview.html', ctx)


@staff_member_required(login_url='/login/')
def tazkiyah_dashboard(request):
    """
    /tazkiyah-114-dashboard/ — STAFF-ONLY internal hub linking every Tazkiyah
    114 preview tool in one place, with summary stats.

    Read-only: runs the three validators (so the dashboard reflects current
    data health) and derives counts from the seed/pathway/repair-engine files.
    No models, no persistence, not public, not in nav.
    """
    from core.management.commands.validate_tazkiyah114_seeds import (
        validate_seeds, validate_pathways, validate_repair_engine,
        DEFAULT_SEED_PATH, DEFAULT_PATHWAYS_PATH, DEFAULT_REPAIR_ENGINE_PATH,
    )
    errors = validate_seeds() + validate_pathways() + validate_repair_engine()

    def _safe_load(path):
        try:
            return _json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            return {}

    seeds = _safe_load(DEFAULT_SEED_PATH)
    paths = _safe_load(DEFAULT_PATHWAYS_PATH)
    engine = _safe_load(DEFAULT_REPAIR_ENGINE_PATH)

    tools = [
        {'title': 'Surah Seed Preview', 'url': 'tazkiyah_preview',
         'desc': 'Review all 114 Surah cards and safety flags.'},
        {'title': 'Choose Your Struggle Preview', 'url': 'tazkiyah_struggles_preview',
         'desc': 'Test struggle → pathway → suggested surahs.'},
        {'title': 'Daily Tazkiyah Tracker Preview', 'url': 'tazkiyah_daily_preview',
         'desc': 'Test Read → Reflect → Act → Make Dua → Journal loop.'},
        {'title': 'Qur’an Repair Engine Preview', 'url': 'tazkiyah_repair_engine_preview',
         'desc': 'Test Struggle → Heart Wound → False Belief → Repair Action journey.'},
    ]

    stats = {
        'surahs': len(seeds.get('surahs', [])),
        'pathways': len(paths.get('pathways', [])),
        'struggles': len(paths.get('struggles', [])),
        'heart_wounds': len(engine.get('heart_wounds', [])),
        'tools': len(tools),
    }

    ctx = {
        'tools': tools,
        'stats': stats,
        'validation_ok': not errors,
        'validation_errors': errors,
    }
    return render(request, 'tazkiyah_dashboard.html', ctx)


@staff_member_required(login_url='/login/')
def video_studio(request):
    """
    /video-studio/ — Staff-only video workflow surface.
    Lists the Remotion templates, previews any already-rendered static file, and
    shows the offline render command. Does NOT render video on the server
    (build-time only — no Node/Remotion at runtime).
    """
    return render(request, 'video_studio.html', {'templates': VIDEO_TEMPLATES})


# ── Khalifa Impact Globe (public) ─────────────────────────────────────────────

def khalifa_impact(request):
    """
    /khalifa-impact/ — Khalifa Impact: villages, homes upgraded, CO₂ reduced,
    sponsor project cards, link to Khalifa Tours / heating. Figures indicative.
    Public, no auth.
    """
    impact = [
        {'value': 4,   'label': 'Pilot villages', 'accent': 'green'},
        {'value': 10,  'label': 'Homes upgraded (pilot)', 'accent': 'gold'},
        {'value': 230, 'label': 'tonnes CO₂/yr avoided', 'accent': 'blue'},
        {'value': 10,  'label': 'Families in healthier homes', 'accent': 'teal'},
    ]
    sponsors = [
        {'name': 'Sponsor 10 Homes', 'budget': '24M–30M KZT', 'desc': '10 verified retrofits + one EcoIQ impact report.', 'accent': 'green'},
        {'name': 'Clean Street Pilot', 'budget': '65M–150M KZT', 'desc': '25–50 homes on one street, launch event, media kit.', 'accent': 'blue'},
        {'name': 'Coal-Free Village Pilot', 'budget': '260M–320M KZT', 'desc': '100 homes, akimat co-launch, full impact study.', 'accent': 'gold'},
        {'name': 'ESG Heat Partnership', 'budget': '300M+ KZT / yr', 'desc': 'Multi-year co-branded programme, audited reporting.', 'accent': 'purple'},
    ]
    return render(request, 'khalifa_impact.html', {'impact': impact, 'sponsors': sponsors})


# ── Kazakhstan Transition Map (public) ────────────────────────────────────────

def kazakhstan_map(request):
    """
    /kazakhstan-map/ — Kazakhstan transition map: Almaty, Shymkent, Turkistan,
    Karatau, each with projects / funding / households / expected emissions cut.
    SVG-based (no WebGL). Public, no auth. Figures indicative.
    """
    regions = [
        {'key': 'almaty', 'name': 'Almaty', 'x': 80, 'y': 72, 'accent': 'green',
         'projects': ['Almaty Clean Air Pilot', 'Insulation-first retrofit'],
         'funding': '£15,000 pilot', 'households': '10 pilot → 1,000 target',
         'emissions': '≈ 50–80 t CO₂/yr (pilot)'},
        {'key': 'shymkent', 'name': 'Shymkent', 'x': 55, 'y': 78, 'accent': 'gold',
         'projects': ['Coal-to-electric retrofit'],
         'funding': '£20,000 pilot', 'households': '12 pilot → 800 target',
         'emissions': '≈ 60 t CO₂/yr (pilot)'},
        {'key': 'turkistan', 'name': 'Turkistan', 'x': 48, 'y': 70, 'accent': 'blue',
         'projects': ['Community greenhouse + clean heating'],
         'funding': '£25,000 pilot', 'households': '15 pilot → 600 target',
         'emissions': '≈ 45 t CO₂/yr (pilot)'},
        {'key': 'karatau', 'name': 'Karatau', 'x': 52, 'y': 64, 'accent': 'teal',
         'projects': ['Industrial-town clean heating'],
         'funding': '£18,000 pilot', 'households': '10 pilot → 500 target',
         'emissions': '≈ 40 t CO₂/yr (pilot)'},
    ]
    return render(request, 'kazakhstan_map.html', {'regions': regions})


# ── Sample Investor Readiness Report ──────────────────────────────────────────

def sample_report(request):
    """
    /sample-report/ — Public sample EcoIQ Investor Readiness Report.
    Shows a realistic report layout using demonstration data only (no real
    claims about any company). Public, no auth required.
    """
    return render(request, 'sample_report.html')


# ── Stewardship ───────────────────────────────────────────────────────────────

def global_intelligence(request):
    """
    /global-intelligence/ — interactive EcoIQ global coverage map.

    Hosts the GlobalCountryExplorer React island (Natural Earth geometry,
    lazy-loaded) plus the Digital Twin preview. Static page shell; country
    intel lives in the island's data model for now.
    """
    return render(request, 'global_intelligence.html')


def stewardship(request):
    """
    /stewardship/ — EcoIQ Stewardship section.

    Positions EcoIQ as a Climate Intelligence + Real-World Stewardship platform.
    Introduces stewardship, responsible resource management, restoration and
    long-term resilience; translates the Khalifah / Mizan / Maqasid foundations
    into institutional sustainability language; presents real-world projects,
    the EcoIQ impact KPIs, and the pilot roadmap.

    Public, no auth required. All content is static context (no models / no DB).
    """
    foundations = [
        {
            'term': 'Khalifah',
            'translation': 'Responsible Stewardship',
            'blurb': ('The principle that institutions hold resources in trust and are '
                      'accountable for managing them responsibly — protecting and improving '
                      'people, communities and ecosystems for the long term.'),
            'icon': '🌱', 'accent': 'green',
        },
        {
            'term': 'Mizan',
            'translation': 'Balance',
            'blurb': ('The discipline of balance — ensuring regeneration keeps pace with '
                      'consumption, and that value created is weighed honestly against harm '
                      'caused across environmental, social and economic systems.'),
            'icon': '⚖️', 'accent': 'gold',
        },
        {
            'term': 'Maqasid',
            'translation': 'Human Wellbeing',
            'blurb': ('The objective of advancing human wellbeing — health, livelihoods, '
                      'education, dignity and a liveable environment — as the ultimate purpose '
                      'of responsible economic and climate activity.'),
            'icon': '🤝', 'accent': 'blue',
        },
    ]

    projects = [
        {'title': 'Clean Air Transition', 'subtitle': 'Replacing coal heating systems',
         'icon': '🏭', 'accent': 'green'},
        {'title': 'Water Restoration', 'subtitle': 'Lake restoration and ecosystem recovery',
         'icon': '💧', 'accent': 'blue'},
        {'title': 'Regenerative Landscapes', 'subtitle': 'Tree planting and land restoration',
         'icon': '🌳', 'accent': 'green'},
        {'title': 'Community Greenhouses', 'subtitle': 'Food resilience infrastructure',
         'icon': '🌾', 'accent': 'gold'},
        {'title': 'Community Resilience', 'subtitle': 'Supporting MSMEs and local economies',
         'icon': '🏘️', 'accent': 'teal'},
        {'title': 'Khalifah Living', 'subtitle': 'Leadership, service and sustainability immersion',
         'icon': '🧭', 'accent': 'purple'},
    ]

    kpis = [
        {'code': 'MQV', 'name': 'Maqasid Value Added', 'accent': 'green',
         'definition': ('Total value created across environmental, social, economic and '
                        'long-term wellbeing dimensions, minus harm created.'),
         'formula': 'MQV = Σ value (env · social · econ · wellbeing) − harm',
         'example': 'A retrofit programme raises local health and jobs while cutting emissions.'},
        {'code': 'MBI', 'name': 'Mizan Balance Index', 'accent': 'gold',
         'definition': 'Measures regeneration versus consumption. MBI > 1 means restoration exceeds resource use.',
         'formula': 'MBI = regeneration ÷ consumption',
         'example': 'Reforestation sequestering more than a project consumes scores MBI > 1.'},
        {'code': 'FHI', 'name': 'Fasad Harm Index', 'accent': 'danger',
         'definition': 'Measures environmental, social and governance harm. Lower is better.',
         'formula': 'FHI = weighted(env harm + social harm + governance harm)',
         'example': 'High pollution and weak oversight raise FHI, lowering the overall balance.'},
        {'code': 'KHI', 'name': 'Khalifah Impact Index', 'accent': 'green',
         'definition': ('How much a project restores, protects and improves people, communities '
                        'and ecosystems relative to resources consumed.'),
         'formula': 'KHI = (restoration + protection + improvement) ÷ resources used',
         'example': 'Lake recovery that revives livelihoods and biodiversity scores a high KHI.'},
        {'code': 'RPI', 'name': 'Rahma Performance Index', 'accent': 'blue',
         'definition': 'Measures benefit delivered to vulnerable communities and public wellbeing.',
         'formula': 'RPI = benefit to vulnerable groups ÷ total benefit',
         'example': 'Clean-air heating prioritising low-income households lifts RPI.'},
        {'code': 'RZQ', 'name': 'Rizq Distribution Coefficient', 'accent': 'teal',
         'definition': 'Measures how fairly value is distributed across stakeholders.',
         'formula': 'RZQ = distribution equity across stakeholders (0–1)',
         'example': 'Returns shared with workers and communities, not only owners, raise RZQ.'},
        {'code': 'AMN', 'name': 'Amanah Trust Score', 'accent': 'purple',
         'definition': 'Measures transparency, accountability, governance quality and ethical stewardship.',
         'formula': 'AMN = weighted(transparency + accountability + governance)',
         'example': 'Open reporting and independent oversight produce a high AMN.'},
    ]

    pilots = [
        {'name': 'Almaty Clean Air Pilot', 'status': 'In Design', 'status_key': 'design',
         'objective': 'Replace coal-based household heating in high-pollution districts.',
         'impact': 'Lower winter PM2.5 exposure and measurable public-health improvement.'},
        {'name': 'Lake Restoration Initiative', 'status': 'Scoping', 'status_key': 'scoping',
         'objective': 'Restore a degraded lake ecosystem and surrounding watershed.',
         'impact': 'Recovered biodiversity, water security and local livelihoods.'},
        {'name': 'Community Greenhouse Program', 'status': 'Pilot Planned', 'status_key': 'planned',
         'objective': 'Deploy food-resilience greenhouse infrastructure for communities.',
         'impact': 'Year-round local food production and reduced supply-chain fragility.'},
        {'name': 'Khalifah Living Experience', 'status': 'Concept', 'status_key': 'concept',
         'objective': 'Immersive leadership, service and sustainability programme.',
         'impact': 'A pipeline of practitioners trained in real-world stewardship.'},
        {'name': 'Future EcoIQ Villages', 'status': 'Vision', 'status_key': 'vision',
         'objective': 'Integrated, regenerative community model combining all pilots.',
         'impact': 'Replicable blueprint for resilient, low-harm settlements.'},
    ]

    return render(request, 'stewardship.html', {
        'foundations': foundations,
        'projects':    projects,
        'kpis':        kpis,
        'pilots':      pilots,
    })


# ── Dashboard ────────────────────────────────────────────────────────────────

def dashboard(request):
    """
    /dashboard/ — Authenticated user home.
    Shows account info and quick-links to platform features.
    Requires login; unauthenticated visitors are redirected to /login/.
    """
    from django.contrib.auth.decorators import login_required as _lr
    if not request.user.is_authenticated:
        return redirect(f'/login/?next=/dashboard/')
    return render(request, 'dashboard.html', {'user': request.user})


# ── Platform module data ──────────────────────────────────────────────────────
# Defined at module level so it is built once per worker, not on every request.
_PLATFORM_MODULES = [
    {
        'id':       'country-intelligence',
            'number':   '01',
            'icon':     '🌍',
            'title':    'Country Transition Intelligence',
            'tagline':  'National-level transition risk and opportunity mapping.',
            'color':    '#00e89a',
            'bg':       'rgba(0,232,154,.1)',
            'border':   'rgba(0,232,154,.2)',
            'link':     '/countries/',
            'link_label': 'View country intelligence',
            'description': (
                'Country Transition Intelligence assesses the industrial and regulatory '
                'environment of a nation relative to the demands of the low-carbon economy. '
                'EcoIQ scores countries across policy clarity, energy infrastructure readiness, '
                'industrial sector composition, climate commitment ambition, and regulatory '
                'trajectory — producing a structured transition risk and opportunity profile.'
            ),
            'dimensions': [
                ('Policy Environment',        'Clarity and ambition of climate and industrial policy frameworks.'),
                ('Energy Infrastructure',     'Renewable capacity, grid modernisation, and fossil fuel dependency.'),
                ('Industrial Composition',    'Sector mix, emissions intensity, and transition-sensitive employment.'),
                ('Climate Commitments',       'NDC ambition, JETP eligibility, and bilateral climate agreements.'),
                ('Regulatory Trajectory',     'Direction and pace of environmental and financial regulation.'),
            ],
            'markets': ['United Kingdom', 'Kazakhstan', 'Saudi Arabia', 'Türkiye'],
            'tags': ['Country Scores', 'JETP Alignment', 'Sector Exposure', 'Policy Risk'],
            'disclaimer': 'Country intelligence is indicative and AI-assisted. Not investment advice.',
        },
        {
            'id':       'company-assessment',
            'number':   '02',
            'icon':     '🏭',
            'title':    'Company EcoIQ Assessment',
            'tagline':  'Six-pillar ethical scoring for industrial companies.',
            'color':    '#58a6ff',
            'bg':       'rgba(88,166,255,.1)',
            'border':   'rgba(88,166,255,.2)',
            'link':     '/companies/',
            'link_label': 'Browse company rankings',
            'description': (
                'The Company EcoIQ Assessment produces a 0–100 score for industrial companies '
                'across six pillars of ethical and environmental performance. All scores are '
                'derived from public evidence: annual reports, sustainability disclosures, '
                'CDP filings, and regulatory records. A harm penalty of up to 30 points is '
                'applied where severe pollution, governance failures, or profit extraction '
                'without proportionate public benefit is identified.'
            ),
            'dimensions': [
                ('Public Benefit',              'Employment quality, regional development, and community investment.'),
                ('Environmental Stewardship',   'Pollution intensity, waste, water, and biodiversity management.'),
                ('Responsible Modernisation',   'Energy transition, digitalisation, and infrastructure upgrades.'),
                ('Transparent Governance',      'Reporting quality, audit standards, and procurement transparency.'),
                ('Anti-Corruption',             'Governance integrity, ethical procurement, and accountability.'),
                ('Ethical Alignment',           'Long-term value creation, controversy management, and stakeholder trust.'),
            ],
            'markets': ['United Kingdom', 'Kazakhstan', 'Saudi Arabia', 'Türkiye', 'Global'],
            'tags': ['EcoIQ Score 0–100', '6 Pillars', 'Harm Signals', 'Moral Label', 'Sector Rank'],
            'disclaimer': 'Scores are AI-assisted and indicative. Not investment advice.',
        },
        {
            'id':       'project-readiness',
            'number':   '03',
            'icon':     '📐',
            'title':    'Project Readiness Review',
            'tagline':  'Climate finance readiness scored across ten dimensions.',
            'color':    '#a855f7',
            'bg':       'rgba(168,85,247,.1)',
            'border':   'rgba(168,85,247,.2)',
            'link':     '/request-access/review/?type=project_readiness',
            'link_label': 'Request a project review',
            'description': (
                'The Project Readiness Review assesses how prepared a climate or transition '
                'project is for review by investors, development finance institutions, or '
                'climate finance programmes. Ten dimensions are scored — from problem clarity '
                'and technical feasibility to revenue model strength and governance quality — '
                'producing a single readiness score and a structured brief of missing documents, '
                'main blockers, and recommended next steps.'
            ),
            'dimensions': [
                ('Problem Clarity',          'Is the transition problem well-defined with a credible baseline?'),
                ('Emissions Baseline',       'Is the GHG impact quantified and methodology credible?'),
                ('Technical Feasibility',    'How proven is the technology? Is a bankable feasibility study in place?'),
                ('CAPEX / OPEX Clarity',     'Is the cost structure defined and funded?'),
                ('Revenue Model',            'Is revenue contracted, market-based, or grant-dependent?'),
                ('Governance & Procurement', 'Are safeguards, procurement standards, and oversight in place?'),
                ('Public Benefit',           'Does the project generate jobs, community benefit, or energy access?'),
                ('Risk Mitigation',          'Are key risks identified and mitigated with documented plans?'),
                ('Evidence Confidence',      'Is the evidence verified, analyst-reviewed, or AI-estimated?'),
                ('Finance Structure',        'Is there a clear finance plan with identified lead institutions?'),
            ],
            'markets': ['United Kingdom', 'Kazakhstan', 'Saudi Arabia', 'Türkiye', 'Global'],
            'tags': ['Readiness Score', '10 Dimensions', 'DFI Criteria', 'IFC / EBRD Standards', 'Investment Label'],
            'disclaimer': (
                'Project Readiness outputs are AI-assisted and indicative. '
                'All outputs require analyst review before use in any investment or financing decision.'
            ),
        },
        {
            'id':       'capital-integrity',
            'number':   '04',
            'icon':     '🏦',
            'title':    'Capital Integrity Score',
            'tagline':  'How responsibly is capital structured and deployed?',
            'color':    '#f4a261',
            'bg':       'rgba(244,162,97,.1)',
            'border':   'rgba(244,162,97,.2)',
            'link':     '/request-access/review/?type=investor_readiness',
            'link_label': 'Request a capital integrity review',
            'description': (
                'The Capital Integrity Score assesses whether the financial structure of a '
                'company or fund aligns with responsible investment principles — including '
                'debt transparency, profit reinvestment ratios, ownership accountability, '
                'and long-term orientation. EcoIQ maps capital structure indicators against '
                'development finance institution criteria and green bond framework requirements '
                'to produce a compatibility assessment. Outputs are indicative and require '
                'qualified analyst review.'
            ),
            'dimensions': [
                ('Ownership Transparency',     'Beneficial ownership clarity and related-party structures.'),
                ('Debt Structure',             'Debt profile, covenants, and alignment with responsible finance norms.'),
                ('Profit Reinvestment',        'Ratio of profit reinvested in operations versus extracted.'),
                ('Shareholder Accountability', 'Board independence, minority protection, and voting structure.'),
                ('Long-Term Orientation',      'Capital allocation toward durable, transition-aligned assets.'),
                ('DFI Compatibility',          'Alignment with IFC, EBRD, and ADB responsible finance criteria.'),
            ],
            'markets': ['United Kingdom', 'Kazakhstan', 'Saudi Arabia', 'Türkiye'],
            'tags': ['Capital Score', 'DFI Compatibility', 'Green Bond Fit', 'Integrity Rating', 'Ownership Transparency'],
            'disclaimer': (
                'Capital Integrity outputs are AI-assisted and indicative. '
                'They do not constitute financial, legal, or investment advice.'
            ),
        },
        {
            'id':       'ethical-finance-fit',
            'number':   '05',
            'icon':     '⚖️',
            'title':    'Ethical Finance Fit',
            'tagline':  'Compatibility with responsible capital frameworks.',
            'color':    '#10b981',
            'bg':       'rgba(16,185,129,.1)',
            'border':   'rgba(16,185,129,.2)',
            'link':     '/request-access/review/',
            'link_label': 'Request an ethical finance review',
            'description': (
                'Ethical Finance Fit assesses the compatibility of a company, fund, or project '
                'with responsible capital frameworks that emphasise ethical stewardship, public '
                'benefit, equitable value distribution, and long-term resilience. EcoIQ examines '
                'asset structure, revenue stream composition, prohibited-activity exposure, '
                'governance quality, and social impact orientation — producing an indicative '
                'compatibility assessment. All outputs require review by a qualified finance '
                'professional before use in any investment or financing decision.'
            ),
            'dimensions': [
                ('Asset Structure Alignment',    'Tangible versus speculative asset composition and leverage profile.'),
                ('Revenue Stream Composition',   'Proportion of revenue from ethically aligned versus excluded activities.'),
                ('Prohibited Activity Exposure', 'Exposure to sectors or practices incompatible with ethical frameworks.'),
                ('Governance Stewardship',        'Board quality, accountability structures, and ethical procurement.'),
                ('Social Impact Orientation',    'Employment, community investment, and equitable value sharing.'),
                ('Long-Term Resilience',          'Capital resilience, sustainability commitments, and transition readiness.'),
            ],
            'markets': ['United Kingdom', 'Kazakhstan', 'Saudi Arabia', 'Türkiye'],
            'tags': ['Ethical Compatibility', 'Stewardship Score', 'Analyst Review Required', 'Responsible Capital'],
            'disclaimer': (
                'Ethical Finance Fit outputs are AI-assisted and indicative. '
                'They are not a determination of permissibility under any legal, religious, '
                'or regulatory framework. Qualified professional review is required before use '
                'in any investment or financing decision.'
            ),
        },
]


def platform(request):
    """
    /platform/ — EcoIQ Intelligence Platform overview.
    Public page showcasing the five analytical modules with descriptions,
    use cases, and a strong Request EcoIQ Review CTA.
    Module data lives in the module-level _PLATFORM_MODULES constant so it is
    built exactly once per worker startup, not re-created on every request.
    """
    from django.conf import settings as _s
    try:
        from companies.models import CompanyProfile as _CP
        _cnt = _CP.objects.filter(status__in=('public', 'verified')).count()
    except Exception:
        _cnt = 0
    return render(request, 'platform.html', {
        'modules':               _PLATFORM_MODULES,
        'calendly_url':          getattr(_s, 'CALENDLY_URL', ''),
        'site_url':              getattr(_s, 'SITE_URL', 'https://ecoiq.uk'),
        'company_count':         _cnt,
        'company_count_display': f"{_cnt}+",
    })


# ── Ethical Governance Intelligence Framework ─────────────────────────────────
# Public-facing labels use professional English only.
# The internal Name-by-Name mapping lives in docs/ethical-governance-internal-map.md
# and is NEVER served via any public URL or API response.

_EGF_MODULES = [
    {
        'number':   '01',
        'icon':     '⚖️',
        'title':    'Justice',
        'subtitle': 'Fair Distribution of Value & Risk',
        'color':    '#00e89a',
        'bg':       'rgba(0,232,154,.09)',
        'border':   'rgba(0,232,154,.22)',
        'principle': (
            'Fair distribution of value, risk, responsibility and benefit '
            'across investors, workers, communities and future generations.'
        ),
        'question': 'Who benefits, who pays, and who is exposed to harm?',
        'metrics': [
            'fair wages', 'local employment quality', 'supplier fairness',
            'tax transparency', 'pollution burden distribution',
            'service affordability', 'regional inequality impact',
        ],
        'signal': (
            'Do not approve projects where profit depends on exploitation, '
            'hidden harm or unfair burden transfer to communities or future generations.'
        ),
    },
    {
        'number':   '02',
        'icon':     '🔭',
        'title':    'Oversight',
        'subtitle': 'Governance, Control & Accountability',
        'color':    '#58a6ff',
        'bg':       'rgba(88,166,255,.09)',
        'border':   'rgba(88,166,255,.22)',
        'principle': (
            'A system must supervise power, prevent abuse and ensure '
            'responsible control at every level of governance.'
        ),
        'question': 'Who controls the company, who watches them, and who can stop harm?',
        'metrics': [
            'ownership transparency', 'board independence', 'audit quality',
            'anti-corruption controls', 'whistleblower protection',
            'governance disclosure completeness',
        ],
        'signal': (
            'No serious capital allocation without visible ownership, '
            'auditability and documented governance accountability.'
        ),
    },
    {
        'number':   '03',
        'icon':     '🛡️',
        'title':    'Protection',
        'subtitle': 'Harm Prevention & Safety Standards',
        'color':    '#a855f7',
        'bg':       'rgba(168,85,247,.09)',
        'border':   'rgba(168,85,247,.22)',
        'principle': (
            'Investment must protect life, health, property, dignity '
            'and the environment from foreseeable harm.'
        ),
        'question': 'What harm could this project create, and who is protected from it?',
        'metrics': [
            'health & safety record', 'environmental risk level',
            'emissions intensity', 'water contamination risk',
            'worker protection standards', 'disaster resilience',
        ],
        'signal': (
            'If harm prevention is weak, the project cannot be considered '
            'ethically strong even if it is profitable.'
        ),
    },
    {
        'number':   '04',
        'icon':     '📈',
        'title':    'Impact Reward',
        'subtitle': 'Recognising & Scaling Positive Outcomes',
        'color':    '#00e89a',
        'bg':       'rgba(0,232,154,.09)',
        'border':   'rgba(0,232,154,.22)',
        'principle': (
            'Good impact should be recognised, measured, rewarded and scaled — '
            'not buried in aggregate ESG scores.'
        ),
        'question': 'Does the company create measurable benefit beyond normal profit?',
        'metrics': [
            'jobs created', 'emissions reduced', 'households served',
            'energy bills lowered', 'waste diverted', 'land restored',
            'local suppliers supported',
        ],
        'signal': (
            'Companies with proven positive impact should receive stronger '
            'investor visibility, better capital access and higher EcoIQ ranking.'
        ),
    },
    {
        'number':   '05',
        'icon':     '🌱',
        'title':    'Provision',
        'subtitle': 'Sustainable Opportunity & Livelihood',
        'color':    '#34d399',
        'bg':       'rgba(52,211,153,.09)',
        'border':   'rgba(52,211,153,.22)',
        'principle': (
            'Provision must be sustainable, dignified and accessible — '
            'creating real opportunity without destroying future resources.'
        ),
        'question': 'Does this company create real livelihood and opportunity without depleting what remains?',
        'metrics': [
            'employment creation', 'SME opportunity generated',
            'food / energy / water access', 'service affordability',
            'skills development', 'household income impact',
        ],
        'signal': (
            'Prefer investments that expand long-term livelihood and opportunity '
            'over those generating temporary profit from resource depletion.'
        ),
    },
    {
        'number':   '06',
        'icon':     '💡',
        'title':    'Wisdom',
        'subtitle': 'Judgment in Capital Allocation',
        'color':    '#f4a261',
        'bg':       'rgba(244,162,97,.09)',
        'border':   'rgba(244,162,97,.22)',
        'principle': (
            'Capital must be placed with evidence, timing and long-term judgment — '
            'not chasing fashion or short-term returns.'
        ),
        'question': 'Is this the right project, in the right place, at the right time?',
        'metrics': [
            'capital efficiency', 'climate transition risk',
            'long-term demand outlook', 'policy alignment',
            'technology maturity', 'community acceptance level',
        ],
        'signal': (
            'Do not fund what is merely fashionable; '
            'fund what is wise, needed, durable and beneficial.'
        ),
    },
    {
        'number':   '07',
        'icon':     '🤝',
        'title':    'Sensitivity',
        'subtitle': 'Protecting Vulnerable & Underserved Communities',
        'color':    '#f472b6',
        'bg':       'rgba(244,114,182,.09)',
        'border':   'rgba(244,114,182,.22)',
        'principle': (
            'Governance must notice subtle harm that powerful systems often ignore — '
            'particularly harm to those least able to protect themselves.'
        ),
        'question': 'How does this project affect people with the least power to complain?',
        'metrics': [
            'low-income household impact', 'children and elderly exposure',
            'rural community effects', 'energy poverty risk',
            'service accessibility', 'grievance response time',
        ],
        'signal': (
            'A project cannot be rated excellent if it looks good on paper '
            'but quietly harms weak or underrepresented groups.'
        ),
    },
    {
        'number':   '08',
        'icon':     '🔒',
        'title':    'Trust',
        'subtitle': 'Fiduciary Responsibility & Agency',
        'color':    '#818cf8',
        'bg':       'rgba(129,140,248,.09)',
        'border':   'rgba(129,140,248,.22)',
        'principle': (
            'Those entrusted with capital must act as responsible agents — '
            'not selfish owners — accountable to investors, communities and regulators.'
        ),
        'question': 'Can investors, communities and regulators trust this company to do what it promises?',
        'metrics': [
            'delivery against commitments', 'audit consistency',
            'contract fulfilment record', 'complaint resolution speed',
            'legal dispute history', 'management integrity signals',
        ],
        'signal': (
            'Trust must be earned through evidence and consistent behaviour, '
            'not asserted through branding or narrative.'
        ),
    },
    {
        'number':   '09',
        'icon':     '👁️',
        'title':    'Visibility',
        'subtitle': 'Monitoring, Evidence & Transparency',
        'color':    '#22d3ee',
        'bg':       'rgba(34,211,238,.09)',
        'border':   'rgba(34,211,238,.22)',
        'principle': (
            'Ethical capital requires visibility. '
            'What is hidden cannot be governed, assessed or improved.'
        ),
        'question': 'Can we see the real impact, real risks and real behaviour of this company?',
        'metrics': [
            'data availability & completeness', 'emissions monitoring quality',
            'financial reporting transparency', 'supply-chain visibility',
            'third-party verification', 'satellite evidence use',
        ],
        'signal': (
            'No visibility, no confidence. '
            'No verifiable evidence means no high ethical governance rating.'
        ),
    },
    {
        'number':   '10',
        'icon':     '📊',
        'title':    'Accounting',
        'subtitle': 'Full Measurement & Consequence Tracking',
        'color':    '#fb923c',
        'bg':       'rgba(251,146,60,.09)',
        'border':   'rgba(251,146,60,.22)',
        'principle': (
            'Everything must be counted: profit, harm, benefit, '
            'responsibility and consequences — not just what is convenient.'
        ),
        'question': 'Is the company honestly measuring what matters?',
        'metrics': [
            'carbon accounting completeness', 'water use reporting',
            'waste output tracking', 'social impact measurement',
            'tax paid and local value created', 'impact per £ invested',
        ],
        'signal': (
            'What cannot be measured responsibly cannot be claimed as impact. '
            'Selective reporting is a governance failure.'
        ),
    },
]

_EGF_EXTENDED = [
    ('🌊', 'Universal Benefit',       'Public benefit across all stakeholders, not just shareholders.'),
    ('💛', 'Targeted Care',           'Deliberate attention to those most affected by a project\'s risks.'),
    ('🏛️', 'Stewardship',            'Responsible management of resources held in trust for communities.'),
    ('✨', 'Ethical Screening',       'Active exclusion of harmful activities from investment consideration.'),
    ('☮️', 'Non-Harm',               'Primary obligation to cause no damage before seeking gain.'),
    ('🔐', 'Security',               'Building systems that communities and investors can rely on.'),
    ('💪', 'Resilience',             'Strategic strength that withstands stress without externalities.'),
    ('🔄', 'Restorative Justice',    'Repairing harm already caused and creating remediation pathways.'),
    ('🔬', 'Innovation',             'Creating new sources of value without increasing harm.'),
    ('♻️', 'Regenerative Design',    'Systems that restore rather than deplete what they use.'),
    ('🧩', 'Inclusive Design',       'Products and services built to serve all users, not only the powerful.'),
    ('🌿', 'Remediation',            'Pathways for companies to repair past failures and re-qualify.'),
    ('⚡', 'Enforcement',            'Clear consequences for abuse, breach of standards or harm.'),
    ('🔓', 'Access',                 'Removing cost and structural barriers to economic participation.'),
    ('🚪', 'Barrier Removal',        'Unlocking markets, finance and opportunity for excluded actors.'),
    ('🧠', 'Intelligence',           'Evidence-based decision-making powered by complete, verified data.'),
    ('🎯', 'Risk Control',           'Disciplined restraint when risk-adjusted returns do not justify harm.'),
    ('📡', 'Impact Scaling',         'Actively growing what works and replicating proven positive models.'),
    ('📉', 'Harm Downgrade',         'Reducing visibility and capital access for persistently harmful actors.'),
    ('📤', 'Leader Elevation',       'Amplifying and rewarding companies that consistently do better.'),
    ('📣', 'Community Voice',        'Structured mechanisms for affected communities to raise concerns.'),
    ('🔎', 'Deep Due Diligence',     'Rigorous analysis below the surface of headline ESG scores.'),
    ('⏳', 'Patient Transition',     'Supporting companies on genuine long-term change pathways.'),
    ('🤲', 'Inclusive Prosperity',   'Capital allocation that broadens economic participation.'),
    ('📋', 'Continuous Supervision', 'Ongoing monitoring rather than point-in-time assessment.'),
    ('🧮', 'Full Quantification',    'Counting all outcomes — positive, negative and indirect.'),
    ('🔃', 'Circularity',            'Investment in systems that restore and repurpose rather than discard.'),
    ('💧', 'Life-Giving Capital',    'Prioritising investment that sustains essential systems.'),
    ('🏗️', 'System Stability',       'Long-term maintenance of infrastructure and operational continuity.'),
    ('🔗', 'Unified Framework',      'Coherent ethical logic applied consistently, not selectively.'),
    ('🕸️', 'Dependency Mapping',     'Understanding and managing critical infrastructure interdependencies.'),
    ('📰', 'Public Transparency',    'Proactive disclosure of material information, not just compliance.'),
    ('🕵️', 'Hidden Risk Detection',  'Identifying risks obscured by complexity, narrative or distance.'),
    ('⚖️', 'Stakeholder Balance',    'Fair consideration of competing interests without systemic bias.'),
    ('🌐', 'Collective Action',      'System-level coordination to solve problems no single actor can fix.'),
    ('🆓', 'Capital Independence',   'Resisting dependency on exploitative or coercive financing.'),
    ('🚫', 'Harm Prevention',        'Active systems to stop damage before it occurs.'),
    ('✅', 'Benefit Creation',       'Deliberate generation of positive outcomes as a primary objective.'),
    ('🔦', 'Disclosure Clarity',     'Plain, accessible communication of risk, impact and governance.'),
    ('🗺️', 'Transition Guidance',    'Roadmaps that help companies move from high-harm to lower-harm models.'),
    ('🌳', 'Long-Term Sustainability','Investment horizons that protect the interests of future generations.'),
    ('⏭️', 'Intergenerational Justice','Ensuring today\'s decisions do not impoverish those who follow.'),
    ('🧭', 'Sound Decision-Making',  'Structured, evidence-based processes for governance choices.'),
    ('🌅', 'Enduring Transformation','Patient commitment to long-term systemic change over short-term gain.'),
]


def ethical_governance(request):
    """
    /ethical-governance/ — EcoIQ Ethical Governance Intelligence Framework.
    A professional, investor-grade presentation of the 10 primary governance
    principles and 44 extended principles. Language is professional English only.
    The internal Name-by-Name mapping is in docs/ethical-governance-internal-map.md.
    """
    from django.conf import settings as _s
    try:
        from companies.models import CompanyProfile as _CP
        _cnt = _CP.objects.filter(status__in=('public', 'verified')).count()
    except Exception:
        _cnt = 0
    return render(request, 'ethical_governance.html', {
        'modules':               _EGF_MODULES,
        'extended':              _EGF_EXTENDED,
        'site_url':              getattr(_s, 'SITE_URL', 'https://ecoiq.uk'),
        'calendly_url':          getattr(_s, 'CALENDLY_URL', ''),
        'company_count':         _cnt,
        'company_count_display': f"{_cnt}+",
    })


def governance_principles(request):
    """
    /governance-principles/ — EcoIQ Capital Ethics Compendium.
    114 governance principles rendered via client-side JavaScript.
    Language: professional English only.
    Internal principle-origin mapping: docs/governance-principles-surah-map.md (INTERNAL ONLY).

    JSON strings are pre-serialised at module load time (in esg_principles_data.py)
    so this view does zero json.dumps() work on the request thread.
    """
    from django.conf import settings as _s
    from .esg_principles_data import PRINCIPLES_JSON, CATEGORIES_JSON, PRINCIPLES

    return render(request, 'governance_principles.html', {
        'principles_json':  PRINCIPLES_JSON,   # pre-baked — no per-request serialisation
        'categories_json':  CATEGORIES_JSON,
        'principles_count': len(PRINCIPLES),
        'site_url':   getattr(_s, 'SITE_URL', 'https://ecoiq.uk'),
        'calendly_url': getattr(_s, 'CALENDLY_URL', ''),
    })
