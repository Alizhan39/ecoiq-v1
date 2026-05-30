"""
ingest_yfinance — Ingest financial + ESG data from Yahoo Finance.

Free, no API key needed.  Uses the yfinance library.
Updates: annual_revenue_usd, description on league.Company.
Optionally blends Yahoo ESG scores into CompanyProfile.ecoiq_total_score.

Usage:
    python manage.py ingest_yfinance
    python manage.py ingest_yfinance --ticker SHEL.L
    python manage.py ingest_yfinance --update-scores
"""
import time
import yfinance as yf
from django.core.management.base import BaseCommand
from companies.models import DataIngestionLog

# Slug → Yahoo Finance ticker symbol
TICKER_MAP = {
    # UK (LSE)
    'national-grid':        'NG.L',
    'sse':                  'SSE.L',
    'centrica':             'CNA.L',
    'rolls-royce':          'RR.L',
    'bae-systems':          'BA.L',
    'drax-group':           'DRX.L',
    'croda-international':  'CRDA.L',
    'johnson-matthey':      'JMAT.L',
    'balfour-beatty':       'BBY.L',
    'severn-trent':         'SVT.L',
    'united-utilities':     'UU.L',
    'anglo-american':       'AAL.L',
    'fresnillo':            'FRES.L',
    'hsbc':                 'HSBA.L',
    'barclays':             'BARC.L',
    'lloyds-banking-group': 'LLOY.L',
    'natwest-group':        'NWG.L',
    'iag-british-airways':  'IAG.L',
    'easyjet':              'EZJ.L',
    # Saudi (Tadawul)
    'saudi-aramco':         '2222.SR',
    'acwa-power':           '2082.SR',
    'al-rajhi-bank':        '1120.SR',
    'saudi-national-bank':  '1180.SR',
    'maaden':               '1211.SR',
    'almarai':              '2280.SR',
    'sabic':                '2010.SR',
    'saudi-telecom':        '7010.SR',
    'riyad-bank':           '1010.SR',
    # Kazakhstan (LSE/NASDAQ listed)
    'kazatomprom':          'KAP.L',
    'kaspi-kz':             'KSPI',
    'air-astana':           'AIRA.L',
    # Global blue-chips
    'shell':                'SHEL.L',
    'bp':                   'BP.L',
    'totalenergies':        'TTE.PA',
    'equinor':              'EQNR',
    'enel':                 'ENEL.MI',
    'iberdrola':            'IBE.MC',
    'vale':                 'VALE',
    'microsoft':            'MSFT',
    'apple':                'AAPL',
    'tesla':                'TSLA',
    'amazon':               'AMZN',
    'volkswagen':           'VOW.DE',
    'airbus':               'AIR.PA',
    'arcelormittal':        'MT',
    'bnp-paribas':          'BNP.PA',
    'deutsche-bank':        'DBK.DE',
    'ing-group':            'INGA.AS',
    'schneider-electric':   'SU.PA',
    'siemens':              'SIE.DE',
    'orsted':               'ORSTED.CO',
    'exxonmobil':           'XOM',
    'chevron':              'CVX',
    'freeport-mcmoran':     'FCX',
    'newmont':              'NEM',
    'blackrock':            'BLK',
    'jpmorgan':             'JPM',
}


