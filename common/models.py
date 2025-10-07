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

    # فیلدهای جدید
    last_interaction = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    tags = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('lawyer', 'client')

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.client.user.get_full_name()} ↔ {self.lawyer.user.get_full_name()} ({status})"

    def get_relation_names(self):
        return {
            "lawyer": self.lawyer.user.get_full_name(),
            "client": self.client.user.get_full_name()
        }

    def summary(self):
        return {
            "lawyer": self.lawyer.user.get_full_name(),
            "client": self.client.user.get_full_name(),
            "last_interaction": self.last_interaction,
            "is_active": self.is_active,
            "tags": self.tags,
            "notes": self.notes
        }

    def touch(self):
        from django.utils import timezone
        self.last_interaction = timezone.now()
        self.save(update_fields=["last_interaction"])