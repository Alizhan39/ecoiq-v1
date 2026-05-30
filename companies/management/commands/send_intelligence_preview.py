"""
send_intelligence_preview — Generate personalised intelligence email list as CSV.

Does NOT send any emails. Produces a CSV file ready for review before any
outreach campaign. Each row contains:
  company_name, country, sector, ecoiq_score, tier_label,
  weakest_pillar, weakest_pillar_score, harm_level,
  claim_url, subject_line, email_body (first 500 chars preview)

Usage:
    python manage.py send_intelligence_preview
    python manage.py send_intelligence_preview --output /tmp/ecoiq_outreach.csv
    python manage.py send_intelligence_preview --min-score 30 --max-score 70
"""
import csv
import os
from datetime import date
from django.core.management.base import BaseCommand


# ── Tier labels ───────────────────────────────────────────────────────────────

def tier_label(score):
    s = float(score)
    if s >= 85: return 'Regenerative Leader'
    if s >= 70: return 'Responsible Builder'
    if s >= 60: return 'Public-Benefit Oriented'
    if s >= 50: return 'Transitional Company'
    if s >= 30: return 'Profit-First Operator'
    return 'Extractive / Harmful'


def harm_level(penalty):
    p = float(penalty or 0)
    if p >= 12: return 'Severe'
    if p >= 6:  return 'High'
    if p >= 2:  return 'Medium'
    return 'Low'


def weakest_pillar(profile):
    """Return (pillar_display_name, score) for the lowest-scoring pillar."""
    pillars = [
        ('Public Benefit',          profile.public_benefit_score),
        ('Environmental',           profile.environmental_responsibility_score),
        ('Modernization',           profile.modernization_score),
        ('Governance',              profile.transparency_anti_corruption_score),
        ('Anti-Corruption',         profile.anti_corruption_score),
        ('Ethical Alignment',       profile.ethical_alignment_score),
    ]
    return min(pillars, key=lambda p: (p[1] or 0))


def build_subject(company_name, score):
    return f'Your EcoIQ Climate Score: {score}/100 — {company_name}'


def build_body(company_name, score, tier, weak_pillar, weak_score, claim_url, country):
    """
    Generate personalised email body text.
    """
    score_f = f'{float(score):.1f}'
    weak_f  = f'{float(weak_score):.1f}' if weak_score else 'N/A'

    return f"""Dear {company_name} Team,

EcoIQ has published a Climate Intelligence Profile for {company_name}.

  EcoIQ Score:  {score_f} / 100
  Tier:         {tier}
  Country:      {country}

Your score is compiled from publicly available information and AI-assisted
analysis across six pillars: Public Benefit, Environmental Stewardship,
Responsible Modernisation, Transparent Governance, Anti-Corruption, and
Ethical Alignment.

Your current lowest-scoring pillar is {weak_pillar} ({weak_f}/100). This is
where focused improvement would have the most impact on your overall score.

── What this means for {company_name} ──────────────────────────────────────

Investors, lenders, and regulatory bodies increasingly use EcoIQ scores as
a first-pass due-diligence signal. A verified, claimed profile gives you
direct control over your data — and signals proactive ESG leadership.

── Claim your profile (£500/mo) ────────────────────────────────────────────

Claiming your EcoIQ profile lets you:
  • Update your company data and correct any inaccuracies
  • Display a "Verified" badge on your public profile
  • Receive monthly score-change alerts
  • Access our Score Improvement advisory (£2,000/mo upgrade)

Claim here: {claim_url}

Or reply to this email and we will set it up for you.

── Next steps ────────────────────────────────────────────────────────────────

  1. View your current profile: https://ecoiq.uk/companies/{'{slug}'}
  2. Claim your profile:        {claim_url}
  3. Book a 30-min call:        https://ecoiq.uk/request-access/

All EcoIQ scores are indicative and based on publicly available data.
They are not investment advice. Methodology: https://ecoiq.uk/methodology/

Best regards,
Alizhan Tazabekov
Founder, EcoIQ
alizhan@ecoiq.uk | https://ecoiq.uk
"""


