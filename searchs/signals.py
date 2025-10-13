from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from users.models import User, LawyerProfile, ClientProfile
from appointments.models import Appointment
from payments.models import Payment
from cases.models import Case

from searchs.documents import (
    UserDocument,
    LawyerProfileDocument,
    ClientProfileDocument,
    AppointmentDocument,
    PaymentDocument,
    CaseDocument
)

# ---------------------- Helper function ----------------------
def index_instance(doc_class, instance):
    try:
        doc = doc_class.from_instance(instance)
        doc.save()
    except Exception as e:
        print(f"[Warning] Failed to update Elasticsearch for {doc_class.__name__} {instance.id}: {e}")

def delete_instance(doc_class, instance):
    try:
        doc = doc_class(meta={'id': instance.id})
        doc.delete()
    except Exception as e:
        print(f"[Warning] Failed to delete Elasticsearch for {doc_class.__name__} {instance.id}: {e}")


# ---------------------- User ----------------------
@receiver(post_save, sender=User)
def index_user(sender, instance, **kwargs):
    index_instance(UserDocument, instance)

@receiver(post_delete, sender=User)
def delete_user(sender, instance, **kwargs):
    delete_instance(UserDocument, instance)


# ---------------------- LawyerProfile ----------------------
@receiver(post_save, sender=LawyerProfile)
def index_lawyer(sender, instance, **kwargs):
    index_instance(LawyerProfileDocument, instance)

@receiver(post_delete, sender=LawyerProfile)
def delete_lawyer(sender, instance, **kwargs):
    delete_instance(LawyerProfileDocument, instance)


# ---------------------- ClientProfile ----------------------
@receiver(post_save, sender=ClientProfile)
def index_client(sender, instance, **kwargs):
    index_instance(ClientProfileDocument, instance)

@receiver(post_delete, sender=ClientProfile)
def delete_client(sender, instance, **kwargs):
    delete_instance(ClientProfileDocument, instance)


# ---------------------- Appointment ----------------------
@receiver(post_save, sender=Appointment)
def index_appointment(sender, instance, **kwargs):
    index_instance(AppointmentDocument, instance)

@receiver(post_delete, sender=Appointment)
def delete_appointment(sender, instance, **kwargs):
    delete_instance(AppointmentDocument, instance)


# ---------------------- Payment ----------------------
@receiver(post_save, sender=Payment)
def index_payment(sender, instance, **kwargs):
    index_instance(PaymentDocument, instance)

@receiver(post_delete, sender=Payment)
def delete_payment(sender, instance, **kwargs):
    delete_instance(PaymentDocument, instance)


# ---------------------- Case ----------------------
@receiver(post_save, sender=Case)
def index_case(sender, instance, **kwargs):
    index_instance(CaseDocument, instance)

@receiver(post_delete, sender=Case)
def delete_case(sender, instance, **kwargs):
    delete_instance(CaseDocument, instance)