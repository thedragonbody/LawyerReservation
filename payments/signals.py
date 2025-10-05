from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Payment
from appointments.models import Appointment
from notifications.models import Notification

@receiver(post_save, sender=Payment)
def confirm_appointment_after_payment(sender, instance, created, **kwargs):
    if instance.status == Payment.Status.COMPLETED:
        appointment = instance.appointment
        appointment.status = Appointment.Status.CONFIRMED
        appointment.save()

        Notification.objects.create(
            user=appointment.client.user,
            title="Payment Successful",
            message=f"Your appointment on {appointment.slot.start_time} has been confirmed."
        )
        Notification.objects.create(
            user=appointment.lawyer.user,
            title="New Appointment Confirmed",
            message=f"{appointment.client.user.get_full_name()} has successfully paid for the appointment on {appointment.slot.start_time}."
        )