# EcoIQ AI Agent Ecosystem 200

A curated roadmap of agent, RAG, code-analysis, security, evaluation, enterprise, climate,
geospatial and justice-aware libraries that can strengthen EcoIQ LegacySafe AI.

**This is an integration roadmap, not a claim that all listed repositories are already
implemented. Current MVP features are marked separately from next integrations and
roadmap-ready tools.** No heavy dependencies were installed, no external APIs were called, and
no API keys were added to produce this document.

**EcoIQ LegacySafe AI is repository-aware, language-aware, permission-aware,
model-provider-ready, and justice-aware.**

Status legend:
- **MVP now** — an equivalent capability already exists (in `legacy_safe`, or platform-wide in
  `requirements.txt` — noted per item)
- **Next integration** — the concrete next adoption candidate for that category
- **Roadmap-ready** — a credible, well-established future option, not scheduled next
- **Research watchlist** — newer, more specialised, or less proven — worth tracking, not a
  committed roadmap item

See also the live page at `/legacy-safe/ai-agent-ecosystem-200/`.

---

## 1. Agent Orchestration and Multi-Agent Frameworks

**EcoIQ use:** multi-agent planning, permission guard workflows, human approval, justice review agents, model switching, controlled enterprise workflows.
**First integration choice:** LangGraph + LlamaIndex.
**Risk if integrated badly:** agents may become uncontrolled, leak context, or execute unsafe actions.
**Safe integration rule:** every agent must receive only permission-filtered context and must write audit logs.

| Repository | Status |
|---|---|
| `langchain-ai/langgraph` | Next integration |
| `langchain-ai/langchain` | Next integration |
| `run-llama/llama_index` | Next integration |
| `crewAIInc/crewAI` | Roadmap-ready |
| `microsoft/autogen` | Roadmap-ready |
| `microsoft/semantic-kernel` | Roadmap-ready |
| `openai/openai-agents-python` | Roadmap-ready |
| `google/adk-python` | Roadmap-ready |
| `mastra-ai/mastra` | Roadmap-ready |
| `deepset-ai/haystack` | Roadmap-ready |
| `agno-agi/agno` | Research watchlist |
| `pydantic/pydantic-ai` | Research watchlist |
| `camel-ai/camel` | Research watchlist |
| `langroid/langroid` | Research watchlist |
| `superagent-ai/superagent` | Research watchlist |
| `AgentOps-AI/agentops` | Research watchlist |

## 2. RAG, Memory and Vector Databases

**EcoIQ use:** permission-aware memory, document retrieval, ESG reports, enterprise evidence, lineage, revocation.
**First integration choice:** pgvector because EcoIQ already uses PostgreSQL.
**Risk if integrated badly:** sensitive chunks can leak if vector search happens before permission filtering.
**Safe integration rule:** filter permissions before retrieval/scoring or enforce metadata-level access constraints.

| Repository | Status |
|---|---|
| `pgvector/pgvector` | Next integration |
| `qdrant/qdrant` | Roadmap-ready |
| `weaviate/weaviate` | Roadmap-ready |
| `chroma-core/chroma` | Roadmap-ready |
| `milvus-io/milvus` | Roadmap-ready |
| `elastic/elasticsearch` | Roadmap-ready |
| `opensearch-project/OpenSearch` | Roadmap-ready |
| `deepset-ai/haystack` | Roadmap-ready |
| `run-llama/llama_index` | Roadmap-ready |
| `langchain-ai/langchain` | Roadmap-ready |
| `facebookresearch/faiss` | Roadmap-ready |
| `microsoft/graphrag` | Roadmap-ready |
| `neo4j/neo4j` | Roadmap-ready |
| `memgraph/memgraph` | Roadmap-ready |
| `redis/redis` | Roadmap-ready |

## 3. Permissions, Policy and Secure Access

**EcoIQ use:** BasedAI-style deterministic access checks, enterprise RBAC/ABAC, retrieval guard, policy-as-code.
**First integration choice:** Casbin or Oso.
**Risk if integrated badly:** the LLM may become the permission decision-maker, which is not acceptable.
**Safe integration rule:** access decisions must be deterministic and happen before model calls.
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
| `authzed/spicedb` | Research watchlist |
| `openfga/openfga` | Research watchlist |
| `cerbos/cerbos` | Research watchlist |

