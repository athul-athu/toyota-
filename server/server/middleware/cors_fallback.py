from __future__ import annotations

import re

from django.conf import settings


def _origin_allowed(origin: str) -> bool:
    if origin in getattr(settings, "CORS_ALLOWED_ORIGINS", []):
        return True
    for pattern in getattr(settings, "CORS_ALLOWED_ORIGIN_REGEXES", []):
        if re.fullmatch(pattern, origin):
            return True
    return False


class EnsureCorsHeadersMiddleware:
    """Add CORS headers on error responses if django-cors-headers did not."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if response.get("Access-Control-Allow-Origin"):
            return response

        origin = request.headers.get("Origin")
        if origin and _origin_allowed(origin):
            response["Access-Control-Allow-Origin"] = origin
            if getattr(settings, "CORS_ALLOW_CREDENTIALS", False):
                response["Access-Control-Allow-Credentials"] = "true"
            response["Vary"] = "Origin"

        return response
