# AI Agent Repository Upgrade Map

How EcoIQ LegacySafe AI could grow using well-known open-source agent, RAG, security,
code-analysis, evaluation, observability, graph, and climate/ESG repositories.

**This is an integration roadmap. It does not claim these repositories are installed or fully
integrated today.** No heavy dependencies were installed to produce this document, and nothing
listed below has been wired into the codebase beyond what's explicitly marked `MVP now`.

Status legend:
- **MVP now** — an equivalent capability already exists in this hackathon build (usually our
  own code, not the listed repository itself)
- **Next integration** — the concrete next adoption candidate for that category
- **Roadmap-ready** — a credible future option, not scheduled next

See also the live page at `/legacy-safe/agent-repository-map/`.

---

## 1. Agent Orchestration

**EcoIQ use:** controlled workflows, multi-agent planning, human-in-the-loop approval, model switching.
**Priority:** LangGraph + LlamaIndex first.

| Repository | Status |
|---|---|
| `langchain-ai/langgraph` | Next integration |
| `run-llama/llama_index` | Next integration |
| `crewAIInc/crewAI` | Roadmap-ready |
| `microsoft/autogen` | Roadmap-ready |
| `microsoft/semantic-kernel` | Roadmap-ready |
| `openai/openai-agents-python` | Roadmap-ready |
| `google/adk-python` | Roadmap-ready |
| `mastra-ai/mastra` | Roadmap-ready |

## 2. RAG and Memory

**EcoIQ use:** permission-aware memory, document retrieval, ESG reports, legacy docs, investment evidence.
**Priority:** pgvector first, because EcoIQ already uses PostgreSQL.

| Repository | Status |
|---|---|
| `pgvector/pgvector` | Next integration |
| `qdrant/qdrant` | Roadmap-ready |
| `weaviate/weaviate` | Roadmap-ready |
| `chroma-core/chroma` | Roadmap-ready |
| `deepset-ai/haystack` | Roadmap-ready |
| `elastic/elasticsearch` | Roadmap-ready |
| `opensearch-project/OpenSearch` | Roadmap-ready |

## 3. Permissions and Policy

**EcoIQ use:** enterprise-grade access control, BasedAI-style permission-aware retrieval.
**Priority:** Casbin or Oso next.
**MVP now:** our own deterministic `can_access()` matrix (`legacy_safe/services/permissions.py`) — not one of the libraries below.

| Repository | Status |
|---|---|
| `casbin/pycasbin` | Next integration |
| `osohq/oso` | Next integration |
| `casbin/casbin` | Roadmap-ready |
| `open-policy-agent/opa` | Roadmap-ready |
| `permitio/opal` | Roadmap-ready |
| `cedar-policy/cedar` | Roadmap-ready |
| `django-guardian/django-guardian` | Roadmap-ready |

## 4. Legacy Code and Repository Analysis

**EcoIQ use:** legacy system scanning, dependency mapping, risky pattern detection, Conduct-style modernisation.
**Priority:** Semgrep + Tree-sitter next.

| Repository | Status |
|---|---|
| `semgrep/semgrep` | Next integration |
| `tree-sitter/tree-sitter` | Next integration |
| `ast-grep/ast-grep` | Roadmap-ready |
| `github/codeql` | Roadmap-ready |
| `sourcegraph/sourcegraph` | Roadmap-ready |
| `openrewrite/rewrite` | Roadmap-ready |
| `SonarSource/sonarqube` | Roadmap-ready |

## 5. Graph Intelligence

**EcoIQ use:** dependency graph, lineage graph, justice impact graph, stakeholder map.
**Priority:** NetworkX already scaffolded; improve PyVis/Mermaid next.

| Repository | Status |
|---|---|
| `networkx/networkx` | MVP now |
| `WestHealth/pyvis` | Next integration |
| `mermaid-js/mermaid` | Next integration |
| `neo4j/neo4j` | Roadmap-ready |
| `memgraph/memgraph` | Roadmap-ready |
| `graphviz/graphviz` | Roadmap-ready |

## 6. Evaluation and Trust

**EcoIQ use:** faithfulness, evidence coverage, permission leakage tests, agent quality, auditability.
**Priority:** custom leakage tests now; Ragas/Phoenix next.
**MVP now:** our own permission-leakage and prompt-injection tests (`legacy_safe/tests.py`) — not one of the libraries below.

| Repository | Status |
|---|---|
| `explodinggradients/ragas` | Next integration |
| `Arize-ai/phoenix` | Next integration |
| `truera/trulens` | Roadmap-ready |
| `Giskard-AI/giskard` | Roadmap-ready |
| `comet-ml/opik` | Roadmap-ready |
| `future-agi/future-agi` | Roadmap-ready |
| `braintrustdata/braintrust` | Roadmap-ready |

## 7. Security and Guardrails

**EcoIQ use:** prompt injection defence, secret detection, safe repository ingestion, no hidden instruction execution.
**Priority:** detect-secrets / gitleaks + LLM Guard next.
**MVP now:** deterministic permission checks and the seeded prompt-injection test document already prove content is never treated as instructions.

| Repository | Status |
|---|---|
| `Yelp/detect-secrets` | Next integration |
| `gitleaks/gitleaks` | Next integration |
| `protectai/llm-guard` | Next integration |
| `guardrails-ai/guardrails` | Roadmap-ready |
| `NVIDIA/NeMo-Guardrails` | Roadmap-ready |
| `microsoft/presidio` | Roadmap-ready |
| `semgrep/semgrep` | Next integration |

## 8. MCP and Tool Integration

**EcoIQ use:** future connectors to GitHub, docs, databases, enterprise tools, climate APIs.
**Priority:** MCP roadmap-ready.

| Repository | Status |
|---|---|
| `modelcontextprotocol/python-sdk` | Roadmap-ready |
| `modelcontextprotocol/typescript-sdk` | Roadmap-ready |
| `modelcontextprotocol/servers` | Roadmap-ready |
| `punkpeye/awesome-mcp-servers` | Roadmap-ready |

## 9. Workflow Automation

**EcoIQ use:** background ingestion, scanning, report generation, evaluation runs, scheduled monitoring.
**Priority:** Celery + Redis next.

| Repository | Status |
|---|---|
| `celery/celery` | Next integration |
| `redis/redis` | Next integration |
| `n8n-io/n8n` | Roadmap-ready |
| `apache/airflow` | Roadmap-ready |
| `PrefectHQ/prefect` | Roadmap-ready |
| `dagster-io/dagster` | Roadmap-ready |

## 10. Climate, ESG, and Energy Modelling

**EcoIQ use:** scenario modelling, heat replacement, grid planning, industrial decarbonisation, justice-aware transition.
**Priority:** EnergyPlus / PyPSA roadmap-ready.

| Repository | Status |
|---|---|
| `NREL/EnergyPlus` | Roadmap-ready |
| `PyPSA/PyPSA` | Roadmap-ready |
| `oemof/oemof-solph` | Roadmap-ready |
| `OpenModelica/OpenModelica` | Roadmap-ready |
| `ladybug-tools/ladybug` | Roadmap-ready |
| `Calliope-project/calliope` | Roadmap-ready |

---

## EcoIQ Contribution Back to GitHub

EcoIQ can contribute back to the open-source ecosystem it draws from:

- Permission-aware RAG patterns for Django
- Justice-aware agent evaluation templates
- Climate transition demo datasets
- Safe repository ingestion checklist
- Maqasid / Justice impact matrix template
- Enterprise legacy modernisation demo workflows

---

**Disclaimer:** This page is an integration roadmap. It does not claim these repositories are
installed or fully integrated today.
