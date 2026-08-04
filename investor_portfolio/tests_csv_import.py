"""CSV import validation tests — parsing/validation only, and the view-level confirm step."""
import io
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from investor_portfolio.csv_import import parse_holdings_csv, summarize_rows
from investor_portfolio.models import Holding, Portfolio
from league.models import Company


def _csv_file(text):
    return io.BytesIO(text.encode('utf-8'))


class CsvParsingTests(TestCase):

    def setUp(self):
        Company.objects.create(slug='aapl-co', name='Apple Inc', ticker='AAPL')

    def test_matched_row_by_ticker(self):
        rows = parse_holdings_csv(_csv_file('ticker,quantity\nAAPL,10\n'))
        self.assertEqual(rows[0]['status'], 'matched')
        self.assertEqual(rows[0]['quantity'], '10')

    def test_matched_row_by_company_name_fallback(self):
        rows = parse_holdings_csv(_csv_file('company_name,quantity\nApple Inc,5\n'))
        self.assertEqual(rows[0]['status'], 'matched')

    def test_unmatched_ticker(self):
        rows = parse_holdings_csv(_csv_file('ticker,quantity\nNOPE,10\n'))
        self.assertEqual(rows[0]['status'], 'unmatched')

    def test_invalid_quantity(self):
        rows = parse_holdings_csv(_csv_file('ticker,quantity\nAAPL,not-a-number\n'))
        self.assertEqual(rows[0]['status'], 'invalid')
        self.assertTrue(any('quantity' in e for e in rows[0]['errors']))

    def test_zero_quantity_invalid(self):
        rows = parse_holdings_csv(_csv_file('ticker,quantity\nAAPL,0\n'))
        self.assertEqual(rows[0]['status'], 'invalid')

    def test_missing_ticker_and_name_invalid(self):
        rows = parse_holdings_csv(_csv_file('quantity\n10\n'))
        self.assertEqual(rows[0]['status'], 'invalid')

    def test_invalid_date_format(self):
        rows = parse_holdings_csv(_csv_file('ticker,quantity,acquisition_date\nAAPL,10,not-a-date\n'))
        self.assertEqual(rows[0]['status'], 'invalid')

    def test_duplicate_within_file(self):
        rows = parse_holdings_csv(_csv_file('ticker,quantity\nAAPL,10\nAAPL,5\n'))
        self.assertEqual(rows[0]['status'], 'matched')
        self.assertEqual(rows[1]['status'], 'duplicate')

    def test_duplicate_against_existing_holding(self):
        company = Company.objects.get(slug='aapl-co')
        rows = parse_holdings_csv(_csv_file('ticker,quantity\nAAPL,10\n'), existing_company_ids=[company.pk])
        self.assertEqual(rows[0]['status'], 'duplicate')

    def test_summary_counts(self):
        rows = parse_holdings_csv(_csv_file(
            'ticker,quantity\nAAPL,10\nNOPE,5\nAAPL,3\nBAD,notanum\n'
        ))
        summary = summarize_rows(rows)
        self.assertEqual(summary['total'], 4)
        self.assertEqual(summary['matched'], 1)   # AAPL,10
        self.assertEqual(summary['unmatched'], 1)  # NOPE,5 — valid quantity, no matching company
        self.assertEqual(summary['duplicate'], 1)  # AAPL,3 — repeats AAPL within the same file
        self.assertEqual(summary['invalid'], 1)    # BAD,notanum — quantity fails to parse


class CsvImportViewTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user('importer', password='x')
        self.client = Client(SERVER_NAME='localhost')
        self.client.force_login(self.user)
        self.portfolio = Portfolio.objects.create(owner=self.user, name='Import Test', base_currency='USD')
        Company.objects.create(slug='msft-co', name='Microsoft', ticker='MSFT')

    def test_upload_shows_preview_without_creating_holdings(self):
        csv_content = _csv_file('ticker,quantity,avg_price,currency\nMSFT,5,300,USD\n')
        r = self.client.post(
            reverse('portfolio:portfolio_import_csv', kwargs={'pk': self.portfolio.pk}),
            {'csv_file': csv_content},
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Matched')
        self.assertEqual(Holding.objects.filter(portfolio=self.portfolio).count(), 0)

    def test_confirm_creates_only_matched_rows(self):
        csv_content = _csv_file('ticker,quantity\nMSFT,5\nNOPE,3\n')
        self.client.post(
            reverse('portfolio:portfolio_import_csv', kwargs={'pk': self.portfolio.pk}),
            {'csv_file': csv_content},
        )
        r = self.client.post(reverse('portfolio:portfolio_import_confirm', kwargs={'pk': self.portfolio.pk}), follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Holding.objects.filter(portfolio=self.portfolio).count(), 1)
        self.assertEqual(Holding.objects.get(portfolio=self.portfolio).shares, Decimal('5'))
