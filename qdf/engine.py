"""
EcoIQ Quranic Decision Filter — Decision Engine.

Turns a DecisionAssessment (the 10 question scores) into an executable plan:

    build_decision_cards()  → one Decision Card per under-target question
                              (detection, root cause, actions, impact, horizon,
                               cost, owner, priority).
    build_action_queue()    → Decision Cards ranked by Next-Best-Action priority.
    generate_roadmap()      → cards sequenced into 30 / 90 / 365 / 1095-day buckets
                              with a projected Decision Integrity trajectory.
    simulate_scenario()     → re-score under hypothetical per-question changes.
    project_integrity()     → projected score if a set of questions reaches target.

Everything is derived deterministically from the assessment — no new facts, no
DB writes. Mirrors how EcoIQ derives score_cards / improvement_pathway on the fly.
"""
from qdf.scoring import compute_from_scores

DEFAULT_TARGET = 8.0

# Per-question delivery metadata (accountable owner + cost band)
QUESTION_META = {
    'niyyah':   {'owner': 'CEO / Board',                      'cost': '£'},
    'halal':    {'owner': 'General Counsel / Compliance',     'cost': '££'},
    'adl':      {'owner': 'General Counsel / Chief Compliance','cost': '££'},
    'rahmah':   {'owner': 'Chief People / Community Officer',  'cost': '££'},
    'mizan':    {'owner': 'COO / Chief Sustainability Officer','cost': '£££'},
    'amanah':   {'owner': 'Board Chair / Audit Committee',     'cost': '££'},
    'maslahah': {'owner': 'Chief Strategy Officer',            'cost': '££'},
    'darar':    {'owner': 'COO / Risk Officer',                'cost': '£££'},
    'shura':    {'owner': 'Chief Stakeholder Officer',         'cost': '£'},
    'akhirah':  {'owner': 'CEO / Board',                       'cost': '££'},
}

COST_FACTOR  = {'£': 1.0, '££': 1.6, '£££': 2.4, '££££': 3.5}
SEVERITY_URGENCY = {'critical': 2.4, 'high': 1.8, 'moderate': 1.3, 'low': 1.0}


def _severity(score, is_red_line):
    if is_red_line and score < 3:
        return 'critical'
    if score < 3:
        return 'critical'
    if score < 5:
        return 'high'
    if score < 6.5:
        return 'moderate'
    return 'low'


def _horizon(severity, is_red_line):
    if is_red_line or severity == 'critical':
        return '30d'
    return {'high': '90d', 'moderate': '1yr', 'low': '3yr'}[severity]


HORIZON_LABEL = {'30d': '30 days', '90d': '90 days', '1yr': '1 year', '3yr': '3 years'}
HORIZON_ORDER = ['30d', '90d', '1yr', '3yr']


def _current_scores(assessment):
    """key -> current 0–10 score for every answered question."""
    return {qs.question.key: float(qs.score) for qs in assessment.ordered_scores}


def _total_weight(assessment):
    return sum(qs.question.weight for qs in assessment.ordered_scores) or 1.0


# ── Decision Cards ──────────────────────────────────────────────────────────────

def build_decision_cards(assessment, target=DEFAULT_TARGET):
    """
    One Decision Card per question scoring below `target`, ranked by Next-Best-
    Action priority. Each card is a self-contained, executable instruction.
    """
    total_w = _total_weight(assessment)
    cards = []

    for qs in assessment.ordered_scores:
        q = qs.question
        score = float(qs.score)
        if score >= target:
            continue

        gap = round(target - score, 1)
        is_rl = q.is_red_line
        severity = _severity(score, is_rl)
        horizon = _horizon(severity, is_rl)
        meta = QUESTION_META.get(q.key, {'owner': 'Executive Sponsor', 'cost': '££'})

        # Projected contribution to the 0–100 Decision Integrity Score if the
        # question moves from `score` to `target`.
        impact_points = round(gap * q.weight / total_w * 10.0, 1)

        urgency = SEVERITY_URGENCY[severity]
        cost_factor = COST_FACTOR.get(meta['cost'], 1.6)
        priority = round(impact_points * urgency / cost_factor, 2)

        actions = list(qs.recommended_actions) or list(q.low_score_actions)

        cards.append({
            'question_key':  q.key,
            'arabic_term':   q.arabic_term,
            'title':         q.title_en,
            'core_question': q.core_question,
            'is_red_line':   is_rl,
            'current_score': round(score, 1),
            'target_score':  target,
            'gap':           gap,
            'severity':      severity,
            'detection':     (f'{q.title_en} ({q.arabic_term}) scored {score:.1f}/10, '
                              f'below the {target:.0f}/10 stewardship target'
                              + (' — RED LINE' if is_rl else '')),
            'root_cause':    qs.rationale or f'Low {q.title_en.lower()} signal in the evidence base.',
            'risk_signals':  list(qs.red_flags_triggered) or list(q.red_flags[:2]),
            'actions':       actions,
            'expected_impact_points': impact_points,
            'horizon':       horizon,
            'horizon_label': HORIZON_LABEL[horizon],
            'cost_band':     meta['cost'],
            'owner':         meta['owner'],
            'evidence_status': qs.evidence_status,
            'priority':      priority,
            'progress_metric': f'{q.title_en} score → {target:.0f}/10',
        })

    cards.sort(key=lambda c: c['priority'], reverse=True)
    return cards


