"""
python manage.py setup_wagtail_site

Creates the initial Wagtail page tree and site record.
Safe to run repeatedly — fully idempotent.
Run in build.sh after every deploy so the site record tracks SITE_URL.
"""
import os
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = 'Initialise Wagtail site structure (idempotent)'

    @transaction.atomic
    def handle(self, *args, **options):
        from wagtail.models import Page, Site
        from cms.models import HomePage, CompanyIndexPage, MethodologyPage, AboutPage

        self.stdout.write('Setting up Wagtail site structure…')

        # The Wagtail root page (depth=1) is created by migrations.
        root = Page.objects.filter(depth=1).first()
        if not root:
            self.stdout.write(self.style.ERROR(
                '  No root page — run python manage.py migrate first.'
            ))
            return

        # ── HomePage ──────────────────────────────────────────────────────────
        home_qs = HomePage.objects.all()
        if not home_qs.exists():
            # Wagtail creates a default Page with slug='home' on first migration.
            # If it exists but isn't a HomePage, change its slug so ours can use 'home'.
            from wagtail.models import Page as WagtailPage
            conflicting = WagtailPage.objects.filter(
                depth=2, slug='home',
            ).exclude(pk__in=HomePage.objects.values('pk')).first()
            if conflicting:
                conflicting.slug = 'wagtail-welcome'
                conflicting.save(update_fields=['slug'])
                self.stdout.write(f'  ○ Renamed conflicting page slug: {conflicting.title}')

            home = HomePage(
                title='EcoIQ — Environmental Intelligence Platform',
                slug='home',
                intro=(
                    '<p>EcoIQ measures real environmental impact across industrial '
                    'facilities. Every score is built from audited projects and '
                    'verified evidence.</p>'
                ),
            )
            root.add_child(instance=home)
            home.save_revision().publish()
            self.stdout.write(self.style.SUCCESS('  ✓ HomePage created'))
        else:
            home = home_qs.order_by('pk').first()
            self.stdout.write(f'  ○ HomePage exists: "{home.title}"')

        # ── CompanyIndexPage ──────────────────────────────────────────────────
        if not CompanyIndexPage.objects.exists():
            cip = CompanyIndexPage(
                title='Companies',
                slug='companies',
                intro=(
                    '<p>Editorial profiles for companies in the EcoIQ Good Deeds '
                    'League, combining live KPI data with curated narrative.</p>'
                ),
            )
            home.add_child(instance=cip)
            cip.save_revision().publish()
            self.stdout.write(self.style.SUCCESS('  ✓ CompanyIndexPage created at /pages/home/companies/'))
        else:
            self.stdout.write('  ○ CompanyIndexPage exists')

        # ── MethodologyPage ───────────────────────────────────────────────────
        if not MethodologyPage.objects.exists():
            mp = MethodologyPage(
                title='Methodology',
                slug='methodology',
                intro=(
                    '<p>How EcoIQ calculates the Good Deeds League ranking — '
                    'data sources, pillar weights, and verification process.</p>'
                ),
            )
            home.add_child(instance=mp)
            mp.save_revision().publish()
            self.stdout.write(self.style.SUCCESS('  ✓ MethodologyPage created'))
        else:
            self.stdout.write('  ○ MethodologyPage exists')

        # ── AboutPage ─────────────────────────────────────────────────────────
        if not AboutPage.objects.exists():
            ap = AboutPage(
                title='About EcoIQ',
                slug='about',
                intro=(
                    '<p>EcoIQ is an environmental intelligence platform for '
                    'industrial facilities in Central Asia and beyond.</p>'
                ),
            )
            home.add_child(instance=ap)
            ap.save_revision().publish()
            self.stdout.write(self.style.SUCCESS('  ✓ AboutPage created'))
        else:
            self.stdout.write('  ○ AboutPage exists')

        # ── Wagtail Site record ───────────────────────────────────────────────
        site_url = os.environ.get('SITE_URL', 'https://ecoiq.uk')
        is_https = site_url.startswith('https://')
        hostname = (
            site_url
            .replace('https://', '')
            .replace('http://', '')
            .rstrip('/')
        )
        port = 443 if is_https else 80

        site, created = Site.objects.update_or_create(
            is_default_site=True,
            defaults={
                'hostname':  hostname,
                'port':      port,
                'site_name': 'EcoIQ',
                'root_page': home,
            },
        )
        verb = 'Created' if created else 'Updated'
        self.stdout.write(self.style.SUCCESS(
            f'  ✓ {verb} default Site → {hostname}:{port}'
        ))

        self.stdout.write(self.style.SUCCESS(
            '\n✓ Wagtail setup complete.\n'
            '  CMS admin:   /cms-admin/\n'
            '  Pages:       /pages/home/\n'
            '  Companies:   /pages/home/companies/\n'
            '  Methodology: /pages/home/methodology/\n'
        ))
