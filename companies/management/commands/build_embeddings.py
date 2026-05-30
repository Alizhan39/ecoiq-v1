"""
build_embeddings — Generate semantic search text (and optionally embeddings)
for all league.Company records.

Without pgvector / sentence-transformers:
  Builds a rich search_text field used by keyword fallback search.

With sentence-transformers + pgvector installed:
  Also generates 384-dimensional sentence embeddings for true semantic
  vector search (nearest-neighbour queries).

Usage:
  python manage.py build_embeddings
  python manage.py build_embeddings --company=schneider-electric
"""

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Build semantic search text (and optional vector embeddings) for all companies'

    def add_arguments(self, parser):
        parser.add_argument(
            '--company', type=str, default=None,
            help='Process a single company by slug'
        )
        parser.add_argument(
            '--force-text-only', action='store_true',
            help='Skip vector generation even if sentence-transformers is installed'
        )

    def handle(self, *args, **options):
        from league.models import Company

        # Try to import vector libraries — graceful degradation if absent
        use_vectors = False
        model = None
        if not options['force_text_only']:
            try:
                from sentence_transformers import SentenceTransformer
                from pgvector.django import L2Distance  # noqa — verify import
                model = SentenceTransformer('all-MiniLM-L6-v2')
                use_vectors = True
                self.stdout.write(
                    self.style.SUCCESS('sentence-transformers loaded — vector mode enabled')
                )
            except ImportError:
                self.stdout.write(
                    self.style.WARNING(
                        'sentence-transformers / pgvector not installed — '
                        'building search_text only (keyword fallback).'
                    )
                )

        qs = Company.objects.all()
        if options['company']:
            qs = qs.filter(slug=options['company'])
            if not qs.exists():
                self.stdout.write(self.style.ERROR(f"Company not found: {options['company']}"))
                return

        total = qs.count()
        self.stdout.write(f'Processing {total} companies…')
        updated = 0
        errors  = 0

        for company in qs.select_related('profile').iterator(chunk_size=50):
            profile = getattr(company, 'profile', None)

            # ── Build rich text representation ────────────────────────────
            parts = [
                f"{company.name}.",
                f"Sector: {company.get_sector_display() if hasattr(company,'get_sector_display') else company.sector}.",
                f"Country: {company.country}.",
                f"EcoIQ score: {company.ecoiq_score}.",
            ]
            if company.description:
                parts.append(company.description[:300])
            if profile:
                parts += [
                    f"Pollution level: {profile.get_pollution_level_display()}.",
                    f"Tier: {profile.moral_label_display}.",
                    f"Public benefit: {profile.public_benefit_score:.0f}.",
                    f"Environmental: {profile.environmental_responsibility_score:.0f}.",
                    f"Governance: {profile.transparency_anti_corruption_score:.0f}.",
                    f"Modernization: {profile.modernization_score:.0f}.",
                ]
            if company.ml_cluster_label:
                parts.append(f"Cluster: {company.ml_cluster_label}.")

            search_text = ' '.join(parts)[:600]

            # ── Save search_text ──────────────────────────────────────────
            update_fields = ['search_text']
            company.search_text = search_text

            # ── Optionally generate vector ────────────────────────────────
            if use_vectors and model is not None:
                try:
                    company.embedding = model.encode(search_text).tolist()
                    update_fields.append('embedding')
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'  Vector error for {company.name}: {e}')
                    )

            try:
                company.save(update_fields=update_fields)
                updated += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  Save error for {company.name}: {e}')
                )
                errors += 1

            if updated % 50 == 0 and updated > 0:
                self.stdout.write(f'  {updated}/{total}…')

        mode = 'vector + text' if use_vectors else 'text only'
        self.stdout.write(self.style.SUCCESS(
            f'\nDone — {updated} updated ({mode}), {errors} errors.'
        ))