## 4. Code and Repository Analysis

**EcoIQ use:** Conduct-style legacy code scanning, dependency mapping, risky pattern detection, repository-aware modernisation.
**First integration choice:** Semgrep + Tree-sitter.
**Risk if integrated badly:** unknown repository instructions may be treated as trusted commands.
**Safe integration rule:** never execute unknown scripts automatically — scan first, classify files, then plan changes with human approval.

| Repository | Status |
|---|---|
| `semgrep/semgrep` | Next integration |
| `tree-sitter/tree-sitter` | Next integration |
| `ast-grep/ast-grep` | Roadmap-ready |
| `github/codeql` | Roadmap-ready |
| `sourcegraph/sourcegraph` | Roadmap-ready |
| `openrewrite/rewrite` | Roadmap-ready |
| `SonarSource/sonarqube` | Roadmap-ready |
| `microsoft/playwright` | Roadmap-ready |
| `eslint/eslint` | Roadmap-ready |
| `prettier/prettier` | Roadmap-ready |
| `pycqa/bandit` | Roadmap-ready |
| `PyCQA/pylint` | Roadmap-ready |
| `astral-sh/ruff` | Roadmap-ready |
| `pypa/pip-audit` | Roadmap-ready |
| `dependabot/dependabot-core` | Research watchlist |

## 5. Microsoft / Enterprise AI Stack

**EcoIQ use:** enterprise-grade multi-agent orchestration, graph-based retrieval, PII protection, document conversion, browser testing, and a future roadmap-ready Azure deployment option.

**These Microsoft tools are roadmap-ready integrations unless explicitly marked as implemented.
The current hackathon MVP does not claim full Microsoft/Azure integration.**

| Tool | Use | Status |
|---|---|---|
| `microsoft/autogen` | Multi-agent enterprise teams and role-based agent collaboration. | Roadmap-ready |
| `microsoft/semantic-kernel` | Enterprise orchestration, planners, skills/plugins, workflow integration. | Roadmap-ready |
| `microsoft/graphrag` | Graph-based RAG (GraphRAG) for relationships between documents, systems, risks, teams and actions. | Next integration |
| `microsoft/presidio` | PII detection and redaction (Microsoft Presidio) before retrieval or model calls. | Next integration |
| `microsoft/markitdown` | Convert PDF, Word, PowerPoint, Excel, HTML and other enterprise files into Markdown/text for ingestion (MarkItDown). | Next integration |
| `microsoft/playwright` | Browser automation for testing EcoIQ pages and future workflow demos. | Next integration |
| `microsoft/typescript` | Future typed frontend and agent UI tooling. | Roadmap-ready |
| `microsoft/vscode` | Developer workflow and future VS Code extension for repo-aware EcoIQ agent assistance. | Roadmap-ready |
| Azure AI / Azure OpenAI-ready provider | Roadmap-ready enterprise deployment option for customers needing Microsoft cloud, compliance, identity and security. | Roadmap-ready |

## 6. Graph Intelligence and Visualisation

**EcoIQ use:** dependency graph, lineage graph, stakeholder impact graph, Maqasid justice graph.
**First integration choice:** NetworkX is already scaffolded; improve PyVis/Mermaid next.
**Risk if integrated badly:** graphs can imply false causality if evidence is weak.
**Safe integration rule:** every graph edge must link to evidence, confidence and source lineage.
**MVP now:** NetworkX is already scaffolded in `legacy_safe/services/graph_builder.py`.

| Repository | Status |
|---|---|
| `networkx/networkx` | MVP now |
| `WestHealth/pyvis` | Next integration |
| `mermaid-js/mermaid` | Next integration |
| `neo4j/neo4j` | Roadmap-ready |
| `memgraph/memgraph` | Roadmap-ready |
| `graphviz/graphviz` | Roadmap-ready |
| `cytoscape/cytoscape.js` | Roadmap-ready |
| `d3/d3` | Roadmap-ready |
| `apache/echarts` | Research watchlist |
| `plotly/plotly.py` | Research watchlist |

## 7. Evaluation, Observability and Trust

