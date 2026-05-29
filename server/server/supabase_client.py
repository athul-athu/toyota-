from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from supabase import Client, create_client


@dataclass(frozen=True)
class SupabaseClients:
    public: Client
    service: Client


_clients: SupabaseClients | None = None


def get_supabase_clients() -> SupabaseClients:
    """
    Returns cached Supabase clients.

    - public: uses SUPABASE_ANON_KEY (safe for end-user permissions)
    - service: uses SUPABASE_SERVICE_ROLE_KEY (admin permissions; server-only)
    """
    global _clients
    if _clients is not None:
        return _clients

    url = getattr(settings, "SUPABASE_URL", None)
    anon_key = getattr(settings, "SUPABASE_ANON_KEY", None)
    service_key = getattr(settings, "SUPABASE_SERVICE_ROLE_KEY", None)

    missing = [
        name
        for name, value in [
            ("SUPABASE_URL", url),
            ("SUPABASE_ANON_KEY", anon_key),
            ("SUPABASE_SERVICE_ROLE_KEY", service_key),
        ]
        if not value
    ]
    if missing:
        raise RuntimeError(f"Missing Supabase settings: {', '.join(missing)}")

    _clients = SupabaseClients(
        public=create_client(url, anon_key),
        service=create_client(url, service_key),
    )
    return _clients

