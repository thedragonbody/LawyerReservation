from elasticsearch_dsl import Document, Text, Keyword, Integer, Date, connections
from django.conf import settings
from .models import User, ClientProfile, LawyerProfile

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


# ================== ClientProfile Document ==================
class ClientProfileDocument(Document):
    user_id = Keyword()
    phone_number = Keyword()
    national_id = Keyword()
    avatar = Keyword()
    created_at = Date()
    updated_at = Date()

    class Index:
        name = 'clients'
        settings = {'number_of_shards': 1, 'number_of_replicas': 0}

    def save(self, **kwargs):
        self.phone_number = self.phone_number or ''
        return super().save(**kwargs)


# ================== LawyerProfile Document ==================
class LawyerProfileDocument(Document):
    user_id = Keyword()
    phone_number = Keyword()
    degree = Text(fields={'raw': Keyword()})
    experience_years = Integer()
    expertise = Text(fields={'raw': Keyword()})
    status = Keyword()
    bio = Text()
    city = Text(fields={'raw': Keyword()})
    specialization = Text(fields={'raw': Keyword()})
    avatar = Keyword()
    created_at = Date()
    updated_at = Date()

    class Index:
        name = 'lawyers'
        settings = {'number_of_shards': 1, 'number_of_replicas': 0}

    def save(self, **kwargs):
        self.phone_number = self.phone_number or ''
        return super().save(**kwargs)