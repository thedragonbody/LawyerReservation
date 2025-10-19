from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
import logging

from .models import Payment
from appointments.models import OnlineAppointment
from notifications.models import Notification
from chat.models import ChatRoom
from common.models import LawyerClientRelation

logger = logging.getLogger("payments")

@receiver(post_save, sender=Payment)
def handle_payment_complete(sender, instance, created, **kwargs):
    try:
        # فقط وقتی پرداخت موفق باشد
        if instance.status == Payment.Status.COMPLETED and instance.appointment:
            appointment = instance.appointment

            # اگر قبلاً تأیید شده، از اجرای دوباره جلوگیری کن
            if appointment.status == OnlineAppointment.Status.CONFIRMED:
                logger.info(f"Signal skipped: Appointment {appointment.id} already confirmed.")
                return

            lawyer_profile = appointment.lawyer
            client_profile = appointment.client

            with transaction.atomic():
                # رابطه و چت فقط در صورت نیاز ساخته شوند
                relation, created_relation = LawyerClientRelation.objects.get_or_create(
                    lawyer=lawyer_profile,
                    client=client_profile
                )
                if created_relation:
                    ChatRoom.objects.get_or_create(relation=relation)

                # تغییر وضعیت نوبت
                appointment.status = OnlineAppointment.Status.CONFIRMED
                appointment.save(update_fields=["status"])

                # نوتیف برای طرفین
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

                logger.info(f"✅ Appointment {appointment.id} confirmed by signal (Payment {instance.id}).")

        # اگر بازپرداخت انجام شد
        elif instance.status == Payment.Status.REFUNDED and instance.appointment:
            appointment = instance.appointment
            slot = appointment.slot

            with transaction.atomic():
                appointment.status = OnlineAppointment.Status.CANCELLED
                appointment.save(update_fields=["status"])
                slot.is_booked = False
                slot.save(update_fields=["is_booked"])

            logger.info(f"💸 Appointment {appointment.id} cancelled and slot released due to refund.")

    except Exception as e:
        logger.exception(f"Error in payment signal: {e}")