"""Views for managing calendar OAuth flows."""

from __future__ import annotations

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone

from rest_framework import permissions, status
from rest_framework.renderers import JSONRenderer, TemplateHTMLRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import OAuthToken
from users.serializers import OAuthTokenSerializer

from .oauth import (
    OAuthIntegrationError,
    build_state_for_user,
    extract_expiry,
    get_oauth_client,
    resolve_state,
)


def _token_defaults(client, payload):
    if "access_token" not in payload:
        raise OAuthIntegrationError("پاسخ OAuth شامل access_token نیست.")
    defaults = {
        "access_token": payload["access_token"],
        "scope": payload.get("scope") or " ".join(client.scope),
        "token_type": payload.get("token_type", "Bearer"),
    }
    refresh_token = payload.get("refresh_token")
    if refresh_token:
        defaults["refresh_token"] = refresh_token
    expires_at = extract_expiry(payload)
    if expires_at:
        defaults["expires_at"] = expires_at
    return defaults


class CalendarOAuthStartView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, provider):
        client = get_oauth_client(provider)
        state = build_state_for_user(request.user, provider)
        authorization_url = client.build_authorization_url(state)
        return Response(
            {
                "authorization_url": authorization_url,
                "state": state,
                "redirect_uri": client.redirect_uri,
                "provider": provider,
            },
            status=status.HTTP_200_OK,
        )


class CalendarOAuthCallbackView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    renderer_classes = [JSONRenderer, TemplateHTMLRenderer]

    def get(self, request, provider):
        code = request.query_params.get("code")
        state = request.query_params.get("state")

        if not code or not state:
            return self._render_error(request, provider, "پارامترهای لازم ارسال نشده‌اند.", status.HTTP_400_BAD_REQUEST)

        try:
            user = resolve_state(state, provider)
            client = get_oauth_client(provider)
            payload = client.exchange_code(code)
            defaults = _token_defaults(client, payload)
            token, _ = OAuthToken.objects.update_or_create(
                user=user,
                provider=provider,
                defaults=defaults,
            )
        except OAuthIntegrationError as exc:
            return self._render_error(request, provider, str(exc), status.HTTP_400_BAD_REQUEST)

        serializer = OAuthTokenSerializer(token)
        context = {
            "detail": "اتصال تقویم با موفقیت انجام شد.",
            "provider": provider,
            "token": serializer.data,
            "success": True,
        }
        return self._render_success(request, context)

    def _render_error(self, request, provider, message, http_status):
        context = {
            "detail": message,
            "provider": provider,
            "success": False,
        }
        if getattr(request.accepted_renderer, "format", None) == "html":
            return Response(context, template_name="appointments/oauth_callback.html", status=http_status)
        return Response(context, status=http_status)

    def _render_success(self, request, context):
        if getattr(request.accepted_renderer, "format", None) == "html":
            return Response(context, template_name="appointments/oauth_callback.html", status=status.HTTP_200_OK)
        return Response(context, status=status.HTTP_200_OK)


class CalendarOAuthRefreshView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, provider):
        token = get_object_or_404(OAuthToken, user=request.user, provider=provider)
        if not token.refresh_token:
            return Response({"detail": "توکن refresh در دسترس نیست."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            client = get_oauth_client(provider)
            payload = client.refresh_token(token.refresh_token)
            defaults = _token_defaults(client, payload)
            token.mark_refreshed(
                expires_in=payload.get("expires_in"),
                access_token=defaults["access_token"],
                refresh_token=defaults.get("refresh_token"),
                scope=defaults.get("scope"),
                token_type=defaults.get("token_type"),
            )
        except OAuthIntegrationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = OAuthTokenSerializer(token)
        return Response({"detail": "توکن با موفقیت تازه‌سازی شد.", "token": serializer.data})


class CalendarOAuthStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, provider):
        token = OAuthToken.objects.filter(user=request.user, provider=provider).first()
        if not token:
            return Response({"connected": False, "provider": provider})

        serializer = OAuthTokenSerializer(token)
        data = serializer.data
        data.update(
            {
                "connected": True,
                "needs_refresh": token.is_expired,
                "can_refresh": bool(token.refresh_token),
            }
        )
        return Response(data)


class CalendarOAuthConnectView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    renderer_classes = [TemplateHTMLRenderer]

    def get(self, request, provider="google"):
        start_url = reverse("appointments:calendar-oauth-start", args=[provider])
        status_url = reverse("appointments:calendar-oauth-status", args=[provider])
        refresh_url = reverse("appointments:calendar-oauth-refresh", args=[provider])
        disconnect_url = reverse("users:oauth-token", args=[provider])
        callback_url = getattr(
            settings,
            "GOOGLE_OAUTH_REDIRECT_URI",
            "http://localhost:8000/appointments/calendar/oauth/google/callback/",
        )
        context = {
            "provider": provider,
            "start_url": start_url,
            "status_url": status_url,
            "refresh_url": refresh_url,
            "disconnect_url": disconnect_url,
            "callback_url": callback_url,
            "generated_at": timezone.now(),
        }
        return Response(context, template_name="appointments/calendar_connect.html")


__all__ = [
    "CalendarOAuthStartView",
    "CalendarOAuthCallbackView",
    "CalendarOAuthRefreshView",
    "CalendarOAuthStatusView",
    "CalendarOAuthConnectView",
]
