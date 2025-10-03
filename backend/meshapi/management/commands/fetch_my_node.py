from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from meshapi.services import get_or_refresh_node_info


class Command(BaseCommand):
    help = "Fetch and store My Node info (refreshes cache)"

    def add_arguments(self, parser):
        parser.add_argument("--name", default="JOST_DEV", help="Node name (default: JOST_DEV)")
        parser.add_argument("--max-age", type=int, default=0, help="Max age in seconds; 0 forces refresh")

    def handle(self, *args, **options):
        name = options["name"]
        max_age = int(options.get("max_age") or 0)
        try:
            data, ts = get_or_refresh_node_info(name=name, max_age_seconds=max_age)
        except Exception as e:
            raise CommandError(str(e))
        self.stdout.write(self.style.SUCCESS(f"Fetched info for {name} at {ts.isoformat()}"))

