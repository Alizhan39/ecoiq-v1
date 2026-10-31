"""
The league PDF, for an organisation whose pillars have never been scored.

TWO DEFECTS, ONE CAUSE
----------------------
`_stub_recommendations` compared each pillar score against a threshold:

    if company.score_pollution_footprint < 60:

Most organisations carry no pillar scores, so for them that raised

    TypeError: '<' not supported between instances of 'NoneType' and 'int'

and /league/<slug>/report.pdf returned a 500 to anonymous callers.

Coercing the unknown to 0 would have been worse than the crash — every
recommendation would fire, and the report would tell a reader that an
organisation nobody has assessed has a critical pollution-monitoring gap.

So unknown pillars produce no recommendation. Which surfaced the second
defect: the empty state read "No critical recommendations — company scores
above threshold on all pillars", reporting silence as a clean bill of health
for an organisation that had never been measured.
"""
from django.test import TestCase
from django.test.utils import override_settings

from league.models import Company
from league.views import _below, _stub_recommendations, unassessed_pillars

PILLARS = ('score_pollution_footprint', 'score_reduction_progress',
           'score_investment', 'score_transparency', 'score_community_impact')


class BelowTests(TestCase):
    """UNKNOWN is not a gap, and 0 is not unknown."""

    def test_a_measured_score_under_the_threshold_is_a_gap(self):
        self.assertTrue(_below(40, 60))

    def test_a_measured_score_over_the_threshold_is_not(self):
        self.assertFalse(_below(80, 60))

    def test_an_unknown_score_is_not_a_gap(self):
        self.assertFalse(
            _below(None, 60),
            'An unmeasured pillar was treated as a measured deficiency.')

    def test_a_measured_zero_IS_a_gap(self):
        """
        The other half of the same rule. Treating 0 as absent would hide the
        worst genuine score there is.
        """
        self.assertTrue(_below(0, 60))

    def test_the_boundary_is_not_a_gap(self):
        self.assertFalse(_below(60, 60))


class RecommendationTests(TestCase):

    def test_an_unscored_organisation_produces_no_recommendation(self):
        company = Company.objects.create(name='Unscored', slug='unscored')
        for pillar in PILLARS:
            self.assertIsNone(getattr(company, pillar),
                              f'{pillar} defaulted to a value; test is moot')
        self.assertEqual(_stub_recommendations(company, []), [])

    def test_a_genuinely_weak_organisation_still_gets_them(self):
        """
        The control. Without it, returning nothing for everyone would pass the
        test above while removing the feature.
        """
        company = Company.objects.create(
            name='Weak', slug='weak',
            **{pillar: 10 for pillar in PILLARS})
        self.assertTrue(_stub_recommendations(company, []))

    def test_a_strong_organisation_gets_none_either(self):
        company = Company.objects.create(
            name='Strong', slug='strong',
            **{pillar: 95 for pillar in PILLARS})
        self.assertEqual(_stub_recommendations(company, []), [])


class UnassessedPillarTests(TestCase):
    """What lets the report tell those last two cases apart."""

    def test_every_pillar_is_named_when_nothing_is_scored(self):
        company = Company.objects.create(name='Unscored', slug='unscored')
        self.assertEqual(len(unassessed_pillars(company)), len(PILLARS))

    def test_nothing_is_named_when_everything_is_scored(self):
        company = Company.objects.create(
            name='Strong', slug='strong', **{pillar: 95 for pillar in PILLARS})
        self.assertEqual(unassessed_pillars(company), [])

    def test_a_zero_is_assessed(self):
        company = Company.objects.create(
            name='Zeroed', slug='zeroed', **{pillar: 0 for pillar in PILLARS})
        self.assertEqual(unassessed_pillars(company), [])

    def test_a_partially_scored_organisation_names_only_the_gaps(self):
        company = Company.objects.create(
            name='Partial', slug='partial', score_pollution_footprint=70)
        named = unassessed_pillars(company)
        self.assertNotIn('Pollution footprint', named)
        self.assertIn('Transparency', named)


@override_settings(ALLOWED_HOSTS=['*'])
class ReportRendersTests(TestCase):
    """End to end: the page that used to 500."""

    def test_the_pdf_route_does_not_crash_for_an_unscored_organisation(self):
        Company.objects.create(name='Unscored', slug='unscored')
        response = self.client.get('/league/unscored/report.pdf')
        self.assertEqual(
            response.status_code, 200,
            'The league PDF still fails for an organisation with no pillar '
            'scores, which is most of them.')
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertEqual(response.content[:4], b'%PDF')

    def test_it_still_renders_for_a_scored_organisation(self):
        Company.objects.create(name='Scored', slug='scored',
                               **{pillar: 45 for pillar in PILLARS})
        response = self.client.get('/league/scored/report.pdf')
        self.assertEqual(response.status_code, 200)


class EmptyStateWordingTests(TestCase):
    """
    The template must not report "not measured" as "above threshold".
    """

    def test_the_template_distinguishes_the_two_empty_cases(self):
        import pathlib

        from django.conf import settings

        body = (pathlib.Path(settings.BASE_DIR)
                / 'templates/league/report_pdf.html').read_text()
        self.assertIn('unassessed_pillars', body)
        self.assertIn('have not been assessed', body)
        # The old sentence survives for the case it is actually true of.
        self.assertIn('above threshold on all pillars', body)
