"""
LegacySafe AI — tests for the deterministic permission matrix, permission-filtered
retrieval, revocation cascade, and audit logging (the BasedAI/Conduct core).
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group
from django.test import TestCase

from legacy_safe.models import AuditLog, DerivedMemory, MemoryChunk, SourceDocument
from legacy_safe.services.llm_provider import MockProvider
from legacy_safe.services.permissions import can_access, get_user_roles
from legacy_safe.services.planner import generate_modernisation_plan
from legacy_safe.services.retrieval import retrieve_allowed_chunks
from legacy_safe.services.revocation import revoke_source_document
from legacy_safe.services.seed_demo import create_demo_data

User = get_user_model()


class PermissionMatrixTests(TestCase):
    """can_access() is the deterministic core — never an LLM decision."""

    def test_public_can_access_public(self):
        self.assertTrue(can_access('public', {'public'}))

    def test_public_cannot_access_finance(self):
        self.assertFalse(can_access('finance', {'public'}))

    def test_public_cannot_access_engineering_or_executive(self):
        self.assertFalse(can_access('engineering', {'public'}))
        self.assertFalse(can_access('executive', {'public'}))

    def test_engineering_can_access_engineering(self):
        self.assertTrue(can_access('engineering', {'public', 'engineering'}))
        self.assertFalse(can_access('finance', {'public', 'engineering'}))

    def test_finance_can_access_finance(self):
        self.assertTrue(can_access('finance', {'public', 'finance'}))
        self.assertFalse(can_access('engineering', {'public', 'finance'}))

    def test_executive_can_access_all(self):
        roles = {'public', 'executive'}
        for level in ('public', 'engineering', 'finance', 'executive'):
            self.assertTrue(can_access(level, roles), f'executive should access {level}')

    def test_revoked_is_never_accessible_even_for_executive(self):
        self.assertFalse(can_access('public', {'public', 'executive'}, is_revoked=True))
        self.assertFalse(can_access('executive', {'executive'}, is_revoked=True))

    def test_get_user_roles_maps_django_groups(self):
        user = User.objects.create_user('fin_user', password='x')
        group, _ = Group.objects.get_or_create(name='finance')
        user.groups.add(group)
        self.assertEqual(get_user_roles(user), {'public', 'finance'})

    def test_get_user_roles_superuser_is_treated_as_executive(self):
        admin = User.objects.create_superuser('admin', 'admin@example.com', 'x')
        self.assertIn('executive', get_user_roles(admin))

    def test_get_user_roles_anonymous_is_public_only(self):
        self.assertEqual(get_user_roles(AnonymousUser()), {'public'})


class RetrievalAndPlannerTests(TestCase):
    """Retrieval must filter by permission before the planner ever sees a chunk."""

    def setUp(self):
        self.project = create_demo_data()

    def test_retrieval_filters_before_planning_for_public_role(self):
        result = generate_modernisation_plan(
            AnonymousUser(), self.project, 'What is the full modernisation plan?')
        allowed_titles = {e['source_title'] for e in result['evidence_used']}
        blocked_titles = {e['source_title'] for e in result['restricted_evidence_excluded']}

        self.assertIn('Public ESG Report', allowed_titles)
        self.assertIn('Heat Pump and Boiler Replacement Plan', blocked_titles)
        self.assertIn('Investment Budget', blocked_titles)
        self.assertIn('Board Strategy Memo', blocked_titles)
        # Never both allowed and blocked, and never silently omitted.
        self.assertFalse(allowed_titles & blocked_titles)

    def test_executive_role_sees_everything_and_nothing_is_excluded(self):
        exec_user = User.objects.create_superuser('exec', 'exec@example.com', 'x')
        result = generate_modernisation_plan(
            exec_user, self.project, 'What is the full modernisation plan?')
        allowed_titles = {e['source_title'] for e in result['evidence_used']}

        self.assertIn('Board Strategy Memo', allowed_titles)
        self.assertEqual(result['restricted_evidence_excluded'], [])

    def test_prompt_injection_document_never_widens_access(self):
        """Public role can retrieve the injection doc (it's public) but never sees restricted docs."""
        result = generate_modernisation_plan(
            AnonymousUser(), self.project, 'What is the full modernisation plan?')
        allowed = result['evidence_used']
        allowed_titles = {e['source_title'] for e in allowed}
        allowed_levels = {e['access_level'] for e in allowed}

        self.assertIn('Malicious Prompt Injection Document', allowed_titles)
        self.assertNotIn('finance', allowed_levels)
        self.assertNotIn('executive', allowed_levels)


class RevocationTests(TestCase):
    def setUp(self):
        self.project = create_demo_data()

    def test_revocation_cascades_to_chunk_and_derived_memory(self):
        doc = SourceDocument.objects.get(project=self.project, title='Board Strategy Memo')
        derived = DerivedMemory.objects.get(
            project=self.project, title='Coal-to-Clean-Heat Modernisation Plan')
        self.assertFalse(doc.is_revoked)
        self.assertFalse(derived.is_revoked)

        revoke_source_document(doc)

        doc.refresh_from_db()
        derived.refresh_from_db()
        chunk = MemoryChunk.objects.get(source_document=doc)
        self.assertTrue(doc.is_revoked)
        self.assertTrue(chunk.is_revoked)
        self.assertTrue(derived.is_revoked)

    def test_revoked_document_becomes_unretrievable_even_for_executive(self):
        doc = SourceDocument.objects.get(project=self.project, title='Board Strategy Memo')
        revoke_source_document(doc)

        exec_user = User.objects.create_superuser('exec2', 'exec2@example.com', 'x')
        result = generate_modernisation_plan(
            exec_user, self.project, 'What is the full modernisation plan?')
        allowed_titles = {e['source_title'] for e in result['evidence_used']}
        self.assertNotIn('Board Strategy Memo', allowed_titles)


class AuditLogTests(TestCase):
    def setUp(self):
        self.project = create_demo_data()

    def test_audit_log_created_on_retrieval(self):
        before = AuditLog.objects.count()
        retrieve_allowed_chunks(AnonymousUser(), self.project, 'test question')
        self.assertEqual(AuditLog.objects.count(), before + 1)
        log = AuditLog.objects.latest('created_at')
        self.assertEqual(log.action, 'ask')

    def test_audit_log_created_on_revocation(self):
        doc = SourceDocument.objects.get(project=self.project, title='Public ESG Report')
        before = AuditLog.objects.count()
        revoke_source_document(doc)
        self.assertEqual(AuditLog.objects.count(), before + 1)
        log = AuditLog.objects.latest('created_at')
        self.assertEqual(log.action, 'revoke')
        self.assertEqual(log.decision, 'revoked')


class MockProviderTests(TestCase):
    """MockProvider must be fully offline/deterministic — no external API required."""

    def test_generate_returns_context_count_without_external_api(self):
        result = MockProvider().generate('any prompt', allowed_context=[{'a': 1}, {'b': 2}])
        self.assertEqual(result['provider'], 'mock')
        self.assertEqual(result['context_count'], 2)
        self.assertIn('answer', result)


class ModelIntegrationReadinessPageTests(TestCase):
    def setUp(self):
        self.project = create_demo_data()

    def test_page_returns_200(self):
        response = self.client.get('/legacy-safe/model-integration-readiness/')
        self.assertEqual(response.status_code, 200)

    def test_page_mentions_openai_compatible(self):
        response = self.client.get('/legacy-safe/model-integration-readiness/')
        self.assertContains(response, 'OpenAI-compatible')

    def test_page_mentions_basedapis(self):
        response = self.client.get('/legacy-safe/model-integration-readiness/')
        self.assertContains(response, 'BasedAPIs')

    def test_page_mentions_sap(self):
        response = self.client.get('/legacy-safe/model-integration-readiness/')
        self.assertContains(response, 'SAP')

    def test_page_mentions_permission_guard_agent(self):
        response = self.client.get('/legacy-safe/model-integration-readiness/')
        self.assertContains(response, 'Permission Guard Agent')


class RepositorySupportPageTests(TestCase):
    def setUp(self):
        self.project = create_demo_data()

    def test_page_returns_200(self):
        response = self.client.get('/legacy-safe/repository-support/')
        self.assertEqual(response.status_code, 200)

    def test_page_is_honest_about_roadmap_status(self):
        response = self.client.get('/legacy-safe/repository-support/')
        self.assertContains(response, 'Not implemented in this hackathon build')


class ProcessOptimisationPageTests(TestCase):
    def setUp(self):
        self.project = create_demo_data()

    def test_page_returns_200(self):
        response = self.client.get('/legacy-safe/process-optimisation/')
        self.assertEqual(response.status_code, 200)

    def test_page_shows_live_document_count(self):
        response = self.client.get('/legacy-safe/process-optimisation/')
        self.assertContains(response, 'Source documents ingested')


class JusticeMaqasidPageTests(TestCase):
    def setUp(self):
        self.project = create_demo_data()

    def test_page_returns_200(self):
        response = self.client.get('/legacy-safe/justice-maqasid/')
        self.assertEqual(response.status_code, 200)

    def test_page_mentions_maqasid(self):
        response = self.client.get('/legacy-safe/justice-maqasid/')
        self.assertContains(response, 'Maqasid')

    def test_page_mentions_amanah(self):
        response = self.client.get('/legacy-safe/justice-maqasid/')
        self.assertContains(response, 'Amanah')

    def test_page_mentions_future_generations(self):
        response = self.client.get('/legacy-safe/justice-maqasid/')
        self.assertContains(response, 'Future Generations')

    def test_page_mentions_worker_and_community(self):
        response = self.client.get('/legacy-safe/justice-maqasid/')
        self.assertContains(response, 'Worker & Community')

    def test_page_mentions_justice_aware(self):
        response = self.client.get('/legacy-safe/justice-maqasid/')
        self.assertContains(response, 'justice-aware')


class AgentRepositoryMapPageTests(TestCase):
    def test_page_returns_200(self):
        response = self.client.get('/legacy-safe/agent-repository-map/')
        self.assertEqual(response.status_code, 200)

    def test_page_mentions_langgraph(self):
        response = self.client.get('/legacy-safe/agent-repository-map/')
        self.assertContains(response, 'LangGraph')

    def test_page_mentions_semgrep(self):
        response = self.client.get('/legacy-safe/agent-repository-map/')
        self.assertContains(response, 'Semgrep')

    def test_page_mentions_permission_aware(self):
        response = self.client.get('/legacy-safe/agent-repository-map/')
        self.assertContains(response, 'permission-aware')

    def test_page_mentions_justice(self):
        response = self.client.get('/legacy-safe/agent-repository-map/')
        self.assertContains(response, 'Justice')

    def test_page_mentions_energyplus(self):
        response = self.client.get('/legacy-safe/agent-repository-map/')
        self.assertContains(response, 'EnergyPlus')


class AIAgentEcosystem200PageTests(TestCase):
    def test_page_returns_200(self):
        response = self.client.get('/legacy-safe/ai-agent-ecosystem-200/')
        self.assertEqual(response.status_code, 200)

    def test_page_mentions_title(self):
        response = self.client.get('/legacy-safe/ai-agent-ecosystem-200/')
        self.assertContains(response, 'EcoIQ AI Agent Ecosystem 200')

    def test_page_mentions_langgraph(self):
        response = self.client.get('/legacy-safe/ai-agent-ecosystem-200/')
        self.assertContains(response, 'LangGraph')

    def test_page_mentions_pgvector(self):
        response = self.client.get('/legacy-safe/ai-agent-ecosystem-200/')
        self.assertContains(response, 'pgvector')

    def test_page_mentions_casbin(self):
        response = self.client.get('/legacy-safe/ai-agent-ecosystem-200/')
        self.assertContains(response, 'Casbin')

    def test_page_mentions_semgrep(self):
        response = self.client.get('/legacy-safe/ai-agent-ecosystem-200/')
        self.assertContains(response, 'Semgrep')

    def test_page_mentions_graphrag(self):
        response = self.client.get('/legacy-safe/ai-agent-ecosystem-200/')
        self.assertContains(response, 'GraphRAG')

    def test_page_mentions_presidio(self):
        response = self.client.get('/legacy-safe/ai-agent-ecosystem-200/')
        self.assertContains(response, 'Presidio')

    def test_page_mentions_energyplus(self):
        response = self.client.get('/legacy-safe/ai-agent-ecosystem-200/')
        self.assertContains(response, 'EnergyPlus')

    def test_page_mentions_justice(self):
        response = self.client.get('/legacy-safe/ai-agent-ecosystem-200/')
        self.assertContains(response, 'Justice')

    def test_page_mentions_maqasid(self):
        response = self.client.get('/legacy-safe/ai-agent-ecosystem-200/')
        self.assertContains(response, 'Maqasid')

    def test_page_mentions_roadmap_ready(self):
        response = self.client.get('/legacy-safe/ai-agent-ecosystem-200/')
        self.assertContains(response, 'roadmap-ready')

    def test_page_mentions_microsoft_autogen(self):
        response = self.client.get('/legacy-safe/ai-agent-ecosystem-200/')
        self.assertContains(response, 'microsoft/autogen')

    def test_page_mentions_semantic_kernel(self):
        response = self.client.get('/legacy-safe/ai-agent-ecosystem-200/')
        self.assertContains(response, 'semantic-kernel')

    def test_page_mentions_markitdown(self):
        response = self.client.get('/legacy-safe/ai-agent-ecosystem-200/')
        self.assertContains(response, 'MarkItDown')

    def test_page_mentions_azure_openai_ready(self):
        response = self.client.get('/legacy-safe/ai-agent-ecosystem-200/')
        self.assertContains(response, 'Azure OpenAI-ready')


class MicrosoftEcosystemReadinessPageTests(TestCase):
    def test_page_returns_200(self):
        response = self.client.get('/legacy-safe/microsoft-ecosystem-readiness/')
        self.assertEqual(response.status_code, 200)

    def test_page_mentions_title(self):
        response = self.client.get('/legacy-safe/microsoft-ecosystem-readiness/')
        self.assertContains(response, 'Microsoft Ecosystem Readiness')

    def test_page_mentions_user(self):
        response = self.client.get('/legacy-safe/microsoft-ecosystem-readiness/')
        self.assertContains(response, 'User')

    def test_page_mentions_data(self):
        response = self.client.get('/legacy-safe/microsoft-ecosystem-readiness/')
        self.assertContains(response, 'Data')

    def test_page_mentions_agent(self):
        response = self.client.get('/legacy-safe/microsoft-ecosystem-readiness/')
        self.assertContains(response, 'Agent')

    def test_page_mentions_model(self):
        response = self.client.get('/legacy-safe/microsoft-ecosystem-readiness/')
        self.assertContains(response, 'Model')

    def test_page_mentions_action(self):
        response = self.client.get('/legacy-safe/microsoft-ecosystem-readiness/')
        self.assertContains(response, 'Action')

    def test_page_mentions_microsoft_fabric(self):
        response = self.client.get('/legacy-safe/microsoft-ecosystem-readiness/')
        self.assertContains(response, 'Microsoft Fabric')

    def test_page_mentions_azure_digital_twins(self):
        response = self.client.get('/legacy-safe/microsoft-ecosystem-readiness/')
        self.assertContains(response, 'Azure Digital Twins')

    def test_page_mentions_azure_iot(self):
        response = self.client.get('/legacy-safe/microsoft-ecosystem-readiness/')
        self.assertContains(response, 'Azure IoT')

    def test_page_mentions_copilot(self):
        response = self.client.get('/legacy-safe/microsoft-ecosystem-readiness/')
        self.assertContains(response, 'Copilot')

    def test_page_mentions_microsoft_entra(self):
        response = self.client.get('/legacy-safe/microsoft-ecosystem-readiness/')
        self.assertContains(response, 'Microsoft Entra')

    def test_page_mentions_power_bi(self):
        response = self.client.get('/legacy-safe/microsoft-ecosystem-readiness/')
        self.assertContains(response, 'Power BI')

    def test_page_mentions_microsoft_autogen(self):
        response = self.client.get('/legacy-safe/microsoft-ecosystem-readiness/')
        self.assertContains(response, 'microsoft/autogen')

    def test_page_mentions_semantic_kernel(self):
        response = self.client.get('/legacy-safe/microsoft-ecosystem-readiness/')
        self.assertContains(response, 'semantic-kernel')

    def test_page_mentions_graphrag(self):
        response = self.client.get('/legacy-safe/microsoft-ecosystem-readiness/')
        self.assertContains(response, 'GraphRAG')

    def test_page_mentions_presidio(self):
        response = self.client.get('/legacy-safe/microsoft-ecosystem-readiness/')
        self.assertContains(response, 'Presidio')

    def test_page_mentions_markitdown(self):
        response = self.client.get('/legacy-safe/microsoft-ecosystem-readiness/')
        self.assertContains(response, 'MarkItDown')

    def test_page_mentions_justice(self):
        response = self.client.get('/legacy-safe/microsoft-ecosystem-readiness/')
        self.assertContains(response, 'Justice')

    def test_page_mentions_maqasid(self):
        response = self.client.get('/legacy-safe/microsoft-ecosystem-readiness/')
        self.assertContains(response, 'Maqasid')

    def test_page_mentions_roadmap_ready(self):
        response = self.client.get('/legacy-safe/microsoft-ecosystem-readiness/')
        self.assertContains(response, 'roadmap-ready')


class FullIndustrialModernisationPlannerTests(TestCase):
    """The expanded planner must cover the full EcoIQ modernisation pathway, role-aware."""

    def setUp(self):
        self.project = create_demo_data()

    @staticmethod
    def _plan_text(result):
        parts = [result['executive_summary']]
        parts += [s['title'] for s in result['sections']]
        parts += [s['content'] for s in result['sections']]
        return ' '.join(parts)

    @staticmethod
    def _user_in_group(username, group_name):
        user = User.objects.create_user(username, password='x')
        group, _ = Group.objects.get_or_create(name=group_name)
        user.groups.add(group)
        return user

    def test_executive_plan_covers_full_modernisation_pathway(self):
        exec_user = User.objects.create_superuser('planner_exec', 'planner_exec@example.com', 'x')
        result = generate_modernisation_plan(
            exec_user, self.project,
            'What is the full industrial modernisation plan, from solar panels and equipment '
            'upgrades to process optimisation?')
        text = self._plan_text(result)
        for term in (
            'solar', 'battery', 'heat pump', 'smart meters', 'IoT',
            'process optimisation', 'CAPEX', 'Justice', 'Maqasid',
        ):
            self.assertIn(term, text, f'expected "{term}" in planner output')

    def test_public_role_excludes_finance_and_executive_evidence(self):
        result = generate_modernisation_plan(
            AnonymousUser(), self.project, 'What is the full industrial modernisation plan?')
        allowed_levels = {e['access_level'] for e in result['evidence_used']}
        self.assertNotIn('finance', allowed_levels)
        self.assertNotIn('executive', allowed_levels)
        self.assertNotIn('engineering', allowed_levels)

    def test_engineering_role_sees_technical_equipment_evidence(self):
        eng_user = self._user_in_group('planner_eng', 'engineering')
        result = generate_modernisation_plan(
            eng_user, self.project, 'What is the full industrial modernisation plan?')
        allowed_titles = {e['source_title'] for e in result['evidence_used']}
        self.assertIn('Solar and Battery Feasibility Notes', allowed_titles)
        self.assertIn('Heat Pump and Boiler Replacement Plan', allowed_titles)
        allowed_levels = {e['access_level'] for e in result['evidence_used']}
        self.assertNotIn('finance', allowed_levels)
        self.assertNotIn('executive', allowed_levels)

    def test_finance_role_sees_budget_and_procurement_evidence(self):
        fin_user = self._user_in_group('planner_fin', 'finance')
        result = generate_modernisation_plan(
            fin_user, self.project, 'What is the full industrial modernisation plan?')
        allowed_titles = {e['source_title'] for e in result['evidence_used']}
        self.assertIn('Investment Budget', allowed_titles)
        self.assertIn('Equipment Procurement Plan', allowed_titles)
        allowed_levels = {e['access_level'] for e in result['evidence_used']}
        self.assertNotIn('engineering', allowed_levels)
        self.assertNotIn('executive', allowed_levels)

    def test_executive_role_sees_the_full_modernisation_plan(self):
        exec_user = User.objects.create_superuser('planner_exec2', 'planner_exec2@example.com', 'x')
        result = generate_modernisation_plan(
            exec_user, self.project, 'What is the full industrial modernisation plan?')
        self.assertEqual(result['restricted_evidence_excluded'], [])
        allowed_titles = {e['source_title'] for e in result['evidence_used']}
        for title in (
            'Public ESG Report', 'Solar and Battery Feasibility Notes',
            'Heat Pump and Boiler Replacement Plan', 'Investment Budget',
            'Board Strategy Memo', 'Worker and Community Transition Plan',
            'Justice and Maqasid Review',
        ):
            self.assertIn(title, allowed_titles)


class PermissionDemoAndDashboardContentTests(TestCase):
    def setUp(self):
        self.project = create_demo_data()

    def test_permission_demo_page_mentions_same_modernisation_question(self):
        response = self.client.get('/legacy-safe/permission-demo/')
        self.assertContains(response, 'same modernisation question')

    def test_dashboard_mentions_full_ecoiq_modernisation_plan(self):
        response = self.client.get('/legacy-safe/')
        self.assertContains(response, 'Full EcoIQ Modernisation Plan')
