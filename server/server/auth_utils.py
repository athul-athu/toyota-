from __future__ import annotations

import functools
import logging

from django.http import JsonResponse

from server.supabase_client import get_supabase_clients

logger = logging.getLogger(__name__)


def bearer_token(request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip()
    return None


def require_auth(view_func):
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        token = bearer_token(request)
        if not token:
            return JsonResponse({"error": "Authorization required"}, status=401)

        try:
            user_res = get_supabase_clients().public.auth.get_user(jwt=token)
        except Exception as exc:
            logger.warning("Auth failed: %s", exc)
            return JsonResponse({"error": "Invalid or expired session"}, status=401)

        if not user_res.user:
            return JsonResponse({"error": "Invalid or expired session"}, status=401)

        request.auth_user = user_res.user
        return view_func(request, *args, **kwargs)

    return wrapper
