"""
LegacySafe AI — AI Agent Repository Upgrade Map.

A read-only reference data structure: how EcoIQ could adopt well-known open-source
agent/RAG/security/graph/climate repositories, and how far along each adoption is.
Nothing here is installed or called — see AGENT_REPOSITORY_UPGRADE_MAP.md and the
/legacy-safe/agent-repository-map/ page for the human-readable version.

Status values (per repo):
  'MVP now'          — an equivalent capability already exists in this hackathon build
                        (usually our own code, not the listed repo itself)
  'Next integration' — the concrete next adoption candidate for this category
  'Roadmap-ready'    — a credible future option, not scheduled next
"""

AGENT_REPOSITORY_MAP = [
    {
        'title': '1. Agent Orchestration',
        'ecoiq_use': 'Controlled workflows, multi-agent planning, human-in-the-loop approval, model switching.',
        'priority': 'LangGraph + LlamaIndex first.',
        'repos': [
            ('langchain-ai/langgraph', 'Next integration'),
            ('run-llama/llama_index', 'Next integration'),
            ('crewAIInc/crewAI', 'Roadmap-ready'),
            ('microsoft/autogen', 'Roadmap-ready'),
            ('microsoft/semantic-kernel', 'Roadmap-ready'),
            ('openai/openai-agents-python', 'Roadmap-ready'),
            ('google/adk-python', 'Roadmap-ready'),
            ('mastra-ai/mastra', 'Roadmap-ready'),
        ],
    },
    {
        'title': '2. RAG and Memory',
        'ecoiq_use': 'Permission-aware memory, document retrieval, ESG reports, legacy docs, investment evidence.',
        'priority': 'pgvector first, because EcoIQ already uses PostgreSQL.',
        'repos': [
            ('pgvector/pgvector', 'Next integration'),
            ('qdrant/qdrant', 'Roadmap-ready'),
            ('weaviate/weaviate', 'Roadmap-ready'),
            ('chroma-core/chroma', 'Roadmap-ready'),
            ('deepset-ai/haystack', 'Roadmap-ready'),
            ('elastic/elasticsearch', 'Roadmap-ready'),
            ('opensearch-project/OpenSearch', 'Roadmap-ready'),
        ],
    },
    {
        'title': '3. Permissions and Policy',
        'ecoiq_use': 'Enterprise-grade access control, BasedAI-style permission-aware retrieval.',
        'priority': 'Casbin or Oso next.',
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
        ],
    },
    {
        'title': '4. Legacy Code and Repository Analysis',
        'ecoiq_use': 'Legacy system scanning, dependency mapping, risky pattern detection, Conduct-style modernisation.',
        'priority': 'Semgrep + Tree-sitter next.',
        'repos': [
            ('semgrep/semgrep', 'Next integration'),
            ('tree-sitter/tree-sitter', 'Next integration'),
            ('ast-grep/ast-grep', 'Roadmap-ready'),
            ('github/codeql', 'Roadmap-ready'),
            ('sourcegraph/sourcegraph', 'Roadmap-ready'),
            ('openrewrite/rewrite', 'Roadmap-ready'),
            ('SonarSource/sonarqube', 'Roadmap-ready'),
        ],
    },
    {
        'title': '5. Graph Intelligence',
        'ecoiq_use': 'Dependency graph, lineage graph, justice impact graph, stakeholder map.',
        'priority': 'NetworkX already scaffolded; improve PyVis/Mermaid next.',
        'repos': [
            ('networkx/networkx', 'MVP now'),
            ('WestHealth/pyvis', 'Next integration'),
            ('mermaid-js/mermaid', 'Next integration'),
            ('neo4j/neo4j', 'Roadmap-ready'),
            ('memgraph/memgraph', 'Roadmap-ready'),
            ('graphviz/graphviz', 'Roadmap-ready'),
        ],
    },
    {
        'title': '6. Evaluation and Trust',
        'ecoiq_use': 'Faithfulness, evidence coverage, permission leakage tests, agent quality, auditability.',
        'priority': 'Custom leakage tests now; Ragas/Phoenix next.',
        'mvp_note': (
            'MVP now: our own permission-leakage and prompt-injection tests '
            '(legacy_safe/tests.py) — not one of the libraries below.'
        ),
        'repos': [
            ('explodinggradients/ragas', 'Next integration'),
            ('Arize-ai/phoenix', 'Next integration'),
            ('truera/trulens', 'Roadmap-ready'),
            ('Giskard-AI/giskard', 'Roadmap-ready'),
            ('comet-ml/opik', 'Roadmap-ready'),
            ('future-agi/future-agi', 'Roadmap-ready'),
            ('braintrustdata/braintrust', 'Roadmap-ready'),
        ],
    },
    {
        'title': '7. Security and Guardrails',
        'ecoiq_use': 'Prompt injection defence, secret detection, safe repository ingestion, no hidden instruction execution.',
        'priority': 'detect-secrets / gitleaks + LLM Guard next.',
        'mvp_note': (
            'MVP now: deterministic permission checks and the seeded prompt-injection '
            'test document already prove content is never treated as instructions.'
        ),
        'repos': [
            ('Yelp/detect-secrets', 'Next integration'),
            ('gitleaks/gitleaks', 'Next integration'),
            ('protectai/llm-guard', 'Next integration'),
            ('guardrails-ai/guardrails', 'Roadmap-ready'),
            ('NVIDIA/NeMo-Guardrails', 'Roadmap-ready'),
            ('microsoft/presidio', 'Roadmap-ready'),
            ('semgrep/semgrep', 'Next integration'),
        ],
    },
    {
        'title': '8. MCP and Tool Integration',
        'ecoiq_use': 'Future connectors to GitHub, docs, databases, enterprise tools, climate APIs.',
        'priority': 'MCP roadmap-ready.',
        'repos': [
            ('modelcontextprotocol/python-sdk', 'Roadmap-ready'),
            ('modelcontextprotocol/typescript-sdk', 'Roadmap-ready'),
            ('modelcontextprotocol/servers', 'Roadmap-ready'),
            ('punkpeye/awesome-mcp-servers', 'Roadmap-ready'),
        ],
    },
    {
        'title': '9. Workflow Automation',
        'ecoiq_use': 'Background ingestion, scanning, report generation, evaluation runs, scheduled monitoring.',
        'priority': 'Celery + Redis next.',
        'repos': [
            ('celery/celery', 'Next integration'),
            ('redis/redis', 'Next integration'),
            ('n8n-io/n8n', 'Roadmap-ready'),
            ('apache/airflow', 'Roadmap-ready'),
            ('PrefectHQ/prefect', 'Roadmap-ready'),
            ('dagster-io/dagster', 'Roadmap-ready'),
        ],
    },
    {
        'title': '10. Climate, ESG, and Energy Modelling',
        'ecoiq_use': 'Scenario modelling, heat replacement, grid planning, industrial decarbonisation, justice-aware transition.',
        'priority': 'EnergyPlus / PyPSA roadmap-ready.',
        'repos': [
            ('NREL/EnergyPlus', 'Roadmap-ready'),
            ('PyPSA/PyPSA', 'Roadmap-ready'),
            ('oemof/oemof-solph', 'Roadmap-ready'),
            ('OpenModelica/OpenModelica', 'Roadmap-ready'),
            ('ladybug-tools/ladybug', 'Roadmap-ready'),
            ('Calliope-project/calliope', 'Roadmap-ready'),
        ],
    },
]
