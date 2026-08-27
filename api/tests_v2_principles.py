"""
Tests for the principle registry and the per-company 114 matrix.

The properties under test are the ones that decide whether the matrix can be
trusted as an entry point into an investigation: that every principle stays in
the denominator whether or not anyone has looked at it, that unconfirmed
evidence is visible without counting, that a conflict resting on a final
regulatory finding is distinguishable from one that does not, that remediation
never rewrites a finding, and that no number stands in for an organisation's
overall quality.
"""
import datetime

from django.test import TestCase

from companies.models import CompanyProfile
from company_intelligence.models import (
    CompanyKPIAssessment, CompanyKPIEvidenceLink, KPIRemediationStep,
)
from core.esg_principles_data import PRINCIPLE_CATEGORIES, PRINCIPLES
from company_intelligence.services.kpi_engine import recompute_assessment_status
from evidence_memory.models import EvidenceMemory
from league.models import Company

REGISTRY_URL = '/api/v2/principles/'
MATRIX_URL = '/api/v2/companies/{slug}/principles/'


class RegistryTests(TestCase):
    """The framework itself. No organisation involved."""

    def get(self):
        return self.client.get(REGISTRY_URL)

    def test_every_principle_is_published(self):
        body = self.get().json()
        self.assertEqual(body['total'], 114)
        self.assertEqual(len(body['principles']), 114)

    def test_ids_are_the_canonical_ones(self):
        """
        core.esg_principles_data is the canonical source. Renumbering here
        would create the fourth registry the architecture exists to avoid.
        """
        ids = [p['kpi_id'] for p in self.get().json()['principles']]
        self.assertEqual(ids, [p['id'] for p in PRINCIPLES])

    def test_categories_partition_the_framework(self):
        body = self.get().json()
        self.assertEqual([c['key'] for c in body['categories']],
                         [key for key, _ in PRINCIPLE_CATEGORIES])
        self.assertEqual(sum(c['principle_count'] for c in body['categories']), 114)

    def test_each_principle_carries_its_investigation_question(self):
        """A principle without its question is a label, not a method."""
        for principle in self.get().json()['principles']:
            self.assertTrue(principle['question'],
                            f"principle {principle['kpi_id']} has no question")

    def test_registry_carries_no_organisation_state(self):
        """
        The registry describes the method, so it carries no finding about
        anybody. Asserted on KEYS, not on prose: one of the ten categories is
        literally "Knowledge, Evidence & Truth", and a substring search would
        fail on the framework's own vocabulary.
        """
        body = self.get().json()
        self.assertNotIn('company', body)
        for key in ('verdict', 'confidence', 'state', 'counts', 'summary'):
            self.assertNotIn(key, body, f'registry leaked assessment state: {key!r}')
        for principle in body['principles']:
            for key in ('state', 'verdict', 'confidence', 'counts', 'is_demo'):
                self.assertNotIn(key, principle,
                                 f'principle row leaked assessment state: {key!r}')

    def test_no_sacred_source_material(self):
        """Same boundary as v2_kpi — the mapping is internal."""
        raw = self.get().content.decode()
        for term in ('surah', 'Surah', 'ayah', 'Ayah', 'Qur', 'Arabic'):
            self.assertNotIn(term, raw, f'sacred-source term leaked: {term!r}')

    def test_post_is_refused(self):
        self.assertEqual(self.client.post(REGISTRY_URL).status_code, 405)


class MatrixTestCase(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name='Testco', slug='testco')
        self.profile = CompanyProfile.objects.create(company=self.company)

    def _assessment(self, kpi_id):
        return CompanyKPIAssessment.objects.create(
            company=self.profile, kpi_id=kpi_id, is_demo=True)

    def _evidence(self, ref, *, legal_status='company_policy'):
        return EvidenceMemory.objects.create(
            text_chunk=f'Body of {ref}', source_reference=ref,
            source_url='https://example.org/x', source_type='manual',
            source_authority='Testco', legal_status=legal_status,
            company=self.profile, date_collected=datetime.date(2026, 1, 1),
            verification_status='verified', review_tier='human_reviewed',
            is_demo=True,
        )

    def _link(self, assessment, evidence, relationship, review_state='confirmed'):
        link = CompanyKPIEvidenceLink.objects.create(
            assessment=assessment, evidence=evidence,
            relationship=relationship, review_state=review_state)
        # The app never leaves a stale status after evidence changes; these
        # tests must not either, or they would assert against a state the
        # product cannot actually be in.
        recompute_assessment_status(assessment)
        return link

    def get(self, slug='testco'):
        return self.client.get(MATRIX_URL.format(slug=slug))

    def row(self, kpi_id, body=None):
        body = body or self.get().json()
        return next(r for r in body['principles'] if r['kpi_id'] == kpi_id)


