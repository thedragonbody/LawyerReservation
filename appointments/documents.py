from elasticsearch_dsl import Document, Text, Date, connections
from .models import Appointment
from django.conf import settings

connections.create_connection(**settings.ELASTICSEARCH_DSL['default'])

class AppointmentDocument(Document):
    lawyer_name = Text()
    created_at = Date()

    class Index:
        name = "appointments"

    def save(self, **kwargs):
        self.lawyer_name = f"{self.lawyer.user.first_name} {self.lawyer.user.last_name}"
        return super().save(**kwargs)