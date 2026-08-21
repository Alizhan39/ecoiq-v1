"""
platform_registry/agents.py — the canonical, code-owned module registry.

ONE source of truth for what EcoIQ actually has. The frontend, the API, the
README and every counter read from here. Nothing may hard-code a module count
or a status label anywhere else.

WHY THIS EXISTS
---------------
The product claimed "33 operational agents". The audit found where that number
comes from: `ai_agent_council.agents.OPERATIONAL_AGENTS`, 33 entries labelled
"Operational Training Pack Ready".

That label means a folder exists containing ten markdown files. `ai_agents/`
holds **298 .md files, 33 .json files and zero .py files**. The thirty-three
"operational agents" are training-pack SPECIFICATIONS — documents describing
agents that could be built — not agents that run.

They are not deleted here. They are real design artefacts and they are
genuinely useful. They are simply not running software, and the registry says
which is which.

THE STATUS RULES, applied literally
-----------------------------------
PRODUCTION    on an active production path, meaningful tests, dependencies
              available, not a placeholder, AND evaluation evidence sufficient
              to support the claim.
BETA          functional, real code, meaningful tests, evaluation incomplete.
EXPERIMENTAL  a working experiment. No enterprise-readiness claim.
PLANNED       conceptual. Not functional.
SPECIFICATION a written design with no implementation. (Added here because the
              four statuses above cannot honestly describe a folder of
              markdown, and PLANNED would overstate it — these are specified in
              detail, which is more than "planned" and far less than "built".)

THE RULE THAT DECIDES MOST OF THIS
----------------------------------
No LLM-backed module in EcoIQ has a measured evaluation. Per the standing rule,
an unevaluated agent may not be presented as proven PRODUCTION unless another
strong basis exists — and for a generative agent, there is no such basis. Its
output quality is exactly the thing evaluation measures.

So **EcoIQ has no PRODUCTION AI agents today.** It has production DETERMINISTIC
ENGINES, whose basis is different in kind: they are formulas, not generators,
their behaviour is pinned by an extensive test suite, and they carry provenance
for every value they write. That is a strong basis, and it is not the same
claim as "our AI is validated".

Stating that plainly is the point of this registry.
"""
from __future__ import annotations

from dataclasses import dataclass, field

PRODUCTION = 'PRODUCTION'
BETA = 'BETA'
EXPERIMENTAL = 'EXPERIMENTAL'
PLANNED = 'PLANNED'
SPECIFICATION = 'SPECIFICATION'

STATUS_ORDER = (PRODUCTION, BETA, EXPERIMENTAL, PLANNED, SPECIFICATION)

#: What a module IS. A scoring formula and a generative agent are different
#: things, and calling both "an agent" is itself a product-truth problem.
ENGINE = 'DETERMINISTIC_ENGINE'
AGENT = 'AI_AGENT'
PIPELINE = 'PIPELINE'
INFRASTRUCTURE = 'INFRASTRUCTURE'

#: The only honest evaluation state for anything not yet measured.
NOT_MEASURED = 'NOT YET MEASURED'


@dataclass(frozen=True)
class Module:
    key: str
    name: str
    kind: str
    status: str
    location: str
    entry_point: str
    #: Who calls it in production. Empty means nothing does.
    consumers: tuple = ()
    #: What it needs to run. A module whose dependency is absent cannot be
    #: PRODUCTION however good its code is.
    dependencies: tuple = ()
    evaluation: str = NOT_MEASURED
    #: Why this status, in one sentence. Required — a status without a stated
    #: basis is an assertion.
    basis: str = ''
    notes: str = ''

    @property
    def is_public_facing(self) -> bool:
        return self.status in (PRODUCTION, BETA)