class MatrixRouteTests(MatrixTestCase):

    def test_renders_for_a_known_company(self):
        self.assertEqual(self.get().status_code, 200)

    def test_unknown_company_is_404(self):
        self.assertEqual(self.get(slug='nope').status_code, 404)

    def test_post_is_refused(self):
        self.assertEqual(
            self.client.post(MATRIX_URL.format(slug='testco')).status_code, 405)


class DenominatorTests(MatrixTestCase):
    """
    A principle nobody has looked at stays in the denominator.

    Dropping it would make coverage look better the less work had been done,
    which is the exact inversion this platform exists to prevent.
    """

    def test_all_114_are_returned_for_a_company_with_no_assessments(self):
        body = self.get().json()
        self.assertEqual(len(body['principles']), 114)
        self.assertEqual(body['summary']['total'], 114)
        self.assertEqual(body['summary']['assessed'], 0)
        self.assertEqual(body['summary']['not_assessed'], 114)

    def test_unlooked_at_principles_are_not_assessed_not_zero(self):
        """not_assessed is a statement about us, not a finding about them."""
        row = self.row(1)
        self.assertEqual(row['state'], 'not_assessed')
        self.assertEqual(row['counts']['confirmed'], 0)
        self.assertIsNone(row['last_assessed_at'])

    def test_assessing_one_principle_leaves_the_other_113_untouched(self):
        assessment = self._assessment(114)
        self._link(assessment, self._evidence('E1'), 'supports')
        body = self.get().json()
        self.assertEqual(body['summary']['assessed'], 1)
        self.assertEqual(body['summary']['not_assessed'], 113)
        self.assertEqual(len(body['principles']), 114)


class EvidenceCountingTests(MatrixTestCase):

    def test_unconfirmed_evidence_is_visible_but_excluded(self):
        """
        The same rule v2_kpi applies per item, aggregated per cell: hiding it
        would overstate the evidence, counting it would let unreviewed material
        move a verdict.
        """
        assessment = self._assessment(114)
        self._link(assessment, self._evidence('E1'), 'supports', 'proposed')
        row = self.row(114)
        self.assertEqual(row['counts']['total'], 1)
        self.assertEqual(row['counts']['confirmed'], 0)
        self.assertEqual(row['counts']['excluded_from_assessment'], 1)
        self.assertEqual(row['pending_review_count'], 1)

    def test_a_proposed_link_does_not_move_the_state(self):
        assessment = self._assessment(114)
        self._link(assessment, self._evidence('E1'), 'supports', 'proposed')
        self.assertEqual(self.row(114)['state'], 'insufficient_evidence')

    def test_confirmed_supporting_evidence_is_counted(self):
        assessment = self._assessment(114)
        self._link(assessment, self._evidence('E1'), 'supports')
        row = self.row(114)
        self.assertEqual(row['counts']['confirmed'], 1)
        self.assertEqual(row['counts']['supports'], 1)
        self.assertEqual(row['counts']['excluded_from_assessment'], 0)

    def test_disputed_evidence_stops_counting(self):
        assessment = self._assessment(114)
        link = self._link(assessment, self._evidence('E1'), 'supports')
        link.review_state = 'disputed'
        link.save()
        row = self.row(114)
        self.assertEqual(row['counts']['confirmed'], 0)
        self.assertEqual(row['counts']['excluded_from_assessment'], 1)


class MaterialConflictTests(MatrixTestCase):
    """
    An allegation is not a regulatory finding, and a preliminary finding is a
    regulator's opening position rather than its conclusion. A matrix that
    cannot tell them apart has told the reader very little.
    """

    def _conflict_at(self, legal_status):
        assessment = self._assessment(114)
        self._link(assessment, self._evidence('S', legal_status='company_policy'),
                   'supports')
        self._link(assessment, self._evidence('C', legal_status=legal_status),
                   'conflicts')
        return self.row(114)

    def test_a_final_regulatory_finding_is_material(self):
        self.assertTrue(self._conflict_at('final_regulatory_finding')['has_material_conflict'])

    def test_a_court_finding_is_material(self):
        self.assertTrue(self._conflict_at('court_finding')['has_material_conflict'])

    def test_a_preliminary_finding_is_not_material(self):
        row = self._conflict_at('preliminary_regulatory_finding')
        self.assertFalse(row['has_material_conflict'])
        self.assertEqual(row['state'], 'mixed')

    def test_an_allegation_is_not_material(self):
        self.assertFalse(self._conflict_at('allegation')['has_material_conflict'])

    def test_an_unconfirmed_regulatory_conflict_is_not_material(self):
        """Review state gates materiality too, or the flag becomes a bypass."""
        assessment = self._assessment(114)
        self._link(assessment,
                   self._evidence('C', legal_status='final_regulatory_finding'),
                   'conflicts', 'proposed')
        self.assertFalse(self.row(114)['has_material_conflict'])


