"""
platform_registry/evaluation.py — how a module's claims get measured.

THE RULE THIS ENCODES
---------------------
NOT YET MEASURED is a valid, honest result. It must never become 0%.

Those are different statements: 0% means "we measured and it failed", NOT YET
MEASURED means "nobody has looked". Rendering the second as the first is the
same defect as a substituted score, applied to the thing that decides whether a
module may be called production.

WHAT IS DELIBERATELY NOT HERE
-----------------------------
An evaluation harness that runs LLM agents against a labelled set. That needs a
labelled set, and EcoIQ does not have one. Building the harness first and
filling it with generated examples would produce impressive numbers measuring
nothing — which is worse than the absence, because the absence is legible.

So this defines the SCHEMA, records what has genuinely been measured, and
leaves the rest explicitly unmeasured.
"""
from __future__ import annotations

from dataclasses import dataclass, field

#: The metric vocabulary. Not every metric applies to every module: citation
#: precision is meaningless for a scoring formula, and a formula's determinism
#: is meaningless for a generative agent.
CITATION_PRECISION = 'citation_precision'
EVIDENCE_GROUNDEDNESS = 'evidence_groundedness'
UNSUPPORTED_CLAIM_RATE = 'unsupported_claim_rate'
TASK_SUCCESS = 'task_success'
HUMAN_OVERRIDE_RATE = 'human_override_rate'
LATENCY = 'latency'
COST = 'cost'
PREDICTION_ERROR = 'prediction_error'
DETERMINISM = 'determinism'

NOT_MEASURED = 'NOT YET MEASURED'


@dataclass(frozen=True)
class Measurement:
    """
    One measured metric.

    `value` is None when unmeasured, and `display` renders that as the words
    NOT YET MEASURED. There is deliberately no code path that turns an
    unmeasured metric into a number.
    """
    metric: str
    value: float | None
    unit: str = ''
    #: How it was measured, specifically enough to repeat. A number without a
    #: method is not a measurement.
    method: str = ''
    #: How many items the measurement covers. A metric over three examples is
    #: not the same claim as one over three thousand.
    sample_size: int | None = None

    @property
    def measured(self) -> bool:
        return self.value is not None

    @property
    def display(self) -> str:
        if self.value is None:
            return NOT_MEASURED
        rendered = f'{self.value:.3g}'
        return f'{rendered}{self.unit}' if self.unit else rendered


@dataclass
class Evaluation:
    """
    What is known about one module's behaviour.

    An Evaluation with no measurements is the normal state, and says so.
    """
    module_key: str
    measurements: list = field(default_factory=list)
    notes: str = ''

    @property
    def is_measured(self) -> bool:
        return any(m.measured for m in self.measurements)

    @property
    def summary(self) -> str:
        if not self.is_measured:
            return NOT_MEASURED
        return ', '.join(
            f'{m.metric} {m.display}' for m in self.measurements if m.measured)

    def get(self, metric: str) -> Measurement:
        for measurement in self.measurements:
            if measurement.metric == metric:
                return measurement
        return Measurement(metric=metric, value=None)


def evaluate_ml_score(profiles=None) -> Evaluation:
    """
    A REAL measurement: how far ml.score sits from the composite it predicts.

    This is feasible today because both numbers exist for the same companies
    and the model artefact is committed. It is a genuine regression error over
    real data, not a proxy.

    What it does NOT establish: that either number is correct. It measures
    agreement between a model and the formula it was trained to imitate, which
    is a real property worth knowing and is not accuracy against ground truth.
    Saying so is the difference between an evaluation and a marketing number.

    Returns an Evaluation whose measurements are unmeasured when there is
    nothing to compare — never a zero.
    """
    from companies.models import CompanyProfile
    from core.unknown import known

    if profiles is None:
        profiles = CompanyProfile.objects.select_related('company')

    errors = []
    for profile in profiles:
        company = getattr(profile, 'company', None)
        predicted = known(getattr(company, 'ml_score', None)) if company else None
        actual = known(profile.ecoiq_total_score)
        if predicted is not None and actual is not None:
            errors.append(abs(predicted - actual))

    if not errors:
        return Evaluation(
            module_key='ml.score',
            measurements=[Measurement(PREDICTION_ERROR, None, 'points')],
            notes='No company holds both an ml_score and a composite, so there '
                  'is nothing to compare. Unmeasured, not zero error.',
        )

    mean_absolute_error = sum(errors) / len(errors)
    return Evaluation(
        module_key='ml.score',
        measurements=[
            Measurement(
                PREDICTION_ERROR, mean_absolute_error, ' points',
                method='Mean absolute difference between league.Company.ml_score '
                       'and CompanyProfile.ecoiq_total_score, over companies '
                       'holding both.',
                sample_size=len(errors),
            ),
        ],
        notes='Measures agreement between the model and the formula it imitates. '
              'It is NOT accuracy against ground truth, and must not be '
              'presented as such.',
    )


def evaluate_all() -> dict:
    """
    Every module's evaluation state.

    Deterministic engines carry a `determinism` measurement rather than an
    accuracy one: the honest claim about a formula is that it produces the same
    answer from the same inputs and is pinned by tests — not that it is
    "accurate", which would need a ground truth the domain does not have.

    Everything else is NOT YET MEASURED, which is the truthful answer.
    """
    from platform_registry.agents import AGENT, MODULES, PRODUCTION

    results = {}
    for module in MODULES:
        if module.key == 'ml.score':
            results[module.key] = evaluate_ml_score()
        # Keyed off STATUS, not a substring of the evaluation text. A string
        # search would silently reclassify a module the day someone reworded
        # its description.
        elif module.status == PRODUCTION and module.kind != AGENT:
            results[module.key] = Evaluation(
                module_key=module.key,
                measurements=[
                    Measurement(DETERMINISM, 1.0, '',
                                method='Same inputs produce the same output; '
                                       'behaviour pinned by the test suite.'),
                ],
                notes='Determinism is the honest claim about a formula. '
                      'Accuracy would require a ground truth this domain does '
                      'not have.',
            )
        else:
            metrics = ([CITATION_PRECISION, EVIDENCE_GROUNDEDNESS,
                        UNSUPPORTED_CLAIM_RATE, TASK_SUCCESS]
                       if module.kind == AGENT else [TASK_SUCCESS])
            results[module.key] = Evaluation(
                module_key=module.key,
                measurements=[Measurement(m, None) for m in metrics],
                notes='No labelled evaluation set exists for this module. '
                      'Building a harness and filling it with generated '
                      'examples would produce numbers measuring nothing.',
            )
    return results
