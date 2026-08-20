"""
EcoIQ Ethical Innovation Scoring Engine.

Calculates a company's EcoIQ Total Score (0-100) from six dimensions:

  Public Benefit            × 0.25
  Environmental Stewardship × 0.25
  Responsible Modernization × 0.20
  Transparent Governance    × 0.15
  Anti-Corruption           × 0.10
  Ethical Alignment         × 0.05
  — Harm Penalty

Profit Extraction Score is a standalone risk indicator only.
It does NOT contribute to the total — it warns.

Moral Labels:
  85–100  Regenerative Leader
  70–84   Responsible Builder
  60–69   Public-Benefit Oriented
  50–59   Transitional Company
  30–49   Profit-First Operator
  0–29    Extractive / Harmful
"""
from __future__ import annotations
import logging
from typing import TYPE_CHECKING

from django.db import transaction

from companies.evidence import PROVENANCE_MODELLED
from core.unknown import clamp, mean_of_known

log = logging.getLogger('companies.scoring')

if TYPE_CHECKING:
    from companies.models import CompanyProfile


# ── Pillar calculators ─────────────────────────────────────────────────────────

def _clamp(v, lo=0.0, hi=100.0) -> float | None:
    """
    Bound a known value. Unknown stays unknown.

    Delegates to core.unknown, which is the single authority since D2b. The
    behaviour is identical — parity is asserted by test across None/0/50/100 and
    out-of-range values — but there is now exactly one implementation to change.

    Was `float(v or 0)`, which had two defects in one expression:

      - None became 0 — the WORST possible score, published as though it were a
        finding. "We have no data" and "we assessed this as zero" are opposite
        statements and this collapsed them.
      - `v or 0` is falsy-triggered, so a genuine measured 0.0 was also rewritten
        to 0. Harmless by coincidence here, but the same idiom in
        financing/matching.py rewrote a real 0.0 to 50.

    Returning None makes the unknown case explicit and forces every caller to
    decide what to do with it, which is the point.
    """
    return clamp(v, lo, hi)


def _avg(*values) -> float | None:
    """
    Mean of the values that are actually known. None when none are.

    The semantics question the D-programme asked was whether a dimension with
    *some* known inputs should average what it has, or refuse. This averages
    what it has, deliberately:

      - Evidence coverage is already reported separately (companies.evidence,
        shipped in #238), so partial knowledge is expressed there rather than by
        destroying the dimension. Refusing here would throw away real
        information AND hide the partiality, which is worse on both counts.
      - Whether partial coverage is good enough to *publish* is a different
        question, owned by score eligibility (plan step D5). Answering it inside
        an averaging helper would make that decision invisible.

    What changes: the old version returned 50.0 when every input was unknown —
    inventing an average out of nothing. That case is now None.

        _avg(80, 60)        -> 70.0
        _avg(80, None)      -> 80.0   (known-only, coverage reports the gap)
        _avg(None, None)    -> None   (was 50.0)
    """
    return mean_of_known(*values)


def _pollution_to_env_base(pollution_level: str) -> float | None:
    """
    Categorical pollution level as a 0-100 base score, or None if unrecognised.

    Was `.get(pollution_level, 50.0)`. An unrecognised or missing category is
    not a medium-pollution company; it is a company whose pollution we have not
    established. A real 'medium' observation still returns 60.0 — the mapping of
    known categories is untouched.
    """
    return {'low': 85.0, 'medium': 60.0, 'high': 30.0, 'severe': 10.0}.get(
        pollution_level
    )


