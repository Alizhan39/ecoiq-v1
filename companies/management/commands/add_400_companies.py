"""
add_400_companies — Bulk-seed UK, Saudi, Kazakh and Global companies.

Usage:
    python manage.py add_400_companies
    python manage.py add_400_companies --overwrite   # update existing records
"""
import random
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

# ── Company data ──────────────────────────────────────────────────────────────
# (name, sector, country, target_ecoiq_score, harm_level)
# harm_level: Severe | High | Medium | Low

COMPANIES = [

    # ─── UK ────────────────────────────────────────────────────────────────────
    ("National Grid",           "energy",     "United Kingdom", 68, "Low"),
    ("SSE",                     "energy",     "United Kingdom", 65, "Low"),
    ("Centrica",                "energy",     "United Kingdom", 58, "Medium"),
    ("Drax Group",              "energy",     "United Kingdom", 48, "High"),
    ("Scottish Power",          "energy",     "United Kingdom", 62, "Low"),
    ("Octopus Energy",          "energy",     "United Kingdom", 74, "Low"),
    ("E.ON UK",                 "energy",     "United Kingdom", 61, "Low"),
    ("Vattenfall UK",           "energy",     "United Kingdom", 66, "Low"),
    ("RWE UK",                  "energy",     "United Kingdom", 58, "Medium"),
    ("EDF Energy UK",           "energy",     "United Kingdom", 64, "Low"),
    ("Harbour Energy",          "oil_gas",    "United Kingdom", 38, "High"),
    ("Ithaca Energy",           "oil_gas",    "United Kingdom", 34, "High"),
    ("EnQuest",                 "oil_gas",    "United Kingdom", 32, "High"),
    ("Petrofac",                "oil_gas",    "United Kingdom", 30, "High"),
    ("Anglo American",          "mining",     "United Kingdom", 48, "High"),
    ("Fresnillo",               "mining",     "United Kingdom", 44, "High"),
    ("Ferrexpo",                "mining",     "United Kingdom", 42, "High"),
    ("Hochschild Mining",       "mining",     "United Kingdom", 40, "High"),
    ("Centamin",                "mining",     "United Kingdom", 45, "Medium"),
    ("Tata Steel UK",           "metallurgy", "United Kingdom", 42, "High"),
    ("British Steel",           "metallurgy", "United Kingdom", 40, "High"),
    ("Liberty Steel UK",        "metallurgy", "United Kingdom", 38, "High"),
    ("Croda International",     "chemical",   "United Kingdom", 70, "Low"),
    ("Johnson Matthey",         "chemical",   "United Kingdom", 68, "Low"),
    ("Ineos",                   "chemical",   "United Kingdom", 44, "High"),
    ("Synthomer",               "chemical",   "United Kingdom", 52, "Medium"),
    ("Rolls-Royce",             "other",      "United Kingdom", 66, "Medium"),
    ("BAE Systems",             "other",      "United Kingdom", 54, "Medium"),
    ("IMI plc",                 "other",      "United Kingdom", 62, "Low"),
    ("Weir Group",              "other",      "United Kingdom", 60, "Medium"),
    ("Smiths Group",            "other",      "United Kingdom", 61, "Low"),
    ("Renishaw",                "other",      "United Kingdom", 67, "Low"),
    ("Bodycote",                "other",      "United Kingdom", 58, "Medium"),
    ("Meggitt",                 "other",      "United Kingdom", 58, "Low"),
    ("IAG British Airways",     "transport",  "United Kingdom", 48, "High"),
    ("easyJet",                 "transport",  "United Kingdom", 50, "High"),
    ("National Express",        "transport",  "United Kingdom", 56, "Medium"),
    ("FirstGroup",              "transport",  "United Kingdom", 54, "Medium"),
    ("Stagecoach",              "transport",  "United Kingdom", 55, "Medium"),
    ("Go-Ahead Group",          "transport",  "United Kingdom", 54, "Medium"),
    ("Associated British Ports","transport",  "United Kingdom", 58, "Medium"),
    ("Severn Trent",            "energy",     "United Kingdom", 64, "Low"),
    ("United Utilities",        "energy",     "United Kingdom", 62, "Low"),
    ("Thames Water",            "energy",     "United Kingdom", 42, "Medium"),
    ("Anglian Water",           "energy",     "United Kingdom", 58, "Low"),
    ("Biffa",                   "other",      "United Kingdom", 60, "Medium"),
    ("Renewi",                  "other",      "United Kingdom", 63, "Medium"),
    ("Balfour Beatty",          "other",      "United Kingdom", 60, "Medium"),
    ("Kier Group",              "other",      "United Kingdom", 55, "Medium"),
    ("Costain",                 "other",      "United Kingdom", 57, "Medium"),
    ("Morgan Sindall",          "other",      "United Kingdom", 60, "Low"),
    ("Mace Group",              "other",      "United Kingdom", 58, "Low"),
    ("HSBC",                    "other",      "United Kingdom", 62, "Low"),
    ("Barclays",                "other",      "United Kingdom", 58, "Low"),
    ("Lloyds Banking Group",    "other",      "United Kingdom", 60, "Low"),
    ("NatWest Group",           "other",      "United Kingdom", 62, "Low"),
    ("Standard Chartered",      "other",      "United Kingdom", 61, "Low"),
    ("Legal and General",       "other",      "United Kingdom", 64, "Low"),
    ("Aviva",                   "other",      "United Kingdom", 63, "Low"),
    ("Prudential UK",           "other",      "United Kingdom", 61, "Low"),

    # ─── Saudi Arabia ──────────────────────────────────────────────────────────
    ("SABIC",                            "chemical",   "Saudi Arabia", 40, "High"),
    ("Sipchem",                          "chemical",   "Saudi Arabia", 36, "High"),
    ("Tasnee",                           "chemical",   "Saudi Arabia", 34, "High"),
    ("Petro Rabigh",                     "chemical",   "Saudi Arabia", 33, "High"),
    ("Advanced Petrochemical",           "chemical",   "Saudi Arabia", 35, "High"),
    ("Saudi Kayan Petrochemical",        "chemical",   "Saudi Arabia", 34, "High"),
    ("Yansab",                           "chemical",   "Saudi Arabia", 35, "High"),
    ("Luberef",                          "chemical",   "Saudi Arabia", 35, "High"),
    ("Maaden",                           "mining",     "Saudi Arabia", 42, "High"),
    ("Arabian Cement",                   "other",      "Saudi Arabia", 38, "High"),
    ("Yamama Cement",                    "other",      "Saudi Arabia", 36, "High"),
    ("Saudi Cement",                     "other",      "Saudi Arabia", 37, "High"),
    ("Saudi Electricity Company",        "energy",     "Saudi Arabia", 38, "High"),
    ("ACWA Power",                       "energy",     "Saudi Arabia", 62, "Low"),
    ("Alfanar Energy",                   "energy",     "Saudi Arabia", 54, "Low"),
    ("Hadeed Steel",                     "metallurgy", "Saudi Arabia", 38, "High"),
    ("Rajhi Steel",                      "metallurgy", "Saudi Arabia", 36, "High"),
    ("United Steel Saudi",               "metallurgy", "Saudi Arabia", 35, "High"),
    ("Emirates Steel",                   "metallurgy", "Saudi Arabia", 40, "High"),
    ("Saudi Airlines Saudia",            "transport",  "Saudi Arabia", 40, "High"),
    ("Flynas",                           "transport",  "Saudi Arabia", 42, "High"),
    ("SAPTCO",                           "transport",  "Saudi Arabia", 45, "Medium"),
    ("Saudi Railway SAR",                "transport",  "Saudi Arabia", 52, "Low"),
    ("Bahri National Shipping",          "transport",  "Saudi Arabia", 44, "High"),
    ("Red Sea Gateway Terminal",         "transport",  "Saudi Arabia", 48, "Medium"),
    ("NEOM",                             "other",      "Saudi Arabia", 55, "Low"),
    ("Red Sea Global",                   "other",      "Saudi Arabia", 62, "Low"),
    ("Diriyah Gate Development Authority","other",     "Saudi Arabia", 54, "Low"),
    ("Qiddiya Investment Company",       "other",      "Saudi Arabia", 50, "Low"),
    ("Al Rajhi Bank",                    "other",      "Saudi Arabia", 58, "Low"),
    ("Saudi National Bank",              "other",      "Saudi Arabia", 56, "Low"),
    ("Riyad Bank",                       "other",      "Saudi Arabia", 54, "Low"),
    ("Alinma Bank",                      "other",      "Saudi Arabia", 55, "Low"),
    ("Saudi Awwal Bank",                 "other",      "Saudi Arabia", 58, "Low"),
    ("Public Investment Fund PIF",       "other",      "Saudi Arabia", 52, "Low"),
    ("Almarai",                          "agriculture","Saudi Arabia", 56, "Low"),
    ("NADEC",                            "agriculture","Saudi Arabia", 52, "Low"),
    ("Savola Group",                     "other",      "Saudi Arabia", 54, "Low"),
    ("National Water Company NWC",       "energy",     "Saudi Arabia", 46, "Medium"),
    ("MARAFIQ",                          "energy",     "Saudi Arabia", 44, "Medium"),

    # ─── Kazakhstan ────────────────────────────────────────────────────────────
    ("KazMunayGas",                      "oil_gas",    "Kazakhstan", 26, "Severe"),
    ("Tengizchevroil",                   "oil_gas",    "Kazakhstan", 28, "Severe"),
    ("NCOC Kashagan",                    "oil_gas",    "Kazakhstan", 24, "Severe"),
    ("Karachaganak Petroleum Operating", "oil_gas",    "Kazakhstan", 28, "High"),
    ("KazTransOil",                      "oil_gas",    "Kazakhstan", 34, "High"),
    ("KazTransGas",                      "oil_gas",    "Kazakhstan", 33, "High"),
    ("Embamunaigas",                     "oil_gas",    "Kazakhstan", 26, "High"),
    ("Mangistaumunaigaz",                "oil_gas",    "Kazakhstan", 27, "High"),
    ("JV Inkai",                         "mining",     "Kazakhstan", 40, "Medium"),
    ("Uranium One KZ",                   "mining",     "Kazakhstan", 38, "Medium"),
    ("Eurasian Resources Group ERG",     "mining",     "Kazakhstan", 22, "Severe"),
    ("KazMinerals",                      "mining",     "Kazakhstan", 38, "High"),
    ("Kazzinc",                          "mining",     "Kazakhstan", 32, "High"),
    ("Kazakhmys",                        "mining",     "Kazakhstan", 30, "High"),
    ("ArcelorMittal Temirtau",           "metallurgy", "Kazakhstan", 24, "Severe"),
    ("Kazakhstan Aluminium Smelter",     "metallurgy", "Kazakhstan", 30, "High"),
    ("Tau-Ken Samruk",                   "mining",     "Kazakhstan", 36, "High"),
    ("Shubarkol Komir",                  "mining",     "Kazakhstan", 20, "Severe"),
    ("Bogatyr Coal",                     "mining",     "Kazakhstan", 18, "Severe"),
    ("Samruk-Energy",                    "energy",     "Kazakhstan", 22, "Severe"),
    ("KEGOC",                            "energy",     "Kazakhstan", 40, "Medium"),
    ("Ekibastuz GRES-1",                 "energy",     "Kazakhstan", 18, "Severe"),
    ("Ekibastuz GRES-2",                 "energy",     "Kazakhstan", 19, "Severe"),
    ("AES Ekibastuz",                    "energy",     "Kazakhstan", 26, "Severe"),
    ("Kazakhstani Wind Energy",          "energy",     "Kazakhstan", 65, "Low"),
    ("Burnoye Solar",                    "energy",     "Kazakhstan", 68, "Low"),
    ("Nur Renewables",                   "energy",     "Kazakhstan", 66, "Low"),
    ("Air Astana",                       "transport",  "Kazakhstan", 46, "High"),
    ("FlyArystan",                       "transport",  "Kazakhstan", 44, "High"),
    ("Kazakhstan Temir Zholy KTZ",       "transport",  "Kazakhstan", 42, "Medium"),
    ("KazLogistics",                     "transport",  "Kazakhstan", 44, "Medium"),
    ("Aktau Port",                       "transport",  "Kazakhstan", 40, "Medium"),
    ("Kaspi.kz",                         "other",      "Kazakhstan", 58, "Low"),
    ("Halyk Bank",                       "other",      "Kazakhstan", 52, "Low"),
    ("Bank CenterCredit",                "other",      "Kazakhstan", 46, "Low"),
    ("Samruk-Kazyna",                    "other",      "Kazakhstan", 38, "Low"),
    ("Development Bank of Kazakhstan",   "other",      "Kazakhstan", 50, "Low"),
    ("Astana Finance Hub",               "other",      "Kazakhstan", 54, "Low"),
    ("KazAgro",                          "agriculture","Kazakhstan", 44, "Medium"),
    ("Kazakhtelecom",                    "other",      "Kazakhstan", 50, "Low"),
    ("Kcell",                            "other",      "Kazakhstan", 52, "Low"),
    ("Beeline Kazakhstan",               "other",      "Kazakhstan", 51, "Low"),
    ("ZERDE",                            "other",      "Kazakhstan", 48, "Low"),

    # ─── Global Top ────────────────────────────────────────────────────────────
    ("TotalEnergies",          "oil_gas",    "France",        40, "High"),
    ("Equinor",                "oil_gas",    "Norway",        52, "High"),
    ("Repsol",                 "oil_gas",    "Spain",         44, "High"),
    ("ENI",                    "oil_gas",    "Italy",         42, "High"),
    ("Iberdrola",              "energy",     "Spain",         76, "Low"),
    ("Enel",                   "energy",     "Italy",         72, "Low"),
    ("Fortum",                 "energy",     "Finland",       68, "Low"),
    ("RWE",                    "energy",     "Germany",       58, "Medium"),
    ("E.ON",                   "energy",     "Germany",       62, "Low"),
    ("Vattenfall",             "energy",     "Sweden",        66, "Low"),
    ("POSCO",                  "metallurgy", "South Korea",   48, "High"),
    ("Hyundai Motor",          "transport",  "South Korea",   58, "Medium"),
    ("NTPC",                   "energy",     "India",         38, "High"),
    ("Reliance Industries",    "oil_gas",    "India",         42, "High"),
    ("Tata Steel",             "metallurgy", "India",         45, "High"),
    ("China Shenhua Energy",   "energy",     "China",         30, "Severe"),
    ("Baowu Steel",            "metallurgy", "China",         36, "High"),
    ("Sinopec",                "oil_gas",    "China",         34, "High"),
    ("PetroChina",             "oil_gas",    "China",         32, "High"),
    ("Vale",                   "mining",     "Brazil",        36, "High"),
    ("Freeport-McMoRan",       "mining",     "United States", 42, "High"),
    ("Newmont",                "mining",     "United States", 50, "Medium"),
    ("Barrick Gold",           "mining",     "Canada",        48, "High"),
    ("Teck Resources",         "mining",     "Canada",        46, "High"),
    ("First Quantum Minerals", "mining",     "Canada",        42, "High"),
    ("Antofagasta",            "mining",     "Chile",         44, "High"),
    ("Southern Copper",        "mining",     "United States", 40, "High"),
    ("Norilsk Nickel",         "mining",     "Russia",        18, "Severe"),
    ("ArcelorMittal",          "metallurgy", "Luxembourg",    40, "High"),
    ("Lufthansa",              "transport",  "Germany",       50, "High"),
    ("Air France-KLM",         "transport",  "France",        48, "High"),
    ("Volkswagen",             "transport",  "Germany",       52, "Medium"),
    ("Stellantis",             "transport",  "Netherlands",   50, "Medium"),
    ("Airbus",                 "transport",  "France",        62, "Medium"),
    ("DP World",               "transport",  "United Arab Emirates", 52, "Medium"),
    ("CMA CGM",                "transport",  "France",        46, "High"),
    ("Hapag-Lloyd",            "transport",  "Germany",       50, "High"),
    ("BNP Paribas",            "other",      "France",        60, "Low"),
    ("Deutsche Bank",          "other",      "Germany",       56, "Low"),
    ("ING Group",              "other",      "Netherlands",   62, "Low"),
    ("Macquarie Group",        "other",      "Australia",     58, "Low"),
    ("Sumitomo Mitsui",        "other",      "Japan",         58, "Low"),
    ("MUFG",                   "other",      "Japan",         57, "Low"),
]

