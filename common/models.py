from django.db import models
from users.models import LawyerProfile, ClientProfile

class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class LawyerClientRelation(models.Model):
    lawyer = models.ForeignKey(LawyerProfile, on_delete=models.CASCADE, related_name="client_relations")
    client = models.ForeignKey(ClientProfile, on_delete=models.CASCADE, related_name="lawyer_relations")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('lawyer', 'client')

    def __str__(self):
        return f"{self.client.user.get_full_name()} ↔ {self.lawyer.user.get_full_name()}"