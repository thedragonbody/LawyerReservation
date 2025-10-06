from elasticsearch_dsl import Document, Text, Date, connections
from elasticsearch_dsl.connections import connections
from .models import Case
from django.conf import settings

connections.create_connection(**settings.ELASTICSEARCH_DSL['default'])

class CaseDocument(Document):
    title = Text()
    description = Text()
    created_at = Date()

    class Index:
        name = "cases"

    def save(self, **kwargs):
        return super().save(**kwargs)