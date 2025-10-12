from django.db import models
from users.models import LawyerProfile, ClientProfile
from common.models import LawyerClientRelation

class LawyerReview(models.Model):
    relation = models.ForeignKey(LawyerClientRelation, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    reply = models.TextField(blank=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['relation'], name='unique_review_per_relation')
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.relation} - {self.rating}"