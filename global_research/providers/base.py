"""
global_research/providers/base.py — the pluggable ResearchProvider
interface. Modeled directly on
`agent_runtime_model_router/services/model_adapters.py`'s adapter contract:
a plain dataclass result type, credentials checked first, never fabricates
a live result when none is available.

No provider in this phase performs uncontrolled scraping — see
docs/adr/ADR-global-research-engine.md decision 6. A future live adapter
(e.g. a real web-search or CrossRef/PatentsView API client) implements this
exact interface and reuses
`backend_intelligence_engine.services.http_client.fetch()` for any
retryable HTTP call; the orchestrator never branches on "is this provider
live," only on this shared interface.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class SourceCandidateResult:
    """What `search()` returns — one discovered source, with enough
    structured data for deterministic claim extraction. `structured_fields`
    holds labelled facts the source explicitly states (e.g.
    {'cop_at_7c': 4.1, 'certified_zone': 'Zone 2'}) — never raw prose to be
    interpreted; see services/claim_extraction.py."""
    title: str
    source_type: str
    provider_name: str
    url: str = ''
    document_reference: str = ''
    publisher: str = ''
    author: str = ''
    publication_date: object = None
    jurisdiction: str = ''
    language: str = 'en'
    source_owner_type: str = 'unknown'
    vendor_affiliation: str = ''
    licence_or_usage_note: str = ''
    snippet: str = ''
    structured_fields: dict = field(default_factory=dict)
    independently_reproduced: bool = False


@dataclass
class SourceDocumentResult:
    """What `fetch()` returns for one candidate — the permitted content."""
    candidate: SourceCandidateResult
    permitted_extract: str = ''
    structured_fields: dict = field(default_factory=dict)


@dataclass
class NormalisedSourceResult:
    """What `normalise()` returns — cleaned, ready to persist as a
    ResearchSource. Same shape as the inputs, kept as a distinct type so a
    future live provider can genuinely transform format (e.g. HTML → text)
    at this step without the orchestrator caring."""
    candidate: SourceCandidateResult
    permitted_extract: str
    structured_fields: dict


@dataclass
class ProviderHealth:
    provider_name: str
    status: str  # 'simulated' | 'live' | 'credentials_missing' | 'error'
    credentials_configured: bool
    message: str = ''


class ResearchProvider(ABC):
    """Base class every evidence-layer provider implements. `layer` names
    which of the 4 evidence layers this provider covers (authoritative,
    commercial, market, early_innovation) — the orchestrator dispatches to
    at least one provider per layer per mission, never just one search
    engine (see docs/adr/ADR-global-research-engine.md decision 6)."""
    name = 'base'
    layer = 'authoritative'

    @abstractmethod
    def search(self, query_plan):
        """query_plan: global_research.models.ResearchQueryPlan.
        Returns list[SourceCandidateResult]."""
        raise NotImplementedError

    @abstractmethod
    def fetch(self, candidate):
        """candidate: SourceCandidateResult. Returns SourceDocumentResult."""
        raise NotImplementedError

    @abstractmethod
    def normalise(self, document):
        """document: SourceDocumentResult. Returns NormalisedSourceResult."""
        raise NotImplementedError

    @abstractmethod
    def health_check(self):
        """Returns ProviderHealth. Must never report 'live' without
        actually verifying configured credentials."""
        raise NotImplementedError
