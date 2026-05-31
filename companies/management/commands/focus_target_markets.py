"""
focus_target_markets — Focus EcoIQ public profiles on 4 target markets.

Actions (both idempotent):
  1. Seeds ~58 Türkiye company profiles (same scoring pattern as add_400_companies).
  2. Sets CompanyProfile.status = 'archived' for every company whose
     country is NOT in {United Kingdom, Kazakhstan, Saudi Arabia, Türkiye},
     leaving existing public/verified profiles in target markets untouched.

Usage:
    python manage.py focus_target_markets
    python manage.py focus_target_markets --overwrite   # re-seed Turkish companies
"""
import random
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

# ── Target markets ─────────────────────────────────────────────────────────────
TARGET_MARKETS = {'United Kingdom', 'Kazakhstan', 'Saudi Arabia', 'Türkiye'}

# ── Türkiye company data ───────────────────────────────────────────────────────
# (name, sector, country, target_ecoiq_score, harm_level)
TURKEY_COMPANIES = [

    # Energy
    ("Enerjisa Enerji",         "energy",     "Türkiye", 58, "Medium"),
    ("Akenerji",                "energy",     "Türkiye", 54, "Medium"),
    ("Zorlu Enerji",            "energy",     "Türkiye", 56, "Medium"),
    ("Kalyon Enerji",           "energy",     "Türkiye", 62, "Low"),
    ("Borusan EnBW Enerji",     "energy",     "Türkiye", 64, "Low"),
    ("EÜAŞ",                    "energy",     "Türkiye", 26, "Severe"),
    ("TEİAŞ",                   "energy",     "Türkiye", 40, "Medium"),
    ("Güneş Enerji GES",        "energy",     "Türkiye", 66, "Low"),

    # Oil & Gas
    ("TÜPRAŞ",                  "oil_gas",    "Türkiye", 42, "High"),
    ("BOTAŞ",                   "oil_gas",    "Türkiye", 38, "High"),
    ("TPAO",                    "oil_gas",    "Türkiye", 30, "High"),
    ("Aygaz",                   "oil_gas",    "Türkiye", 44, "Medium"),

    # Chemical / Petrochemical
    ("Petkim",                  "chemical",   "Türkiye", 36, "High"),
    ("DÖSAB Kimya",             "chemical",   "Türkiye", 42, "Medium"),

    # Metallurgy / Steel
    ("Erdemir",                 "metallurgy", "Türkiye", 44, "High"),
    ("İsdemir",                 "metallurgy", "Türkiye", 40, "High"),
    ("Kardemir",                "metallurgy", "Türkiye", 38, "High"),
    ("Borusan Mannesmann",      "metallurgy", "Türkiye", 54, "Medium"),
    ("Çolakoğlu Metalurji",     "metallurgy", "Türkiye", 36, "High"),
    ("Borçelik",                "metallurgy", "Türkiye", 46, "High"),

    # Mining
    ("Türkiye Kömür İşletmeleri", "mining",   "Türkiye", 16, "Severe"),
    ("Eti Maden",               "mining",     "Türkiye", 44, "Medium"),
    ("Koza Altın",              "mining",     "Türkiye", 38, "High"),
    ("Park Elektrik Madencilik","mining",     "Türkiye", 32, "High"),
    ("Çayeli Bakır",            "mining",     "Türkiye", 30, "High"),

    # Transport
    ("Türk Hava Yolları THY",   "transport",  "Türkiye", 52, "High"),
    ("Pegasus Airlines",        "transport",  "Türkiye", 48, "High"),
    ("TCDD Taşımacılık",        "transport",  "Türkiye", 46, "Medium"),
    ("İstanbul Deniz Otobüsleri","transport", "Türkiye", 44, "Medium"),
    ("Arkas Denizcilik",        "transport",  "Türkiye", 46, "Medium"),
    ("Akfen Holding",           "transport",  "Türkiye", 50, "Medium"),
    ("Global Liman İşletmeleri","transport",  "Türkiye", 50, "Low"),
    ("Ulaşım A.Ş.",             "transport",  "Türkiye", 48, "Medium"),

    # Banking & Finance
    ("Türkiye İş Bankası",      "other",      "Türkiye", 58, "Low"),
    ("Garanti BBVA",            "other",      "Türkiye", 60, "Low"),
    ("Akbank",                  "other",      "Türkiye", 56, "Low"),
    ("Yapı Kredi",              "other",      "Türkiye", 54, "Low"),
    ("Halkbank",                "other",      "Türkiye", 50, "Low"),
    ("Ziraat Bankası",          "other",      "Türkiye", 52, "Low"),
    ("TSKB Kalkınma Bankası",   "other",      "Türkiye", 62, "Low"),
    ("Vakıfbank",               "other",      "Türkiye", 50, "Low"),

    # Telecom
    ("Türk Telekom",            "other",      "Türkiye", 54, "Low"),
    ("Turkcell",                "other",      "Türkiye", 58, "Low"),
    ("Vodafone Türkiye",        "other",      "Türkiye", 56, "Low"),

    # Conglomerates / Manufacturing
    ("Sabancı Holding",         "other",      "Türkiye", 58, "Low"),
    ("Koç Holding",             "other",      "Türkiye", 62, "Low"),
    ("Anadolu Grubu",           "other",      "Türkiye", 54, "Low"),
    ("Doğuş Grubu",             "other",      "Türkiye", 48, "Low"),
    ("Çalık Holding",           "other",      "Türkiye", 40, "Medium"),
    ("Gama Holding",            "other",      "Türkiye", 50, "Low"),
    ("Rönesans Holding",        "other",      "Türkiye", 50, "Low"),
    ("Limak Holding",           "other",      "Türkiye", 46, "Low"),

    # Technology & Defence
    ("Aselsan",                 "other",      "Türkiye", 56, "Medium"),
    ("TAI Türk Havacılık",      "other",      "Türkiye", 58, "Low"),
    ("Türk Traktör",            "other",      "Türkiye", 52, "Low"),
    ("Vestel",                  "other",      "Türkiye", 62, "Low"),
    ("Arçelik",                 "other",      "Türkiye", 64, "Low"),

    # Agriculture / Food
    ("Türkiye Şeker Fabrikaları", "agriculture", "Türkiye", 44, "Medium"),
    ("Konya Şeker",             "agriculture", "Türkiye", 48, "Low"),
    ("Ülker Bisküvi",           "other",      "Türkiye", 52, "Low"),
]