class RemediationTests(MatrixTestCase):
    """Remediation is reported alongside a finding, never instead of it."""

    def test_remediation_does_not_change_the_finding(self):
        assessment = self._assessment(114)
        self._link(assessment,
                   self._evidence('C', legal_status='final_regulatory_finding'),
                   'conflicts')
        before = self.row(114)['state']

        KPIRemediationStep.objects.create(
            assessment=assessment, position=1, kind='independent_verification',
            summary='Independently verified', occurred_on=datetime.date(2026, 2, 1),
            verification='independently_verified', is_demo=True)

        after = self.row(114)
        self.assertEqual(after['state'], before,
                         'remediation must not rewrite the historical finding')
        self.assertEqual(after['remediation_step_count'], 1)
        self.assertTrue(after['has_material_conflict'],
                        'the original regulatory conflict remains visible')

    def test_no_remediation_reports_zero_steps(self):
        self._assessment(114)
        self.assertEqual(self.row(114)['remediation_step_count'], 0)


class NoScoreTests(MatrixTestCase):
    """
    §9: the matrix reports evidence state. It must not become a scoreboard.
    """

    def test_the_payload_carries_no_overall_score(self):
        body = self.get().json()
        self.assertNotIn('score', body)
        self.assertNotIn('score', body['summary'])
        self.assertNotIn('rating', body['summary'])

    def test_percentage_is_named_for_what_it_measures(self):
        """
        assessed_pct says how much of the framework has been investigated. A
        key called coverage_pct or score here would read as a verdict.
        """
        summary = self.get().json()['summary']
        self.assertIn('assessed_pct', summary)
        self.assertEqual(summary['assessed_pct'], 0.0)

    def test_no_principle_row_carries_a_numeric_verdict(self):
        assessment = self._assessment(114)
        self._link(assessment, self._evidence('E1'), 'supports')
        row = self.row(114)
        self.assertIsInstance(row['state'], str)
        for key in ('score', 'rating', 'value'):
            self.assertNotIn(key, row)


class ContainmentTests(MatrixTestCase):

    def test_no_sacred_source_material(self):
        self._assessment(114)
        raw = self.get().content.decode()
        for term in ('surah', 'Surah', 'An-Nas', 'an-nas', 'ayah', 'Ayah',
                     'Qur', 'Arabic'):
            self.assertNotIn(term, raw, f'sacred-source term leaked: {term!r}')

    def test_demo_data_is_flagged_as_demo(self):
        """A reader must be able to tell a fixture from a real finding."""
        assessment = self._assessment(114)
        self._link(assessment, self._evidence('E1'), 'supports')
        self.assertTrue(self.row(114)['is_demo'])


class QueryCountTests(MatrixTestCase):
    """
    The matrix is the one endpoint that will be asked about a fully assessed
    organisation. Walking evidence per principle there is 114 queries for a
    page that needs a handful, so the cost must not grow with the number of
    assessed principles.
    """

    def _assess(self, count):
        for kpi_id in range(1, count + 1):
            assessment = self._assessment(kpi_id)
            self._link(assessment, self._evidence(f'E{kpi_id}'), 'supports')

    def test_query_count_does_not_grow_with_assessed_principles(self):
        self._assess(3)
        with self.assertNumQueries(5) as ctx:
            self.get()
        few = len(ctx.captured_queries)

        CompanyKPIAssessment.objects.filter(company=self.profile).delete()
        self._assess(30)
        with self.assertNumQueries(few):
            self.get()


