import logging
import uuid
from typing import TYPE_CHECKING, Optional

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