#: Which CompanyProfile fields each dimension reads.
#:
#: Declared next to the calculators rather than inferred at the call site,
#: because D3C-3 has to record the inputs a calculation ACTUALLY CONSUMED — and
#: a lineage assembled from a guess about the formula is worse than none.
#: tests_composite_lineage asserts this mapping against the fields each function
#: really references, by parsing them, so the two cannot drift silently.
#:
#: `pollution_level` is deliberately absent: it is a categorical, it is not a
#: MATERIAL_INPUTS metric, and no provenance row exists for it. That is a real
#: gap in the lineage and it is documented rather than papered over.
DIMENSION_INPUTS: dict[str, tuple[str, ...]] = {
    'public_benefit_score': (
        'jobs_created_score', 'regional_development_score',
        'infrastructure_contribution_score', 'national_value_score',
    ),
    'environmental_responsibility_score': (
        'waste_management_score', 'water_impact_score', 'biodiversity_impact_score',
    ),
    'modernization_score': (
        'energy_transition_score', 'digitalization_score',
        'infrastructure_upgrade_score', 'future_readiness_score',
    ),
    'transparency_anti_corruption_score': (
        'transparency_score_detail', 'audit_quality_score',
        'procurement_transparency_score',
    ),
    'anti_corruption_score': ('anti_corruption_score',),
    'ethical_alignment_score': ('controversy_risk_score', 'national_value_score'),
}

#: calculate_harm_penalty's inputs. Separate because the penalty is subtracted
#: from the composite rather than being one of the six weighted dimensions.
#:
#: Note that two of these — public_benefit_score and modernization_score — are
#: DERIVED fields, so the penalty reads outputs of the same calculation round.
#: Only the material ones are linked as lineage here; the derived-on-derived
#: edge needs the recursive case and is left to a later writer PR.
HARM_PENALTY_INPUTS: tuple[str, ...] = (
    'controversy_risk_score', 'transparency_score_detail',
)


def consumed_material_inputs(p: 'CompanyProfile') -> list[str]:
    """
    The material metrics this profile's composite would actually consume.

    "Actually" is the operative word. _avg() and _weighted() skip unknown values
    and re-normalise, so a formula that MENTIONS four inputs may consume three.
    Attaching all four as lineage would overstate what supported the number.

    Returns sorted, de-duplicated field names — national_value_score feeds two
    dimensions and must appear once.
    """
    from companies.evidence import MATERIAL_INPUTS

    material = {item.field_name for item in MATERIAL_INPUTS}
    referenced = {
        field
        for fields in DIMENSION_INPUTS.values()
        for field in fields
    } | set(HARM_PENALTY_INPUTS)

    return sorted(
        field for field in referenced & material
        if getattr(p, field, None) is not None
    )


def calculate_public_benefit(p: 'CompanyProfile') -> float | None:
    """0-100: How much the company generates tangible public benefit."""
    return _avg(
        p.jobs_created_score,
        p.regional_development_score,
        p.infrastructure_contribution_score,
        p.national_value_score,
    )


def calculate_environmental_responsibility(p: 'CompanyProfile') -> float | None:
    """0-100: Quality of environmental stewardship across all dimensions."""
    pollution_base = _pollution_to_env_base(p.pollution_level)
    return _avg(
        pollution_base,
        p.waste_management_score,
        p.water_impact_score,
        p.biodiversity_impact_score,
    )


def calculate_modernization(p: 'CompanyProfile') -> float | None:
    """0-100: Commitment to responsible modernization and future readiness."""
    return _avg(
        p.energy_transition_score,
        p.digitalization_score,
        p.infrastructure_upgrade_score,
        p.future_readiness_score,
    )


def calculate_transparency(p: 'CompanyProfile') -> float | None:
    """0-100: Governance quality and transparency of operations."""
    # Weighted, so an unknown input cannot simply be dropped the way _avg drops
    # one: the remaining weights would no longer sum to 1 and the dimension
    # would be silently rescaled. Re-normalise across the weights that are
    # actually known, and return None when none are.
    parts = [
        (_clamp(p.transparency_score_detail), 0.40),
        (_clamp(p.audit_quality_score), 0.35),
        (_clamp(p.procurement_transparency_score), 0.25),
    ]
    known = [(v, w) for v, w in parts if v is not None]
    if not known:
        return None
    total_weight = sum(w for _, w in known)
    return sum(v * w for v, w in known) / total_weight


