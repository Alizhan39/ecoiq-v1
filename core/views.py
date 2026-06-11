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


@login_required
def index(request):
    # Limit to the 50 most-recent assessments — avoids loading all rows into memory.
    assessments = Assessment.objects.order_by('-created_at')[:50]
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
