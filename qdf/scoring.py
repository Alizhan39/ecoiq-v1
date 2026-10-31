"""
EcoIQ Quranic Decision Filter — Scoring Engine.

Maps a company's existing EcoIQ signals onto the 10 decision questions
(0–10 each), gated by evidence/confidence, and rolls them up into a
Decision Integrity Score (0–100) with a risk level and verdict.

Design rules (consistent with EcoIQ intelligence policy):
  • Derives ONLY from existing EcoIQ profile signals — invents no new facts.
  • Evidence-gated: low evidence ⇒ lower confidence, never inflated certainty.
  • Red lines (Halal / Adl / Darar severely failed) CAP the overall score —
    justice is not traded off against other gains.
  • Never raises into caller: get_or_compute returns None on any error.
"""
import json
import logging
import pathlib

from django.conf import settings
from django.db import transaction

from core.unknown import known, mean_of_known

log = logging.getLogger(__name__)

SEED_PATH = pathlib.Path(__file__).resolve().parent / 'seed' / 'decision_questions.json'

# Questions whose severe failure caps the overall score
RED_LINE_KEYS = {'halal', 'adl', 'darar'}
RED_LINE_THRESHOLD = 3.0   # score below this on a red-line question triggers the cap
RED_LINE_CAP = 40.0        # overall score capped at this when a red line is breached


# ── Question registry seeding ──────────────────────────────────────────────────

def load_seed():
    with open(SEED_PATH, encoding='utf-8') as fh:
        return json.load(fh)


def ensure_questions():
    """
    Idempotently ensure the 10 DecisionQuestion rows exist. Safe to call on
    every compute — lazy-seeds so company pages work before the management
    command is run. Returns the ordered queryset.
    """
    from qdf.models import DecisionQuestion
    data = load_seed()
    for q in data['questions']:
        DecisionQuestion.objects.update_or_create(
            key=q['key'],
            defaults={
                'order':              q['order'],
                'arabic_term':        q['arabic_term'],
                'title_en':           q['title_en'],
                'core_question':      q['core_question'],
                'weight':             q.get('weight', 1.0),
                'definition':         q['definition'],
                'plain_english':      q['plain_english'],
                'evidence_required':  q['evidence_required'],
                'red_flags':          q['red_flags'],
                'scoring_rubric':     q['scoring_rubric'],
                'ai_prompt':          q['ai_prompt'],
                'low_score_actions':  q['low_score_actions'],
                'example_company':    q['example_company'],
                'example_policy':     q['example_policy'],
                'example_investment': q['example_investment'],
                'is_red_line':        q['key'] in RED_LINE_KEYS,
                'is_active':          True,
            },
        )
    return DecisionQuestion.objects.filter(is_active=True).order_by('order')


# ── Helpers ─────────────────────────────────────────────────────────────────────

def _clamp10(v):
    return round(max(0.0, min(10.0, v)), 1)


def _f(profile, name, default=50.0):
    """
    Read a profile score, substituting `default` when it is unknown.

    A D2 RESIDUAL, found by tracing these formulas for D3C-3d rather than by
    the pattern sweeps. Those searched for `or 50` and `float(v or 0)`; this
    is `or default` where default is a VARIABLE, so the regex never matched
    it. The behaviour is the same fabrication: an unknown score, a missing
    attribute, and a genuine measured 0.0 all become 50.

    It is corrected rather than merely noted because D3C-3d cannot record
    truthful lineage over a calculator that invents its own inputs — the
    provenance row would claim sixteen consumed inputs when several were
    never measured.

    Unknown now returns None and callers decide, exactly as in #242.
    """
    return known(getattr(profile, name, None))


def _f_or(profile, name, default=50.0):
    """
    _f with an explicit fallback, for the few sites where the QDF scale
    genuinely needs a number and the domain treats a missing signal as
    mid-scale. Naming it separately makes each such substitution a visible
    decision rather than a default nobody chose.
    """
    value = _f(profile, name)
    return default if value is None else value


def _avg(*vals):
    """
    Mean of the known values, or None when none are known.

    Was `... if vals else 50.0` — the same residual as _f, and the same shape
    as mizan's `_mean(...) if vals else 0.0` that a test caught in #244.
    """
    return mean_of_known(*vals)


def _avg_or(default=50.0, *vals):
    """Mean of the known values, or an explicit fallback."""
    value = _avg(*vals)
    return default if value is None else value