def calculate_anti_corruption(p: 'CompanyProfile') -> float | None:
    """0-100: Anti-corruption practices and ethical procurement."""
    return _clamp(p.anti_corruption_score)


def calculate_ethical_alignment(p: 'CompanyProfile') -> float | None:
    """
    0-100: Alignment with long-term ethical value creation.
    High controversy risk and low national value reduce this score.
    """
    # 100 - None is a TypeError, and "unknown controversy" is not "no
    # controversy" — so the inverted term stays unknown and _avg drops it.
    controversy = _clamp(p.controversy_risk_score)
    inv_controversy = None if controversy is None else _clamp(100.0 - controversy)
    return _avg(inv_controversy, p.national_value_score)


# ── Harm penalty ───────────────────────────────────────────────────────────────

def calculate_harm_penalty(p: 'CompanyProfile') -> float:
    """
    Deduction applied when a company causes significant harm
    without adequate mitigation or transparency.
    """
    penalty = 0.0

    # Pollution severity
    if p.pollution_level == 'severe':
        penalty += 15.0
    elif p.pollution_level == 'high':
        penalty += 8.0

    # Every trigger below is guarded on the value being KNOWN.
    #
    # This is the most consequential part of the change. Previously an unknown
    # score arrived as 0, so `_clamp(x) < 30` was True for a company we had no
    # transparency data about at all — and the company was penalised for it.
    # EcoIQ was manufacturing harm findings out of missing data.
    #
    # Absence of evidence is not evidence of harm. An unknown input now fires
    # nothing.
    controversy = _clamp(p.controversy_risk_score)
    transparency = _clamp(p.transparency_score_detail)
    extraction = _clamp(p.profit_extraction_score)
    public_benefit = _clamp(p.public_benefit_score)
    modernization = _clamp(p.modernization_score)

    # High controversy without remediation
    if controversy is not None and controversy >= 70:
        penalty += 5.0

    # Opacity — very low transparency
    if transparency is not None and transparency < 30:
        penalty += 5.0

    # Profit extraction without public benefit
    if (
        extraction is not None and extraction > 75
        and public_benefit is not None and public_benefit < 50
    ):
        penalty += 5.0

    # Severe pollution + no modernization = high transition need penalty
    if (
        p.pollution_level in ('high', 'severe')
        and modernization is not None and modernization < 40
    ):
        penalty += 3.0

    return min(penalty, 30.0)  # cap penalty at 30 points


# ── Main scoring entry point ───────────────────────────────────────────────────

def compute_ecoiq_profile_score(p: 'CompanyProfile') -> dict:
    """
    Compute all six EcoIQ dimensions + penalty + total score.
    Returns a dict of results — does NOT save to the model.
    Caller is responsible for calling profile.save() after applying results.
    """
    pb  = calculate_public_benefit(p)
    env = calculate_environmental_responsibility(p)
    mod = calculate_modernization(p)
    trn = calculate_transparency(p)
    ac  = calculate_anti_corruption(p)
    eth = calculate_ethical_alignment(p)

    dimensions = [
        ('public_benefit_score', pb, 0.25),
        ('environmental_responsibility_score', env, 0.25),
        ('modernization_score', mod, 0.20),
        ('transparency_anti_corruption_score', trn, 0.15),
        ('anti_corruption_score', ac, 0.10),
        ('ethical_alignment_score', eth, 0.05),
    ]
    unknown = [name for name, value, _ in dimensions if value is None]

    # A composite is only defensible when every dimension it claims to weigh is
    # known. Re-normalising across the survivors — the trick used one level down
    # in calculate_transparency, where the sub-inputs measure one thing — is not
    # defensible here: the six dimensions measure different things, so dropping
    # one and rescaling silently redefines what the score means and still
    # presents it as a complete assessment.
    #
    # So the total is None when anything material is missing, and the caller is
    # told which. Whether a PARTIAL composite should ever be published, and
    # against what coverage threshold, is score eligibility — plan step D5.
    if unknown:
        base = total = label = None
        penalty = calculate_harm_penalty(p)
    else:
        base = sum(value * weight for _, value, weight in dimensions)
        penalty = calculate_harm_penalty(p)
        total = round(_clamp(base - penalty), 1)
        label = get_moral_label(total)

    def _round(value):
        return None if value is None else round(value, 1)

    return {
        'public_benefit_score':              _round(pb),
        'environmental_responsibility_score': _round(env),
        'modernization_score':               _round(mod),
        'transparency_anti_corruption_score':_round(trn),
        'anti_corruption_score':             _round(ac),
        'ethical_alignment_score':           _round(eth),
        'ecoiq_total_score':                 total,
        'moral_label':                       label,
        'ecoiq_category':                    None if total is None else get_ecoiq_category(total),
        'harm_penalty':                      round(penalty, 1),
        # D3C-3 — the inputs this run actually read, for provenance lineage.
        '_consumed_inputs':                  consumed_material_inputs(p),
        '_base_score':                       _round(base),
        # Named so a caller cannot mistake an absent score for a computed one.
        '_unknown_dimensions':               unknown,
        '_is_complete':                      not unknown,
    }


