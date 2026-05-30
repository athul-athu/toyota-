from __future__ import annotations

import json
import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from server.auth_utils import bearer_token
from server.supabase_client import get_supabase_clients

logger = logging.getLogger(__name__)


def _json_body(request) -> dict:
    if not request.body:
        return {}
    return json.loads(request.body)


def _default_profile(user_id: str, email: str, full_name: str | None = None) -> dict:
    return {
        "id": user_id,
        "email": email,
        "full_name": full_name,
        "role": "staff",
        "is_active": True,
    }


def _profile_for_user(service_client, user_id: str) -> dict | None:
    try:
        res = (
            service_client.table("admin_profiles")
            .select("id, email, full_name, role, is_active")
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )
        return res.data
    except Exception as exc:
        logger.warning("Could not load admin_profiles: %s", exc)
        return None


def _ensure_profile(
    service_client,
    user_id: str,
    email: str,
    full_name: str | None = None,
) -> dict:
    """Create or update profile; falls back if Supabase table is missing."""
    try:
        profile = _profile_for_user(service_client, user_id)
        if profile:
            updates = {}
            if not profile.get("is_active"):
                updates["is_active"] = True
            if full_name and not profile.get("full_name"):
                updates["full_name"] = full_name
            if updates:
                service_client.table("admin_profiles").update(updates).eq(
                    "id", user_id
                ).execute()
                profile = {**profile, **updates}
            return profile

        service_client.table("admin_profiles").insert(
            {
                "id": user_id,
                "email": email,
                "full_name": full_name,
                "role": "staff",
                "is_active": True,
            }
        ).execute()
        return _profile_for_user(service_client, user_id) or _default_profile(
            user_id, email, full_name
        )
    except Exception as exc:
        logger.warning("Profile sync skipped: %s", exc)
        return _default_profile(user_id, email, full_name)


def _user_payload(user, profile: dict) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "full_name": profile.get("full_name"),
        "role": profile.get("role"),
    }


def _session_payload(session, user_payload: dict) -> dict:
    return {
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
        "expires_in": session.expires_in,
        "user": user_payload,
    }


def _validate_credentials(email: str, password: str) -> str | None:
    if not email or not password:
        return "Email and password are required"
    if len(password) < 8:
        return "Password must be at least 8 characters"
    return None


@csrf_exempt
@require_http_methods(["POST"])
def signup(request):
    try:
        body = _json_body(request)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    full_name = (body.get("full_name") or "").strip() or None

    validation_error = _validate_credentials(email, password)
    if validation_error:
        return JsonResponse({"error": validation_error}, status=400)

    clients = get_supabase_clients()

    try:
        auth_res = clients.public.auth.sign_up(
            {
                "email": email,
                "password": password,
                "options": {"data": {"full_name": full_name}} if full_name else {},
            }
        )
    except Exception as exc:
        message = str(exc).lower()
        if "already" in message or "registered" in message:
            return JsonResponse({"error": "An account with this email already exists"}, status=409)
        return JsonResponse({"error": "Could not create account. Try again later."}, status=400)

    if not auth_res.user:
        return JsonResponse({"error": "Could not create account"}, status=400)

    profile = _ensure_profile(
        clients.service, auth_res.user.id, email, full_name
    )

    if not auth_res.session:
        return JsonResponse(
            {
                "message": "Account created. Check your email to confirm, then sign in.",
                "requires_email_confirmation": True,
            },
            status=201,
        )

    return JsonResponse(
        _session_payload(
            auth_res.session,
            _user_payload(auth_res.user, profile),
        ),
        status=201,
    )


@csrf_exempt
@require_http_methods(["POST"])
def login(request):
    try:
        body = _json_body(request)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""

    validation_error = _validate_credentials(email, password)
    if validation_error:
        return JsonResponse({"error": validation_error}, status=400)

    clients = get_supabase_clients()

    try:
        auth_res = clients.public.auth.sign_in_with_password(
            {"email": email, "password": password}
        )
    except Exception as exc:
        logger.warning("Login failed for %s: %s", email, exc)
        return JsonResponse({"error": "Invalid email or password"}, status=401)

    if not auth_res.session or not auth_res.user:
        return JsonResponse({"error": "Invalid email or password"}, status=401)

    try:
        profile = _ensure_profile(
            clients.service, auth_res.user.id, auth_res.user.email or email
        )
        return JsonResponse(
            _session_payload(
                auth_res.session,
                _user_payload(auth_res.user, profile),
            )
        )
    except Exception as exc:
        logger.exception("Login post-processing failed: %s", exc)
        return JsonResponse(
            {"error": "Login succeeded but server error. Try again."},
            status=500,
        )


@csrf_exempt
@require_http_methods(["GET"])
def me(request):
    token = bearer_token(request)
    if not token:
        return JsonResponse({"error": "Authorization required"}, status=401)

    clients = get_supabase_clients()

    try:
        user_res = clients.public.auth.get_user(jwt=token)
    except Exception:
        return JsonResponse({"error": "Invalid or expired session"}, status=401)

    user = user_res.user
    if not user:
        return JsonResponse({"error": "Invalid or expired session"}, status=401)

    profile = _ensure_profile(
        clients.service, user.id, user.email or ""
    )

    return JsonResponse({"user": _user_payload(user, profile)})


@csrf_exempt
@require_http_methods(["POST"])
def refresh(request):
    try:
        body = _json_body(request)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    refresh_token = (body.get("refresh_token") or "").strip()
    if not refresh_token:
        return JsonResponse({"error": "refresh_token is required"}, status=400)

    clients = get_supabase_clients()
    try:
        auth_res = clients.public.auth.refresh_session(refresh_token)
    except Exception as exc:
        logger.warning("Token refresh failed: %s", exc)
        return JsonResponse(
            {"error": "Session expired. Please sign in again."},
            status=401,
        )

    if not auth_res.session or not auth_res.user:
        return JsonResponse(
            {"error": "Session expired. Please sign in again."},
            status=401,
        )

    profile = _ensure_profile(
        clients.service, auth_res.user.id, auth_res.user.email or ""
    )
    return JsonResponse(
        _session_payload(
            auth_res.session,
            _user_payload(auth_res.user, profile),
        )
    )


@csrf_exempt
@require_http_methods(["POST"])
def logout(request):
    token = bearer_token(request)
    if token:
        clients = get_supabase_clients()
        try:
            clients.service.auth.admin.sign_out(token)
        except Exception:
            pass

    return JsonResponse({"ok": True})