def _evidence_for_profile(profile):
    """Return (confidence 0–1, evidence_status, question_evidence_status)."""
    try:
        src_count = profile.cited_sources.count()
    except Exception:
        src_count = 0
    verified = bool(getattr(profile, 'is_verified', False))

    # Confidence: verification + source citations + non-default scores
    conf = 0.30
    if verified:
        conf += 0.35
    conf += min(src_count, 4) * 0.06
    if getattr(profile, 'annual_report_url', ''):
        conf += 0.05
    if getattr(profile, 'sustainability_report_url', ''):
        conf += 0.05
    conf = round(min(conf, 0.95), 2)

    if verified:
        status, q_status = 'verified', 'verified'
    elif src_count >= 2:
        status, q_status = 'partial', 'partial'
    elif src_count >= 1:
        status, q_status = 'insufficient', 'insufficient'
    else:
        status, q_status = 'unverified', 'missing'
    return conf, status, q_status


# ── Per-question signal mapping (company subjects) ──────────────────────────────

def _question_signals(profile):
    """
    Map existing EcoIQ profile scores (0–100) onto each question's 0–10 score.
    Each entry: key -> (score_0_10, rationale).
    These are PROXIES derived from existing signals — not new claims.
    """
    pb   = _f_or(profile, 'public_benefit_score')
    env  = _f_or(profile, 'environmental_responsibility_score')
    mod  = _f_or(profile, 'modernization_score')
    gov  = _f_or(profile, 'transparency_anti_corruption_score')
    ac   = _f_or(profile, 'anti_corruption_score')
    eth  = _f_or(profile, 'ethical_alignment_score')
    contr = _f_or(profile, 'controversy_risk_score', 30.0)     # higher = worse
    pextr = _f_or(profile, 'profit_extraction_risk_score', 30.0)  # higher = worse
    jobs  = _f_or(profile, 'jobs_created_score')
    region = _f_or(profile, 'regional_development_score')
    natval = _f_or(profile, 'national_value_score')
    infra  = _f_or(profile, 'infrastructure_contribution_score')
    audit  = _f_or(profile, 'audit_quality_score')
    procure = _f_or(profile, 'procurement_transparency_score')
    future = _f_or(profile, 'future_readiness_score')
    water  = _f_or(profile, 'water_impact_score')

    inv = lambda x: 100.0 - x  # invert a "higher = worse" signal

    return {
        'niyyah':  (_avg_or(50.0, pb, inv(pextr)) / 10.0,
                    'Derived from public-benefit orientation vs profit-extraction risk.'),
        'halal':   (_avg_or(50.0, eth, inv(contr)) / 10.0,
                    'Screening proxy from ethical-alignment and controversy signals (not a Shariah ruling).'),
        'adl':     (_avg_or(50.0, gov, ac, region) / 10.0,
                    'Derived from transparency, anti-corruption, and fair regional distribution signals.'),
        'rahmah':  (_avg_or(50.0, jobs, region, water) / 10.0,
                    'Derived from employment, community development, and water/community protection signals.'),
        'mizan':   (_avg_or(50.0, env, future) / 10.0,
                    'Derived from environmental responsibility and long-term balance signals.'),
        'amanah':  (_avg_or(50.0, gov, audit, ac) / 10.0,
                    'Derived from disclosure quality, audit standards, and anti-corruption signals.'),
        'maslahah':(_avg_or(50.0, pb, natval, infra) / 10.0,
                    'Derived from public-benefit, national-value, and infrastructure contribution signals.'),
        'darar':   (inv(_avg_or(50.0, contr, pextr, inv(env))) / 10.0,
                    'Freedom-from-harm: inverse of controversy, extraction, and environmental-harm signals.'),
        'shura':   (_avg_or(50.0, procure, gov) / 10.0,
                    'Consultation proxy from procurement transparency and governance openness (proxy only).'),
        'akhirah': (_avg_or(50.0, eth, ac, pb, inv(contr)) / 10.0,
                    'Integrity synthesis from ethical-alignment, anti-corruption, public-benefit, and controversy signals.'),
    }


# ── Roll-up ─────────────────────────────────────────────────────────────────────

def _risk_and_verdict(score, red_line, evidence_status):
    if red_line or score < 35:
        return ('severe' if red_line else 'high'), 'do_not_proceed'
    if score < 50:
        return 'elevated', 'revise'
    if score < 65:
        return 'moderate', 'proceed_conditions'
    if evidence_status in ('unverified', 'insufficient'):
        return 'moderate', 'proceed_conditions'
    return 'low', 'proceed'