#: STEP 2 — a stable, human-readable calculation identity.
#:
#: The scoring engine had no version constant; this is the smallest explicit,
#: code-owned one. Not a git SHA: a SHA changes on every unrelated commit, so it
#: cannot answer "did the formula change?" — which is the only question a
#: version on a MODELLED row exists to answer.
#:
#: Bump COMPOSITE_VERSION when the formula, weights or dimension set change.
COMPOSITE_METHOD = 'ecoiq-company-composite'
COMPOSITE_VERSION = '1'

#: The registry key this function produces. Confirmed against
#: companies.metric_registry, not assumed.
COMPOSITE_METRIC_KEY = 'company.ecoiq_total'


def recalculate_and_save(profile: 'CompanyProfile',
                         record_provenance: bool = True) -> 'CompanyProfile':
    """
    Compute EcoIQ scores, apply to profile fields, save, and record lineage.

    Returns the updated profile instance, with a transient
    `provenance_status` attribute describing what was recorded:

        'recorded'      a MODELLED row with complete input lineage
        'unchanged'     nothing semantically changed; the existing row stands
        'incomplete'    an input it consumed has no provenance row, so no
                        derived row was created — see below
        'no_composite'  the composite is None, so there is nothing to attest
        'skipped'       record_provenance=False

    THE INCOMPLETE CASE, which is the one that matters today.

    D3B has not been applied in production, so a profile can hold material
    values with no provenance rows at all. When that happens this function
    records NO derived provenance rather than a row with an empty input list.
    An empty list would read as "this composite rests on nothing", which is
    indistinguishable from "we did not record what it rests on" — and the
    second is the truth. The schema cannot express partial lineage, so the
    honest option is to abstain (option A of the D3C-3 brief).

    It also does NOT create material provenance to fill the gap. Inventing a
    LEGACY_UNKNOWN_PROVENANCE row here would be this function labelling history
    it did not witness. D3B owns historical labelling, deliberately, because it
    reports what it did and can be rolled back by writer.

    The SCORE is written either way. Provenance completeness does not gate the
    calculation, and the public surface is gated on evidence (#239/#240) rather
    than on these columns' face value.
    """
    results = compute_ecoiq_profile_score(profile)

    # A computed value of None means "not established". These columns are still
    # NOT NULL with default=50.0 — making them nullable is plan step D4 and
    # deliberately not part of this change — so an unknown result cannot be
    # written at all: assigning None would raise IntegrityError on save.
    #
    # So an unknown dimension is SKIPPED rather than written. The previously
    # stored value stays where it is, untouched and unrefreshed, which is the
    # honest option available before D4: this function will not overwrite a
    # column with a number it did not compute, and will not pretend it can store
    # "unknown" in a column that has no way to hold it.
    #
    # Nothing here reaches the public surface unfiltered — #239 gates the web
    # and #240 the API on evidence, both of which read companies.evidence rather
    # than these columns' face value.
    assignable = {
        'public_benefit_score':               results['public_benefit_score'],
        'environmental_responsibility_score': results['environmental_responsibility_score'],
        'modernization_score':                results['modernization_score'],
        'transparency_anti_corruption_score': results['transparency_anti_corruption_score'],
        'ethical_alignment_score':            results['ethical_alignment_score'],
        'harm_penalty':                       results['harm_penalty'],
        'ecoiq_total_score':                  results['ecoiq_total_score'],
        'moral_label':                        results['moral_label'],
        'ecoiq_category':                     results['ecoiq_category'],
    }
    written = [name for name, value in assignable.items() if value is not None]
    for name in written:
        setattr(profile, name, assignable[name])

    # STEP 6 — the value and its lineage commit together or not at all.
    #
    # This function owns the transaction, unlike record_seed_write() where the
    # caller does: here the same call writes both the value and the provenance,
    # so the boundary belongs around both. Callers vary — three seed commands,
    # the admin action, the ingestion pipeline and a Celery task, some already
    # inside a transaction and some not — and an inner atomic() joins an outer
    # one as a savepoint, so this is correct in either context rather than
    # creating a second inconsistent layer.
    with transaction.atomic():
        profile.save(update_fields=written + ['updated_at'])
        profile.provenance_status = (
            _record_composite_provenance(profile, results)
            if record_provenance else 'skipped'
        )
    return profile