class SacredSourceContainmentAcrossAll114Tests(TestCase):
    """
    The containment rule, checked against every principle rather than one.

    This class exists because the rule was already enforced and already tested
    — but only for principle 114, the single worked example. Six public titles
    (#31, #35, #36, #38, #50, #106) had carried their Surah name into the
    public registry and were served in production for as long as the registry
    had existed, because nothing ever looked at the other 113.

    The term list is derived from `docs/governance-principles-surah-map.md`
    rather than hand-written, so a name nobody thought to add to a literal list
    cannot slip past. That is precisely how the original six survived: the
    existing guard's hardcoded list happened to contain 'Qur' but not 'Luqman',
    'Fatir', 'Ya-Sin', 'Sad' or 'Qaf'.
    """

    MAP = 'docs/governance-principles-surah-map.md'

    @classmethod
    def _surah_names(cls):
        """id -> Surah name, read from the internal map."""
        from pathlib import Path

        from django.conf import settings

        path = Path(settings.BASE_DIR) / cls.MAP
        names = {}
        for line in path.read_text(encoding='utf-8').splitlines():
            cells = [c.strip() for c in line.split('|')]
            if len(cells) >= 6 and cells[1].isdigit():
                names[int(cells[1])] = cells[2]
        return names

    def test_the_map_is_readable_and_complete(self):
        """If this file moves, the guard below silently stops guarding."""
        names = self._surah_names()
        self.assertEqual(len(names), 114,
                         f'expected 114 mapped principles, found {len(names)}')

    def test_no_public_title_contains_its_own_surah_name(self):
        import re

        names = self._surah_names()
        leaked = [
            (p['id'], names[p['id']], p['title'])
            for p in PRINCIPLES
            if names.get(p['id'])
            and re.search(rf"\b{re.escape(names[p['id']])}\b", p['title'])
        ]
        self.assertEqual(
            leaked, [],
            'public principle titles carry their Surah name: '
            + '; '.join(f'#{i} {s!r} in {t!r}' for i, s, t in leaked))

    def test_no_public_field_contains_any_surah_name(self):
        """
        Titles are not the only public field. tagline, question, metrics and
        the analyst signal are all served by /api/v2/principles/ and by the
        investigation endpoint.
        """
        import re

        names = self._surah_names()
        # Single-word English homographs. 'Sad', 'Light', 'Iron' and the like
        # are ordinary words as well as Surah names, so matching them anywhere
        # in prose would fail on sentences that are entirely innocent. The
        # title check above is the strict one; here they would only produce
        # noise.
        homographs = {'Sad', 'Light', 'Iron', 'The Cave', 'Dawn', 'Morning',
                      'Night', 'Sun', 'Moon', 'Star', 'Fig', 'Elephant',
                      'Cattle', 'Bee', 'Ant', 'Spider', 'Smoke', 'Thunder'}
        leaked = []
        for principle in PRINCIPLES:
            surah = names.get(principle['id'], '')
            if not surah or surah in homographs:
                continue
            haystack = ' '.join([
                principle['title'], principle['tagline'], principle['question'],
                principle.get('signal', ''), ' '.join(principle.get('metrics', [])),
            ])
            if re.search(rf'\b{re.escape(surah)}\b', haystack):
                leaked.append((principle['id'], surah))
        self.assertEqual(leaked, [], f'Surah names in public principle text: {leaked}')

    def test_no_arabic_script_anywhere_in_the_public_registry(self):
        """
        The map holds the Arabic column; the public registry must not. A
        codepoint range catches this without needing to enumerate any word.
        """
        import re

        arabic = re.compile(r'[؀-ۿݐ-ݿ]')
        offenders = [
            p['id'] for p in PRINCIPLES
            if arabic.search(' '.join([
                p['title'], p['tagline'], p['question'], p.get('signal', ''),
                ' '.join(p.get('metrics', [])),
            ]))
        ]
        self.assertEqual(offenders, [],
                         f'Arabic script in public principle text: {offenders}')

    def test_the_registry_endpoint_serves_no_surah_name(self):
        """The end-to-end assertion: what actually leaves the server."""
        import re

        raw = self.client.get(REGISTRY_URL).content.decode()
        names = self._surah_names()
        homographs = {'Sad', 'Light', 'Iron', 'The Cave', 'Dawn', 'Morning',
                      'Night', 'Sun', 'Moon', 'Star', 'Fig', 'Elephant',
                      'Cattle', 'Bee', 'Ant', 'Spider', 'Smoke', 'Thunder'}
        leaked = sorted({
            surah for surah in names.values()
            if surah and surah not in homographs
            and re.search(rf'\b{re.escape(surah)}\b', raw)
        })
        self.assertEqual(leaked, [], f'Surah names served publicly: {leaked}')


