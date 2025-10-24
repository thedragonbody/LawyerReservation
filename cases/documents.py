from elasticsearch_dsl import Document, Text, Date

from common.elasticsearch import create_default_connection
from .models import Case

create_default_connection()

class CaseDocument(Document):
    title = Text()
    description = Text()
    created_at = Date()

    class Index:
        name = "cases"

    def save(self, **kwargs):
        return super().save(**kwargs)

