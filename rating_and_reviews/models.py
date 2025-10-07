from django.db import models
from common.models import LawyerClientRelation

class LawyerReview(models.Model):
    relation = models.ForeignKey(LawyerClientRelation, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField()  # 1 تا 5
    comment = models.TextField(blank=True, null=True)
    is_approved = models.BooleanField(default=True)  # برای مدیریت ادمین
    reply = models.TextField(blank=True, null=True)  # پاسخ وکیل
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("relation", "created_at")  # هر رابطه و نظر در زمان متفاوت

    def __str__(self):
        return f"{self.relation.lawyer.user.get_full_name()} - {self.rating} ⭐"