def build_action_queue(assessment, target=DEFAULT_TARGET):
    """Decision Cards ranked by priority, annotated with queue rank."""
    cards = build_decision_cards(assessment, target=target)
    for i, c in enumerate(cards, start=1):
        c['rank'] = i
    return cards


# ── Roadmap Generator ───────────────────────────────────────────────────────────

def generate_roadmap(assessment, target=DEFAULT_TARGET):
    """
    Sequence cards into 30 / 90 / 365 / 1095-day buckets and project the Decision
    Integrity trajectory after each horizon (cumulative — earlier work persists).
    """
    cards = build_action_queue(assessment, target=target)
    current = _current_scores(assessment)
    base = compute_from_scores(
        current, subject_name=assessment.subject_name,
        evidence_status=assessment.evidence_status, confidence=assessment.confidence)

    buckets = {h: [] for h in HORIZON_ORDER}
    for c in cards:
        buckets[c['horizon']].append(c)

    # Cumulative projection: at each horizon, all carded questions up to and
    # including that horizon reach target.
    overlay = dict(current)
    trajectory = []
    cumulative_keys = []
    for h in HORIZON_ORDER:
        for c in buckets[h]:
            overlay[c['question_key']] = target
            cumulative_keys.append(c['question_key'])
        projected = compute_from_scores(
            overlay, subject_name=assessment.subject_name,
            evidence_status=assessment.evidence_status, confidence=assessment.confidence)
        trajectory.append({
            'horizon':       h,
            'horizon_label': HORIZON_LABEL[h],
            'card_count':    len(buckets[h]),
            'cards':         buckets[h],
            'projected_integrity': projected['overall'],
            'projected_verdict':   projected['verdict'],
            'projected_risk':      projected['risk'],
        })

    final = trajectory[-1]['projected_integrity'] if trajectory else base['overall']
    return {
        'baseline_integrity': base['overall'],
        'target_integrity':   final,
        'total_uplift':       round(final - base['overall'], 1),
        'buckets':            buckets,
        'trajectory':         trajectory,
        'card_count':         len(cards),
    }


# ── Scenario Engine + Re-scoring ────────────────────────────────────────────────

def simulate_scenario(assessment, overrides, evidence_status=None, confidence=None):
    """
    Re-score under hypothetical per-question changes.
    `overrides`: {question_key: new_score 0–10}. Returns the projected rollup
    plus the delta versus the current assessment.
    """
    scores = _current_scores(assessment)
    for k, v in (overrides or {}).items():
        try:
            scores[str(k)] = max(0.0, min(10.0, float(v)))
        except (TypeError, ValueError):
            continue
    projected = compute_from_scores(
        scores, subject_name=assessment.subject_name,
        evidence_status=evidence_status or assessment.evidence_status,
        confidence=confidence if confidence is not None else assessment.confidence)
    projected['delta'] = round(projected['overall'] - assessment.decision_integrity_score, 1)
    projected['baseline'] = round(assessment.decision_integrity_score, 1)
    return projected


def project_integrity(assessment, completed_keys, target=DEFAULT_TARGET):
    """Projected integrity if every question in `completed_keys` reaches target."""
    overrides = {k: target for k in (completed_keys or [])}
    return simulate_scenario(assessment, overrides)