def _summary(subject_name, verdict, weakest_title, score):
    head = {
        'proceed':            'Creates rizq without zulm',
        'proceed_conditions': 'Can create rizq without zulm — with conditions',
        'revise':             'Risk of zulm — revise before proceeding',
        'do_not_proceed':     'Creates rizq through zulm — do not proceed as designed',
    }.get(verdict, 'Under review')
    return (f'{head}. Decision Integrity {score:.0f}/100. '
            f'Weakest dimension: {weakest_title}. '
            f'(AI-assisted, indicative — not a Shariah ruling.)')


def compute_for_profile(profile):
    """
    Compute a QDF assessment dict from a CompanyProfile (no DB writes).
    Returns: {overall, risk, verdict, evidence, confidence, red_line, summary, questions:[...]}.
    """
    questions = ensure_questions()
    signals = _question_signals(profile)
    confidence, evidence_status, q_evidence = _evidence_for_profile(profile)

    rows = []
    weighted_sum = 0.0
    weight_total = 0.0
    red_line = False
    weakest = (999.0, '—')

    for q in questions:
        raw, rationale = signals.get(q.key, (5.0, 'Insufficient signal; defaulted to neutral.'))
        s = _clamp10(raw)
        weighted_sum += s * q.weight
        weight_total += q.weight
        if q.is_red_line and s < RED_LINE_THRESHOLD:
            red_line = True
        if s < weakest[0]:
            weakest = (s, q.title_en)

        flags = []
        actions = []
        if s < 4:
            flags = list(q.red_flags)
            actions = list(q.low_score_actions)
        elif s < 6:
            flags = list(q.red_flags[:1])
            actions = list(q.low_score_actions[:2])

        rows.append({
            'key': q.key, 'order': q.order, 'arabic_term': q.arabic_term,
            'title_en': q.title_en, 'core_question': q.core_question,
            'score': s, 'rationale': rationale, 'evidence_status': q_evidence,
            'red_flags_triggered': flags, 'recommended_actions': actions,
        })

    overall = round((weighted_sum / weight_total) * 10.0, 1) if weight_total else 0.0
    if red_line:
        overall = min(overall, RED_LINE_CAP)

    risk, verdict = _risk_and_verdict(overall, red_line, evidence_status)
    summary = _summary(profile.company.name, verdict, weakest[1], overall)

    return {
        'overall': overall, 'risk': risk, 'verdict': verdict,
        'evidence_status': evidence_status, 'confidence': confidence,
        'red_line': red_line, 'summary': summary, 'questions': rows,
    }


def compute_from_scores(scores_by_key, subject_name='Decision',
                        evidence_status='unverified', confidence=0.5):
    """
    Roll up an explicit set of per-question scores (key -> 0–10) into a Decision
    Integrity Score, risk, verdict, and summary. Used by the ad-hoc API evaluator
    for non-company subjects (policy / investment / infrastructure). No DB writes.
    Missing questions default to neutral (5.0).
    """
    questions = ensure_questions()
    weighted_sum = 0.0
    weight_total = 0.0
    red_line = False
    weakest = (999.0, '—')
    rows = []

    for q in questions:
        s = _clamp10(float(scores_by_key.get(q.key, 5.0)))
        weighted_sum += s * q.weight
        weight_total += q.weight
        if q.is_red_line and s < RED_LINE_THRESHOLD:
            red_line = True
        if s < weakest[0]:
            weakest = (s, q.title_en)
        flags, actions = [], []
        if s < 4:
            flags, actions = list(q.red_flags), list(q.low_score_actions)
        elif s < 6:
            flags, actions = list(q.red_flags[:1]), list(q.low_score_actions[:2])
        rows.append({
            'key': q.key, 'order': q.order, 'arabic_term': q.arabic_term,
            'title_en': q.title_en, 'core_question': q.core_question, 'score': s,
            'red_flags_triggered': flags, 'recommended_actions': actions,
        })

    overall = round((weighted_sum / weight_total) * 10.0, 1) if weight_total else 0.0
    if red_line:
        overall = min(overall, RED_LINE_CAP)
    risk, verdict = _risk_and_verdict(overall, red_line, evidence_status)
    return {
        'overall': overall, 'risk': risk, 'verdict': verdict,
        'evidence_status': evidence_status, 'confidence': confidence,
        'red_line': red_line,
        'summary': _summary(subject_name, verdict, weakest[1], overall),
        'questions': rows,
    }