def _record_composite_provenance(profile, results) -> str:
    """
    Record MODELLED provenance for the composite, or explain why it was not.

    Called inside recalculate_and_save's transaction, so raising here rolls the
    score write back with it.
    """
    from companies import provenance as prov

    if results['ecoiq_total_score'] is None:
        # No composite was produced, so there is nothing to attest to.
        return 'no_composite'

    consumed = results.get('_consumed_inputs', [])
    if not consumed:
        return 'incomplete'

    current_rows = prov.current_map(profile)
    missing = [key for key in consumed if key not in current_rows]
    if missing:
        log.debug(
            'Composite provenance not recorded for %s — consumed inputs without '
            'provenance: %s. The score was still written.',
            profile, ', '.join(missing),
        )
        return 'incomplete'

    input_rows = [current_rows[key] for key in consumed]

    # STEP 7 — identity is (origin, methodology, version, exact input rows).
    #
    # NOT the output value, deliberately. Two reasons:
    #
    #   1. It cannot be compared. `existing.value` resolves live through the
    #      registry, and by this point profile.save() has already written the
    #      new number — so the comparison would always find them equal and
    #      never fire. A check that cannot fail is worse than no check.
    #
    #   2. It should not be compared. The formula is deterministic, so the
    #      same input ROWS under the same version give the same answer. If the
    #      number moved while the input rows did not, a material VALUE changed
    #      without anyone recording a provenance event for it — a gap in the
    #      writer that wrote it, not a new lineage claim for this one to make.
    #      Value history is CompanyScoreSnapshot's job; this records lineage.
    existing = prov.current(profile, COMPOSITE_METRIC_KEY)
    if (existing is not None
            and existing.origin == PROVENANCE_MODELLED
            and existing.methodology == COMPOSITE_METHOD
            and existing.calculation_version == COMPOSITE_VERSION
            and set(existing.inputs.values_list('pk', flat=True))
                == {row.pk for row in input_rows}):
        return 'unchanged'

    prov.record_derived(
        profile, COMPOSITE_METRIC_KEY,
        writer='companies.scoring.recalculate_and_save',
        methodology=COMPOSITE_METHOD,
        calculation_version=COMPOSITE_VERSION,
        inputs=input_rows,
    )
    return 'recorded'


# ── Label helpers ──────────────────────────────────────────────────────────────

