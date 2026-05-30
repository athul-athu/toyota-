from __future__ import annotations

import re

from django.conf import settings
from django.http import HttpResponse


def is_origin_allowed(origin: str) -> bool:
    if not origin:
        return False
    allowed = getattr(settings, "CORS_ALLOWED_ORIGINS", [])
    if origin in allowed:
        return True
    for pattern in getattr(settings, "CORS_ALLOWED_ORIGIN_REGEXES", []):
        if re.fullmatch(pattern, origin):
            return True
    return False


def apply_cors_headers(response: HttpResponse, origin: str) -> None:
    response["Access-Control-Allow-Origin"] = origin
    if getattr(settings, "CORS_ALLOW_CREDENTIALS", False):
        response["Access-Control-Allow-Credentials"] = "true"
    methods = getattr(settings, "CORS_ALLOW_METHODS", None)
    if methods:
        response["Access-Control-Allow-Methods"] = ", ".join(methods)
    headers = getattr(settings, "CORS_ALLOW_HEADERS", None)
    if headers:
        response["Access-Control-Allow-Headers"] = ", ".join(headers)
    expose = getattr(settings, "CORS_EXPOSE_HEADERS", None)
    if expose:
        response["Access-Control-Expose-Headers"] = ", ".join(expose)
    response["Access-Control-Max-Age"] = str(
        getattr(settings, "CORS_PREFLIGHT_MAX_AGE", 86400)
    )
    vary = response.get("Vary", "")
    if "Origin" not in vary:
        response["Vary"] = f"{vary}, Origin".strip(", ")


def cors_preflight_response(origin: str) -> HttpResponse:
    response = HttpResponse(status=200)
    apply_cors_headers(response, origin)
    return response