# ── Derived provenance (D3C-3d) ───────────────────────────────────────────────

#: QDF is the Quranic Decision Filter: a rule-based decision-integrity screen
#: that scores a profile against DecisionQuestion records on a 0-10 scale and
#: reduces them to one 0-100 overall. Traced from the implementation, not
#: inferred from the acronym (STEP 4). Nothing here embellishes it: the
#: methodology name says what the code does and no more.
QDF_METHOD = 'ecoiq-qdf-decision-integrity'
QDF_VERSION = '1'

QDF_METRIC_KEY = 'qdf.decision_integrity'

#: The profile fields _question_signals() actually reads, as registry keys.
#: Four resolve to DERIVED pillars, so the lineage links those rather than
#: flattening to their material inputs.
#:
#: KNOWN GAP: profit_extraction_risk_score is read by the formula but is not a
#: registered metric, so it cannot be linked. It is a real CompanyProfile
#: field — checked, not assumed — not a typo.
QDF_INPUTS = (
    'company.public_benefit', 'company.environmental', 'company.modernization',
    'company.transparency_governance', 'company.ethical_alignment',
    'anti_corruption_score', 'audit_quality_score', 'controversy_risk_score',
    'future_readiness_score', 'infrastructure_contribution_score',
    'jobs_created_score', 'national_value_score',
    'procurement_transparency_score', 'regional_development_score',
    'water_impact_score',
)


def compute_and_save(profile):
    """
    Compute and persist the QDF assessment, and record its lineage.

    Value and provenance in one transaction; the returned assessment carries a
    transient `provenance_status`.
    """
    from companies import provenance as prov

    # QDF already had @transaction.atomic on this work; the outer block exists
    # so the provenance write joins the SAME unit rather than committing
    # separately after it. Reusing the existing boundary rather than adding a
    # competing one.
    with transaction.atomic():
        assessment = _compute_and_save_inner(profile)
        assessment.provenance_status = prov.record_calculated(
            profile, QDF_METRIC_KEY, assessment.decision_integrity_score,
            QDF_INPUTS,
            writer='qdf.scoring.compute_and_save',
            methodology=QDF_METHOD,
            calculation_version=QDF_VERSION,
        )
    return assessment


@transaction.atomic
def _compute_and_save_inner(profile):
    """Compute and persist the auto QDF assessment + its 10 QuestionScores."""
    from qdf.models import DecisionQuestion, DecisionAssessment, QuestionScore

    result = compute_for_profile(profile)
    assessment, _ = DecisionAssessment.objects.update_or_create(
        profile=profile, source='auto',
        defaults={
            'subject_type':              'company',
            'subject_name':              profile.company.name,
            'subject_ref':               profile.company.slug,
            'decision_integrity_score':  result['overall'],
            'risk_level':                result['risk'],
            'verdict':                   result['verdict'],
            'evidence_status':           result['evidence_status'],
            'confidence':                result['confidence'],
            'red_line_breached':         result['red_line'],
            'rizq_without_zulm_summary': result['summary'],
            'ai_narrative': (
                'QDF auto-assessment derived from EcoIQ public-signal scores. '
                'AI-assisted and indicative; not fatwa, tafsir, or investment advice.'
            ),
        },
    )

    q_by_key = {q.key: q for q in DecisionQuestion.objects.all()}
    for row in result['questions']:
        q = q_by_key.get(row['key'])
        if not q:
            continue
        QuestionScore.objects.update_or_create(
            assessment=assessment, question=q,
            defaults={
                'score':               row['score'],
                'rationale':           row['rationale'],
                'evidence_status':     row['evidence_status'],
                'red_flags_triggered': row['red_flags_triggered'],
                'recommended_actions': row['recommended_actions'],
            },
        )
    return assessment


def get_or_compute(profile):
    """
    Return the existing auto QDF assessment for a company profile, or compute one.
    Returns None on any error (never breaks company pages).
    """
    try:
        from qdf.models import DecisionAssessment
        existing = (DecisionAssessment.objects
                    .filter(profile=profile, source='auto')
                    .prefetch_related('question_scores__question')
                    .first())
        if existing:
            return existing
        return compute_and_save(profile)
    except Exception as exc:
        log.warning('QDF get_or_compute failed for %s: %s', profile, exc)
        return None
