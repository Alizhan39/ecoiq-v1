"""
ingest_real_sustainability_evidence — feat/company-discovery-ranking
(PR 11): registers and ingests REAL, staff-verified official sustainability
report URLs for a small, controlled set of real public companies, closing
the real data gap PR10 documented — SEC EDGAR gives strong Shariah
financial-screening evidence but essentially no narrative stewardship
evidence, which is why PR10's Apple/Tesla both showed
kpi_candidates_proposed=0.

Real URLs used (verified reachable via `curl -sI` during development, never
guessed or fabricated):
  apple      — https://www.apple.com/environment/pdf/Apple_Environmental_Progress_Report_2024.pdf
               (real PDF, Apple's own domain, 200 OK, application/pdf)
  microsoft  — https://www.microsoft.com/en-us/corporate-responsibility/sustainability
               (real HTML, Microsoft's own domain, 200 OK)
  walmart    — https://corporate.walmart.com/purpose/sustainability
               (real HTML, Walmart's own domain, 200 OK)

Tesla and Unilever were deliberately NOT included: both real sustainability
domains (tesla.com, unilever.com) returned HTTP 403 to a standard fetch
during verification — an Akamai/WAF-level access restriction, not a
missing page. Per the brief's own instruction ("do not scrape in violation
of access restrictions"), this command does not attempt to bypass that —
Tesla's real, honest state is "narrative sustainability evidence
unavailable" (it still has real SEC EDGAR financial evidence from PR10),
which is itself a genuine, unforced "incomplete evidence" example for the
verification set, not a gap this command papers over.

Idempotent — re-running creates zero new SourceDocument/Evidence/
EvidenceMemory rows when the registered document's content is unchanged
(see harvester.services.ingestion_pipeline.ingest_source's SourceDocument
get_or_create on content_hash).
"""
from django.core.management.base import BaseCommand

# feat/stewardship-universe (PR 13) — moved to services/known_sources.py so
# this command and the new source_discovery service read the exact same
# curated list, never a second, possibly-drifting copy. Re-exported here
# under its original name for backward compatibility with anything that
# imported REAL_DOCUMENT_SOURCES from this module.
from company_intelligence.services.known_sources import KNOWN_SUSTAINABILITY_DOCUMENTS as REAL_DOCUMENT_SOURCES


class Command(BaseCommand):
    help = 'Registers and ingests REAL official sustainability report documents for a small set of real public companies (PR 11).'

    def add_arguments(self, parser):
        parser.add_argument('--slug', action='append', help='Company slug to ingest (repeatable). Default: all of REAL_DOCUMENT_SOURCES.')

    def handle(self, *args, **options):
        from league.models import Company
        from companies.models import CompanyProfile
        from company_intelligence.management.commands.ingest_real_company_evidence import REAL_COMPANY_SEEDS, _reference_methodology
        from company_intelligence.services.evidence_ingestion import ingest_sustainability_document
        from company_intelligence.services.shariah_screening import run_shariah_screen

        slugs = options.get('slug') or list(REAL_DOCUMENT_SOURCES.keys())
        methodology = _reference_methodology()

        for slug in slugs:
            doc_source = REAL_DOCUMENT_SOURCES.get(slug)
            if doc_source is None:
                self.stdout.write(self.style.WARNING(f'{slug}: no real document source registered — skipped.'))
                continue
            seed = REAL_COMPANY_SEEDS.get(slug, {'name': slug.title(), 'sector': 'other', 'country': 'United States'})

            company, _ = Company.objects.get_or_create(slug=slug, defaults={**seed, 'is_public': True})
            profile, _ = CompanyProfile.objects.get_or_create(company=company, defaults={'status': 'public'})

            result = ingest_sustainability_document(
                profile, doc_source['url'], doc_source['document_type'], publisher=doc_source['publisher'],
            )
            run = result['ingestion_run']
            if run is None or run.status == 'failed':
                self.stdout.write(self.style.WARNING(f'{slug}: document fetch failed — {run.error_message if run else "no run recorded"}'))
                continue

            # Re-screen Shariah with whatever financial facts already exist
            # (this command adds narrative evidence, not financial facts —
            # run_shariah_screen reuses the latest CompanyFinancialFacts
            # snapshot from ingest_real_company_evidence if that command
            # already ran for this company; otherwise Not Screened, honest).
            latest_facts = profile.financial_facts.order_by('-as_of_date', '-id').first()
            screen = run_shariah_screen(profile, methodology, financial_facts=latest_facts) if latest_facts else None

            self.stdout.write(
                f'{slug}: document_ingestion={run.status}, '
                f'kpi_candidates_proposed={len(result["kpi_candidates_proposed"])}, '
                f'shariah={"re-screened: " + screen.overall_result if screen else "not re-screened (no financial facts on file yet)"}'
            )
            for w in result['warnings']:
                self.stdout.write(f'  ⚠ {w}')

        self.stdout.write(self.style.SUCCESS(
            'Real sustainability document ingestion complete. Every chunk is real, sourced, and traceable to '
            'its exact page/section — never one giant evidence record for a whole report.'
        ))