class Command(BaseCommand):
    help = (
        'Generate personalised EcoIQ intelligence email list as CSV. '
        'Does NOT send any emails.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--output', '-o',
            default='ecoiq_intelligence_preview.csv',
            help='Output CSV file path (default: ecoiq_intelligence_preview.csv)',
        )
        parser.add_argument(
            '--min-score', type=float, default=0,
            help='Only include companies with score >= this value (default: 0)',
        )
        parser.add_argument(
            '--max-score', type=float, default=100,
            help='Only include companies with score <= this value (default: 100)',
        )
        parser.add_argument(
            '--country',
            help='Filter by country name (partial match, case-insensitive)',
        )
        parser.add_argument(
            '--sector',
            help='Filter by sector slug (e.g. oil_gas, energy, mining)',
        )

    def handle(self, *args, **options):
        from companies.models import CompanyProfile

        output_path = options['output']
        min_score   = options['min_score']
        max_score   = options['max_score']
        country_f   = (options.get('country') or '').strip()
        sector_f    = (options.get('sector') or '').strip()

        qs = (
            CompanyProfile.objects
            .filter(status__in=('public', 'verified'))
            .select_related('company')
            .order_by('-ecoiq_total_score')
        )

        if min_score > 0:
            qs = qs.filter(ecoiq_total_score__gte=min_score)
        if max_score < 100:
            qs = qs.filter(ecoiq_total_score__lte=max_score)
        if country_f:
            qs = qs.filter(company__country__icontains=country_f)
        if sector_f:
            qs = qs.filter(company__sector=sector_f)

        profiles = list(qs)
        total = len(profiles)

        if not total:
            self.stdout.write(self.style.WARNING('No profiles match the given filters.'))
            return

        self.stdout.write(f'Generating email list for {total} companies → {output_path}')

        base_url = 'https://ecoiq.uk'
        today    = date.today().strftime('%d %B %Y')

        fieldnames = [
            'rank',
            'company_name',
            'slug',
            'country',
            'sector',
            'ecoiq_score',
            'tier_label',
            'harm_level',
            'weakest_pillar',
            'weakest_pillar_score',
            'profile_url',
            'claim_url',
            'email_subject',
            'email_body_preview',
        ]

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for rank, profile in enumerate(profiles, 1):
                co    = profile.company
                score = profile.ecoiq_total_score or 0
                tier  = tier_label(score)
                harm  = harm_level(profile.harm_penalty)
                weak_name, weak_score = weakest_pillar(profile)

                slug        = co.slug
                profile_url = f'{base_url}/companies/{slug}/'
                claim_url   = f'{base_url}/request-access/claim/?company={slug}'

                subject = build_subject(co.name, f'{float(score):.1f}')
                body    = build_body(
                    company_name=co.name,
                    score=score,
                    tier=tier,
                    weak_pillar=weak_name,
                    weak_score=weak_score,
                    claim_url=claim_url,
                    country=co.country or '',
                ).replace('{slug}', slug)

                writer.writerow({
                    'rank':                 rank,
                    'company_name':         co.name,
                    'slug':                 slug,
                    'country':              co.country or '',
                    'sector':               co.get_sector_display(),
                    'ecoiq_score':          f'{float(score):.1f}',
                    'tier_label':           tier,
                    'harm_level':           harm,
                    'weakest_pillar':       weak_name,
                    'weakest_pillar_score': f'{float(weak_score):.1f}' if weak_score else '',
                    'profile_url':          profile_url,
                    'claim_url':            claim_url,
                    'email_subject':        subject,
                    'email_body_preview':   body[:600].replace('\n', ' ').strip(),
                })

                if rank % 50 == 0:
                    self.stdout.write(f'  … {rank}/{total} rows written')

        size_kb = os.path.getsize(output_path) / 1024
        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Done. {total} rows written to {output_path} ({size_kb:.1f} KB)\n'
            f'  Score range: {min_score}–{max_score}\n'
            f'  Country filter: {country_f or "all"}\n'
            f'  Sector filter:  {sector_f or "all"}\n'
            f'\n  ⚠  NO EMAILS WERE SENT. Review the CSV before any outreach.'
        ))
