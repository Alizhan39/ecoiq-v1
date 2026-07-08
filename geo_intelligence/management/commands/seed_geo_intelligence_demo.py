"""
Seed the EcoIQ Geo Intelligence Phase 1 demo (idempotent).

Real Kazakhstan city coordinates (Almaty, Astana, Shymkent, Karaganda) are
genuine geographic facts, not demo data. The one stewardship-site marker and
the one investment opportunity are built directly from the real, already-
seeded Kazakhstan Clean Heat Stewardship Tour (khalifa_stewardship_tour_
operating_system) — its real capex/benefit figures, never re-derived or
guessed here — and are explicitly flagged `is_demo=True`. The one climate
risk zone is derived from a real, live Meteostat fetch for Almaty; if that
fetch fails (e.g. no network in this environment), the command still
completes and simply skips creating a risk zone rather than inventing one.

Usage:
    python manage.py seed_geo_intelligence_demo
"""
from django.core.management.base import BaseCommand

from countries.models import CountryProfile
from geo_intelligence.models import GeoAsset, GeoRiskZone, InvestmentGeoOpportunity
from geo_intelligence.services import weather

KAZAKHSTAN_CLEAN_HEAT_SLUG = 'kazakhstan-clean-heat'
# A small, deterministic offset from Almaty's own centroid so the demo
# household marker doesn't sit exactly on top of the city marker.
DEMO_SITE_LATITUDE = 43.28
DEMO_SITE_LONGITUDE = 76.95