**EcoIQ use:** permission leakage tests, faithfulness, auditability, agent traces, model cost, hallucination checks.
**First integration choice:** custom permission leakage tests now; Ragas/Phoenix next.
**Risk if integrated badly:** evaluation may become vanity metrics rather than safety checks.
**Safe integration rule:** always include permission leakage, evidence coverage, revocation propagation and prompt-injection tests.
**MVP now:** our own permission-leakage and prompt-injection tests (`legacy_safe/tests.py`) — not one of the libraries below.

| Repository | Status |
|---|---|
| `explodinggradients/ragas` | Next integration |
| `Arize-ai/phoenix` | Next integration |
| `langfuse/langfuse` | Roadmap-ready |
| `truera/trulens` | Roadmap-ready |
| `Giskard-AI/giskard` | Roadmap-ready |
| `comet-ml/opik` | Roadmap-ready |
| `braintrustdata/braintrust` | Roadmap-ready |
| `open-telemetry/opentelemetry-python` | Roadmap-ready |
| `getsentry/sentry` | Roadmap-ready |
| `wandb/wandb` | Research watchlist |
| `mlflow/mlflow` | Research watchlist |
| `promptfoo/promptfoo` | Research watchlist |

## 8. Security, Prompt-Injection and Data Protection

**EcoIQ use:** prompt-injection defence, PII redaction, secret detection, safe repository ingestion, enterprise governance.
**First integration choice:** detect-secrets/gitleaks + LLM Guard.
**Risk if integrated badly:** malicious document/repo text can become an instruction.
**Safe integration rule:** treat untrusted documents and repository text as data, never as system instructions.
**MVP now:** deterministic permission checks and the seeded prompt-injection test document already prove content is never treated as instructions.

| Repository | Status |
|---|---|
| `protectai/llm-guard` | Next integration |
| `Yelp/detect-secrets` | Next integration |
| `gitleaks/gitleaks` | Next integration |
| `guardrails-ai/guardrails` | Roadmap-ready |
| `NVIDIA/NeMo-Guardrails` | Roadmap-ready |
| `microsoft/presidio` | Roadmap-ready |
| `trufflesecurity/trufflehog` | Roadmap-ready |
| `semgrep/semgrep` | Next integration |
| `pyupio/safety` | Roadmap-ready |
| `pypa/pip-audit` | Roadmap-ready |
| `OWASP/Top10` | Research watchlist |
| `OWASP/www-project-top-10-for-large-language-model-applications` | Research watchlist |

## 9. Document Ingestion and File Understanding

**EcoIQ use:** ESG reports, PDFs, Word files, Excel budgets, board memos, enterprise documentation.
**First integration choice:** MarkItDown + pypdf + python-docx.
**Risk if integrated badly:** tables, footnotes, scanned text or hidden instructions may be misread.
**Safe integration rule:** preserve source references, page numbers, file lineage and access levels.

| Repository | Status |
|---|---|
| `Unstructured-IO/unstructured` | Next integration |
| `microsoft/markitdown` | Next integration |
| `py-pdf/pypdf` | Next integration |
| `python-openxml/python-docx` | Next integration |
| `pandas-dev/pandas` | Roadmap-ready |
| `openpyxl/openpyxl` | Roadmap-ready |
| `apache/tika` | Roadmap-ready |
| `explosion/spaCy` | Roadmap-ready |
| `huggingface/transformers` | Research watchlist |
| `langchain-ai/langchain` | Roadmap-ready |
| `run-llama/llama_index` | Roadmap-ready |

## 10. Workflow Automation and Background Jobs

**EcoIQ use:** background ingestion, scheduled scanning, report generation, recurring climate intelligence, audit jobs.
**First integration choice:** Celery + Redis.
**Risk if integrated badly:** background tasks may process revoked or restricted documents.
**Safe integration rule:** every task must re-check revocation and permissions at execution time.

| Repository | Status |
|---|---|
| `celery/celery` | Next integration |
| `redis/redis` | Next integration |
| `rq/rq` | Roadmap-ready |
| `n8n-io/n8n` | Roadmap-ready |
| `apache/airflow` | Roadmap-ready |
| `PrefectHQ/prefect` | Roadmap-ready |
| `dagster-io/dagster` | Roadmap-ready |
| `temporalio/sdk-python` | Research watchlist |
| `apscheduler/apscheduler` | Roadmap-ready |
| `django-q2/django-q2` | Roadmap-ready |

