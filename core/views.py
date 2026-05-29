import json as _json
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

    # Live platform data for homepage
    top_companies = []
    company_count = 0
    country_count = 0
    try:
        from companies.models import CompanyProfile
        from countries.models import CountryProfile
        top_companies = list(
            CompanyProfile.objects
            .filter(status__in=('public', 'verified'))
            .select_related('company')
            .order_by('-ecoiq_total_score')[:8]
        )
        _co = CompanyProfile.objects.filter(status__in=('public', 'verified')).count()
        _ct = CountryProfile.objects.filter(is_published=True).count()
        # Format as "400+", "200+" etc. for display
        if _co >= 400:
            company_count = '400+'
        elif _co >= 200:
            company_count = '200+'
        elif _co >= 100:
            company_count = '100+'
        else:
            company_count = _co or 38
        # Use actual company-country diversity if CountryProfile count is low
        from league.models import Company as _Co
        _distinct_countries = _Co.objects.values('country').distinct().count()
        country_count = (
            f'{_ct}+' if _ct >= 15
            else (f'{_distinct_countries}+' if _distinct_countries >= 15 else (_ct or 11))
        )
    except Exception:
        pass  # DB may not be ready (first migration)

    pillars_meta = [
        {'icon': '🌍', 'label': 'Public Benefit',              'desc': 'Employment quality, regional development, community investment, national value', 'weight': '25%'},
        {'icon': '♻️', 'label': 'Environmental Stewardship',   'desc': 'Pollution intensity, waste management, water stewardship, biodiversity',          'weight': '25%'},
        {'icon': '⚡', 'label': 'Responsible Modernization',   'desc': 'Energy transition, digitalization, infrastructure upgrades, future readiness',     'weight': '20%'},
        {'icon': '🔍', 'label': 'Transparent Governance',      'desc': 'Reporting quality, audit standards, procurement transparency',                    'weight': '15%'},
        {'icon': '⚖️', 'label': 'Anti-Corruption',            'desc': 'Governance integrity, ethical procurement, institutional accountability',           'weight': '10%'},
        {'icon': '✦',  'label': 'Ethical Alignment',           'desc': 'Long-term value creation, controversy management, stakeholder trust',              'weight': '5%'},
    ]

    return render(request, 'landing.html', {
        # Live data
        'top_companies':  top_companies,
        'company_count':  company_count,
        'country_count':  country_count,
        'pillars_meta':   pillars_meta,
        'audience_labels': ['Investors', 'Governments', 'Companies', 'Climate Programmes', 'Development Banks'],
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
        import weasyprint
        html_string = render_to_string('core/report_pdf.html', ctx, request=request)
        pdf_bytes   = weasyprint.HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()
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
    return render(request, 'about.html')


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
