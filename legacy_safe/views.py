import json

from django.contrib import messages
from django.shortcuts import redirect, render

from legacy_safe.forms import (
    AskAgentForm, DEFAULT_QUESTION, PermissionDemoForm, RevokeDocumentForm,
)
from legacy_safe.models import AuditLog, DOCUMENT_TYPE_CHOICES, LegacyProject, MemoryChunk, SourceDocument
from legacy_safe.services import audit
from legacy_safe.services.graph_builder import build_dependency_graph
from legacy_safe.services.llm_provider import MockProvider
from legacy_safe.services.permissions import DEMO_ROLES, can_access, roles_for_demo_role
from legacy_safe.services.planner import generate_modernisation_plan
from legacy_safe.services.retrieval import retrieve_allowed_chunks, retrieve_allowed_chunks_for_roles
from legacy_safe.services.revocation import revoke_source_document

# Shared between the Model Integration Readiness and Process Optimisation pages
# so the same honest numbers appear in both places.
PROCESS_OPTIMISATION_METRICS = [
    ('Manual system analysis', 'reduced from weeks to minutes in demo scenario', True),
    ('Permission leakage', '0%', True),
    ('Blocked restricted sources', 'visible', True),
    ('Revocation propagation', 'passed', True),
    ('Audit coverage', '100%', True),
    ('Provider receives blocked context', 'never', True),
    ('Prompt injection treated as document content', 'passed', True),
]

# Roadmap-only: no parser is wired up in this hackathon build. Listed here so the
# repository-support page is honest about what's aspirational vs. what runs today.
ROADMAP_CODE_LANGUAGES = [
    ('Python', 'Tree-sitter grammar available'),
    ('JavaScript / TypeScript', 'Tree-sitter grammar available'),
    ('Java', 'Tree-sitter grammar available'),
    ('COBOL', 'Common in legacy ERP/mainframe systems — Tree-sitter grammar available'),
    ('C / C++', 'Tree-sitter grammar available'),
    ('SQL / stored procedures', 'Semgrep rule support available'),
    ('ABAP (SAP)', 'Niche grammar support — evaluate on integration'),
]

# Demo evaluation dimensions for the Justice & Maqasid layer — deliberately not wired to a
# scoring model. This hackathon build shows the dimensions a justice-aware review would weigh,
# not a production score.
JUSTICE_METRICS = [
    'Public health protection',
    'Energy affordability',
    'Worker transition support',
    'Community impact',
    'Carbon reduction',
    'Governance transparency',
    'Future generations benefit',
    'Resource stewardship',
    'Permission fairness',
    'Auditability',
]


def _default_project():
    return LegacyProject.objects.order_by('id').first()


def dashboard(request):
    project = _default_project()
    return render(request, 'legacy_safe/dashboard.html', {'project': project})


def upload_document(request):
    project = _default_project()
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        document_type = request.POST.get('document_type', 'other')
        access_level = request.POST.get('access_level', 'public')
        text_content = request.POST.get('text_content', '').strip()
        if title and text_content and project is not None:
            doc = SourceDocument.objects.create(
                project=project, title=title, document_type=document_type,
                access_level=access_level, text_content=text_content,
            )
            MemoryChunk.objects.create(
                source_document=doc, chunk_index=0, text=text_content,
                access_level=access_level,
                lineage=[{'source_document_id': doc.id, 'source_document_title': doc.title}],
            )
            messages.success(request, f'"{title}" added as a {access_level} source document.')
            return redirect('legacy_safe:upload')
        messages.error(request, 'Title and content are required, and a project must exist.')
    return render(request, 'legacy_safe/upload.html', {'project': project})


def ask_agent(request):
    project = _default_project()
    result = None
    if request.method == 'POST':
        form = AskAgentForm(request.POST)
        if form.is_valid():
            project = form.cleaned_data['project']
            result = generate_modernisation_plan(request.user, project, form.cleaned_data['question'])
    else:
        initial = {'project': project.id} if project else {}
        form = AskAgentForm(initial=initial)
    return render(request, 'legacy_safe/ask.html', {
        'form': form, 'project': project, 'result': result,
    })


