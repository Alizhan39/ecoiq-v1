"""
The KPI payload against the TypeScript type React is compiled with.

WHY THIS EXISTS
---------------
`KpiEvidence.title` was declared `string` while the API already returned null
for evidence whose source recorded no title. TypeScript therefore permitted
`title.split()`, which crashed the entire investigation page in production —
and 6,381 backend plus 261 frontend tests passed throughout, because a type
that lies is invisible to both suites.

The frontend contract tests hold the API to its documented KEYS. Nothing held
it to the TYPES, so a field could quietly become nullable on one side and stay
non-nullable on the other. That is the gap here.

WHY IT READS THE .ts FILE
-------------------------
Because the mismatch lives between two languages, and neither compiler can see
the other. Parsing the declaration is crude, and it is the only thing that
fails when the two drift apart.
"""
import datetime
import pathlib
import re

from django.conf import settings
from django.test import TestCase

from companies.models import CompanyProfile
from company_intelligence.models import CompanyKPIAssessment, CompanyKPIEvidenceLink
from evidence_memory.models import EvidenceMemory
from league.models import Company

KPI_TYPES = pathlib.Path(settings.BASE_DIR) / 'frontend/web/src/types/kpi.ts'


def declared_type(interface: str, field: str) -> str | None:
    """The declared type of one field, as written in the .ts file."""
    source = KPI_TYPES.read_text(encoding='utf-8')
    block = re.search(rf'export interface {interface} \{{(.*?)^\}}',
                      source, re.S | re.M)
    if not block:
        return None
    found = re.search(rf'^\s*{field}\??:\s*([^;]+);', block.group(1), re.M)
    return found.group(1).strip() if found else None


class TypeFileReadableTests(TestCase):
    def test_the_type_file_is_where_this_expects(self):
        """If it moves, every assertion below silently stops guarding."""
        self.assertTrue(KPI_TYPES.exists(), f'{KPI_TYPES} is missing')

    def test_the_interface_can_be_parsed(self):
        self.assertIsNotNone(declared_type('KpiEvidence', 'id'))


class NullableFieldsAreDeclaredNullableTests(TestCase):
    """
    Every field the API can send as null must say so in the type.
    """

    def setUp(self):
        self.company = Company.objects.create(name='Testco', slug='testco')
        self.profile = CompanyProfile.objects.create(company=self.company)
        self.assessment = CompanyKPIAssessment.objects.create(
            company=self.profile, kpi_id=114)
        # No harvester lineage and no human-written reference: the shape whose
        # title resolves to null, which is what crashed production.
        evidence = EvidenceMemory.objects.create(
            text_chunk='Body.', source_reference='harvester.Evidence:999999',
            source_type='harvester_evidence', source_url='https://example.org/x',
            company=self.profile, date_collected=datetime.date(2026, 1, 1),
            is_demo=False)
        CompanyKPIEvidenceLink.objects.create(
            assessment=self.assessment, evidence=evidence,
            relationship='supports', review_state='confirmed')

    def payload(self):
        return self.client.get('/api/v2/companies/testco/kpis/114/').json()

    def test_the_api_really_can_send_a_null_title(self):
        """The premise. If this stops being true the guard below is moot."""
        self.assertIsNone(self.payload()['evidence'][0]['title'])

    def test_title_is_declared_nullable(self):
        declared = declared_type('KpiEvidence', 'title')
        self.assertIsNotNone(declared, 'KpiEvidence.title is not declared')
        self.assertIn(
            'null', declared,
            f'The API can send a null title but TypeScript declares it '
            f'{declared!r}. That is what let `title.split()` compile and crash '
            f'the investigation page.')

    def test_every_nullable_payload_field_is_nullable_in_the_type(self):
        """
        Generic version of the same rule: whatever the API actually sends as
        null on a real response must be declared nullable.
        """
        evidence = self.payload()['evidence'][0]
        for field, value in evidence.items():
            if value is not None or field == 'provenance':
                continue
            declared = declared_type('KpiEvidence', field)
            if declared is None:
                continue  # not declared at all is a separate test
            self.assertIn(
                'null', declared,
                f'API sent null for {field!r} but TypeScript declares it '
                f'{declared!r}')

    def test_provenance_is_declared_since_the_api_sends_it(self):
        """
        It was sent for a whole release without being in the type, so no
        component could read it without an unchecked cast.
        """
        self.assertIn('provenance', self.payload()['evidence'][0])
        source = KPI_TYPES.read_text(encoding='utf-8')
        self.assertIn('EvidenceProvenance', source)
        self.assertIsNotNone(declared_type('KpiEvidence', 'provenance'))

    def test_the_idempotency_key_is_never_offered_as_a_title(self):
        evidence = self.payload()['evidence'][0]
        self.assertIsNone(evidence['title'])
        self.assertIn('harvester.Evidence:',
                      evidence['provenance']['record_reference'])
