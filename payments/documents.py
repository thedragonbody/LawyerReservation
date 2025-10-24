from elasticsearch_dsl import Document, Text, Date, Float

from common.elasticsearch import create_default_connection
from .models import Payment

create_default_connection()

class PaymentDocument(Document):
    transaction_id = Text()
    amount = Float()
    created_at = Date()

    class Index:
        name = "payments"

    def save(self, **kwargs):
        return super().save(**kwargs)

