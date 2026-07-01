"""
LegacySafe AI — EcoIQ AI Agent Ecosystem 200.

A curated, read-only roadmap data structure: how EcoIQ could evolve into a broader agentic
platform using well-known open-source (and select commercial/enterprise) repositories/products,
across 17 categories. Nothing here is installed, called, or wired into the running app beyond
what is explicitly marked 'MVP now'.

Status values (per entry):
  'MVP now'             — an equivalent capability already exists (usually in this repo, either
                          in legacy_safe or platform-wide in requirements.txt — noted per item)
  'Next integration'    — the concrete next adoption candidate for that category
  'Roadmap-ready'       — a credible, well-established future option, not scheduled next
  'Research watchlist'  — newer, more specialised, or less proven — worth tracking, not yet a
                          committed roadmap item
"""

CAPABILITY_STATEMENT = (
    'EcoIQ LegacySafe AI is repository-aware, language-aware, permission-aware, '
    'model-provider-ready, and justice-aware.'
)

TOP_DISCLAIMER = (
    'This is an integration roadmap, not a claim that all listed repositories are already '
    'implemented. Current MVP features are marked separately from next integrations and '
    'roadmap-ready tools.'
)

MICROSOFT_DISCLAIMER = (
    'These Microsoft tools are roadmap-ready integrations unless explicitly marked as '
    'implemented. The current hackathon MVP does not claim full Microsoft/Azure integration.'
)

# Section 5: Microsoft / Enterprise AI Stack — a distinct structure (name, use, status) rather
# than a plain repo table, because each entry needs its own explanation.
MICROSOFT_ENTERPRISE_AI_STACK = {
    'title': '5. Microsoft / Enterprise AI Stack',
    'ecoiq_use': (
        'Enterprise-grade multi-agent orchestration, graph-based retrieval, PII protection, '
        'document conversion, browser testing, and a future roadmap-ready Azure deployment option.'
    ),
    'disclaimer': MICROSOFT_DISCLAIMER,
    'items': [
        ('microsoft/autogen', 'Multi-agent enterprise teams and role-based agent collaboration.', 'Roadmap-ready'),
        ('microsoft/semantic-kernel', 'Enterprise orchestration, planners, skills/plugins, workflow integration.', 'Roadmap-ready'),
        ('microsoft/graphrag', 'Graph-based RAG (GraphRAG) for relationships between documents, systems, risks, teams and actions.', 'Next integration'),
        ('microsoft/presidio', 'PII detection and redaction (Microsoft Presidio) before retrieval or model calls.', 'Next integration'),
        ('microsoft/markitdown', 'Convert PDF, Word, PowerPoint, Excel, HTML and other enterprise files into Markdown/text for ingestion (MarkItDown).', 'Next integration'),
        ('microsoft/playwright', 'Browser automation for testing EcoIQ pages and future workflow demos.', 'Next integration'),
        ('microsoft/typescript', 'Future typed frontend and agent UI tooling.', 'Roadmap-ready'),
        ('microsoft/vscode', 'Developer workflow and future VS Code extension for repo-aware EcoIQ agent assistance.', 'Roadmap-ready'),
        ('Azure AI / Azure OpenAI-ready provider', 'Roadmap-ready enterprise deployment option for customers needing Microsoft cloud, compliance, identity and security.', 'Roadmap-ready'),
    ],
}

