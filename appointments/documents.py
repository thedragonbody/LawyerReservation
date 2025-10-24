from elasticsearch_dsl import Document, Text, Date

from common.elasticsearch import create_default_connection
from .models import OnlineAppointment

create_default_connection()

class OnlineAppointmentDocument(Document):
    lawyer_name = Text()
    created_at = Date()

    class Index:
        name = "appointments"

    def save(self, **kwargs):
        self.lawyer_name = f"{self.lawyer.user.first_name} {self.lawyer.user.last_name}"
        return super().save(**kwargs)

