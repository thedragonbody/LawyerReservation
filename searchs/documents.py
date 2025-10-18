from elasticsearch_dsl import Document, Text, Keyword, Date, Float
from users.models import User
from lawyer_profile.models import LawyerProfile
from client_profile.models import ClientProfile
from appointments.models import Appointment
from payments.models import Payment
from cases.models import Case
from elasticsearch_dsl import analyzer

english_analyzer = analyzer("english")
persian_analyzer = analyzer("persian")

# ---------------------- User ----------------------
class UserDocument(Document):
    email = Keyword()
    first_name = Text()
    last_name = Text()
    full_name = Text()

    class Index:
        name = 'users'

    @classmethod
    def from_instance(cls, instance: User):
        return cls(
            meta={'id': instance.id},
            email=instance.email,
            first_name=instance.first_name,
            last_name=instance.last_name,
            full_name=f"{instance.first_name} {instance.last_name}"
        )

# ---------------------- LawyerProfile ----------------------
class LawyerProfileDocument(Document):
    full_name = Text(analyzer=persian_analyzer)
    expertise = Text()
    degree = Text()

    class Index:
        name = 'lawyers'

    @classmethod
    def from_instance(cls, instance: LawyerProfile):
        return cls(
            meta={'id': instance.id},
            full_name=f"{instance.user.first_name} {instance.user.last_name}",
            expertise=instance.expertise,
            degree=instance.degree
        )

# ---------------------- ClientProfile ----------------------
class ClientProfileDocument(Document):
    full_name = Text(analyzer=persian_analyzer)
    national_id = Keyword()

    class Index:
        name = 'clients'

    @classmethod
    def from_instance(cls, instance: ClientProfile):
        return cls(
            meta={'id': instance.id},
            full_name=f"{instance.user.first_name} {instance.user.last_name}",
            national_id=instance.national_id
        )

# ---------------------- Appointment ----------------------
class AppointmentDocument(Document):
    lawyer_name = Text(analyzer=persian_analyzer)
    client_name = Text(analyzer=persian_analyzer)
    status = Keyword()
    date = Date()
    session_type = Keyword()
    price = Float()

    class Index:
        name = 'appointments'

    @classmethod
    def from_instance(cls, instance: Appointment):
        return cls(
            meta={'id': instance.id},
            lawyer_name=f"{instance.lawyer.user.first_name} {instance.lawyer.user.last_name}",
            client_name=f"{instance.client.user.first_name} {instance.client.user.last_name}",
            date=instance.slot.start_time,
            status=instance.status,
            session_type=instance.session_type,
            price=float(instance.slot.price)
        )

# ---------------------- Payment ----------------------
class PaymentDocument(Document):
    transaction_id = Keyword()
    status = Keyword()
    amount = Float()
    date = Date()

    class Index:
        name = 'payments'

    @classmethod
    def from_instance(cls, instance: Payment):
        return cls(
            meta={'id': instance.id},
            transaction_id=instance.transaction_id,
            status=instance.status,
            amount=float(instance.amount),
            date=instance.created_at
        )

# ---------------------- Case ----------------------
class CaseDocument(Document):
    case_number = Keyword()
    title = Text(analyzer=persian_analyzer)
    status = Keyword()
    created_at = Date()

    class Index:
        name = 'cases'

    @classmethod
    def from_instance(cls, instance: Case):
        return cls(
            meta={'id': instance.id},
            case_number=instance.case_number,
            title=instance.title,
            status=instance.status,
            created_at=instance.created_at
        )