AI_AGENT_ECOSYSTEM_200 = [
    {
        'title': '1. Agent Orchestration and Multi-Agent Frameworks',
        'ecoiq_use': 'Multi-agent planning, permission guard workflows, human approval, justice review agents, model switching, controlled enterprise workflows.',
        'first_choice': 'LangGraph + LlamaIndex.',
        'risk': 'Agents may become uncontrolled, leak context, or execute unsafe actions.',
        'safe_rule': 'Every agent must receive only permission-filtered context and must write audit logs.',
        'repos': [
            ('langchain-ai/langgraph', 'Next integration'),
            ('langchain-ai/langchain', 'Next integration'),
            ('run-llama/llama_index', 'Next integration'),
            ('crewAIInc/crewAI', 'Roadmap-ready'),
            ('microsoft/autogen', 'Roadmap-ready'),
            ('microsoft/semantic-kernel', 'Roadmap-ready'),
            ('openai/openai-agents-python', 'Roadmap-ready'),
            ('google/adk-python', 'Roadmap-ready'),
            ('mastra-ai/mastra', 'Roadmap-ready'),
            ('deepset-ai/haystack', 'Roadmap-ready'),
            ('agno-agi/agno', 'Research watchlist'),
            ('pydantic/pydantic-ai', 'Research watchlist'),
            ('camel-ai/camel', 'Research watchlist'),
            ('langroid/langroid', 'Research watchlist'),
            ('superagent-ai/superagent', 'Research watchlist'),
            ('AgentOps-AI/agentops', 'Research watchlist'),
        ],
    },
    {
        'title': '2. RAG, Memory and Vector Databases',
        'ecoiq_use': 'Permission-aware memory, document retrieval, ESG reports, enterprise evidence, lineage, revocation.',
        'first_choice': 'pgvector because EcoIQ already uses PostgreSQL.',
        'risk': 'Sensitive chunks can leak if vector search happens before permission filtering.',
        'safe_rule': 'Filter permissions before retrieval/scoring or enforce metadata-level access constraints.',
        'repos': [
            ('pgvector/pgvector', 'Next integration'),
            ('qdrant/qdrant', 'Roadmap-ready'),
            ('weaviate/weaviate', 'Roadmap-ready'),
            ('chroma-core/chroma', 'Roadmap-ready'),
            ('milvus-io/milvus', 'Roadmap-ready'),
            ('elastic/elasticsearch', 'Roadmap-ready'),
            ('opensearch-project/OpenSearch', 'Roadmap-ready'),
            ('deepset-ai/haystack', 'Roadmap-ready'),
            ('run-llama/llama_index', 'Roadmap-ready'),
            ('langchain-ai/langchain', 'Roadmap-ready'),
            ('facebookresearch/faiss', 'Roadmap-ready'),
            ('microsoft/graphrag', 'Roadmap-ready'),
            ('neo4j/neo4j', 'Roadmap-ready'),
            ('memgraph/memgraph', 'Roadmap-ready'),
            ('redis/redis', 'Roadmap-ready'),
        ],
    },
    {
        'title': '3. Permissions, Policy and Secure Access',
        'ecoiq_use': 'BasedAI-style deterministic access checks, enterprise RBAC/ABAC, retrieval guard, policy-as-code.',
        'first_choice': 'Casbin or Oso.',
        'risk': 'The LLM may become the permission decision-maker, which is not acceptable.',
        'safe_rule': 'Access decisions must be deterministic and happen before model calls.',
        'mvp_note': (
            'MVP now: our own deterministic can_access() matrix '
            '(legacy_safe/services/permissions.py) — not one of the libraries below.'
        ),
        'repos': [
            ('casbin/pycasbin', 'Next integration'),
            ('osohq/oso', 'Next integration'),
            ('casbin/casbin', 'Roadmap-ready'),
            ('open-policy-agent/opa', 'Roadmap-ready'),
            ('permitio/opal', 'Roadmap-ready'),
            ('cedar-policy/cedar', 'Roadmap-ready'),
            ('django-guardian/django-guardian', 'Roadmap-ready'),
            ('authzed/spicedb', 'Research watchlist'),
            ('openfga/openfga', 'Research watchlist'),
            ('cerbos/cerbos', 'Research watchlist'),
        ],
    },
    {
        'title': '4. Code and Repository Analysis',
        'ecoiq_use': 'Conduct-style legacy code scanning, dependency mapping, risky pattern detection, repository-aware modernisation.',
        'first_choice': 'Semgrep + Tree-sitter.',
        'risk': 'Unknown repository instructions may be treated as trusted commands.',
        'safe_rule': 'Never execute unknown scripts automatically. Scan first, classify files, then plan changes with human approval.',
        'repos': [
            ('semgrep/semgrep', 'Next integration'),
            ('tree-sitter/tree-sitter', 'Next integration'),
            ('ast-grep/ast-grep', 'Roadmap-ready'),
            ('github/codeql', 'Roadmap-ready'),
            ('sourcegraph/sourcegraph', 'Roadmap-ready'),
            ('openrewrite/rewrite', 'Roadmap-ready'),
            ('SonarSource/sonarqube', 'Roadmap-ready'),
            ('microsoft/playwright', 'Roadmap-ready'),
            ('eslint/eslint', 'Roadmap-ready'),
            ('prettier/prettier', 'Roadmap-ready'),
            ('pycqa/bandit', 'Roadmap-ready'),
            ('PyCQA/pylint', 'Roadmap-ready'),
            ('astral-sh/ruff', 'Roadmap-ready'),
            ('pypa/pip-audit', 'Roadmap-ready'),
            ('dependabot/dependabot-core', 'Research watchlist'),
        ],
    },
    # Section 5 (Microsoft / Enterprise AI Stack) is MICROSOFT_ENTERPRISE_AI_STACK above —
    # rendered separately by the template because of its different (name, use, status) shape.
    {
        'title': '6. Graph Intelligence and Visualisation',
        'ecoiq_use': 'Dependency graph, lineage graph, stakeholder impact graph, Maqasid justice graph.',
        'first_choice': 'NetworkX is already scaffolded; improve PyVis/Mermaid next.',
        'risk': 'Graphs can imply false causality if evidence is weak.',
        'safe_rule': 'Every graph edge must link to evidence, confidence and source lineage.',
        'mvp_note': 'MVP now: NetworkX is already scaffolded in legacy_safe/services/graph_builder.py.',
        'repos': [
            ('networkx/networkx', 'MVP now'),
            ('WestHealth/pyvis', 'Next integration'),
            ('mermaid-js/mermaid', 'Next integration'),
            ('neo4j/neo4j', 'Roadmap-ready'),
            ('memgraph/memgraph', 'Roadmap-ready'),
            ('graphviz/graphviz', 'Roadmap-ready'),
            ('cytoscape/cytoscape.js', 'Roadmap-ready'),
            ('d3/d3', 'Roadmap-ready'),
            ('apache/echarts', 'Research watchlist'),
            ('plotly/plotly.py', 'Research watchlist'),
        ],
    },
    {
        'title': '7. Evaluation, Observability and Trust',
        'ecoiq_use': 'Permission leakage tests, faithfulness, auditability, agent traces, model cost, hallucination checks.',
        'first_choice': 'Custom permission leakage tests now; Ragas/Phoenix next.',
        'risk': 'Evaluation may become vanity metrics rather than safety checks.',
        'safe_rule': 'Always include permission leakage, evidence coverage, revocation propagation and prompt-injection tests.',
        'mvp_note': (
            'MVP now: our own permission-leakage and prompt-injection tests '
            '(legacy_safe/tests.py) — not one of the libraries below.'
        ),
        'repos': [
            ('explodinggradients/ragas', 'Next integration'),
            ('Arize-ai/phoenix', 'Next integration'),
            ('langfuse/langfuse', 'Roadmap-ready'),
            ('truera/trulens', 'Roadmap-ready'),
            ('Giskard-AI/giskard', 'Roadmap-ready'),
            ('comet-ml/opik', 'Roadmap-ready'),
            ('braintrustdata/braintrust', 'Roadmap-ready'),
            ('open-telemetry/opentelemetry-python', 'Roadmap-ready'),
            ('getsentry/sentry', 'Roadmap-ready'),
            ('wandb/wandb', 'Research watchlist'),
            ('mlflow/mlflow', 'Research watchlist'),
            ('promptfoo/promptfoo', 'Research watchlist'),
        ],
    },
    {
        'title': '8. Security, Prompt-Injection and Data Protection',
        'ecoiq_use': 'Prompt-injection defence, PII redaction, secret detection, safe repository ingestion, enterprise governance.',
        'first_choice': 'detect-secrets/gitleaks + LLM Guard.',
        'risk': 'Malicious document/repo text can become an instruction.',
        'safe_rule': 'Treat untrusted documents and repository text as data, never as system instructions.',
        'mvp_note': (
            'MVP now: deterministic permission checks and the seeded prompt-injection test '
            'document already prove content is never treated as instructions.'
        ),
        'repos': [
            ('protectai/llm-guard', 'Next integration'),
            ('Yelp/detect-secrets', 'Next integration'),
            ('gitleaks/gitleaks', 'Next integration'),
            ('guardrails-ai/guardrails', 'Roadmap-ready'),
            ('NVIDIA/NeMo-Guardrails', 'Roadmap-ready'),
            ('microsoft/presidio', 'Roadmap-ready'),
            ('trufflesecurity/trufflehog', 'Roadmap-ready'),
            ('semgrep/semgrep', 'Next integration'),
            ('pyupio/safety', 'Roadmap-ready'),
            ('pypa/pip-audit', 'Roadmap-ready'),
            ('OWASP/Top10', 'Research watchlist'),
            ('OWASP/www-project-top-10-for-large-language-model-applications', 'Research watchlist'),
        ],
    },
    {
        'title': '9. Document Ingestion and File Understanding',
        'ecoiq_use': 'ESG reports, PDFs, Word files, Excel budgets, board memos, enterprise documentation.',
        'first_choice': 'MarkItDown + pypdf + python-docx.',
        'risk': 'Tables, footnotes, scanned text or hidden instructions may be misread.',
        'safe_rule': 'Preserve source references, page numbers, file lineage and access levels.',
        'repos': [
            ('Unstructured-IO/unstructured', 'Next integration'),
            ('microsoft/markitdown', 'Next integration'),
            ('py-pdf/pypdf', 'Next integration'),
            ('python-openxml/python-docx', 'Next integration'),
            ('pandas-dev/pandas', 'Roadmap-ready'),
            ('openpyxl/openpyxl', 'Roadmap-ready'),
            ('apache/tika', 'Roadmap-ready'),
            ('explosion/spaCy', 'Roadmap-ready'),
            ('huggingface/transformers', 'Research watchlist'),
            ('langchain-ai/langchain', 'Roadmap-ready'),
            ('run-llama/llama_index', 'Roadmap-ready'),
        ],
    },
    {
        'title': '10. Workflow Automation and Background Jobs',
        'ecoiq_use': 'Background ingestion, scheduled scanning, report generation, recurring climate intelligence, audit jobs.',
        'first_choice': 'Celery + Redis.',
        'risk': 'Background tasks may process revoked or restricted documents.',
        'safe_rule': 'Every task must re-check revocation and permissions at execution time.',
        'repos': [
            ('celery/celery', 'Next integration'),
            ('redis/redis', 'Next integration'),
            ('rq/rq', 'Roadmap-ready'),
            ('n8n-io/n8n', 'Roadmap-ready'),
            ('apache/airflow', 'Roadmap-ready'),
            ('PrefectHQ/prefect', 'Roadmap-ready'),
            ('dagster-io/dagster', 'Roadmap-ready'),
            ('temporalio/sdk-python', 'Research watchlist'),
            ('apscheduler/apscheduler', 'Roadmap-ready'),
            ('django-q2/django-q2', 'Roadmap-ready'),
        ],
    },
    {
        'title': '11. Web, Frontend and Dashboards',
        'ecoiq_use': 'Enterprise dashboard, 3D maps, agent UI, testing, repository visualisation.',
        'first_choice': 'Django templates now; React/Three.js later.',
        'risk': 'UI may hide blocked evidence or make security decisions look vague.',
        'safe_rule': 'Always show allowed evidence, blocked evidence, role, audit state and confidence.',
        'mvp_note': 'MVP now: Django itself already powers every page in this module.',
        'repos': [
            ('django/django', 'MVP now'),
            ('encode/django-rest-framework', 'Next integration'),
            ('microsoft/playwright', 'Next integration'),
            ('fastapi/fastapi', 'Research watchlist'),
            ('vercel/next.js', 'Roadmap-ready'),
            ('facebook/react', 'Roadmap-ready'),
            ('vuejs/vue', 'Research watchlist'),
            ('tailwindlabs/tailwindcss', 'Roadmap-ready'),
            ('framer/motion', 'Research watchlist'),
            ('threejs/three.js', 'Roadmap-ready'),
            ('pmndrs/react-three-fiber', 'Research watchlist'),
            ('microsoft/typescript', 'Research watchlist'),
        ],
    },
    {
        'title': '12. MCP and Tool Connectors',
        'ecoiq_use': 'Future connectors to GitHub, docs, climate APIs, enterprise systems, databases, browsers.',
        'first_choice': 'MCP roadmap-ready after permission model is stable.',
        'risk': 'Tools can expose or modify external systems without proper approval.',
        'safe_rule': 'No tool call without role permission, audit logging and human approval for write actions.',
        'repos': [
            ('modelcontextprotocol/python-sdk', 'Roadmap-ready'),
            ('modelcontextprotocol/typescript-sdk', 'Roadmap-ready'),
            ('modelcontextprotocol/servers', 'Roadmap-ready'),
            ('punkpeye/awesome-mcp-servers', 'Research watchlist'),
            ('github/github-mcp-server', 'Roadmap-ready'),
            ('zapier/mcp', 'Research watchlist'),
            ('stripe/agent-toolkit', 'Research watchlist'),
            ('browserbase/mcp-server-browserbase', 'Research watchlist'),
        ],
    },
    {
        'title': '13. Climate, ESG and Energy Modelling',
        'ecoiq_use': 'Scenario modelling, clean heat transition, energy system planning, climate-risk analysis, industrial decarbonisation.',
        'first_choice': 'EnergyPlus / PyPSA roadmap-ready.',
        'risk': 'Models may create false precision or unrealistic climate/energy claims.',
        'safe_rule': 'Show assumptions, uncertainty, data source and confidence.',
        'mvp_note': (
            'MVP now: scikit-learn is already installed platform-wide (requirements.txt) for '
            "EcoIQ's existing ML scoring pipeline — not yet wired into legacy_safe."
        ),
        'repos': [
            ('NREL/EnergyPlus', 'Roadmap-ready'),
            ('PyPSA/PyPSA', 'Roadmap-ready'),
            ('oemof/oemof-solph', 'Research watchlist'),
            ('OpenModelica/OpenModelica', 'Research watchlist'),
            ('ladybug-tools/ladybug', 'Research watchlist'),
            ('Calliope-project/calliope', 'Research watchlist'),
            ('project-pareto/project-pareto', 'Research watchlist'),
            ('nasa/earthdata-search', 'Research watchlist'),
            ('pydata/xarray', 'Roadmap-ready'),
            ('geopandas/geopandas', 'Roadmap-ready'),
            ('scikit-learn/scikit-learn', 'MVP now'),
            ('scipy/scipy', 'Roadmap-ready'),
        ],
    },
    {
        'title': '14. Geospatial, Maps and Country Intelligence',
        'ecoiq_use': 'Country pages, transition maps, infrastructure risk, climate exposure, city/aul project planning.',
        'first_choice': 'GeoPandas + Leaflet.',
        'risk': 'Location data may expose sensitive sites or vulnerable communities.',
        'safe_rule': 'Protect sensitive geolocation data and aggregate where needed.',
        'repos': [
            ('geopandas/geopandas', 'Next integration'),
            ('leaflet/leaflet', 'Next integration'),
            ('shapely/shapely', 'Roadmap-ready'),
            ('pyproj4/pyproj', 'Research watchlist'),
            ('mapbox/mapbox-gl-js', 'Roadmap-ready'),
            ('keplergl/kepler.gl', 'Research watchlist'),
            ('deckgl/deck.gl', 'Research watchlist'),
            ('osmnx/osmnx', 'Research watchlist'),
            ('rasterio/rasterio', 'Research watchlist'),
            ('cartopy/cartopy', 'Research watchlist'),
        ],
    },
    {
        'title': '15. Data Science and Forecasting',
        'ecoiq_use': 'Risk forecasting, ESG scoring, company ranking, transition scenario modelling.',
        'first_choice': 'pandas + scikit-learn.',
        'risk': 'Bad training data can create biased or misleading scores.',
        'safe_rule': 'Keep scoring explainable, auditable and reviewed by humans.',
        'mvp_note': (
            'MVP now: scikit-learn is already installed platform-wide (requirements.txt) for '
            "EcoIQ's existing ML scoring pipeline — not yet wired into legacy_safe."
        ),
        'repos': [
            ('pandas-dev/pandas', 'Next integration'),
            ('scikit-learn/scikit-learn', 'MVP now'),
            ('numpy/numpy', 'Roadmap-ready'),
            ('scipy/scipy', 'Roadmap-ready'),
            ('statsmodels/statsmodels', 'Research watchlist'),
            ('facebook/prophet', 'Research watchlist'),
            ('Nixtla/neuralforecast', 'Research watchlist'),
            ('pytorch/pytorch', 'Research watchlist'),
            ('tensorflow/tensorflow', 'Research watchlist'),
            ('huggingface/transformers', 'Research watchlist'),
        ],
    },
    {
        'title': '16. Justice, Governance and Responsible AI',
        'ecoiq_use': 'Justice & Maqasid layer, fairness checks, explainability, stakeholder impact, vulnerable community protection.',
        'first_choice': 'Fairlearn + SHAP roadmap-ready.',
        'risk': 'Justice scoring can become superficial or culturally insensitive.',
        'safe_rule': 'Use the Justice & Maqasid layer as governance support, not as a final moral authority.',
        'mvp_note': (
            'MVP now: SHAP is already installed platform-wide (requirements.txt) for '
            "EcoIQ's existing ML explainability pipeline — not yet wired into the Justice & Maqasid layer."
        ),
        'repos': [
            ('fairlearn/fairlearn', 'Roadmap-ready'),
            ('slundberg/shap', 'MVP now'),
            ('Trusted-AI/AIF360', 'Roadmap-ready'),
            ('Giskard-AI/giskard', 'Roadmap-ready'),
            ('interpretml/interpret', 'Roadmap-ready'),
            ('microsoft/responsible-ai-toolbox', 'Roadmap-ready'),
            ('IBM/lale', 'Research watchlist'),
            ('pytorch/captum', 'Research watchlist'),
            ('mlflow/mlflow', 'Roadmap-ready'),
        ],
    },
    {
        'title': '17. Enterprise Integration Targets',
        'ecoiq_use': 'Conduct-style enterprise workflows, ERP context, change management, documentation, tickets, compliance data.',
        'first_choice': 'GitHub/GitLab + Jira + Confluence.',
        'risk': 'Enterprise connectors can expose sensitive systems.',
        'safe_rule': 'Read-only first, least privilege, audit every access, human approval for write actions.',
        'is_products': True,
        'mvp_note': (
            'Note: these are enterprise integration targets (platforms/products), not '
            'necessarily GitHub repositories.'
        ),
        'repos': [
            ('GitHub', 'Roadmap-ready'),
            ('GitLab', 'Roadmap-ready'),
            ('Jira', 'Roadmap-ready'),
            ('Confluence', 'Roadmap-ready'),
            ('ServiceNow', 'Roadmap-ready'),
            ('Salesforce', 'Roadmap-ready'),
            ('Oracle', 'Roadmap-ready'),
            ('SAP', 'Roadmap-ready'),
            ('Workday', 'Research watchlist'),
            ('Azure', 'Research watchlist'),
            ('Google Cloud', 'Research watchlist'),
            ('AWS', 'Research watchlist'),
        ],
    },
]

CONTRIBUTIONS_BACK_TO_GITHUB = [
    'Django permission-aware RAG reference implementation',
    'Justice-aware agent evaluation templates',
    'Maqasid impact matrix for climate transition',
    'Safe repository ingestion checklist',
    'Enterprise legacy modernisation demo workflow',
    'Climate transition seed datasets',
    'Revocation and lineage test templates',
    'Prompt-injection-as-content demo pattern',
    'Evidence-first modernisation report template',
]