class Command(BaseCommand):
    help = 'Seed EcoIQ Geo Intelligence Phase 1: Kazakhstan cities, one real stewardship-site asset, one Meteostat-derived risk zone, one investment opportunity.'

    def handle(self, *args, **options):
        kazakhstan = CountryProfile.objects.filter(name__iexact='Kazakhstan').first()

        city_count = 0
        for name, coords in weather.KAZAKHSTAN_CITIES.items():
            asset, _ = GeoAsset.objects.get_or_create(
                name=name, asset_type='city',
                defaults={'latitude': coords['latitude'], 'longitude': coords['longitude']},
            )
            asset.latitude = coords['latitude']
            asset.longitude = coords['longitude']
            asset.city = name
            asset.country = kazakhstan
            asset.is_demo = False  # real, verifiable city coordinates — not sample data
            asset.notes = 'Reference city — real coordinates, not a company/asset location.'
            asset.save()
            city_count += 1

        stewardship_asset = None
        tour = self._get_kazakhstan_tour()
        almaty_climate = weather.get_city_climate_summary(
            'Almaty', **{k: v for k, v in weather.KAZAKHSTAN_CITIES['Almaty'].items()},
        )
        exposure_score = weather.climate_exposure_score(almaty_climate)

        if tour is not None:
            stewardship_asset, _ = GeoAsset.objects.get_or_create(
                name=tour.title, asset_type='stewardship_site',
                defaults={'latitude': DEMO_SITE_LATITUDE, 'longitude': DEMO_SITE_LONGITUDE},
            )
            stewardship_asset.latitude = DEMO_SITE_LATITUDE
            stewardship_asset.longitude = DEMO_SITE_LONGITUDE
            stewardship_asset.region = tour.region
            stewardship_asset.country = kazakhstan
            stewardship_asset.sector = 'Residential Heating'
            stewardship_asset.climate_exposure_score = exposure_score
            stewardship_asset.modernisation_priority = 'high'
            stewardship_asset.source_reference = f'khalifa_stewardship_tour_operating_system:{tour.slug}'
            stewardship_asset.workbench_case_slug = KAZAKHSTAN_CLEAN_HEAT_SLUG
            stewardship_asset.workbench_agent_slug = 'research-agent'
            stewardship_asset.is_demo = True
            stewardship_asset.notes = f'Built from the real, seeded "{tour.title}" tour (status: {tour.get_status_display()}).'
            stewardship_asset.save()

        risk_zone = None
        if almaty_climate['available']:
            current = almaty_climate['extreme_heat_days_current_year']
            previous = almaty_climate['extreme_heat_days_previous_year']
            severity = 'high' if (previous is not None and current > previous) else 'medium'
            risk_zone, _ = GeoRiskZone.objects.get_or_create(
                name='Almaty Extreme Heat Zone', risk_type='extreme_heat',
                defaults={'latitude': weather.KAZAKHSTAN_CITIES['Almaty']['latitude'],
                          'longitude': weather.KAZAKHSTAN_CITIES['Almaty']['longitude']},
            )
            risk_zone.latitude = weather.KAZAKHSTAN_CITIES['Almaty']['latitude']
            risk_zone.longitude = weather.KAZAKHSTAN_CITIES['Almaty']['longitude']
            risk_zone.region = 'Almaty Region'
            risk_zone.country = kazakhstan
            risk_zone.radius_km = 40.0
            risk_zone.severity = severity
            risk_zone.confidence = 80.0
            risk_zone.source = f'Meteostat historical analysis — {current} extreme-heat days ({almaty_climate["years"][1]}) vs {previous} ({almaty_climate["years"][0]})'
            risk_zone.is_demo = True
            risk_zone.save()
        else:
            self.stdout.write(self.style.WARNING(
                f'Skipped Almaty risk zone — live Meteostat fetch unavailable ({almaty_climate["reason"]}).',
            ))

        opportunity = None
        if tour is not None:
            intervention = (
                tour.problems.first().interventions.order_by('-estimated_benefit').first()
                if tour.problems.exists() else None
            )
            if intervention is not None:
                investment_score = None
                if intervention.capex_estimate and intervention.estimated_benefit is not None:
                    investment_score = round(min(100, (intervention.estimated_benefit / intervention.capex_estimate) * 100), 0)
                opportunity, _ = InvestmentGeoOpportunity.objects.get_or_create(
                    title=f'{tour.region} — {intervention.title}',
                    defaults={'latitude': DEMO_SITE_LATITUDE, 'longitude': DEMO_SITE_LONGITUDE},
                )
                opportunity.latitude = DEMO_SITE_LATITUDE
                opportunity.longitude = DEMO_SITE_LONGITUDE
                opportunity.region = tour.region
                opportunity.country = kazakhstan
                opportunity.opportunity_type = 'heating_replacement'
                opportunity.estimated_impact = (
                    f'{intervention.currency} {intervention.estimated_benefit:,.0f} estimated annual benefit '
                    f'vs {intervention.currency} {intervention.capex_estimate:,.0f} capex'
                )
                opportunity.risk_level = 'medium'
                opportunity.investment_score = investment_score
                opportunity.confidence = 70.0
                opportunity.recommended_action = 'Review with Capital Allocation Agent before funder outreach.'
                opportunity.source_reference = f'khalifa_stewardship_tour_operating_system:{tour.slug}'
                opportunity.workbench_case_slug = KAZAKHSTAN_CLEAN_HEAT_SLUG
                opportunity.workbench_agent_slug = 'capital-allocation-agent'
                opportunity.is_demo = True
                opportunity.save()

        self.stdout.write(self.style.SUCCESS(
            f'Geo Intelligence demo ready: {city_count} reference cities, '
            f'{"1" if stewardship_asset else "0"} stewardship-site asset, '
            f'{"1" if risk_zone else "0"} climate risk zone, '
            f'{"1" if opportunity else "0"} investment opportunity. '
            f'Totals — assets: {GeoAsset.objects.count()}, risk zones: {GeoRiskZone.objects.count()}, '
            f'opportunities: {InvestmentGeoOpportunity.objects.count()}.',
        ))

    def _get_kazakhstan_tour(self):
        try:
            from khalifa_stewardship_tour_operating_system.models import StewardshipTour
        except ImportError:
            return None
        return StewardshipTour.objects.filter(slug=KAZAKHSTAN_CLEAN_HEAT_SLUG).prefetch_related(
            'problems__interventions',
        ).first()
