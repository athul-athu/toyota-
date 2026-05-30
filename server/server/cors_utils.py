from __future__ import annotations

from django.conf import settings
from django.http import HttpResponse


def is_origin_allowed(origin: str) -> bool:
    """All origins allowed (see CORS_ALLOW_ALL_ORIGINS in settings)."""
    return True


def apply_cors_headers(response: HttpResponse, origin: str) -> None:
    if origin:
        response["Access-Control-Allow-Origin"] = origin
    elif getattr(settings, "CORS_ALLOW_ALL_ORIGINS", False):
        response["Access-Control-Allow-Origin"] = "*"
    if getattr(settings, "CORS_ALLOW_CREDENTIALS", False) and origin:
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
    if origin and "Origin" not in vary:
        response["Vary"] = f"{vary}, Origin".strip(", ")


def cors_preflight_response(origin: str) -> HttpResponse:
    response = HttpResponse(status=200)
    apply_cors_headers(response, origin)
    return response
