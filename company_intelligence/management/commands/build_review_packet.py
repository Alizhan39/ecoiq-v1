"""
build_review_packet — the proposed evidence for one organisation, as something
a person can actually read.

INFORMATIONAL ONLY
------------------
This command writes nothing. It has no --apply, no --confirm, and no code path
that touches review_state; `apply_review_decision()` remains the only writer and
still requires a named reviewer. Running it against production is a read.

It exists because the alternative to a packet is a reviewer opening database
rows, and a reviewer who cannot see the source title, the principle's question
and what is still unknown is being asked to decide without the things the
decision depends on.
"""
import json

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Prints the review packet for an organisation\'s proposed evidence. Read-only.'

    def add_arguments(self, parser):
        parser.add_argument('--slug', required=True, help='Organisation slug.')
        parser.add_argument('--state', default='proposed',
                            help="Review state to include (default: proposed).")
        parser.add_argument('--json', action='store_true',
                            help='Emit JSON instead of the readable form.')

    def handle(self, *args, **options):
        from company_intelligence.models import CompanyKPIEvidenceLink
        from company_intelligence.services.review_recommendation import review_packet

        links = (CompanyKPIEvidenceLink.objects
                 .filter(assessment__company__company__slug=options['slug'],
                         review_state=options['state'])
                 .select_related('assessment', 'assessment__company',
                                 'assessment__company__company', 'evidence')
                 .order_by('assessment__kpi_id', 'pk'))
        packet = review_packet(links)

        if options['json']:
            self.stdout.write(json.dumps(packet, indent=2))
            return

        if not packet:
            self.stdout.write(f"No {options['state']} evidence for {options['slug']}.")
            return

        self.stdout.write(f"REVIEW PACKET — {packet[0]['entity']['name']}")
        self.stdout.write(f"{len(packet)} item(s) in state '{options['state']}'. "
                          f"Nothing here has been applied.\n")

        for i, item in enumerate(packet, 1):
            p, s, r = item['principle'], item['source'], item['recommendation']
            self.stdout.write(f"\n{'=' * 72}")
            self.stdout.write(f"[{i}/{len(packet)}] link #{item['link_id']} — "
                              f"Principle #{p['kpi_id']}: {p['title']}")
            self.stdout.write(f"{'=' * 72}")
            self.stdout.write(f"  QUESTION      {p['question']}")
            self.stdout.write(f"  SOURCE        {s['title'] or '(no title recorded)'}")
            self.stdout.write(f"  PUBLISHER     {s['publisher'] or '(none recorded)'}")
            self.stdout.write(f"  TYPE          {s['source_type'] or '(none)'}")
            self.stdout.write(f"  AUTHORITY     Tier {s['authority']['tier']} · "
                              f"{s['authority']['label']}")
            self.stdout.write(f"  PUBLISHED     {s['publication_date'] or 'UNKNOWN'}")
            self.stdout.write(f"  RETRIEVED     {s['retrieved_at'] or 'UNKNOWN'}")
            self.stdout.write(f"  LOCATION      {s['location'] or '(whole document)'}")
            self.stdout.write(f"  VERSION HASH  {s['content_hash'] or 'UNKNOWN'}")
            self.stdout.write(f"  URL           {s['url'] or '(none)'}")
            self.stdout.write(f"\n  WHY LINKED    {item['proposed']['match_basis'] or '(no basis recorded)'}")
            self.stdout.write(f"  PROPOSED AS   {item['proposed']['relationship']} "
                              f"({item['proposed']['review_state']}, counts toward "
                              f"assessment: {item['proposed']['counts_toward_assessment']})")
            self.stdout.write(f"\n  {r['label'].upper()}")
            self.stdout.write(f"    standing    {r['standing'] or '(none offered)'}")
            self.stdout.write(f"    reason      {r['reason']}")
            if item['uncertainty']:
                self.stdout.write("\n  STILL UNKNOWN")
                for gap in item['uncertainty']:
                    self.stdout.write(f"    - {gap}")
            self.stdout.write("\n  REVIEWER MUST DECIDE")
            for question in r['must_decide']:
                self.stdout.write(f"    - {question}")

        self.stdout.write(f"\n{'=' * 72}")
        self.stdout.write("Nothing above has been applied. Classification is an "
                          "explicit human action in the Evidence Review Workbench.")
