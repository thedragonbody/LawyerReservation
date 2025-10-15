from elasticsearch_dsl import Document, Text, Integer, connections
from django.conf import settings
from .models import User, ClientProfile, LawyerProfile

# اتصال به Elasticsearch
connections.create_connection(**settings.ELASTICSEARCH_DSL['default'])

# ===================== User =====================
class UserDocument(Document):
    first_name = Text()
    last_name = Text()
    phone_number = Text()  # ایمیل حذف شد
    full_name = Text()

    class Index:
        name = "users"

    def save(self, **kwargs):
        self.full_name = f"{self.first_name or ''} {self.last_name or ''}"
        return super().save(**kwargs)

# ===================== ClientProfile =====================
class ClientProfileDocument(Document):
    user_id = Text()
    phone_number = Text()
    national_id = Text()
    avatar = Text()

    class Index:
        name = "clients"

# ===================== LawyerProfile =====================
class LawyerProfileDocument(Document):
    user_id = Text()
    phone_number = Text()
    degree = Text()
    experience_years = Integer()
    expertise = Text()
    status = Text()
    bio = Text()
    city = Text()
    specialization = Text()
    avatar = Text()

    class Index:
        name = "lawyers"