#: Deterministic analytical engines on the live evidence path.
#:
#: PRODUCTION on a basis that is NOT evaluation: these are formulas whose
#: behaviour is pinned by the test suite and whose every written value carries
#: provenance. That is a different and stronger claim than "validated AI".
_ENGINES = (
    Module(
        key='scoring.composite', name='EcoIQ Composite Scoring',
        kind=ENGINE, status=PRODUCTION,
        location='companies/scoring.py',
        entry_point='companies.scoring.recalculate_and_save',
        consumers=('ingestion.pipeline', 'companies.admin', 'seed commands'),
        dependencies=('PostgreSQL',),
        evaluation='Deterministic; behaviour pinned by the provenance test suite.',
        basis='Runs on every profile write, records MODELLED provenance with '
              'full lineage, and refuses to produce a composite when any '
              'dimension is unknown.',
    ),
    Module(
        key='evidence.coverage', name='Evidence Coverage',
        kind=INFRASTRUCTURE, status=PRODUCTION,
        location='companies/evidence.py',
        entry_point='companies.evidence.coverage_for',
        consumers=('api.v2_serializers', 'companies.eligibility', 'companies.views'),
        dependencies=('PostgreSQL',),
        evaluation='Deterministic; computed from recorded provenance rows.',
        basis='Weighted from the scoring engine own weights; excludes seeded '
              'and legacy provenance by construction.',
    ),
    Module(
        key='evidence.confidence', name='Evidence Confidence',
        kind=INFRASTRUCTURE, status=PRODUCTION,
        location='companies/confidence.py',
        entry_point='companies.confidence.confidence_for',
        consumers=('api.v2_serializers', 'companies.eligibility'),
        dependencies=('PostgreSQL',),
        evaluation='Deterministic; categorical bands over recorded provenance.',
        basis='Independent of coverage, returns a label rather than a '
              'fabricated percentage.',
    ),
    Module(
        key='evidence.eligibility', name='Publication Eligibility',
        kind=INFRASTRUCTURE, status=PRODUCTION,
        location='companies/eligibility.py',
        entry_point='companies.eligibility.decide',
        consumers=('companies.evidence', 'companies.views', 'api.v2_serializers'),
        dependencies=('PostgreSQL',),
        evaluation='Deterministic; single authority for publication.',
        basis='The one place that decides publication; fails closed on every '
              'path.',
    ),
    Module(
        key='evidence.provenance', name='Metric Provenance Store',
        kind=INFRASTRUCTURE, status=PRODUCTION,
        location='companies/provenance.py',
        entry_point='companies.provenance.record',
        consumers=('every metric writer',),
        dependencies=('PostgreSQL',),
        evaluation='Deterministic; append-only with transitive defensibility.',
        basis='Eleven writer families record through it; lineage is pinned to '
              'rows, not keys.',
    ),
    Module(
        key='ethics.scoring', name='Ethical Intelligence (NEI / TSS / RVI)',
        kind=ENGINE, status=PRODUCTION,
        location='ethics/scoring.py',
        entry_point='ethics.scoring.compute_and_save',
        consumers=('ingestion.pipeline', 'api.views'),
        dependencies=('PostgreSQL',),
        evaluation='Deterministic; unknown propagation covered by tests.',
        basis='Records MODELLED lineage for each of its three outputs.',
    ),
    Module(
        key='financing.readiness', name='Financing Readiness',
        kind=ENGINE, status=PRODUCTION,
        location='financing/matching.py',
        entry_point='financing.matching.compute_and_save',
        consumers=('companies.views',),
        dependencies=('PostgreSQL',),
        evaluation='Deterministic; refuses to estimate without inputs.',
        basis='Eligibility-gated at the public surface; records lineage.',
    ),
    Module(
        key='qdf.decision_integrity', name='QDF Decision Integrity',
        kind=ENGINE, status=PRODUCTION,
        location='qdf/scoring.py',
        entry_point='qdf.scoring.compute_and_save',
        consumers=('qdf.views',),
        dependencies=('PostgreSQL',),
        evaluation='Deterministic.',
        basis='Records lineage over fifteen declared inputs.',
    ),
    Module(
        key='mizan.score', name='Mizan Balance Assessment',
        kind=ENGINE, status=BETA,
        location='mizan/scoring.py',
        entry_point='mizan.scoring.score_and_record',
        consumers=(),
        dependencies=('PostgreSQL',),
        evaluation=NOT_MEASURED,
        basis='Real code with lineage and a full test suite, but the recording '
              'entry point has no production caller yet — mizan/views.py still '
              'calls the pure function.',
        notes='Ephemeral metric: the provenance row carries the value.',
    ),
)

