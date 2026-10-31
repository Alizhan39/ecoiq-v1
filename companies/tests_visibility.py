"""
Who may see an archived organisation.

Two failures, running in opposite directions, from one rule that was written out
in four places and skipped in two:

  - an archived organisation's full evidence chain answered 200 to an anonymous
    caller on the KPI and matrix endpoints, while the page built on them 404'd
    for everybody;

  - a staff reviewer could not open an archived organisation's investigation at
    all, which made the evidence candidates in their own queue unexaminable.

Not public and not reviewable are different decisions. Only the first was ever
intended.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase

from companies.models import CompanyProfile
from companies.visibility import (
    PUBLICLY_VISIBLE_STATUSES, can_see_every_status, visible_statuses,
)
from company_intelligence.models import CompanyKPIAssessment
from league.models import Company

KPI_URL = '/api/v2/companies/{slug}/kpis/114/'
MATRIX_URL = '/api/v2/companies/{slug}/principles/'
PAGE_URL = '/companies/{slug}/'
INVESTIGATION_URL = '/companies/{slug}/kpis/114/'

ALL_SURFACES = (KPI_URL, MATRIX_URL, PAGE_URL, INVESTIGATION_URL)


class VisibilityTestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user(
            username='reviewer', password='x', is_staff=True)
        self.member = User.objects.create_user(username='member', password='x')

        self.archived_company = Company.objects.create(
            name='Archived Co', slug='archived-co')
        self.archived = CompanyProfile.objects.create(
            company=self.archived_company, status='archived')
        CompanyKPIAssessment.objects.create(company=self.archived, kpi_id=114)

        self.public_company = Company.objects.create(
            name='Public Co', slug='public-co')
        self.public = CompanyProfile.objects.create(
            company=self.public_company, status='public')
        CompanyKPIAssessment.objects.create(company=self.public, kpi_id=114)


class RuleTests(VisibilityTestCase):

    def test_archived_is_not_publicly_visible(self):
        self.assertNotIn('archived', PUBLICLY_VISIBLE_STATUSES)

    def test_staff_are_unrestricted(self):
        self.assertTrue(can_see_every_status(self.staff))
        self.assertIsNone(visible_statuses(self.staff))

    def test_a_signed_in_non_staff_user_is_still_the_public(self):
        """
        Being logged in is not being a reviewer. Otherwise any account could
        read withdrawn profiles.
        """
        self.assertFalse(can_see_every_status(self.member))
        self.assertEqual(visible_statuses(self.member), PUBLICLY_VISIBLE_STATUSES)

    def test_anonymous_is_restricted(self):
        self.assertEqual(visible_statuses(None), PUBLICLY_VISIBLE_STATUSES)


class AnonymousTests(VisibilityTestCase):
    """The leak: archived evidence must not be served to the public."""

    def test_every_surface_refuses_an_archived_organisation(self):
        for url in ALL_SURFACES:
            with self.subTest(url=url):
                response = self.client.get(url.format(slug='archived-co'))
                self.assertEqual(response.status_code, 404,
                                 f'{url} served an archived organisation')

    def test_the_kpi_endpoint_no_longer_leaks(self):
        """
        This one had no status filter at all — the original hole.
        """
        self.assertEqual(
            self.client.get(KPI_URL.format(slug='archived-co')).status_code, 404)

    def test_the_matrix_endpoint_no_longer_leaks(self):
        """And this one inherited the hole when it was added."""
        self.assertEqual(
            self.client.get(MATRIX_URL.format(slug='archived-co')).status_code, 404)

    def test_a_public_organisation_is_unaffected(self):
        for url in ALL_SURFACES:
            with self.subTest(url=url):
                self.assertEqual(
                    self.client.get(url.format(slug='public-co')).status_code, 200)

    def test_refusal_is_404_not_403(self):
        """
        Whether an archived organisation exists is itself not public, and a 403
        would confirm it. Both a withdrawn and an invented slug answer the same.
        """
        archived = self.client.get(KPI_URL.format(slug='archived-co'))
        invented = self.client.get(KPI_URL.format(slug='no-such-company'))
        self.assertEqual(archived.status_code, invented.status_code)
        self.assertEqual(archived.status_code, 404)


class SignedInNonStaffTests(VisibilityTestCase):

    def setUp(self):
        super().setUp()
        self.client.force_login(self.member)

    def test_an_ordinary_account_still_cannot_see_archived(self):
        for url in ALL_SURFACES:
            with self.subTest(url=url):
                self.assertEqual(
                    self.client.get(url.format(slug='archived-co')).status_code, 404)


class StaffReviewTests(VisibilityTestCase):
    """
    Not public must not mean not reviewable. The evidence candidates in a
    reviewer's queue belong to organisations they must be able to open.
    """

    def setUp(self):
        super().setUp()
        self.client.force_login(self.staff)

    def test_staff_can_reach_an_archived_organisation_on_every_surface(self):
        for url in ALL_SURFACES:
            with self.subTest(url=url):
                response = self.client.get(url.format(slug='archived-co'))
                self.assertEqual(response.status_code, 200,
                                 f'{url} blocked a reviewer')

    def test_staff_see_the_real_evidence_chain_not_a_stub(self):
        body = self.client.get(KPI_URL.format(slug='archived-co')).json()
        self.assertEqual(body['company']['slug'], 'archived-co')
        self.assertIn('chain', body)
        self.assertIn('evidence', body)

    def test_staff_see_the_matrix_for_an_archived_organisation(self):
        body = self.client.get(MATRIX_URL.format(slug='archived-co')).json()
        self.assertEqual(body['summary']['total'], 114)

    def test_a_genuinely_unknown_slug_is_still_404_for_staff(self):
        """The bypass widens which statuses resolve, not which slugs exist."""
        self.assertEqual(
            self.client.get(KPI_URL.format(slug='no-such-company')).status_code, 404)


class NoRegressionTests(VisibilityTestCase):
    """
    The published statuses behave exactly as before for everyone.
    """

    def test_draft_remains_publicly_visible(self):
        company = Company.objects.create(name='Draft Co', slug='draft-co')
        CompanyProfile.objects.create(company=company, status='draft')
        self.assertEqual(self.client.get(PAGE_URL.format(slug='draft-co')).status_code, 200)

    def test_verified_remains_publicly_visible(self):
        company = Company.objects.create(name='Verified Co', slug='verified-co')
        CompanyProfile.objects.create(company=company, status='verified')
        self.assertEqual(
            self.client.get(PAGE_URL.format(slug='verified-co')).status_code, 200)
