from elasticsearch_dsl import Document, Text, Date, Float, connections
from elasticsearch_dsl.connections import connections
from .models import Payment
from django.conf import settings

connections.create_connection(**settings.ELASTICSEARCH_DSL['default'])

class PaymentDocument(Document):
    transaction_id = Text()
    amount = Float()
    created_at = Date()

    class Index:
        name = "payments"

    def save(self, **kwargs):
        return super().save(**kwargs)