#: Machine-learning modules. Statistical, not generative — but their output
#: quality IS the thing evaluation would measure, and none has been measured.
_ML = (
    Module(
        key='ml.score', name='ML Company Score (GBR)',
        kind=ENGINE, status=BETA,
        location='ml/scoring_model.py',
        entry_point='ml.scoring_model.EcoIQScoringModel.predict_company',
        consumers=('companies.views',),
        dependencies=('scikit-learn', 'committed model artefact'),
        evaluation=NOT_MEASURED,
        basis='Trained artefact is committed and the model refuses to predict '
              'on imputed inputs, but no accuracy evaluation has been run.',
        notes='15 of 29 features carry provenance; the rest do not.',
    ),
    Module(
        key='ml.predicted_12m', name='12-Month Score Forecast',
        kind=ENGINE, status=EXPERIMENTAL,
        location='ml/prediction.py',
        entry_point='ml.prediction.predict_12m',
        consumers=('train_ml_models command',),
        dependencies=('numpy', 'ScoreHistory rows'),
        evaluation=NOT_MEASURED,
        basis='An OLS trend over score history with no backtest; its lineage '
              'is admittedly partial.',
    ),
    Module(
        key='greenwashing.risk', name='Greenwashing Risk Assessment',
        kind=ENGINE, status=BETA,
        location='ml/ethics/greenwashing_risk.py',
        entry_point='ml.ethics.greenwashing_risk.assess_and_record',
        consumers=('api.views', 'mizan.scoring (advisory only)'),
        dependencies=('PostgreSQL',),
        evaluation=NOT_MEASURED,
        basis='Deterministic and careful about insufficient evidence, but no '
              'validation against known greenwashing cases.',
    ),
    Module(
        key='ml.responsible_finance', name='Responsible Finance Assessment',
        kind=ENGINE, status=BETA,
        location='ml/responsible_finance.py',
        entry_point='ml.responsible_finance.compute_and_record',
        consumers=('api.views',),
        dependencies=('PostgreSQL',),
        evaluation=NOT_MEASURED,
        basis='Live API consumer and full lineage; framework not externally '
              'validated.',
    ),
    Module(
        key='ml.cluster', name='Peer Cluster Assignment',
        kind=ENGINE, status=EXPERIMENTAL,
        location='ml/clustering.py',
        entry_point='ml.clustering.CompanyClusterer.assign_company',
        consumers=('companies.views',),
        dependencies=('scikit-learn', 'committed model artefact'),
        evaluation=NOT_MEASURED,
        basis='K-Means over the same feature set; output is population-relative '
              'and carries no provenance.',
    ),
    Module(
        key='ml.anomaly', name='Anomaly Detection',
        kind=ENGINE, status=EXPERIMENTAL,
        location='ml/anomaly_detection.py',
        entry_point='ml.anomaly_detection.AnomalyDetector.score_company',
        consumers=('companies.views',),
        dependencies=('scikit-learn', 'committed model artefact'),
        evaluation=NOT_MEASURED,
        basis='IsolationForest output with no provenance and no validation.',
    ),
)

