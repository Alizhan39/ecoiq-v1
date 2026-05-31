"""
check_public_placeholders — Scan public company profiles for forbidden phrases.

Finds profiles whose ai_summary contains seed placeholder text that should
never appear in a production environment:
  - "Seeded by"
  - "focus_target_markets"
  - "add_400_companies"
  - "seed_global_companies"
  - "lorem ipsum"
  - "placeholder"
  - "TODO"

Usage:
    python manage.py check_public_placeholders
    python manage.py check_public_placeholders --fix   # update summaries using make_ai_summary
    python manage.py check_public_placeholders --fail-on-found  # exit 1 if any found (CI use)
"""
from django.core.management.base import BaseCommand, CommandError


FORBIDDEN_PHRASES = (
    'seeded by',
    'focus_target_markets',
    'add_400_companies',
    'seed_global_companies',
    'seed_phase2_companies',
    'lorem ipsum',
    'placeholder',
    'TODO',
)


class Command(BaseCommand):
    help = 'Scan public CompanyProfile records for seed placeholder text in ai_summary.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix', action='store_true',
            help='Regenerate ai_summary for affected profiles using make_ai_summary()',
        )
        parser.add_argument(
            '--fail-on-found', action='store_true',
            help='Exit with code 1 if any placeholder profiles are found (for CI pipelines)',
        )

    def handle(self, *args, **options):
        from companies.models import CompanyProfile

        profiles = CompanyProfile.objects.filter(
            status__in=('public', 'verified')
        ).select_related('company')

        found = []
        for profile in profiles:
            summary_lower = (profile.ai_summary or '').lower()
            matched = [p for p in FORBIDDEN_PHRASES if p.lower() in summary_lower]
            if matched:
                found.append((profile, matched))

        if not found:
            self.stdout.write(self.style.SUCCESS(
                f'OK — No placeholder text found in {profiles.count()} public profiles.'
            ))
            return

        self.stdout.write(self.style.WARNING(
            f'\nFound {len(found)} profile(s) with placeholder text:\n'
        ))

        for profile, phrases in found:
            self.stdout.write(
                self.style.ERROR(
                    f'  [{profile.company.country}] {profile.company.name}'
                    f'  — matches: {", ".join(phrases)}'
                )
            )
            if options.get('verbosity', 1) >= 2:
                self.stdout.write(f'    Summary: {(profile.ai_summary or "")[:120]}')

        if options['fix']:
            self.stdout.write(self.style.MIGRATE_HEADING(
                f'\n── Fixing {len(found)} profiles ──'
            ))
            # Import the summary generator from focus_target_markets
            try:
                from companies.management.commands.focus_target_markets import make_ai_summary
                from companies.management.commands.focus_target_markets import gen_scores
            except ImportError as exc:
                raise CommandError(f'Cannot import make_ai_summary: {exc}')

            fixed = 0
            for profile, _ in found:
                co = profile.company
                # We don't have the original target/harm_level, so derive scores from stored values
                scores = {'ecoiq_total_score': float(profile.ecoiq_total_score or 50)}
                new_summary = make_ai_summary(co.name, co.sector, co.country, scores)
                profile.ai_summary = new_summary
                profile.save(update_fields=['ai_summary'])
                self.stdout.write(self.style.SUCCESS(
                    f'  Fixed: {co.name}'
                ))
                fixed += 1

            self.stdout.write(self.style.SUCCESS(f'\nFixed {fixed} profiles.'))

        elif options['fail_on_found']:
            raise CommandError(
                f'{len(found)} placeholder profile(s) found. '
                'Run with --fix to repair, or re-seed with updated commands.'
            )
        else:
            self.stdout.write(
                '\nRun with --fix to update affected summaries, '
                'or re-deploy (build.sh will regenerate all seeded profiles).'
            )