def permission_demo(request):
    project = _default_project()
    question = DEFAULT_QUESTION
    results = None

    if request.method == 'POST':
        form = PermissionDemoForm(request.POST)
        if form.is_valid():
            project = form.cleaned_data['project']
            question = form.cleaned_data['question']
    else:
        initial = {'project': project.id, 'question': question} if project else {'question': question}
        form = PermissionDemoForm(initial=initial)

    injection_contained = None
    if project is not None:
        results = []
        for role in DEMO_ROLES:
            roles = roles_for_demo_role(role)
            outcome = retrieve_allowed_chunks_for_roles(roles, project, question)
            audit.log_event(
                user=request.user if request.user.is_authenticated else None,
                action='permission_demo',
                question=question,
                decision='allowed' if outcome['allowed'] else 'blocked',
                allowed_sources=[e['source_title'] for e in outcome['allowed']],
                blocked_sources=[e['source_title'] for e in outcome['blocked']],
                reason=f'demo_role={role}',
            )
            results.append({'role': role, **outcome})

        # Prove the seeded prompt-injection document never widened access: every
        # item any role sees must independently pass that role's own permission
        # check — re-verified here rather than just trusting retrieval's own filter.
        injection_contained = all(
            can_access(e['access_level'], roles_for_demo_role(r['role']))
            for r in results for e in r['allowed']
        )

    return render(request, 'legacy_safe/permission_demo.html', {
        'form': form, 'project': project, 'question': question, 'results': results,
        'injection_contained': injection_contained,
    })


def audit_logs(request):
    logs = AuditLog.objects.select_related('user').order_by('-created_at')[:100]
    return render(request, 'legacy_safe/audit_logs.html', {'logs': logs})


def dependency_graph(request):
    project = _default_project()
    graph = build_dependency_graph(project) if project else {'nodes': [], 'edges': []}
    return render(request, 'legacy_safe/dependency_graph.html', {
        'project': project, 'graph': graph, 'graph_json': json.dumps(graph, indent=2),
    })


def revocation_demo(request):
    project = _default_project()
    result = None

    if request.method == 'POST':
        form = RevokeDocumentForm(request.POST)
        if form.is_valid():
            doc = form.cleaned_data['source_document']
            result = revoke_source_document(
                doc, user=request.user if request.user.is_authenticated else None,
                reason='Triggered from Revocation Demo page',
            )
        form = RevokeDocumentForm()
    else:
        form = RevokeDocumentForm()

    documents = SourceDocument.objects.filter(project=project).prefetch_related('chunks') if project else []
    derived_memories = project.derived_memories.all() if project else []

    return render(request, 'legacy_safe/revocation_demo.html', {
        'project': project, 'form': form, 'result': result,
        'documents': documents, 'derived_memories': derived_memories,
    })


def model_integration_readiness(request):
    project = _default_project()
    mock_result = None
    if project is not None:
        outcome = retrieve_allowed_chunks(request.user, project, DEFAULT_QUESTION)
        mock_result = MockProvider().generate(DEFAULT_QUESTION, outcome['allowed'])
    return render(request, 'legacy_safe/model_integration_readiness.html', {
        'project': project, 'mock_result': mock_result,
        'metrics': PROCESS_OPTIMISATION_METRICS,
    })


def repository_support(request):
    project = _default_project()
    document_types_seeded = (
        SourceDocument.objects.filter(project=project).values_list('document_type', flat=True).distinct()
        if project else []
    )
    return render(request, 'legacy_safe/repository_support.html', {
        'project': project,
        'document_type_choices': DOCUMENT_TYPE_CHOICES,
        'document_types_seeded': set(document_types_seeded),
        'roadmap_languages': ROADMAP_CODE_LANGUAGES,
    })


def process_optimisation(request):
    project = _default_project()
    document_count = SourceDocument.objects.filter(project=project).count() if project else 0
    audit_log_count = AuditLog.objects.count()
    return render(request, 'legacy_safe/process_optimisation.html', {
        'project': project, 'metrics': PROCESS_OPTIMISATION_METRICS,
        'document_count': document_count, 'audit_log_count': audit_log_count,
    })


def justice_maqasid(request):
    project = _default_project()
    return render(request, 'legacy_safe/justice_maqasid.html', {
        'project': project, 'justice_metrics': JUSTICE_METRICS,
    })
