from django.utils.timezone import now, timedelta
from appointments.models import Appointment
from notifications.models import Notification
from common.utils import send_sms

def send_upcoming_appointment_notifications():
    upcoming_time = now() + timedelta(hours=24)
    appointments = Appointment.objects.filter(
        status='CONFIRMED',
        slot__start_time__lte=upcoming_time,
        slot__start_time__gte=now()
    )

    for appt in appointments:
        # بررسی نوتیفیکیشن موجود
        if not Notification.objects.filter(appointment=appt, title="جلسه آینده").exists():
            Notification.objects.create(
                user=appt.client.user,
                appointment=appt,
                title="جلسه آینده",
                message=f"جلسه شما با {appt.lawyer.user.get_full_name()} در {appt.slot.start_time} نزدیک است."
            )
            # ارسال پیامک
            send_sms(appt.client.user.phone_number,
                     f"جلسه شما با {appt.lawyer.user.get_full_name()} در {appt.slot.start_time} نزدیک است.")