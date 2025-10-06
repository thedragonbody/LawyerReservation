from django.db import models
from django.conf import settings
from django.contrib.postgres.indexes import GinIndex
from .utils import preprocess_query

class SearchHistory(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="search_history"
    )
    query = models.CharField(max_length=255)
    normalized_query = models.CharField(max_length=255, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['normalized_query']),
            GinIndex(
                fields=['normalized_query'],
                opclasses=['gin_trgm_ops'],  # ← حتما اضافه شود
                name='sh_norm_query_gin',     # ← کوتاه و < 30 کاراکتر
            ),
        ]
        unique_together = ("user", "normalized_query")

    def save(self, *args, **kwargs):
        self.normalized_query = preprocess_query(self.query)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.email} → {self.query}"