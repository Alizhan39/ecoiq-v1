"""
What the response cache hands to the next caller.

`cache_response` keyed a cached body by request path alone, on the reasoning —
stated in its own docstring — that "output depends only on the URL, not the
user". That was not true of every view wearing it, and the exception mattered.

`sector_pdf_report` serves twenty-five rows to staff and five to everybody
else. It is a deliberate preview gate, stated in the view's own docstring. With
a path-only key, whichever audience arrived first decided what the other one
got: a staff request populated the key, and the next anonymous visitor to the
same URL was handed the full report, byte for byte, for the rest of the TTL.

A gate the cache in front of it can hand around is not a gate.
"""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.test.utils import override_settings

from companies.models import CompanyProfile
from league.models import Company

SECTOR_URL = '/companies/reports/sector/energy/'


@override_settings(ALLOWED_HOSTS=['*'])
class SectorReportAudienceTests(TestCase):
    """The preview gate, across the cache."""

    def setUp(self):
        cache.clear()
        for i in range(12):
            company = Company.objects.create(
                name=f'Energy Co {i:02d}', slug=f'energy-{i:02d}', sector='energy')
            CompanyProfile.objects.create(
                company=company, status='public', ecoiq_total_score=90 - i)

    def staff_client(self, username):
        get_user_model().objects.create_user(
            username=username, password='x', is_staff=True)
        client = self.client_class()
        client.login(username=username, password='x')
        return client

    def test_a_staff_report_is_not_handed_to_the_next_anonymous_visitor(self):
        staff = self.staff_client('reporter')
        privileged = staff.get(SECTOR_URL).content
        public = self.client.get(SECTOR_URL).content
        self.assertNotEqual(
            privileged, public,
            'An anonymous visitor received the staff report byte for byte. '
            'The preview gate is real; the cache in front of it was not.')

    def test_an_anonymous_preview_is_not_handed_to_staff(self):
        """The same crossing in the other direction — order must not decide."""
        public = self.client.get(SECTOR_URL).content
        staff = self.staff_client('reporter-2')
        privileged = staff.get(SECTOR_URL).content
        self.assertNotEqual(privileged, public)

    def test_the_cache_still_works_within_one_audience(self):
        """
        Non-vacuous in the other direction: keying by audience must not turn
        into keying by user, which would end the caching this decorator exists
        for.
        """
        first = self.client.get(SECTOR_URL).content
        second = self.client_class().get(SECTOR_URL).content
        self.assertEqual(first, second,
                         'two anonymous visitors got separately generated '
                         'bodies — the cache is no longer caching')


@override_settings(ALLOWED_HOSTS=['*'])
class MlInsightsAudienceTests(TestCase):
    """
    The same trap, on the endpoint the visibility fix just made user-dependent.
    Staff may open an archived organisation's ML insights; nobody else may, and
    the cache must not carry it across.
    """

    def setUp(self):
        cache.clear()
        company = Company.objects.create(name='Withdrawn Org', slug='withdrawn-org')
        CompanyProfile.objects.create(company=company, status='archived')

    def url(self):
        return '/companies/withdrawn-org/ml-insights.json'

    def test_a_staff_read_does_not_publish_the_archived_payload(self):
        get_user_model().objects.create_user(
            username='reviewer', password='x', is_staff=True)
        staff = self.client_class()
        staff.login(username='reviewer', password='x')
        self.assertEqual(staff.get(self.url()).status_code, 200)

        self.assertEqual(
            self.client.get(self.url()).status_code, 404,
            'A staff read populated a path-keyed cache and published an '
            'archived organisation to everyone for the rest of the TTL.')

    def test_an_ordinary_account_is_not_staff_here_either(self):
        get_user_model().objects.create_user(username='ordinary', password='x')
        client = self.client_class()
        client.login(username='ordinary', password='x')
        self.assertEqual(client.get(self.url()).status_code, 404)
