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
    return float(getattr(profile, name, default) or default)


def _avg(*vals):
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else 50.0


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
    pb   = _f(profile, 'public_benefit_score')
    env  = _f(profile, 'environmental_responsibility_score')
    mod  = _f(profile, 'modernization_score')
    gov  = _f(profile, 'transparency_anti_corruption_score')
    ac   = _f(profile, 'anti_corruption_score')
    eth  = _f(profile, 'ethical_alignment_score')
    contr = _f(profile, 'controversy_risk_score', 30.0)     # higher = worse
    pextr = _f(profile, 'profit_extraction_risk_score', 30.0)  # higher = worse
    jobs  = _f(profile, 'jobs_created_score')
    region = _f(profile, 'regional_development_score')
    natval = _f(profile, 'national_value_score')
    infra  = _f(profile, 'infrastructure_contribution_score')
    audit  = _f(profile, 'audit_quality_score')
    procure = _f(profile, 'procurement_transparency_score')
    future = _f(profile, 'future_readiness_score')
    water  = _f(profile, 'water_impact_score')

    inv = lambda x: 100.0 - x  # invert a "higher = worse" signal

    return {
        'niyyah':  (_avg(pb, inv(pextr)) / 10.0,
                    'Derived from public-benefit orientation vs profit-extraction risk.'),
        'halal':   (_avg(eth, inv(contr)) / 10.0,
                    'Screening proxy from ethical-alignment and controversy signals (not a Shariah ruling).'),
        'adl':     (_avg(gov, ac, region) / 10.0,
                    'Derived from transparency, anti-corruption, and fair regional distribution signals.'),
        'rahmah':  (_avg(jobs, region, water) / 10.0,
                    'Derived from employment, community development, and water/community protection signals.'),
        'mizan':   (_avg(env, future) / 10.0,
                    'Derived from environmental responsibility and long-term balance signals.'),
        'amanah':  (_avg(gov, audit, ac) / 10.0,
                    'Derived from disclosure quality, audit standards, and anti-corruption signals.'),
        'maslahah':(_avg(pb, natval, infra) / 10.0,
                    'Derived from public-benefit, national-value, and infrastructure contribution signals.'),
        'darar':   (inv(_avg(contr, pextr, inv(env))) / 10.0,
                    'Freedom-from-harm: inverse of controversy, extraction, and environmental-harm signals.'),
        'shura':   (_avg(procure, gov) / 10.0,
                    'Consultation proxy from procurement transparency and governance openness (proxy only).'),
        'akhirah': (_avg(eth, ac, pb, inv(contr)) / 10.0,
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


@transaction.atomic
def compute_and_save(profile):
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
