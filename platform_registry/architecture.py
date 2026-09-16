"""
The canonical layered architecture contract for EcoIQ.

This file answers a different question from ``platform_registry.agents``:
the module registry says *what software exists and how mature it is*; this
map says *where that software sits in the request/decision lifecycle*.

Module maturity is never copied here. ``as_payload()`` resolves every
``module_key`` through the canonical registry at call time, so the diagram,
API and module catalogue cannot silently disagree.
"""
from __future__ import annotations

from dataclasses import dataclass

from platform_registry.agents import REGISTRY

ACTIVE = 'ACTIVE'
PARTIAL = 'PARTIAL'
PLANNED = 'PLANNED'
LAYER_MATURITY = (ACTIVE, PARTIAL, PLANNED)


@dataclass(frozen=True)
class ArchitectureLayer:
    key: str
    name: str
    responsibility: str
    maturity: str
    basis: str
    module_keys: tuple[str, ...] = ()
    implementation_paths: tuple[str, ...] = ()
    gaps: tuple[str, ...] = ()
    cross_cutting: bool = False


LAYERS: tuple[ArchitectureLayer, ...] = (
    ArchitectureLayer(
        key='experience_contract',
        name='Experience & API Contract',
        responsibility='Serve the public React product and its canonical, session-authenticated API contract.',
        maturity=ACTIVE,
        basis='The React SPA is served by Django from one origin and consumes API v2.',
        implementation_paths=('frontend/web/', 'api/v2_urls.py', 'core/spa.py'),
    ),
    ArchitectureLayer(
        key='orchestration',
        name='AI Orchestration & Workflow',
        responsibility='Classify requests, coordinate bounded workflows, route models and stop safely on failure.',
        maturity=PARTIAL,
        basis='The runtime, graph and Celery tasks are implemented and tested; the worker path is not deployed on Render.',
        module_keys=('agent_runtime.model_router', 'langgraph.orchestration', 'backend.workflow'),
        implementation_paths=('langgraph_orchestration/', 'backend_intelligence_engine/tasks.py'),
        gaps=('Deploy and operate a Redis-backed Celery worker before describing background automation as live.',),
    ),
    ArchitectureLayer(
        key='decision_core',
        name='Decision Intelligence Core',
        responsibility='Calculate evidence-backed scores, confidence and publication eligibility with explicit unknowns.',
        maturity=ACTIVE,
        basis='Deterministic engines run on the current evidence path and record provenance.',
        module_keys=(
            'scoring.composite', 'evidence.coverage', 'evidence.confidence',
            'evidence.eligibility', 'evidence.provenance', 'ethics.scoring',
            'financing.readiness', 'qdf.decision_integrity', 'mizan.score',
        ),
        implementation_paths=('companies/', 'ethics/', 'financing/', 'qdf/', 'mizan/'),
    ),
    ArchitectureLayer(
        key='knowledge_retrieval',
        name='Knowledge, Evidence Memory & Retrieval',
        responsibility='Ingest, scope, retrieve and cite evidence without crossing project or organisation boundaries.',
        maturity=PARTIAL,
        basis='Evidence Memory and pgvector retrieval are implemented; retrieval relevance has no labelled evaluation yet.',
        module_keys=('evidence.memory', 'ingestion.pipeline'),
        implementation_paths=('evidence_memory/', 'ingestion/'),
        gaps=('Create a labelled retrieval evaluation set and measure precision, recall and citation coverage.',),
    ),
    ArchitectureLayer(
        key='model_gateway',
        name='Model Gateway',
        responsibility='Select an allowed provider/model by capability, privacy, health and cost policy.',
        maturity=PARTIAL,
        basis='The multi-provider gateway and deterministic routing are implemented; routing quality is not evaluated.',
        module_keys=('ai_gateway', 'agent_runtime.model_router'),
        implementation_paths=('ai_gateway/', 'agent_runtime_model_router/services/model_router.py'),
        gaps=('Consolidate the two routing surfaces behind one policy contract after compatibility tests exist.',),
    ),
    ArchitectureLayer(
        key='tools_connectors',
        name='Tools, MCP & External Connectors',
        responsibility='Connect governed workflows to government data, ERP, procurement, documents and operational systems.',
        maturity=PLANNED,
        basis='The current API Integration Layer is a product blueprint, not a general connector runtime.',
        implementation_paths=('api_integration_layer/', '.mcp.json'),
        gaps=(
            'Implement a server-side connector registry with per-tool permissions, schemas, timeouts and audit events.',
            'Treat MCP as an adapter protocol; do not expose repository-development MCP configuration as product runtime.',
        ),
    ),
    ArchitectureLayer(
        key='data_platform',
        name='Data Platform',
        responsibility='Persist relational state, provenance, vectors and durable uploaded evidence.',
        maturity=ACTIVE,
        basis='PostgreSQL is the durable system of record; pgvector is used by Evidence Memory and R2 stores uploads.',
        implementation_paths=('ecoiq/settings.py', 'evidence_memory/models.py', 'core/storage.py'),
    ),
    ArchitectureLayer(
        key='trust_safety',
        name='Trust, Safety & Human Approval',
        responsibility='Fail closed on unsupported claims and require human confirmation for consequential actions.',
        maturity=PARTIAL,
        basis='Publication eligibility, safety assertions and approval gates exist, but enforcement is not yet universal.',
        module_keys=('evidence.eligibility', 'evidence.provenance', 'agent_runtime.model_router'),
        implementation_paths=(
            'companies/eligibility.py',
            'agent_runtime_model_router/services/safety_assertions.py',
            'agent_runtime_model_router/services/human_approval_gate.py',
        ),
        gaps=('Route every new AI execution path through the shared runtime or an equivalent tested gate.',),
        cross_cutting=True,
    ),
    ArchitectureLayer(
        key='observability_audit',
        name='Observability, Audit & Provenance',
        responsibility='Record which evidence, workflow stages and physical model calls produced an outcome.',
        maturity=PARTIAL,
        basis='Metric provenance and AI Observatory are real shared stores; some legacy AI callers bypass them.',
        module_keys=('evidence.provenance', 'ai.observatory'),
        implementation_paths=('companies/provenance.py', 'ai_observatory/'),
        gaps=('Instrument legacy direct model calls or retire them in favour of the shared gateway/runtime.',),
        cross_cutting=True,
    ),
    ArchitectureLayer(
        key='institutional_memory',
        name='Institutional Memory',
        responsibility='Reuse verified evidence and preserve why earlier decisions were made.',
        maturity=PARTIAL,
        basis='Evidence Memory and Council decision memory exist, with scoped retrieval and explicit sharing states.',
        module_keys=('evidence.memory',),
        implementation_paths=('evidence_memory/', 'ai_agent_council/models.py'),
        gaps=('Measure whether retrieved memory improves decisions without leaking restricted context.',),
        cross_cutting=True,
    ),
)


def as_payload() -> list[dict]:
    """Serialize the map while resolving module truth from ``REGISTRY``."""
    return [
        {
            'key': layer.key,
            'name': layer.name,
            'responsibility': layer.responsibility,
            'maturity': layer.maturity,
            'basis': layer.basis,
            'cross_cutting': layer.cross_cutting,
            'implementation_paths': list(layer.implementation_paths),
            'gaps': list(layer.gaps),
            'components': [
                {
                    'key': REGISTRY[key].key,
                    'name': REGISTRY[key].name,
                    'kind': REGISTRY[key].kind,
                    'status': REGISTRY[key].status,
                    'location': REGISTRY[key].location,
                    'entry_point': REGISTRY[key].entry_point,
                }
                for key in layer.module_keys
            ],
        }
        for layer in LAYERS
    ]