class SurahDerivedTitleTests(TestCase):
    """
    Public titles that carry their Surah name IN TRANSLATION.

    WHY THIS IS SEPARATE FROM THE TRANSLITERATION GUARD
    ---------------------------------------------------
    SacredSourceContainmentAcrossAll114Tests catches transliterations —
    'Luqman', 'Quraysh', 'Ya-Sin'. It cannot catch translations, because the
    surah map has no translation column, and two of its assertions skip
    ordinary English homographs ('Iron', 'Light', 'Bee') precisely so that
    innocent prose does not trip them.

    The effect was a blind spot: 48 of the 114 public titles were built on the
    English translation of their Surah name, and nothing looked. Principle 57
    is Al-Hadid, 'The Iron', and was titled 'Iron & Infrastructure
    Responsibility'.

    THE POSITION THIS ENCODES
    -------------------------
    Reviewed, and deliberately not "rename everything". A translated common
    noun that reads as ordinary governance English — Iron, Consultation, The
    Pen, Light — is allowed to stand. Thirteen titles that did NOT read that
    way were changed, because 'The Disbelievers & Value Pluralism' and
    'Hypocrites & Integrity Testing' are indefensible on a page shown to an
    investment committee, quite apart from the governance boundary.

    So this asserts an EXACT set rather than an empty one. The thirty-five
    below are a reviewed decision. A new title that derives from a Surah
    translation fails here and has to be looked at; one of these thirty-five
    being renamed away also fails, which is the cheap way to keep the list
    honest rather than letting it rot.
    """

    #: Reviewed 2026-08-27. Translated Surah names judged to read as ordinary
    #: governance English. NOT a licence to add more — see the docstring.
    REVIEWED_DERIVED_TITLES = {
        13, 24, 25, 26, 27, 29, 30, 39, 42, 44, 49, 51,
        53, 54, 56, 57, 61, 67, 68, 69, 88, 89, 90, 91,
        92, 93, 95, 97, 99, 101, 103, 105, 107, 108, 110,
    }

    SEEDS = 'content/tazkiyah114/surah_seeds.json'

    @classmethod
    def _translations(cls):
        """id -> English translation of the Surah name."""
        import json
        from pathlib import Path

        from django.conf import settings

        data = json.loads(
            (Path(settings.BASE_DIR) / cls.SEEDS).read_text(encoding='utf-8'))
        return {
            int(s['surah_number']): s['surah_name_translation'].strip()
            for s in data['surahs']
            if s.get('surah_number') and s.get('surah_name_translation')
        }

    @classmethod
    def _derived(cls):
        import re

        translations = cls._translations()
        found = set()
        for principle in PRINCIPLES:
            translation = translations.get(principle['id'])
            if not translation:
                continue
            # Singular, plural and article-stripped: 'The Ants' must match a
            # title reading 'Ants & Collective Intelligence Systems'.
            forms = {translation, translation.rstrip('s'), translation + 's',
                     translation.replace('The ', '')}
            for form in {f for f in forms if len(f) > 2}:
                if re.search(rf'\b{re.escape(form)}\b', principle['title'], re.I):
                    found.add(principle['id'])
                    break
        return found

    def test_the_translation_source_is_readable(self):
        """If the seed file moves, the guard below silently stops guarding."""
        self.assertEqual(len(self._translations()), 114)

    def test_derived_titles_match_the_reviewed_set(self):
        derived = self._derived()
        new = sorted(derived - self.REVIEWED_DERIVED_TITLES)
        gone = sorted(self.REVIEWED_DERIVED_TITLES - derived)
        by_id = {p['id']: p['title'] for p in PRINCIPLES}
        self.assertEqual(
            (new, gone), ([], []),
            'Surah-derived public titles no longer match the reviewed set.\n'
            f'  NEW (needs review): {[(i, by_id[i]) for i in new]}\n'
            f'  NO LONGER DERIVED (drop from the list): {gone}')

    def test_the_thirteen_renamed_titles_stay_renamed(self):
        """
        The specific names that were judged indefensible in a public ESG
        product. Pinned by id so a well-meaning revert is loud.
        """
        by_id = {p['id']: p['title'] for p in PRINCIPLES}
        for kpi_id, banned in [
            (45, 'Kneeling'), (62, 'Friday'), (63, 'Hypocrites'),
            (65, 'Divorce'), (66, 'Prohibition'), (71, 'Noah'),
            (75, 'Resurrection'), (78, 'Great News'), (82, 'Cleaving'),
            (87, 'The Most High'), (96, 'Clot'), (109, 'Disbelievers'),
            (111, 'Palm Fibre'),
        ]:
            self.assertNotIn(
                banned.lower(), by_id[kpi_id].lower(),
                f'principle #{kpi_id} is titled {by_id[kpi_id]!r} again')