# ── AI summary helpers ────────────────────────────────────────────────────────

_SECTOR_INTRO = {
    'energy':     "an energy sector company covering power generation, distribution, and renewable energy development",
    'oil_gas':    "an oil and gas operator",
    'chemical':   "a chemical or petrochemical company",
    'metallurgy': "a metals and materials company",
    'mining':     "a mining and natural resources company",
    'transport':  "a transport or logistics operator",
    'agriculture':"an agricultural or agri-food company",
}

_SECTOR_DETAIL = {
    'oil_gas':    "EcoIQ evaluates decarbonisation commitments, methane reduction progress, and capital allocation towards energy transition.",
    'chemical':   "EcoIQ scoring reflects process emissions intensity, circular chemistry initiatives, and transition pathways.",
    'metallurgy': "EcoIQ evaluates carbon intensity, recycled input rates, and investment in low-carbon smelting or steelmaking technologies.",
    'mining':     "The EcoIQ profile assesses environmental rehabilitation, water stewardship, community impact, and governance against international standards.",
    'transport':  "EcoIQ scoring covers fleet and operational emissions, modal shift initiatives, and infrastructure investment in lower-carbon mobility.",
    'agriculture':"EcoIQ evaluates land-use efficiency, water management, food system resilience, and supply chain sustainability.",
}


