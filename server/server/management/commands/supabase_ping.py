from __future__ import annotations

from django.core.management.base import BaseCommand

from server.supabase_client import get_supabase_clients


class Command(BaseCommand):
    help = "Ping Supabase (auth + REST) using .env credentials"

    def add_arguments(self, parser):
        parser.add_argument(
            "--table",
            default=None,
            help="Optional: a table name to try selecting from (requires RLS/permissions).",
        )

    def handle(self, *args, **options):
        clients = get_supabase_clients()

        # Validates service-role key against Supabase Auth API.
        result = clients.service.auth.admin.list_users()
        users = getattr(result, "users", None) or []
        self.stdout.write(
            self.style.SUCCESS(f"Supabase auth OK ({len(users)} user(s) in project)")
        )

        table = options.get("table")
        if table:
            res = clients.service.table(table).select("*").limit(1).execute()
            self.stdout.write(self.style.SUCCESS(f"Select OK from '{table}': {res.data}"))

