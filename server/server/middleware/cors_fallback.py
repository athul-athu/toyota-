from __future__ import annotations

from server.cors_utils import apply_cors_headers, cors_preflight_response


class EarlyCorsMiddleware:
    """Answer OPTIONS for /api/* before auth, CSRF, or view method checks."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = request.headers.get("Origin", "")
        if request.method == "OPTIONS" and request.path.startswith("/api/"):
            return cors_preflight_response(origin)
        return self.get_response(request)


class EnsureCorsHeadersMiddleware:
    """Add CORS headers to API responses when django-cors-headers did not."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = request.headers.get("Origin", "")
        response = self.get_response(request)

        if (
            request.path.startswith("/api/")
            and not response.get("Access-Control-Allow-Origin")
        ):
            apply_cors_headers(response, origin)

        return response
