import logging
import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Mapping, Optional

from django.db.models import QuerySet

from rest_framework.exceptions import ValidationError

from .integrations import CalendarService, CalendarSyncError

if TYPE_CHECKING:
    from .models import Appointment


logger = logging.getLogger(__name__)

GOOGLE_MEET_BASE_URL = "https://meet.google.com"


def _appointment_identifier(appointment: "Appointment") -> Optional[int]:
    return getattr(appointment, "pk", getattr(appointment, "id", None))


def _format_google_slug(seed: str) -> str:
    """Return a Meet-compatible slug in the form ``xxx-xxxx-xxx``."""

    cleaned = "".join(ch for ch in seed if ch.isalnum())
    if len(cleaned) < 10:
        cleaned = (cleaned + uuid.uuid4().hex)[:10]
    else:
        cleaned = cleaned[:10]

    return f"{cleaned[:3]}-{cleaned[3:7]}-{cleaned[7:10]}"


def _temporary_google_link(appointment_id: Optional[int] = None) -> str:
    slug_source = f"{appointment_id}-{uuid.uuid4().hex}" if appointment_id else uuid.uuid4().hex
    slug = _format_google_slug(slug_source)
    return f"{GOOGLE_MEET_BASE_URL}/{slug}"


def _calendar_backed_google_link(appointment: "Appointment", calendar_service: CalendarService) -> str:
    try:
        event_id = calendar_service.create_event(appointment)
    except CalendarSyncError as exc:
        identifier = _appointment_identifier(appointment)
        logger.warning(
            "Google Calendar event creation failed for appointment %s: %s",
            identifier,
            exc,
        )
        return _temporary_google_link(identifier)

    if not event_id:
        identifier = _appointment_identifier(appointment)
        logger.info(
            "Google Calendar service returned empty event id for appointment %s, falling back to temporary link.",
            identifier,
        )
        return _temporary_google_link(identifier)

    logger.info(
        "Created Google Calendar event %s for appointment %s.",
        event_id,
        _appointment_identifier(appointment),
    )
    return f"{GOOGLE_MEET_BASE_URL}/{_format_google_slug(event_id)}"


def create_meeting_link(
    appointment: "Appointment",
    provider: str = "jitsi",
    calendar_service: Optional[CalendarService] = None,
):
    """
    Stub: تولید لینک جلسه. در production می‌تونیم Google Meet API یا Jitsi API صدا بزنیم.
    provider: 'jitsi' | 'google'
    """
    if provider == "jitsi":
        meeting_id = f"alovakil-{appointment.id}-{uuid.uuid4().hex[:8]}"
        base = "https://meet.jit.si"
        return f"{base}/{meeting_id}"

    if provider == "google":
        service = calendar_service or CalendarService(provider="google")
        return _calendar_backed_google_link(appointment, service)

    logger.warning("Unknown meeting provider '%s'. Falling back to temporary Google link.", provider)
    return _temporary_google_link(_appointment_identifier(appointment))


def filter_online_slots(queryset: QuerySet, params: Mapping[str, str]) -> QuerySet:
    """Apply common OnlineSlot filters based on query parameters.

    Supported filters:
        - date: ISO format YYYY-MM-DD (filters by start_time__date)
        - price_min / price_max: positive decimal values
    """

    errors = {}

    date_value = None
    date_str = params.get("date")
    if date_str:
        try:
            date_value = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            errors["date"] = "فرمت تاریخ معتبر نیست. از قالب YYYY-MM-DD استفاده کنید."

    min_value = None
    price_min = params.get("price_min")
    if price_min not in (None, ""):
        try:
            min_value = Decimal(price_min)
            if min_value < 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            errors["price_min"] = "حداقل قیمت باید یک عدد معتبر و غیرمنفی باشد."

    max_value = None
    price_max = params.get("price_max")
    if price_max not in (None, ""):
        try:
            max_value = Decimal(price_max)
            if max_value < 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            errors["price_max"] = "حداکثر قیمت باید یک عدد معتبر و غیرمنفی باشد."

    if min_value is not None and max_value is not None and min_value > max_value:
        errors["price_range"] = "حداقل قیمت نمی‌تواند بیشتر از حداکثر قیمت باشد."

    if errors:
        raise ValidationError(errors)

    if date_value:
        queryset = queryset.filter(start_time__date=date_value)
    if min_value is not None:
        queryset = queryset.filter(price__gte=min_value)
    if max_value is not None:
        queryset = queryset.filter(price__lte=max_value)

    return queryset