class Command(BaseCommand):
    help = 'Ingest financial + ESG data from Yahoo Finance (no API key needed)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ticker', type=str,
            help='Only process this ticker (e.g. SHEL.L)',
        )
        parser.add_argument(
            '--update-scores', action='store_true',
            help='Blend Yahoo ESG scores into CompanyProfile.ecoiq_total_score (70/30 blend)',
        )

    def handle(self, *args, **options):
        from league.models import Company

        target_ticker  = options.get('ticker')
        update_scores  = options['update_scores']

        tickers = (
            {k: v for k, v in TICKER_MAP.items() if v == target_ticker}
            if target_ticker else TICKER_MAP
        )

        ok, skip, err = 0, 0, 0

        for slug, ticker in tickers.items():
            try:
                company = Company.objects.get(slug=slug)
            except Company.DoesNotExist:
                skip += 1
                continue

            try:
                stock = yf.Ticker(ticker)
                info  = stock.info or {}

                # yfinance returns an empty dict or raises on unknown tickers
                if not info or 'regularMarketPrice' not in info and 'currentPrice' not in info and 'marketCap' not in info:
                    self.stdout.write(f'  — {slug} ({ticker}): no market data')
                    skip += 1
                    continue

                esg_raw = info.get('esgScores') or {}
                extracted = {
                    'ticker':            ticker,
                    'market_cap':        info.get('marketCap'),
                    'revenue':           info.get('totalRevenue'),
                    'employees':         info.get('fullTimeEmployees'),
                    'country':           info.get('country'),
                    'sector':            info.get('sector'),
                    'industry':          info.get('industry'),
                    'esg_total':         esg_raw.get('totalEsg'),
                    'esg_environment':   esg_raw.get('environmentScore'),
                    'esg_social':        esg_raw.get('socialScore'),
                    'esg_governance':    esg_raw.get('governanceScore'),
                    'description':       (info.get('longBusinessSummary') or '')[:500],
                }

                fields_updated = []

                # 1. Revenue
                if extracted['revenue'] and not company.annual_revenue_usd:
                    company.annual_revenue_usd = int(extracted['revenue'])
                    fields_updated.append('annual_revenue_usd')

                # 2. Description
                if extracted['description'] and not company.description:
                    company.description = extracted['description']
                    fields_updated.append('description')

                # 3. Blend Yahoo ESG into CompanyProfile score (optional)
                if update_scores and extracted['esg_total'] is not None:
                    try:
                        profile = company.profile
                        yahoo_esg = float(extracted['esg_total'])
                        # Yahoo ESG: lower = less risky (inverted from EcoIQ).
                        # Convert: yahoo 10 → EcoIQ ~90, yahoo 50 → EcoIQ ~50
                        yahoo_converted = max(10.0, min(95.0, 100.0 - yahoo_esg))
                        old_score = float(profile.ecoiq_total_score or 50.0)
                        blended   = round(old_score * 0.70 + yahoo_converted * 0.30, 1)
                        profile.ecoiq_total_score = blended
                        profile.save(update_fields=['ecoiq_total_score'])
                        fields_updated.append('ecoiq_total_score')
                    except Exception:
                        pass   # profile may not exist yet

                if fields_updated:
                    company.save()

                DataIngestionLog.objects.create(
                    company=company,
                    source='yfinance',
                    raw_data=extracted,
                    fields_updated=fields_updated,
                    success=True,
                )

                cap_str = (
                    f'£{extracted["market_cap"]/1e9:.1f}B'
                    if extracted['market_cap'] else '—'
                )
                esg_str = str(extracted['esg_total']) if extracted['esg_total'] else '—'
                self.stdout.write(
                    f'  ✓ {company.name} ({ticker})  '
                    f'Cap:{cap_str}  Yahoo ESG:{esg_str}'
                )
                ok += 1

            except Exception as exc:
                err += 1
                self.stdout.write(self.style.ERROR(f'  ✗ {slug} ({ticker}): {exc}'))
                try:
                    DataIngestionLog.objects.create(
                        company=company,
                        source='yfinance',
                        raw_data={'ticker': ticker},
                        fields_updated=[],
                        success=False,
                        error_msg=str(exc),
                    )
                except Exception:
                    pass

            time.sleep(0.6)   # Polite delay — Yahoo blocks aggressive scrapers

        self.stdout.write(self.style.SUCCESS(
            f'\nyFinance complete — OK:{ok}  Skipped:{skip}  Errors:{err}'
        ))