def _readiness_sentence(name: str, total: float) -> str:
    if total >= 70:
        return (
            f"With an EcoIQ score of {total}/100, {name} demonstrates strong transition "
            "readiness across environmental stewardship, governance, and public benefit delivery."
        )
    elif total >= 55:
        return (
            f"With an EcoIQ score of {total}/100, {name} shows moderate transition readiness "
            "with identified opportunities to strengthen environmental and governance commitments."
        )
    elif total >= 40:
        return (
            f"With an EcoIQ score of {total}/100, {name} is at an early transition stage "
            "with significant scope to improve decarbonisation strategy and governance quality."
        )
    return (
        f"With an EcoIQ score of {total}/100, {name} faces material climate transition risks. "
        "EcoIQ identifies high-priority areas for emissions reduction and responsible resource management."
    )


def make_ai_summary(name: str, sector: str, country: str, scores: dict) -> str:
    """Generate a credible, sector-specific AI summary. Replaces generic seed placeholders."""
    desc   = _SECTOR_INTRO.get(sector, f"a company in the {sector.replace('_', ' ')} sector")
    detail = _SECTOR_DETAIL.get(sector, "")
    intro  = f"{name} is {desc}, operating in {country}."
    body   = f"{detail} " if detail else ""
    return f"{intro} {body}{_readiness_sentence(name, scores['ecoiq_total_score'])}"