# ── Helpers (mirror of add_400_companies) ─────────────────────────────────────
HARM_PENALTY   = {'Severe': 12, 'High': 6, 'Medium': 2, 'Low': 0}
POLLUTION_MAP  = {'Severe': 'severe', 'High': 'high', 'Medium': 'medium', 'Low': 'low'}

MORAL_LABEL_FROM_SCORE = [
    (85, 'regenerative_leader'),
    (70, 'responsible_builder'),
    (60, 'public_benefit_oriented'),
    (50, 'transitional_company'),
    (30, 'profit_first_operator'),
    (0,  'extractive_harmful'),
]


def moral_label(score):
    for threshold, label in MORAL_LABEL_FROM_SCORE:
        if score >= threshold:
            return label
    return 'extractive_harmful'


def clamp(v, lo=1.0, hi=100.0):
    return round(max(lo, min(hi, v)), 1)


def gen_scores(name, target, harm_level):
    penalty = HARM_PENALTY[harm_level]
    base    = float(target) + penalty
    rng     = random.Random(abs(hash(name)) % (2 ** 31))

    def n(centre, amp=5):
        return clamp(centre + rng.uniform(-amp, amp))

    pb  = n(base); env = n(base); mod = n(base)
    gov = n(base); ac  = n(base); eth = n(base)

    weighted = pb * 0.25 + env * 0.25 + mod * 0.20 + gov * 0.15 + ac * 0.10 + eth * 0.05
    total    = clamp(round(weighted - penalty, 1), lo=1.0)

    return {
        'public_benefit_score':               pb,
        'environmental_responsibility_score': env,
        'modernization_score':                mod,
        'transparency_anti_corruption_score': gov,
        'anti_corruption_score':              ac,
        'ethical_alignment_score':            eth,
        'jobs_created_score':                       n(pb),
        'regional_development_score':               n(pb),
        'infrastructure_contribution_score':        n(pb),
        'national_value_score':                     n(pb),
        'waste_management_score':                   n(env),
        'water_impact_score':                       n(env),
        'biodiversity_impact_score':                n(env),
        'energy_transition_score':                  n(mod),
        'digitalization_score':                     n(mod),
        'infrastructure_upgrade_score':             n(mod),
        'future_readiness_score':                   n(mod),
        'transparency_score_detail':                n(gov),
        'audit_quality_score':                      n(gov),
        'procurement_transparency_score':           n(gov),
        'controversy_risk_score':  clamp(penalty * 7 + rng.uniform(-5, 5), lo=0.0),
        'harm_penalty':            float(penalty),
        'ecoiq_total_score':       total,
        'moral_label':             moral_label(total),
        'score_pollution_footprint': n(float(target), 4),
        'score_reduction_progress':  n(float(target), 4),
        'score_investment':          n(float(target), 4),
        'score_transparency':        n(float(target), 4),
        'score_community_impact':    n(float(target), 4),
    }


