from dataclasses import dataclass
from typing import Optional

from django.utils import timezone

from users.models import OAuthToken


class CalendarSyncError(Exception):
    """Raised when calendar synchronisation fails."""


@dataclass
class CalendarSyncResult:
    success: bool
    message: str = ""
    event_id: Optional[str] = None


class CalendarService:
    """A lightweight abstraction over external calendar providers."""

    default_provider = "google"

    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or self.default_provider

    # --- CRUD helpers -------------------------------------------------
    def create_event(self, appointment) -> str:
        token = self._get_token(appointment)
        return self._build_event_id(appointment, token)

    def update_event(self, appointment) -> str:
        token = self._get_token(appointment)
        if not appointment.calendar_event_id:
            raise CalendarSyncError("رویداد قبلی برای بروزرسانی یافت نشد.")
        # در پیاده‌سازی واقعی باید درخواست API ارسال شود.
        return appointment.calendar_event_id

    def delete_event(self, appointment) -> None:
        token = self._get_token(appointment)
        if not appointment.calendar_event_id:
            raise CalendarSyncError("رویداد تقویمی برای حذف وجود ندارد.")
        # حذف رویداد در پیاده‌سازی واقعی انجام می‌شود.
        return None

    # --- internal helpers ---------------------------------------------
    def _get_token(self, appointment):
        lawyer_user = appointment.lawyer.user
        token = OAuthToken.objects.filter(user=lawyer_user, provider=self.provider).first()
        if not token:
            raise CalendarSyncError("توکن OAuth برای همگام‌سازی تقویم یافت نشد.")
        if token.is_expired:
            raise CalendarSyncError("توکن OAuth منقضی شده است، لطفاً مجدداً وارد شوید.")
        # دسترسی به access_token برای جلوگیری از هشدارهای lint
        _ = token.access_token
        return token

    def _build_event_id(self, appointment, token: OAuthToken) -> str:
        timestamp = int(timezone.now().timestamp())
        return f"{self.provider}-{appointment.pk}-{timestamp}"