# ── Score generation helpers ──────────────────────────────────────────────────

HARM_PENALTY = {'Severe': 12, 'High': 6, 'Medium': 2, 'Low': 0}
POLLUTION_MAP = {'Severe': 'severe', 'High': 'high', 'Medium': 'medium', 'Low': 'low'}

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
    """
    Generate deterministic, internally-consistent pillar scores.

    Strategy:
      base  = target + penalty  (raw pillar mean before penalty is subtracted)
      pillar scores are generated with ±5 noise around base
      ecoiq_total_score = weighted pillar sum − penalty  ≈ target
    """
    penalty = HARM_PENALTY[harm_level]
    base = float(target) + penalty          # pre-penalty weighted mean
    rng = random.Random(abs(hash(name)) % (2**31))

    def n(centre, amp=5):
        return clamp(centre + rng.uniform(-amp, amp))

    # Six CompanyProfile pillars
    pb  = n(base)   # public_benefit        25 %
    env = n(base)   # environmental         25 %
    mod = n(base)   # modernization         20 %
    gov = n(base)   # governance            15 %
    ac  = n(base)   # anti_corruption       10 %
    eth = n(base)   # ethical_alignment      5 %

    weighted = pb*0.25 + env*0.25 + mod*0.20 + gov*0.15 + ac*0.10 + eth*0.05
    total = clamp(round(weighted - penalty, 1), lo=1.0)

    # Sub-scores within each pillar
    jobs      = n(pb)
    reg_dev   = n(pb)
    infra_c   = n(pb)
    nat_val   = n(pb)

    waste     = n(env)
    water     = n(env)
    biodiv    = n(env)

    energy_tr = n(mod)
    digital   = n(mod)
    infra_u   = n(mod)
    future    = n(mod)

    trans_det = n(gov)
    audit     = n(gov)
    procure   = n(gov)

    # Five Company (league) sub-scores — weighted to produce ≈ target
    pol = n(float(target), 4)
    red = n(float(target), 4)
    inv = n(float(target), 4)
    tra = n(float(target), 4)
    com = n(float(target), 4)

    controversy = clamp(penalty * 7 + rng.uniform(-5, 5), lo=0.0)

    return {
        # CompanyProfile pillar scores
        'public_benefit_score':             pb,
        'environmental_responsibility_score': env,
        'modernization_score':              mod,
        'transparency_anti_corruption_score': gov,
        'anti_corruption_score':            ac,
        'ethical_alignment_score':          eth,
        # CompanyProfile sub-scores
        'jobs_created_score':                     jobs,
        'regional_development_score':             reg_dev,
        'infrastructure_contribution_score':      infra_c,
        'national_value_score':                   nat_val,
        'waste_management_score':                 waste,
        'water_impact_score':                     water,
        'biodiversity_impact_score':              biodiv,
        'energy_transition_score':                energy_tr,
        'digitalization_score':                   digital,
        'infrastructure_upgrade_score':           infra_u,
        'future_readiness_score':                 future,
        'transparency_score_detail':              trans_det,
        'audit_quality_score':                    audit,
        'procurement_transparency_score':         procure,
        'controversy_risk_score':                 controversy,
        # Totals
        'harm_penalty':     float(penalty),
        'ecoiq_total_score': total,
        'moral_label':       moral_label(total),
        # Company (league) sub-scores
        'score_pollution_footprint': pol,
        'score_reduction_progress':  red,
        'score_investment':          inv,
        'score_transparency':        tra,
        'score_community_impact':    com,
    }


