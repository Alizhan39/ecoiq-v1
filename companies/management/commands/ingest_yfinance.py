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
from core.unknown import known
import datetime
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

# slug → explicit TradingView exchange code. Populated for every ticker in
# TICKER_MAP above so the stock chart link never has to guess an exchange
# from the Yahoo ticker suffix (league.Company.tradingview_symbol falls back
# to suffix-guessing only for companies NOT in this map).
EXCHANGE_MAP = {
    # LSE
    'national-grid': 'LSE', 'sse': 'LSE', 'centrica': 'LSE', 'rolls-royce': 'LSE',
    'bae-systems': 'LSE', 'drax-group': 'LSE', 'croda-international': 'LSE',
    'johnson-matthey': 'LSE', 'balfour-beatty': 'LSE', 'severn-trent': 'LSE',
    'united-utilities': 'LSE', 'anglo-american': 'LSE', 'fresnillo': 'LSE',
    'hsbc': 'LSE', 'barclays': 'LSE', 'lloyds-banking-group': 'LSE',
    'natwest-group': 'LSE', 'iag-british-airways': 'LSE', 'easyjet': 'LSE',
    'kazatomprom': 'LSE', 'air-astana': 'LSE', 'shell': 'LSE', 'bp': 'LSE',
    # Tadawul
    'saudi-aramco': 'TADAWUL', 'acwa-power': 'TADAWUL', 'al-rajhi-bank': 'TADAWUL',
    'saudi-national-bank': 'TADAWUL', 'maaden': 'TADAWUL', 'almarai': 'TADAWUL',
    'sabic': 'TADAWUL', 'saudi-telecom': 'TADAWUL', 'riyad-bank': 'TADAWUL',
    # NASDAQ
    'kaspi-kz': 'NASDAQ', 'microsoft': 'NASDAQ', 'apple': 'NASDAQ',
    'tesla': 'NASDAQ', 'amazon': 'NASDAQ',
    # NYSE
    'equinor': 'NYSE', 'vale': 'NYSE', 'arcelormittal': 'NYSE', 'exxonmobil': 'NYSE',
    'chevron': 'NYSE', 'freeport-mcmoran': 'NYSE', 'newmont': 'NYSE',
    'blackrock': 'NYSE', 'jpmorgan': 'NYSE',
    # Euronext Paris / Amsterdam
    'totalenergies': 'EURONEXT', 'airbus': 'EURONEXT', 'bnp-paribas': 'EURONEXT',
    'schneider-electric': 'EURONEXT', 'ing-group': 'EURONEXT',
    # Xetra / Frankfurt
    'volkswagen': 'XETR', 'deutsche-bank': 'XETR', 'siemens': 'XETR',
    # Milan / Madrid / Copenhagen
    'enel': 'MIL', 'iberdrola': 'BME', 'orsted': 'OMXCOP',
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
                current_price = info.get('currentPrice') or info.get('regularMarketPrice')
                previous_close = info.get('previousClose') or info.get('regularMarketPreviousClose')
                day_change_pct = None
                if current_price and previous_close:
                    day_change_pct = (current_price - previous_close) / previous_close * 100
                extracted = {
                    'ticker':            ticker,
                    'price':             current_price,
                    'currency':          info.get('currency'),
                    'market_cap':        info.get('marketCap'),
                    'previous_close':    previous_close,
                    'day_high':          info.get('dayHigh') or info.get('regularMarketDayHigh'),
                    'day_low':           info.get('dayLow') or info.get('regularMarketDayLow'),
                    'week52_high':       info.get('fiftyTwoWeekHigh'),
                    'week52_low':        info.get('fiftyTwoWeekLow'),
                    'day_change_pct':    day_change_pct,
                    'market_status':     info.get('marketState'),
                    'exchange':          EXCHANGE_MAP.get(slug),
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

                # 3. Ticker / stock price / market cap / exchange / OHLC
                # Every field below is only ever set when the source actually returned a
                # value — a failed/partial fetch NEVER clears a previously good value, so
                # stock_price_updated_at always reflects the true age of what's displayed.
                if extracted['ticker'] and company.ticker != extracted['ticker']:
                    company.ticker = extracted['ticker']
                    fields_updated.append('ticker')
                if extracted['exchange'] and company.exchange != extracted['exchange']:
                    company.exchange = extracted['exchange']
                    fields_updated.append('exchange')
                if extracted['price']:
                    company.stock_price = round(extracted['price'], 2)
                    company.stock_price_currency = extracted['currency'] or company.stock_price_currency or 'USD'
                    company.stock_price_updated_at = datetime.datetime.now(datetime.timezone.utc)
                    fields_updated += ['stock_price', 'stock_price_currency', 'stock_price_updated_at']
                if extracted['previous_close']:
                    company.previous_close = round(extracted['previous_close'], 2)
                    fields_updated.append('previous_close')
                if extracted['day_high']:
                    company.day_high = round(extracted['day_high'], 2)
                    fields_updated.append('day_high')
                if extracted['day_low']:
                    company.day_low = round(extracted['day_low'], 2)
                    fields_updated.append('day_low')
                if extracted['week52_high']:
                    company.week52_high = round(extracted['week52_high'], 2)
                    fields_updated.append('week52_high')
                if extracted['week52_low']:
                    company.week52_low = round(extracted['week52_low'], 2)
                    fields_updated.append('week52_low')
                if extracted['day_change_pct'] is not None:
                    company.day_change_pct = round(extracted['day_change_pct'], 2)
                    fields_updated.append('day_change_pct')
                if extracted['market_status']:
                    company.market_status = extracted['market_status']
                    fields_updated.append('market_status')
                if extracted['market_cap']:
                    company.market_cap_usd = int(extracted['market_cap'])
                    fields_updated.append('market_cap_usd')
                if extracted['price'] or extracted['market_cap']:
                    if not company.is_public:
                        company.is_public = True
                        fields_updated.append('is_public')

                # 4. Blend Yahoo ESG into CompanyProfile score (optional)
                if update_scores and extracted['esg_total'] is not None:
                    try:
                        profile = company.profile
                        yahoo_esg = float(extracted['esg_total'])
                        # Yahoo ESG: lower = less risky (inverted from EcoIQ).
                        # Convert: yahoo 10 → EcoIQ ~90, yahoo 50 → EcoIQ ~50
                        yahoo_converted = max(10.0, min(95.0, 100.0 - yahoo_esg))
                        # `or 50.0` blended an INVENTED average into a real
                        # reading and stored the result as a measurement. With
                        # no prior score there is nothing to blend, so the
                        # converted Yahoo figure stands alone rather than being
                        # averaged with a number nobody produced.
                        old_score = known(profile.ecoiq_total_score)
                        blended = (round(yahoo_converted, 1) if old_score is None
                                   else round(old_score * 0.70
                                              + yahoo_converted * 0.30, 1))
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
