"""
What the organisation directory finds, and what it wrongly reports as absent.

An empty result on this product is not a blank screen. The directory says
"organisations", and finding none reads as EcoIQ holding nothing on the one you
searched for — a claim about evidence coverage. Making that claim depend on
whether the reader typed a hyphen is the kind of accidental assertion the rest
of the API exists to avoid.

`name__icontains=q` required the query to appear in the stored name exactly as
typed, whitespace and all. Measured against the real directory: "coca cola"
found nothing while "coca-cola" found the company; a trailing space from a
paste or an autocomplete found nothing; any word order but the stored one found
nothing.

v1 has stripped and tokenised since it was written. v2 is what the React app
actually calls, and it did neither.
"""
from django.test import TestCase
from django.test.utils import override_settings

from companies.models import CompanyProfile
from league.models import Company

URL = '/api/v2/companies/'

NAMES = (
    ('Coca-Cola', 'coca-cola'),
    ('Alphabet / Google', 'alphabet-google'),
    ('Apple', 'apple'),
    ('Energy Co 01', 'energy-01'),
    ('BHP', 'bhp'),
)


@override_settings(ALLOWED_HOSTS=['*'])
class SearchTestCase(TestCase):
    def setUp(self):
        for name, slug in NAMES:
            company = Company.objects.create(name=name, slug=slug, sector='energy')
            CompanyProfile.objects.create(company=company, status='public')

    def found(self, query):
        response = self.client.get(URL, {'q': query})
        self.assertEqual(response.status_code, 200)
        return {row['slug'] for row in response.json()['results']}


class PunctuationTests(SearchTestCase):
    """The sharpest case: the ordinary way to type a real company's name."""

    def test_a_hyphenated_name_is_found_without_the_hyphen(self):
        self.assertIn(
            'coca-cola', self.found('coca cola'),
            'Typing the company name the ordinary way reported that EcoIQ '
            'holds nothing on it.')

    def test_the_hyphenated_spelling_still_works(self):
        self.assertIn('coca-cola', self.found('coca-cola'))

    def test_a_name_with_a_separator_is_found_by_its_words(self):
        self.assertIn('alphabet-google', self.found('alphabet google'))


class WhitespaceTests(SearchTestCase):
    """What a paste or an autocomplete actually puts in the box."""

    def test_a_trailing_space_does_not_hide_the_organisation(self):
        self.assertIn('apple', self.found('apple '))

    def test_a_leading_space_does_not_hide_it_either(self):
        self.assertIn('apple', self.found(' apple'))

    def test_a_doubled_space_between_words_is_tolerated(self):
        self.assertIn('energy-01', self.found('Energy  Co'))

    def test_a_query_of_only_whitespace_narrows_nothing(self):
        """
        Not zero results — no query was really given, so the directory is
        unfiltered. Returning nothing would announce a filter that is not there.
        """
        self.assertEqual(len(self.found('   ')), len(NAMES))


class WordOrderTests(SearchTestCase):
    def test_words_in_a_different_order_still_match(self):
        self.assertIn('energy-01', self.found('Co Energy'))

    def test_every_word_must_still_be_true_of_the_result(self):
        """
        Tokens are ANDed. A directory being narrowed should not widen because
        the reader typed a second word.
        """
        self.assertEqual(self.found('energy apple'), set())

    def test_a_more_specific_query_narrows(self):
        self.assertEqual(self.found('energy 01'), {'energy-01'})


class SlugTests(SearchTestCase):
    def test_an_organisation_is_findable_by_its_slug(self):
        """The slug is what appears in the URL a reader may be pasting back."""
        self.assertIn('coca-cola', self.found('coca-cola'))


class NoWideningTests(SearchTestCase):
    """
    Tokenising must not turn a filter into a way to reach withheld records.
    """

    def setUp(self):
        super().setUp()
        withdrawn = Company.objects.create(name='Withdrawn Energy Co',
                                           slug='withdrawn-energy')
        CompanyProfile.objects.create(company=withdrawn, status='archived')

    def test_search_cannot_surface_an_archived_organisation(self):
        self.assertEqual(self.found('withdrawn'), set())

    def test_a_matching_token_does_not_drag_it_in(self):
        self.assertNotIn('withdrawn-energy', self.found('energy'))


class LiteralCharacterTests(SearchTestCase):
    """
    A LIKE wildcard typed by a reader is a character, not an operator.
    """

    def test_a_percent_sign_is_not_a_wildcard(self):
        self.assertEqual(self.found('%'), set())

    def test_an_underscore_is_not_a_single_character_wildcard(self):
        self.assertEqual(self.found('_'), set())

    def test_a_quote_does_not_break_the_query(self):
        response = self.client.get(URL, {'q': "'"})
        self.assertEqual(response.status_code, 200)