# ── Management command ────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = 'Seed UK, Saudi, Kazakh and Global company profiles (skips existing slugs).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--overwrite', action='store_true',
            help='Overwrite scores for already-existing companies',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        from league.models import Company
        from companies.models import CompanyProfile

        overwrite = options['overwrite']
        created = updated = skipped = 0

        for (name, sector, country, target, harm_level) in COMPANIES:
            slug = slugify(name)
            scores = gen_scores(name, target, harm_level)

            # ── Company (league) ─────────────────────────────────────────────
            company, co_created = Company.objects.get_or_create(
                slug=slug,
                defaults=dict(
                    name=name,
                    sector=sector,
                    country=country,
                    is_public=True,
                    verified=False,
                    score_pollution_footprint=scores['score_pollution_footprint'],
                    score_reduction_progress =scores['score_reduction_progress'],
                    score_investment         =scores['score_investment'],
                    score_transparency       =scores['score_transparency'],
                    score_community_impact   =scores['score_community_impact'],
                ),
            )

            if not co_created and overwrite:
                company.name    = name
                company.sector  = sector
                company.country = country
                company.score_pollution_footprint = scores['score_pollution_footprint']
                company.score_reduction_progress  = scores['score_reduction_progress']
                company.score_investment          = scores['score_investment']
                company.score_transparency        = scores['score_transparency']
                company.score_community_impact    = scores['score_community_impact']
                company.save()
            elif not co_created:
                # Check if profile already exists; if yes, skip
                if CompanyProfile.objects.filter(company=company).exists():
                    skipped += 1
                    continue
            else:
                # Trigger compute_score via save (slug+score set in defaults)
                company.save()

            # ── CompanyProfile ───────────────────────────────────────────────
            profile_defaults = dict(
                status            = 'public',
                is_verified       = False,
                pollution_level   = POLLUTION_MAP[harm_level],
                # Pillar scores
                public_benefit_score              = scores['public_benefit_score'],
                environmental_responsibility_score= scores['environmental_responsibility_score'],
                modernization_score               = scores['modernization_score'],
                transparency_anti_corruption_score= scores['transparency_anti_corruption_score'],
                anti_corruption_score             = scores['anti_corruption_score'],
                ethical_alignment_score           = scores['ethical_alignment_score'],
                # Sub-scores
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
                # Totals
                harm_penalty      = scores['harm_penalty'],
                ecoiq_total_score = scores['ecoiq_total_score'],
                moral_label       = scores['moral_label'],
                ai_summary        = make_ai_summary(name, sector, country, scores),
            )

            profile, pr_created = CompanyProfile.objects.get_or_create(
                company=company,
                defaults=profile_defaults,
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
                    f"  {verb:7s} [{country[:15]:15s}] {name[:40]:40s} "
                    f"EcoIQ={scores['ecoiq_total_score']:5.1f}  {harm_level}"
                )
            )

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. Created={created}  Updated={updated}  Skipped={skipped}"
        ))
