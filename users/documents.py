from elasticsearch_dsl import Document, Text, Date, connections
from elasticsearch_dsl.connections import connections
from .models import User, ClientProfile, LawyerProfile
from django.conf import settings

connections.create_connection(**settings.ELASTICSEARCH_DSL['default'])

# ===================== User =====================
class UserDocument(Document):
    first_name = Text()
    last_name = Text()
    email = Text()
    full_name = Text()

    class Index:
        name = "users"

# ===================== ClientProfile =====================
class ClientProfileDocument(Document):
    user_id = Text()
    national_id = Text()
    avatar = Text()

    class Index:
        name = "clients"

# ===================== LawyerProfile =====================
class LawyerProfileDocument(Document):
    user_id = Text()
    degree = Text()
    experience_years = Text()
    expertise = Text()
    status = Text()
    bio = Text()
    city = Text()
    specialization = Text()
    avatar = Text()

    class Index:
        name = "lawyers"