def get_moral_label(score: float) -> str:
    """Return canonical moral_label key for storage."""
    if score >= 85: return 'regenerative_leader'
    if score >= 70: return 'responsible_builder'
    if score >= 60: return 'public_benefit_oriented'
    if score >= 50: return 'transitional_company'
    if score >= 30: return 'profit_first_operator'
    return 'extractive_harmful'


def get_moral_label_display(score: float) -> str:
    """Return human-readable moral label."""
    labels = {
        'regenerative_leader':    'Regenerative Leader',
        'responsible_builder':    'Responsible Builder',
        'public_benefit_oriented':'Public-Benefit Oriented',
        'transitional_company':   'Transitional Company',
        'profit_first_operator':  'Profit-First Operator',
        'extractive_harmful':     'Extractive / Harmful',
    }
    return labels.get(get_moral_label(score), 'Unknown')


def get_ecoiq_category(score: float) -> str:
    if score >= 85: return 'Exceptional'
    if score >= 70: return 'Strong'
    if score >= 60: return 'Moderate'
    if score >= 50: return 'Fair'
    if score >= 30: return 'Below Average'
    return 'Critical'


def get_moral_label_color(label_key: str) -> str:
    colours = {
        'regenerative_leader':    '#00e89a',
        'responsible_builder':    '#58a6ff',
        'public_benefit_oriented':'#8b5cf6',
        'transitional_company':   '#f4a261',
        'profit_first_operator':  '#e63946',
        'extractive_harmful':     '#b91c1c',
    }
    return colours.get(label_key, '#888')


# ── Path-to-100 advisor ────────────────────────────────────────────────────────

def get_path_to_100_actions(profile: 'CompanyProfile') -> list[dict]:
    """
    Return a prioritised list of improvement actions that would most
    increase EcoIQ score. Used for the 'Path to 100%' section.
    """
    actions = []

    def _add(title, description, potential_gain, pillar):
        actions.append({
            'title': title,
            'description': description,
            'potential_gain': potential_gain,
            'pillar': pillar,
        })

    if profile.pollution_level in ('high', 'severe'):
        _add(
            'Reduce Pollution Intensity',
            'Invest in filtration, emissions controls, and cleaner processes '
            'to move from high/severe to medium pollution classification.',
            10 if profile.pollution_level == 'severe' else 6,
            'Environmental Stewardship',
        )

    if (value := _clamp(profile.transparency_score_detail)) is not None and value < 60:
        _add(
            'Improve Public Reporting',
            'Publish an annual sustainability/ESG report aligned with GRI or CDP '
            'standards to boost transparency and investor confidence.',
            7, 'Transparent Governance',
        )

    if (value := _clamp(profile.energy_transition_score)) is not None and value < 50:
        _add(
            'Accelerate Energy Transition',
            'Develop a renewable energy integration plan and set measurable '
            'interim targets for clean energy share.',
            6, 'Responsible Modernization',
        )

    if (value := _clamp(profile.anti_corruption_score)) is not None and value < 60:
        _add(
            'Strengthen Anti-Corruption Controls',
            'Implement ISO 37001 anti-bribery management system and independent '
            'procurement audits.',
            5, 'Anti-Corruption',
        )

    if (value := _clamp(profile.jobs_created_score)) is not None and value < 60:
        _add(
            'Invest in Quality Employment',
            'Create formal workforce development programmes and community '
            'hiring initiatives to increase regional employment quality.',
            4, 'Public Benefit',
        )

    if (value := _clamp(profile.future_readiness_score)) is not None and value < 50:
        _add(
            'Build Future Readiness',
            'Commission a technology modernization audit and develop a '
            'five-year digital transformation roadmap.',
            4, 'Responsible Modernization',
        )

    if (value := _clamp(profile.biodiversity_impact_score)) is not None and value < 50:
        _add(
            'Address Biodiversity Impact',
            'Conduct a biodiversity impact assessment and commit to '
            'nature-positive operational practices.',
            3, 'Environmental Stewardship',
        )

    # Sort by highest potential gain
    actions.sort(key=lambda x: x['potential_gain'], reverse=True)
    return actions[:7]
