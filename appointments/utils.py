import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Appointment


def create_meeting_link(appointment: "Appointment", provider="jitsi"):
    """
    Stub: تولید لینک جلسه. در production می‌تونیم Google Meet API یا Jitsi API صدا بزنیم.
    provider: 'jitsi' | 'google'
    """
    if provider == "jitsi":
        # simple unique meeting id
        meeting_id = f"alovakil-{appointment.id}-{uuid.uuid4().hex[:8]}"
        base = "https://meet.jit.si"
        return f"{base}/{meeting_id}"
    else:
        # TODO: google meet integration
        return None