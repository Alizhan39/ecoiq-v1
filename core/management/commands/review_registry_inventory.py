"""Read-only operator access to the typed review inventory; never a verdict."""
import json

from django.core.management.base import BaseCommand, CommandError

from ecoiq_os.review_registry import REGISTRY_KINDS, registry_page, registry_summary


class Command(BaseCommand):
    help = "Inspect canonical catalogue counts or one bounded page of review work."

    def add_arguments(self, parser):
        parser.add_argument("--entries", action="store_true", help="Show a bounded entry page.")
        parser.add_argument("--kind", choices=REGISTRY_KINDS)
        parser.add_argument("--start", type=int, default=0)
        parser.add_argument("--limit", type=int, default=50)

    def handle(self, *args, **options):
        try:
            if options["entries"]:
                result = registry_page(kind=options["kind"], start=options["start"], limit=options["limit"])
            elif options["kind"] is not None or options["start"] != 0 or options["limit"] != 50:
                raise ValueError("Pagination options require --entries.")
            else:
                result = registry_summary()
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