## 11. Web, Frontend and Dashboards

**EcoIQ use:** enterprise dashboard, 3D maps, agent UI, testing, repository visualisation.
**First integration choice:** Django templates now; React/Three.js later.
**Risk if integrated badly:** UI may hide blocked evidence or make security decisions look vague.
**Safe integration rule:** always show allowed evidence, blocked evidence, role, audit state and confidence.
**MVP now:** Django itself already powers every page in this module.

| Repository | Status |
|---|---|
| `django/django` | MVP now |
| `encode/django-rest-framework` | Next integration |
| `microsoft/playwright` | Next integration |
| `fastapi/fastapi` | Research watchlist |
| `vercel/next.js` | Roadmap-ready |
| `facebook/react` | Roadmap-ready |
| `vuejs/vue` | Research watchlist |
| `tailwindlabs/tailwindcss` | Roadmap-ready |
| `framer/motion` | Research watchlist |
| `threejs/three.js` | Roadmap-ready |
| `pmndrs/react-three-fiber` | Research watchlist |
| `microsoft/typescript` | Research watchlist |

## 12. MCP and Tool Connectors

**EcoIQ use:** future connectors to GitHub, docs, climate APIs, enterprise systems, databases, browsers.
**First integration choice:** MCP roadmap-ready after permission model is stable.
**Risk if integrated badly:** tools can expose or modify external systems without proper approval.
**Safe integration rule:** no tool call without role permission, audit logging and human approval for write actions.

| Repository | Status |
|---|---|
| `modelcontextprotocol/python-sdk` | Roadmap-ready |
| `modelcontextprotocol/typescript-sdk` | Roadmap-ready |
| `modelcontextprotocol/servers` | Roadmap-ready |
| `punkpeye/awesome-mcp-servers` | Research watchlist |
| `github/github-mcp-server` | Roadmap-ready |
| `zapier/mcp` | Research watchlist |
| `stripe/agent-toolkit` | Research watchlist |
| `browserbase/mcp-server-browserbase` | Research watchlist |

## 13. Climate, ESG and Energy Modelling

**EcoIQ use:** scenario modelling, clean heat transition, energy system planning, climate-risk analysis, industrial decarbonisation.
**First integration choice:** EnergyPlus / PyPSA roadmap-ready.
**Risk if integrated badly:** models may create false precision or unrealistic climate/energy claims.
**Safe integration rule:** show assumptions, uncertainty, data source and confidence.
**MVP now:** scikit-learn is already installed platform-wide (`requirements.txt`) for EcoIQ's existing ML scoring pipeline — not yet wired into `legacy_safe`.

| Repository | Status |
|---|---|
| `NREL/EnergyPlus` | Roadmap-ready |
| `PyPSA/PyPSA` | Roadmap-ready |
| `oemof/oemof-solph` | Research watchlist |
| `OpenModelica/OpenModelica` | Research watchlist |
| `ladybug-tools/ladybug` | Research watchlist |
| `Calliope-project/calliope` | Research watchlist |
| `project-pareto/project-pareto` | Research watchlist |
| `nasa/earthdata-search` | Research watchlist |
| `pydata/xarray` | Roadmap-ready |
| `geopandas/geopandas` | Roadmap-ready |
| `scikit-learn/scikit-learn` | MVP now |
| `scipy/scipy` | Roadmap-ready |

## 14. Geospatial, Maps and Country Intelligence

**EcoIQ use:** country pages, transition maps, infrastructure risk, climate exposure, city/project planning.
**First integration choice:** GeoPandas + Leaflet.
**Risk if integrated badly:** location data may expose sensitive sites or vulnerable communities.
**Safe integration rule:** protect sensitive geolocation data and aggregate where needed.

