from elasticsearch_dsl import Document, Text, Integer, connections
from django.conf import settings
from .models import User, ClientProfile, LawyerProfile


# ===================== User =====================
class UserDocument:
    pass

class ClientProfileDocument:
    pass

class LawyerProfileDocument:
    pass