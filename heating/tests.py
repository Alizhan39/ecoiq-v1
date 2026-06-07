"""Khalifa Heat — tests for calculator logic, pages, forms and admin actions."""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from .models import (
    HeatingPackage, HeatingApplication, HomeAssessment, CompanySponsorshipLead,
)
from .calculator import recommend, recommend_boiler_kw


class CalculatorLogicTests(TestCase):
    def test_boiler_sizing_rounds_up_to_standard(self):
        # 100 m² medium = 100 W/m² = 10 kW -> next standard size 12
        self.assertEqual(recommend_boiler_kw(100, 'medium'), 12)
        # 50 m² good = 70 W/m² = 3.5 kW -> 6
        self.assertEqual(recommend_boiler_kw(50, 'good'), 6)
        # 200 m² poor = 130 W/m² = 26 kW -> caps at 24
        self.assertEqual(recommend_boiler_kw(200, 'poor'), 24)

    def test_three_phase_warning_for_large_boiler_on_220v(self):
        r = recommend(120, 'medium', 4, True, '220', 30, 'full_install', 'full')
        self.assertTrue(r['capacity_warning'])
        self.assertIn('380V', r['capacity_warning'])

    def test_capacity_warning_when_supply_too_low(self):
        r = recommend(60, 'good', 3, True, '380', 4, 'assisted', 'assisted')
        self.assertTrue(r['capacity_warning'])

    def test_diy_warning_for_demanding_setup(self):
        r = recommend(150, 'poor', 6, True, '380', 40, 'diy_basic', 'diy')
        self.assertTrue(r['installation_warning'])

    def test_insulation_recommendation_for_poor(self):
        r = recommend(80, 'poor', 3, True, '380', 40, 'assisted', 'full')
        self.assertTrue(r['insulation_recommendation'])

    def test_hp_ready_recommended_for_large_home(self):
        r = recommend(140, 'medium', 5, True, '380', 40, 'full_install', 'full')
        self.assertTrue(r['hp_ready_recommended'])

    def test_large_home_surcharge_applied(self):
        small = recommend(60, 'good', 2, True, '380', 40, 'assisted', 'full')
        large = recommend(60, 'good', 6, True, '380', 40, 'assisted', 'full')  # rooms>=5
        self.assertFalse(small['large_home_surcharge'])
        self.assertTrue(large['large_home_surcharge'])
        self.assertGreater(large['estimated_cost_min'], small['estimated_cost_min'])


class PagesTests(TestCase):
    def setUp(self):
        self.c = Client(SERVER_NAME='localhost')

    def test_all_pages_200(self):
        for name in ['overview', 'packages', 'calculator', 'company_sponsorship', 'pilot_application']:
            r = self.c.get(reverse(f'heating:{name}'))
            self.assertEqual(r.status_code, 200, name)

    def test_packages_seeded_by_migration(self):
        self.assertEqual(HeatingPackage.objects.count(), 5)

    def test_calculator_post_creates_assessment_and_shows_result(self):
        r = self.c.post(reverse('heating:calculator'), {
            'area_m2': 100, 'insulation': 'medium', 'rooms': 4, 'has_radiators': 'yes',
            'electricity': '380', 'available_kw': '30', 'package': 'full_install', 'install_type': 'full',
        })
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Recommended boiler size')
        self.assertEqual(HomeAssessment.objects.count(), 1)
        self.assertEqual(HomeAssessment.objects.first().recommended_kw, 12)


class LeadFormTests(TestCase):
    def setUp(self):
        self.c = Client(SERVER_NAME='localhost')

    def test_household_application_creates_lead(self):
        r = self.c.post(reverse('heating:pilot_application'), {
            'form_type': 'household', 'hh-full_name': 'Aliya', 'hh-phone': '+77001234567',
            'hh-install_type': 'assisted',
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(HeatingApplication.objects.filter(lead_type='household').count(), 1)

    def test_akimat_application_sets_lead_type(self):
        r = self.c.post(reverse('heating:pilot_application'), {
            'form_type': 'akimat', 'ak-organisation': 'Almaty Akimat',
            'ak-full_name': 'Bekzat', 'ak-email': 'b@akimat.kz',
        })
        self.assertEqual(r.status_code, 200)
        obj = HeatingApplication.objects.filter(lead_type='akimat').first()
        self.assertIsNotNone(obj)
        self.assertEqual(obj.organisation, 'Almaty Akimat')

    def test_honeypot_blocks_household_lead(self):
        self.c.post(reverse('heating:pilot_application'), {
            'form_type': 'household', 'hh-full_name': 'Bot', 'hh-phone': '123',
            'hh-hp_field': 'spam',
        })
        self.assertEqual(HeatingApplication.objects.count(), 0)

    def test_company_sponsorship_creates_lead(self):
        r = self.c.post(reverse('heating:company_sponsorship'), {
            'company_name': 'Acme', 'contact_name': 'Dana', 'email': 'd@acme.kz',
            'package': 'sponsor_10',
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(CompanySponsorshipLead.objects.count(), 1)

    def test_company_honeypot_blocks(self):
        self.c.post(reverse('heating:company_sponsorship'), {
            'company_name': 'Acme', 'contact_name': 'Dana', 'email': 'd@acme.kz', 'hp_field': 'x',
        })
        self.assertEqual(CompanySponsorshipLead.objects.count(), 0)


class AdminActionTests(TestCase):
    def setUp(self):
        U = get_user_model()
        self.admin = U.objects.create_superuser('su', 'su@ecoiq.uk', 'x')
        self.c = Client(SERVER_NAME='localhost')
        self.c.force_login(self.admin)
        self.app = HeatingApplication.objects.create(full_name='Aliya', phone='123', lead_type='household')

    def test_generate_starter_report_action(self):
        self.c.post(reverse('admin:heating_heatingapplication_changelist'), {
            'action': 'generate_starter_report', '_selected_action': [str(self.app.pk)],
        })
        self.app.refresh_from_db()
        self.assertIn('STARTER REPORT', self.app.starter_report)

    def test_export_csv_action(self):
        r = self.c.post(reverse('admin:heating_heatingapplication_changelist'), {
            'action': 'export_leads_csv', '_selected_action': [str(self.app.pk)],
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'text/csv')
        self.assertIn('Aliya', r.content.decode())
