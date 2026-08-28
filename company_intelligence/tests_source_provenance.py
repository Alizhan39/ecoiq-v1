"""
Provenance of an evidence record, and the two counter systems that must not be
confused with each other.

These pin the defects the first real production ingestion exposed: an evidence
item served with the title `harvester.Evidence:41`, and a platform that could
truthfully report both "11 real evidence records" and "0 evidenced
organisations" without saying they measured different things.
"""
import datetime

from django.test import TestCase
from django.utils import timezone

from companies.models import CompanyProfile
from company_intelligence.models import CompanyKPIAssessment, CompanyKPIEvidenceLink
from company_intelligence.services.source_provenance import (
    display_title, provenance_for_memory,
)
from evidence_memory.models import EvidenceMemory
from harvester.models import Evidence as HarvesterEvidence, Source, SourceDocument
from league.models import Company


class ProvenanceTestCase(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Testco', slug='testco')
        self.profile = CompanyProfile.objects.create(company=self.company)

    def _lineage(self, *, source_type='sustainability_report', title='Testco Report 2026',
                 publisher='Testco Inc.', published=datetime.date(2026, 3, 1),
                 location='Section: Emissions', content_hash='abc123',
                 url='https://testco.example/sustainability'):
        source = Source.objects.create(
            name='Testco sustainability', source_type=source_type,
            source_url=url, source_owner=publisher, company=self.profile)
        document = SourceDocument.objects.create(
            source=source, company=self.profile, company_slug='testco',
            title=title, document_type=source_type, publisher=publisher,
            url=url, publication_date=published, content_hash=content_hash)
        evidence = HarvesterEvidence.objects.create(
            company=self.profile, company_slug='testco', source=source,
            document=document, title=title, url=document.url,
            publication_date=published, source_location=location,
            excerpt='Body text.', category='environmental',
            document_type=source_type, content_hash=content_hash)
        return evidence

    def _memory(self, evidence):
        return EvidenceMemory.objects.create(
            text_chunk=evidence.excerpt, source_type='harvester_evidence',
            source_reference=f'harvester.Evidence:{evidence.pk}',
            source_url=evidence.url, company=self.profile,
            date_collected=evidence.publication_date, is_demo=False)


class TitleTests(ProvenanceTestCase):
    """
    `source_reference` is the idempotency key create_memory_from_evidence()
    writes. Rendering it as a title is what produced `harvester.Evidence:41` on
    the first real production evidence item.
    """

    def test_the_source_title_survives_ingestion(self):
        memory = self._memory(self._lineage())
        self.assertEqual(display_title(memory), 'Testco Report 2026')

    def test_the_idempotency_key_is_never_the_title(self):
        memory = self._memory(self._lineage())
        self.assertNotIn('harvester.Evidence:', display_title(memory) or '')

    def test_the_key_is_still_exposed_as_the_key(self):
        """Losing it would remove the only handle on the record's identity."""
        memory = self._memory(self._lineage())
        provenance = provenance_for_memory(memory)
        self.assertTrue(provenance['record_reference'].startswith('harvester.Evidence:'))

    def test_an_untitled_source_yields_no_title_rather_than_a_key(self):
        """
        None, not a fallback. A record whose source recorded no title has none,
        and printing a primary key at a reader is worse than saying so.
        """
        memory = self._memory(self._lineage(title=''))
        self.assertIsNone(display_title(memory))

    def test_a_memory_with_no_harvester_lineage_reports_no_source_record(self):
        memory = EvidenceMemory.objects.create(
            text_chunk='Hand-written fixture.', source_type='manual',
            source_reference='fixture:1', company=self.profile, is_demo=True)
        provenance = provenance_for_memory(memory)
        self.assertFalse(provenance['has_source_record'])
        self.assertIsNone(provenance['publisher'])

    def test_a_human_written_reference_IS_a_title(self):
        """
        The rule is the PATTERN, not the field.

        The first version of this module refused `source_reference` outright,
        which was too blunt: the hand-seeded corpus writes real citations there
        — "European Commission — non-compliance decision" — and refusing them
        left the investigation page with a null title, which crashed it.
        """
        memory = EvidenceMemory.objects.create(
            text_chunk='Body.', source_type='manual',
            source_reference='European Commission — non-compliance decision',
            company=self.profile, is_demo=True)
        self.assertEqual(display_title(memory),
                         'European Commission — non-compliance decision')

    def test_the_harvester_key_is_still_never_a_title(self):
        """The original defect must not return through the new fallback."""
        memory = EvidenceMemory.objects.create(
            text_chunk='Body.', source_type='harvester_evidence',
            source_reference='harvester.Evidence:999999',
            company=self.profile, is_demo=False)
        self.assertIsNone(display_title(memory))

    def test_a_record_with_no_reference_at_all_has_no_title(self):
        memory = EvidenceMemory.objects.create(
            text_chunk='Body.', source_type='manual', source_reference='',
            company=self.profile, is_demo=True)
        self.assertIsNone(display_title(memory))


class SourceMetadataTests(ProvenanceTestCase):

    def test_publisher_survives_ingestion(self):
        memory = self._memory(self._lineage(publisher='Testco Inc.'))
        self.assertEqual(provenance_for_memory(memory)['publisher'], 'Testco Inc.')

    def test_publication_date_survives_ingestion(self):
        memory = self._memory(self._lineage())
        self.assertEqual(provenance_for_memory(memory)['publication_date'], '2026-03-01')

    def test_an_undated_source_reports_null_not_today(self):
        """
        The freshness of an undated document is unknown. Substituting the
        retrieval date would silently make every scraped page look current.
        """
        memory = self._memory(self._lineage(published=None))
        provenance = provenance_for_memory(memory)
        self.assertIsNone(provenance['publication_date'])
        self.assertIsNotNone(provenance['retrieved_at'])

    def test_the_page_or_section_reference_survives(self):
        """What makes a citation checkable rather than pointing at a whole report."""
        memory = self._memory(self._lineage(location='Section: Emissions'))
        self.assertEqual(provenance_for_memory(memory)['location'], 'Section: Emissions')

    def test_the_content_hash_survives(self):
        """Establishes 'reviewed against this version of this source'."""
        memory = self._memory(self._lineage(content_hash='deadbeef'))
        self.assertEqual(provenance_for_memory(memory)['content_hash'], 'deadbeef')

    def test_retrieval_time_is_always_present_for_harvested_evidence(self):
        memory = self._memory(self._lineage())
        self.assertIsNotNone(provenance_for_memory(memory)['retrieved_at'])


class AuthorityTests(ProvenanceTestCase):
    """
    Derived from what the source IS, via the canonical tier table — never from
    how its prose reads.
    """

    def test_a_regulatory_filing_is_tier_one(self):
        memory = self._memory(self._lineage(source_type='sec_edgar'))
        authority = provenance_for_memory(memory)['authority']
        self.assertEqual(authority['tier'], 1)
        self.assertEqual(authority['class'], 'REGULATOR_OR_STATUTORY_FILING')

    def test_a_company_sustainability_page_is_not_regulatory(self):
        """
        The exact case production produced: Walmart's own sustainability page.
        Real evidence, genuinely useful, and not a regulator saying anything.
        """
        memory = self._memory(self._lineage(source_type='sustainability_report'))
        authority = provenance_for_memory(memory)['authority']
        self.assertEqual(authority['tier'], 2)
        self.assertEqual(authority['class'], 'COMPANY_REPORTED')

    def test_an_unmapped_source_type_falls_to_the_conservative_tier(self):
        """Never a middle tier for something nobody classified."""
        memory = self._memory(self._lineage(source_type='some_blog'))
        authority = provenance_for_memory(memory)['authority']
        self.assertEqual(authority['tier'], 4)
        self.assertFalse(authority['classified'])

    def test_a_mapped_tier_four_is_distinguishable_from_an_unmapped_one(self):
        """Both are Tier 4; only one was actually a decision."""
        mapped = provenance_for_memory(
            self._memory(self._lineage(source_type='press_release')))['authority']
        self.assertEqual(mapped['tier'], 4)
        self.assertTrue(mapped['classified'])

    def test_authority_ignores_the_text_entirely(self):
        """
        Formal-sounding prose must not promote a source. Same type, wildly
        different body text, identical authority.
        """
        plain = self._lineage(source_type='company_website', title='A',
                              url='https://testco.example/a', content_hash='a1')
        memory_a = self._memory(plain)
        memory_a.text_chunk = 'we try hard'
        memory_a.save()

        formal = self._lineage(source_type='company_website', title='B',
                               url='https://testco.example/b', content_hash='b1')
        memory_b = self._memory(formal)
        memory_b.text_chunk = ('PURSUANT TO REGULATION (EU) 2019/2088 THE '
                               'UNDERSIGNED HEREBY CERTIFIES COMPLIANCE')
        memory_b.save()

        self.assertEqual(provenance_for_memory(memory_a)['authority'],
                         provenance_for_memory(memory_b)['authority'])


class ReviewStateTests(ProvenanceTestCase):
    """Richer provenance must not move anything toward being believed."""

    def test_real_evidence_does_not_become_confirmed_automatically(self):
        evidence = self._lineage()
        memory = self._memory(evidence)
        assessment = CompanyKPIAssessment.objects.create(
            company=self.profile, kpi_id=103)
        link = CompanyKPIEvidenceLink.objects.create(
            assessment=assessment, evidence=memory,
            relationship='supports', review_state='proposed')

        provenance = provenance_for_memory(memory)
        self.assertTrue(provenance['has_source_record'])
        self.assertEqual(provenance['authority']['tier'], 2)
        # Full provenance, still proposed, still not counted.
        link.refresh_from_db()
        self.assertEqual(link.review_state, 'proposed')
        assessment.refresh_from_db()
        self.assertEqual(assessment.status, 'not_assessed')

    def test_demo_and_real_evidence_stay_distinguishable(self):
        real = self._memory(self._lineage())
        demo = EvidenceMemory.objects.create(
            text_chunk='Fixture.', source_type='manual', source_reference='fixture:2',
            company=self.profile, is_demo=True)
        self.assertFalse(provenance_for_memory(real)['is_demo'])
        self.assertTrue(provenance_for_memory(demo)['is_demo'])


class DeduplicationTests(ProvenanceTestCase):
    """
    The production run reported `ingestion=unchanged` on a second pass. Richer
    provenance must not break that.
    """

    def test_promotion_is_idempotent_on_the_source_reference(self):
        from evidence_memory.services.memory import create_memory_from_evidence

        evidence = self._lineage()
        first = create_memory_from_evidence(evidence)
        second = create_memory_from_evidence(evidence)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(
            EvidenceMemory.objects.filter(
                source_reference=f'harvester.Evidence:{evidence.pk}').count(), 1)

    def test_two_distinct_documents_stay_two_records(self):
        """Dedup must not merge genuinely different sources."""
        from evidence_memory.services.memory import create_memory_from_evidence

        a = create_memory_from_evidence(
            self._lineage(title='Report A', url='https://testco.example/a',
                          content_hash='aaa'))
        b = create_memory_from_evidence(
            self._lineage(title='Report B', url='https://testco.example/b',
                          content_hash='bbb'))
        self.assertNotEqual(a.pk, b.pk)

    def test_document_identity_is_a_database_constraint(self):
        """
        `SourceDocument` is UNIQUE on (company_slug, url, content_hash). That is
        the canonical document identity, enforced by the database rather than by
        convention — the same URL fetched again with unchanged content cannot
        become a second document, which is what makes a re-run report
        `ingestion=unchanged` rather than duplicating a report.
        """
        from django.db import IntegrityError, transaction

        self._lineage(url='https://testco.example/same', content_hash='same')
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._lineage(url='https://testco.example/same', content_hash='same')

    def test_a_changed_document_is_a_new_version_not_a_duplicate(self):
        """
        Same URL, different content hash — a revised report. Two records is
        correct: the reviewer confirmed the earlier one against text that no
        longer stands, and collapsing them would hide that.
        """
        from evidence_memory.services.memory import create_memory_from_evidence

        first = create_memory_from_evidence(
            self._lineage(url='https://testco.example/report', content_hash='v1'))
        second = create_memory_from_evidence(
            self._lineage(url='https://testco.example/report', content_hash='v2'))
        self.assertNotEqual(first.pk, second.pk)
        self.assertNotEqual(provenance_for_memory(first)['content_hash'],
                            provenance_for_memory(second)['content_hash'])


class CounterSeparationTests(TestCase):
    """
    Production could truthfully report 11 real evidence records AND 0 evidenced
    organisations, because the two counters measure different systems. They must
    say which system they mean rather than being summed into a number that
    describes neither.
    """

    def setUp(self):
        self.company = Company.objects.create(name='Testco', slug='testco')
        self.profile = CompanyProfile.objects.create(company=self.company)

    def _stats(self):
        from platform_registry.stats import platform_stats
        return platform_stats()

    def test_both_counter_systems_are_present(self):
        stats = self._stats()
        for key in ('investigation_evidence_records',
                    'investigation_evidence_awaiting_review',
                    'investigation_evidence_confirmed',
                    'organisations_under_investigation'):
            self.assertIn(key, stats)
        # The legacy composite-score layer is still reported, not removed.
        self.assertIn('provenance_rows_current', stats)
        self.assertIn('companies_with_evidence', stats)

    def test_each_counter_names_the_system_it_measures(self):
        stats = self._stats()
        self.assertIn('investigation',
                      stats['investigation_evidence_records'].derivation.lower())
        self.assertIn('composite-score',
                      stats['provenance_rows_current'].derivation.lower())

    def test_investigation_evidence_is_counted_without_touching_score_provenance(self):
        evidence = EvidenceMemory.objects.create(
            text_chunk='Real.', source_type='harvester_evidence',
            source_reference='harvester.Evidence:999',
            company=self.profile, is_demo=False)
        assessment = CompanyKPIAssessment.objects.create(
            company=self.profile, kpi_id=103)
        CompanyKPIEvidenceLink.objects.create(
            assessment=assessment, evidence=evidence,
            relationship='supports', review_state='proposed')

        stats = self._stats()
        self.assertEqual(stats['investigation_evidence_records'].value, 1)
        self.assertEqual(stats['investigation_evidence_awaiting_review'].value, 1)
        self.assertEqual(stats['investigation_evidence_confirmed'].value, 0)
        # The composite-score layer is untouched by an investigation record.
        self.assertEqual(stats['companies_with_evidence'].value, 0)

    def test_awaiting_review_and_confirmed_are_never_the_same_number(self):
        """
        The distinction the whole truth model rests on. A counter that summed
        them would report unreviewed material as established.
        """
        evidence = EvidenceMemory.objects.create(
            text_chunk='Real.', source_type='harvester_evidence',
            source_reference='harvester.Evidence:1000',
            company=self.profile, is_demo=False)
        assessment = CompanyKPIAssessment.objects.create(
            company=self.profile, kpi_id=16)
        CompanyKPIEvidenceLink.objects.create(
            assessment=assessment, evidence=evidence,
            relationship='supports', review_state='proposed')
        stats = self._stats()
        self.assertNotEqual(stats['investigation_evidence_awaiting_review'].value,
                            stats['investigation_evidence_confirmed'].value)

    def test_demo_evidence_is_excluded_from_the_real_counters(self):
        EvidenceMemory.objects.create(
            text_chunk='Fixture.', source_type='manual', source_reference='fixture:3',
            company=self.profile, is_demo=True)
        self.assertEqual(self._stats()['investigation_evidence_records'].value, 0)

    def test_an_empty_platform_reports_zero_not_null(self):
        """
        A real measured count of zero. Distinct from `projects_total`, which is
        null when there is genuinely nothing to measure — the two must not be
        rendered the same way.
        """
        stats = self._stats()
        self.assertEqual(stats['investigation_evidence_records'].value, 0)
        self.assertIsNone(stats['projects_total'].value)