# ── Management command ────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = (
        'Seed Türkiye companies and archive non-target-market profiles. '
        'Target markets: United Kingdom, Kazakhstan, Saudi Arabia, Türkiye.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--overwrite', action='store_true',
            help='Overwrite scores for already-existing Turkish companies',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        from league.models import Company
        from companies.models import CompanyProfile

        overwrite = options['overwrite']

        # ── Step 1: Seed Türkiye profiles ─────────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING('─── Step 1: Seeding Türkiye companies ───'))
        created = updated = skipped = 0

        for (name, sector, country, target, harm_level) in TURKEY_COMPANIES:
            slug   = slugify(name)
            scores = gen_scores(name, target, harm_level)

            company, co_created = Company.objects.get_or_create(
                slug=slug,
                defaults=dict(
                    name=name, sector=sector, country=country,
                    is_public=True, verified=False,
                    score_pollution_footprint=scores['score_pollution_footprint'],
                    score_reduction_progress =scores['score_reduction_progress'],
                    score_investment         =scores['score_investment'],
                    score_transparency       =scores['score_transparency'],
                    score_community_impact   =scores['score_community_impact'],
                ),
            )

            if not co_created and overwrite:
                company.name    = name; company.sector  = sector
                company.country = country
                company.score_pollution_footprint = scores['score_pollution_footprint']
                company.score_reduction_progress  = scores['score_reduction_progress']
                company.score_investment          = scores['score_investment']
                company.score_transparency        = scores['score_transparency']
                company.score_community_impact    = scores['score_community_impact']
                company.save()
            elif not co_created:
                if CompanyProfile.objects.filter(company=company).exists():
                    skipped += 1
                    continue
            else:
                company.save()

            profile_defaults = dict(
                status          = 'public',
                is_verified     = False,
                pollution_level = POLLUTION_MAP[harm_level],
                public_benefit_score              = scores['public_benefit_score'],
                environmental_responsibility_score= scores['environmental_responsibility_score'],
                modernization_score               = scores['modernization_score'],
                transparency_anti_corruption_score= scores['transparency_anti_corruption_score'],
                anti_corruption_score             = scores['anti_corruption_score'],
                ethical_alignment_score           = scores['ethical_alignment_score'],
                jobs_created_score                = scores['jobs_created_score'],
                regional_development_score        = scores['regional_development_score'],
                infrastructure_contribution_score = scores['infrastructure_contribution_score'],
                national_value_score              = scores['national_value_score'],
                waste_management_score            = scores['waste_management_score'],
                water_impact_score                = scores['water_impact_score'],
                biodiversity_impact_score         = scores['biodiversity_impact_score'],
                energy_transition_score           = scores['energy_transition_score'],
                digitalization_score              = scores['digitalization_score'],
                infrastructure_upgrade_score      = scores['infrastructure_upgrade_score'],
                future_readiness_score            = scores['future_readiness_score'],
                transparency_score_detail         = scores['transparency_score_detail'],
                audit_quality_score               = scores['audit_quality_score'],
                procurement_transparency_score    = scores['procurement_transparency_score'],
                controversy_risk_score            = scores['controversy_risk_score'],
                harm_penalty                      = scores['harm_penalty'],
                ecoiq_total_score                 = scores['ecoiq_total_score'],
                moral_label                       = scores['moral_label'],
                ai_summary=(
                    f"{name} is a {sector.replace('_', ' ')} company based in {country}. "
                    f"EcoIQ score: {scores['ecoiq_total_score']}/100. "
                    f"Seeded by focus_target_markets management command."
                ),
            )

            profile, pr_created = CompanyProfile.objects.get_or_create(
                company=company, defaults=profile_defaults,
            )

            if not pr_created and overwrite:
                for k, v in profile_defaults.items():
                    setattr(profile, k, v)
                profile.save()
                updated += 1
            elif pr_created:
                created += 1
            else:
                skipped += 1
                continue

            verb = 'Created' if pr_created else 'Updated'
            self.stdout.write(
                self.style.SUCCESS(
                    f"  {verb:7s} [Türkiye         ] {name[:40]:40s} "
                    f"EcoIQ={scores['ecoiq_total_score']:5.1f}  {harm_level}"
                )
            )

        self.stdout.write(self.style.SUCCESS(
            f"  Türkiye done. Created={created}  Updated={updated}  Skipped={skipped}"
        ))

        # ── Step 2: Archive non-target-market profiles ────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING(
            '\n─── Step 2: Archiving non-target-market profiles ───'
        ))

        archived_qs = CompanyProfile.objects.exclude(
            company__country__in=TARGET_MARKETS
        ).filter(status__in=('public', 'verified'))

        archive_count = archived_qs.count()
        archived_qs.update(status='archived')

        self.stdout.write(self.style.WARNING(
            f"  Archived {archive_count} profiles outside target markets."
        ))
        self.stdout.write(self.style.SUCCESS(
            f"  Active target markets: {', '.join(sorted(TARGET_MARKETS))}"
        ))

        # ── Summary ───────────────────────────────────────────────────────────
        self.stdout.write(self.style.MIGRATE_HEADING('\n─── Distribution after focus ───'))
        from collections import Counter
        dist = Counter(
            p.company.country
            for p in CompanyProfile.objects.filter(
                status__in=('public', 'verified')
            ).select_related('company')
        )
        for country, count in sorted(dist.items(), key=lambda x: -x[1]):
            self.stdout.write(f"  {country:<30s} {count}")

        self.stdout.write(self.style.SUCCESS('\nfocus_target_markets complete.'))