| Repository | Status |
|---|---|
| `geopandas/geopandas` | Next integration |
| `leaflet/leaflet` | Next integration |
| `shapely/shapely` | Roadmap-ready |
| `pyproj4/pyproj` | Research watchlist |
| `mapbox/mapbox-gl-js` | Roadmap-ready |
| `keplergl/kepler.gl` | Research watchlist |
| `deckgl/deck.gl` | Research watchlist |
| `osmnx/osmnx` | Research watchlist |
| `rasterio/rasterio` | Research watchlist |
| `cartopy/cartopy` | Research watchlist |

## 15. Data Science and Forecasting

**EcoIQ use:** risk forecasting, ESG scoring, company ranking, transition scenario modelling.
**First integration choice:** pandas + scikit-learn.
**Risk if integrated badly:** bad training data can create biased or misleading scores.
**Safe integration rule:** keep scoring explainable, auditable and reviewed by humans.
**MVP now:** scikit-learn is already installed platform-wide (`requirements.txt`) for EcoIQ's existing ML scoring pipeline — not yet wired into `legacy_safe`.

| Repository | Status |
|---|---|
| `pandas-dev/pandas` | Next integration |
| `scikit-learn/scikit-learn` | MVP now |
| `numpy/numpy` | Roadmap-ready |
| `scipy/scipy` | Roadmap-ready |
| `statsmodels/statsmodels` | Research watchlist |
| `facebook/prophet` | Research watchlist |
| `Nixtla/neuralforecast` | Research watchlist |
| `pytorch/pytorch` | Research watchlist |
| `tensorflow/tensorflow` | Research watchlist |
| `huggingface/transformers` | Research watchlist |

## 16. Justice, Governance and Responsible AI

**EcoIQ use:** Justice & Maqasid layer, fairness checks, explainability, stakeholder impact, vulnerable community protection.
**First integration choice:** Fairlearn + SHAP roadmap-ready.
**Risk if integrated badly:** justice scoring can become superficial or culturally insensitive.
**Safe integration rule:** use the Justice & Maqasid layer as governance support, not as a final moral authority.
**MVP now:** SHAP is already installed platform-wide (`requirements.txt`) for EcoIQ's existing ML explainability pipeline — not yet wired into the Justice & Maqasid layer.

| Repository | Status |
|---|---|
| `fairlearn/fairlearn` | Roadmap-ready |
| `slundberg/shap` | MVP now |
| `Trusted-AI/AIF360` | Roadmap-ready |
| `Giskard-AI/giskard` | Roadmap-ready |
| `interpretml/interpret` | Roadmap-ready |
| `microsoft/responsible-ai-toolbox` | Roadmap-ready |
| `IBM/lale` | Research watchlist |
| `pytorch/captum` | Research watchlist |
| `mlflow/mlflow` | Roadmap-ready |

## 17. Enterprise Integration Targets

**EcoIQ use:** Conduct-style enterprise workflows, ERP context, change management, documentation, tickets, compliance data.
**First integration choice:** GitHub/GitLab + Jira + Confluence.
**Risk if integrated badly:** enterprise connectors can expose sensitive systems.
**Safe integration rule:** read-only first, least privilege, audit every access, human approval for write actions.
**Note:** these are enterprise integration targets (platforms/products), not necessarily GitHub repositories.

| Enterprise target | Status |
|---|---|
| GitHub | Roadmap-ready |
| GitLab | Roadmap-ready |
| Jira | Roadmap-ready |
| Confluence | Roadmap-ready |
| ServiceNow | Roadmap-ready |
| Salesforce | Roadmap-ready |
| Oracle | Roadmap-ready |
| SAP | Roadmap-ready |
| Workday | Research watchlist |
| Azure | Research watchlist |
| Google Cloud | Research watchlist |
| AWS | Research watchlist |

---

## EcoIQ Contributions Back to GitHub

EcoIQ can contribute back to the open-source ecosystem it draws from:

- Django permission-aware RAG reference implementation
- Justice-aware agent evaluation templates
- Maqasid impact matrix for climate transition
- Safe repository ingestion checklist
- Enterprise legacy modernisation demo workflow
- Climate transition seed datasets
- Revocation and lineage test templates
- Prompt-injection-as-content demo pattern
- Evidence-first modernisation report template

---

**Disclaimer:** This is an integration roadmap, not a claim that all listed repositories are
already implemented. Current MVP features are marked separately from next integrations and
roadmap-ready tools.
