from elasticsearch_dsl import Document, Text, Keyword, Integer, Date, connections
from django.conf import settings
from .models import User

# ================== اتصال به ES ==================
connections.create_connection(**settings.ELASTICSEARCH_DSL['default'])

# ================== User Document ==================
class UserDocument(Document):
    phone_number = Keyword()
    first_name = Text(fields={'raw': Keyword()})
    last_name = Text(fields={'raw': Keyword()})
    full_name = Text(fields={'raw': Keyword()})
    is_active = Keyword()
    date_joined = Date()

    class Index:
        name = 'users'
        settings = {'number_of_shards': 1, 'number_of_replicas': 0}

    def save(self, **kwargs):
        self.full_name = f"{self.first_name or ''} {self.last_name or ''}".strip()
        return super().save(**kwargs)

