from __future__ import annotations

import re

from django.conf import settings
from django.http import HttpResponse


def _origin_allowed(origin: str) -> bool:
    if not origin:
        return False
    if origin in getattr(settings, "CORS_ALLOWED_ORIGINS", []):
        return True
    for pattern in getattr(settings, "CORS_ALLOWED_ORIGIN_REGEXES", []):
        if re.fullmatch(pattern, origin):
            return True
    return False


def _apply_cors_headers(response, origin: str) -> None:
    response["Access-Control-Allow-Origin"] = origin
    if getattr(settings, "CORS_ALLOW_CREDENTIALS", False):
        response["Access-Control-Allow-Credentials"] = "true"
    methods = getattr(settings, "CORS_ALLOW_METHODS", None)
    if methods:
        response["Access-Control-Allow-Methods"] = ", ".join(methods)
    headers = getattr(settings, "CORS_ALLOW_HEADERS", None)
    if headers:
        response["Access-Control-Allow-Headers"] = ", ".join(headers)
    response["Vary"] = "Origin"


class EnsureCorsHeadersMiddleware:
    """Ensure CORS headers on every API response (including errors)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = request.headers.get("Origin", "")

        if request.method == "OPTIONS" and _origin_allowed(origin):
            response = HttpResponse(status=204)
            _apply_cors_headers(response, origin)
            return response

        response = self.get_response(request)

        if not response.get("Access-Control-Allow-Origin") and _origin_allowed(origin):
            _apply_cors_headers(response, origin)

        return response
