"""
ingest_rss_signals — Monitor regulatory & news RSS feeds for company ESG signals.

Detects: fines, penalties, pollution incidents, greenwashing, positive ESG announcements.
Writes DataIngestionLog records with signal_type='harm' or 'positive'.

Usage:
    python manage.py ingest_rss_signals
    python manage.py ingest_rss_signals --days 3   # look back 3 days (default: 7)
"""
import feedparser
import re
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from companies.models import DataIngestionLog


def _word_in(word: str, text: str) -> bool:
    """Return True only if *word* appears as a whole word in *text*."""
    return bool(re.search(r'\b' + re.escape(word) + r'\b', text))

RSS_FEEDS = [
    # UK Regulatory
    {
        'name':   'Environment Agency',
        'url':    'https://www.gov.uk/search/news-and-communications.atom?keywords=enforcement+fine&organisations%5B%5D=environment-agency',
        'signal': 'regulatory_fine',
    },
    {
        'name':   'FCA News',
        'url':    'https://www.fca.org.uk/news/rss.xml',
        'signal': 'financial_regulatory',
    },
    {
        'name':   'HSE Press Releases',
        'url':    'https://press.hse.gov.uk/feed/',
        'signal': 'safety_regulatory',
    },
    # ESG / Climate news
    {
        'name':   'Carbon Brief',
        'url':    'https://www.carbonbrief.org/feed/',
        'signal': 'climate_news',
    },
    {
        'name':   'Reuters Business',
        'url':    'https://feeds.reuters.com/reuters/businessNews',
        'signal': 'esg_news',
    },
    # Gulf / Saudi
    {
        'name':   'Arab News Business',
        'url':    'https://www.arabnews.com/taxonomy/term/3/feed',
        'signal': 'gulf_news',
    },
    # Kazakhstan / Central Asia
    {
        'name':   'Kazinform',
        'url':    'https://www.inform.kz/rss/',
        'signal': 'kz_news',
    },
]

HARM_KEYWORDS = [
    # Specific legal/enforcement actions (not generic "investigation")
    'fined', 'penalised', 'penalized', 'prosecution', 'convicted',
    'pleaded guilty', 'guilty plea', 'ordered to pay', 'enforcement notice',
    # Specific ESG / environmental
    'oil spill', 'chemical spill', 'pollution incident', 'emissions breach',
    'illegal dumping', 'environmental damage', 'toxic leak', 'sewage discharge',
    'greenwashing', 'misleading climate', 'false green',
    # Specific governance
    'bribery', 'fraud charges', 'money laundering', 'sanctions breach',
    'safety violation', 'workplace accident', 'fatality',
    # Russian / Kazakh
    'штраф', 'загрязнение', 'авария', 'коррупция',
]

POSITIVE_KEYWORDS = [
    'renewable energy', 'green bond', 'net zero', 'carbon neutral',
    'solar power', 'wind farm', 'decarbonization', 'decarbonisation',
    'ESG award', 'climate commitment', 'clean energy transition',
    'zero emission', 'green hydrogen', 'carbon offset',
    'sustainability report', 'carbon removal',
]

# Company first-words that are too generic to use for matching alone
_SKIP_SINGLE_WORDS = frozenset([
    'national', 'global', 'first', 'general', 'standard', 'eastern',
    'western', 'north', 'south', 'central', 'united', 'american',
    'british', 'royal', 'new', 'public', 'state', 'international',
])


class Command(BaseCommand):
    help = 'Monitor regulatory RSS feeds for company harm/positive ESG signals'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=7,
                            help='Look back N days (default: 7)')

    def handle(self, *args, **options):
        from league.models import Company

        lookback_days = options['days']
        companies     = list(Company.objects.values('id', 'name', 'slug'))
        signals_found = 0
        feed_errors   = 0

        for feed_cfg in RSS_FEEDS:
            self.stdout.write(f"  Scanning: {feed_cfg['name']}…")
            try:
                feed = feedparser.parse(feed_cfg['url'])
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f'    Feed error: {exc}'))
                feed_errors += 1
                continue

            entries = feed.get('entries', [])[:30]

            for entry in entries:
                title   = (entry.get('title',   '') or '').lower()
                summary = (entry.get('summary', '') or '').lower()
                content = f'{title} {summary}'

                for co_data in companies:
                    co_name = co_data['name'].lower()

                    # Build match tokens: significant words (5+ chars, not stopwords)
                    stop = {'group', 'plc', 'ltd', 'inc', 'corp', 'company',
                            'holdings', 'limited', 'the', 'and', 'of'}
                    sig_words = [w for w in co_name.split()
                                 if len(w) >= 5 and w not in stop]

                    if not sig_words:
                        continue

                    first_word = sig_words[0]

                    # Skip generic first-words unless the company has a longer
                    # unique name we can match on (require 2 sig words in content)
                    if first_word in _SKIP_SINGLE_WORDS:
                        if len(sig_words) < 2:
                            continue
                        # Need BOTH first and second significant word to match
                        if not (_word_in(sig_words[0], content)
                                and _word_in(sig_words[1], content)):
                            continue
                    else:
                        if not _word_in(first_word, content):
                            continue

                    harm_found     = any(kw in content for kw in HARM_KEYWORDS)
                    positive_found = any(kw in content for kw in POSITIVE_KEYWORDS)

                    if not harm_found and not positive_found:
                        continue

                    try:
                        company = Company.objects.get(id=co_data['id'])
                    except Company.DoesNotExist:
                        continue

                    signal_type = 'harm' if harm_found else 'positive'
                    marker      = '⚠️ HARM' if harm_found else '✅ POS '

                    DataIngestionLog.objects.create(
                        company=company,
                        source='rss',
                        raw_data={
                            'feed':        feed_cfg['name'],
                            'signal':      feed_cfg['signal'],
                            'signal_type': signal_type,
                            'title':       entry.get('title', ''),
                            'link':        entry.get('link', ''),
                            'published':   entry.get('published', ''),
                        },
                        fields_updated=[],
                        success=True,
                    )

                    self.stdout.write(
                        f'    {marker} {company.name}: '
                        f'{entry.get("title", "")[:70]}'
                    )
                    signals_found += 1

        self.stdout.write(self.style.SUCCESS(
            f'\nRSS signals complete — Detected:{signals_found}  Feed errors:{feed_errors}'
        ))