#: LLM-backed modules. NONE is PRODUCTION, and none can be until evaluated:
#: for a generative system, output quality is exactly what evaluation measures,
#: so there is no "other strong basis" available.
_AI = (
    Module(
        key='ingestion.pipeline', name='Evidence Ingestion Pipeline',
        kind=PIPELINE, status=BETA,
        location='ingestion/pipeline.py',
        entry_point='ingestion.pipeline.IngestionPipeline.run',
        consumers=('ingestion.views', 'management commands'),
        dependencies=('ANTHROPIC_API_KEY', 'outbound HTTP', 'PostgreSQL'),
        evaluation=NOT_MEASURED,
        basis='Runs end to end and records INFERRED provenance with evidence '
              'links, but extraction accuracy has never been measured.',
        notes='Fans five LLM-assessed signals across sixteen material fields.',
    ),
    Module(
        key='core.ai', name='Core AI Client',
        kind=INFRASTRUCTURE, status=BETA,
        location='core/ai.py',
        entry_point='core.ai',
        consumers=('several apps',),
        dependencies=('ANTHROPIC_API_KEY',),
        evaluation=NOT_MEASURED,
        basis='A shared client wrapper, not an agent; quality depends entirely '
              'on its callers.',
    ),
    Module(
        key='ai_gateway', name='Multi-Provider AI Gateway',
        kind=INFRASTRUCTURE, status=BETA,
        location='ai_gateway/',
        entry_point='ai_gateway.registry',
        consumers=('ai_gateway.views',),
        dependencies=('provider API keys',),
        evaluation=NOT_MEASURED,
        basis='Routes to several providers with tests, but provider selection '
              'quality is unmeasured.',
    ),
    Module(
        key='intelligence.compute', name='Intelligence Compute',
        kind=AGENT, status=EXPERIMENTAL,
        location='intelligence/compute.py',
        entry_point='intelligence.compute',
        consumers=('intelligence.views',),
        dependencies=('ANTHROPIC_API_KEY', 'PostgreSQL'),
        evaluation=NOT_MEASURED,
        basis='Real code with no test module of its own.',
    ),
    Module(
        key='audit.ai_engine', name='ESG Document Audit Engine',
        kind=AGENT, status=EXPERIMENTAL,
        location='audit/ai_engine.py',
        entry_point='audit.ai_engine',
        consumers=('audit.views',),
        dependencies=('ANTHROPIC_API_KEY',),
        evaluation=NOT_MEASURED,
        basis='Functional document analysis; no grounding or citation '
              'measurement.',
    ),
    Module(
        key='transition.engine', name='Transition Roadmap Engine',
        kind=AGENT, status=EXPERIMENTAL,
        location='transition/engine.py',
        entry_point='transition.engine',
        consumers=('transition.views',),
        dependencies=('ANTHROPIC_API_KEY',),
        evaluation=NOT_MEASURED,
        basis='Generates roadmaps with no test module and no evaluation.',
    ),
    Module(
        key='investor_portfolio.briefing', name='Investor Briefing',
        kind=AGENT, status=EXPERIMENTAL,
        location='investor_portfolio/briefing.py',
        entry_point='investor_portfolio.briefing',
        consumers=('investor_portfolio.views',),
        dependencies=('ANTHROPIC_API_KEY',),
        evaluation=NOT_MEASURED,
        basis='Generative output presented to investors, entirely unevaluated.',
    ),
    Module(
        key='companies.ai_helpers', name='Company Narrative Helpers',
        kind=AGENT, status=EXPERIMENTAL,
        location='companies/ai_helpers.py',
        entry_point='companies.ai_helpers',
        consumers=('companies.views',),
        dependencies=('ANTHROPIC_API_KEY',),
        evaluation=NOT_MEASURED,
        basis='Prompt construction is now null-safe, but output is unmeasured.',
    ),
    Module(
        key='good_agents.orchestrator', name='Good Agents Orchestrator',
        kind=AGENT, status=EXPERIMENTAL,
        location='good_agents/services/orchestrator.py',
        entry_point='good_agents.services.orchestrator',
        consumers=('good_agents.views',),
        dependencies=('PostgreSQL',),
        evaluation=NOT_MEASURED,
        basis='A lab surface with tests but no production consumer.',
    ),
    Module(
        key='decision_studio.engine', name='Decision Studio',
        kind=AGENT, status=EXPERIMENTAL,
        location='decision_studio/services/decision_engine.py',
        entry_point='decision_studio.services.decision_engine',
        consumers=('decision_studio.views',),
        dependencies=('PostgreSQL',),
        evaluation=NOT_MEASURED,
        basis='Experimental decision surface.',
    ),
    Module(
        key='global_research.council', name='Global Research Council',
        kind=AGENT, status=EXPERIMENTAL,
        location='global_research/services/council.py',
        entry_point='global_research.services.council',
        consumers=('global_research.views',),
        dependencies=('PostgreSQL',),
        evaluation=NOT_MEASURED,
        basis='Multi-agent research experiment.',
    ),
    Module(
        key='digital_twin.council', name='Digital Twin Council',
        kind=AGENT, status=EXPERIMENTAL,
        location='digital_twin/services/council.py',
        entry_point='digital_twin.services.council',
        consumers=('digital_twin.views',),
        dependencies=('PostgreSQL',),
        evaluation=NOT_MEASURED,
        basis='Scenario experiment.',
    ),
    Module(
        key='langgraph.orchestration', name='LangGraph Orchestration',
        kind=AGENT, status=EXPERIMENTAL,
        location='langgraph_orchestration/',
        entry_point='langgraph_orchestration',
        consumers=(),
        dependencies=('langgraph',),
        evaluation=NOT_MEASURED,
        basis='Orchestration experiment with no production route.',
    ),
)

MODULES: tuple = _ENGINES + _ML + _AI

REGISTRY = {m.key: m for m in MODULES}


def by_status(status: str) -> list:
    return [m for m in MODULES if m.status == status]


def counts() -> dict:
    """
    Status counts, derived. Nothing may hard-code these.

    `specification_packs` is deliberately separate from the module statuses: a
    training-pack folder is a document, and folding it into an agent count is
    exactly how "33 operational agents" came to describe 298 markdown files.
    """
    from pathlib import Path

    from django.conf import settings

    packs = 0
    base = Path(settings.BASE_DIR) / 'ai_agents'
    if base.is_dir():
        packs = len([p for p in base.iterdir() if p.is_dir()])

    result = {f'{status.lower()}_modules': len(by_status(status))
              for status in STATUS_ORDER}
    result['total_modules'] = len(MODULES)
    result['specification_packs'] = packs
    result['evaluated_modules'] = sum(
        1 for m in MODULES if m.evaluation != NOT_MEASURED)
    result['unevaluated_modules'] = sum(
        1 for m in MODULES if m.evaluation == NOT_MEASURED)
    return result


def production_ai_agents() -> list:
    """
    Generative agents claimed as PRODUCTION.

    Expected to be empty, and a test asserts it: no LLM-backed module has a
    measured evaluation, and for a generative system there is no other basis on
    which to make the claim.
    """
    return [m for m in MODULES if m.kind == AGENT and m.status == PRODUCTION]
