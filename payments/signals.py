from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Payment
from appointments.models import Appointment
from notifications.models import Notification
from chat.models import ChatRoom
from common.models import LawyerClientRelation

# ---------------------- Signal ترکیبی ----------------------
@receiver(post_save, sender=Payment)
def handle_payment_complete(sender, instance, created, **kwargs):
    if instance.status == Payment.Status.COMPLETED and instance.appointment:
        appointment = instance.appointment
        lawyer_profile = appointment.lawyer
        client_profile = appointment.client

        # ------------------ ایجاد رابطه و چت ------------------
        relation, _ = LawyerClientRelation.objects.get_or_create(
            lawyer=lawyer_profile,
            client=client_profile
        )
        ChatRoom.objects.get_or_create(relation=relation)

        # ------------------ تایید Appointment ------------------
        appointment.status = Appointment.Status.CONFIRMED
        appointment.save()

        # ------------------ نوتیف داخلی ------------------
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