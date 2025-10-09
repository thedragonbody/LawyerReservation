from django.db import models
from django.conf import settings

class AIQuestion(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ai_questions"
    )
    question = models.TextField()
    answer = models.TextField(blank=True, null=True)
    persona = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="نوع شخصیت یا نقش AI (مثلاً lawyer, educator, career)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    answered_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        short_q = (self.question[:30] + "...") if len(self.question) > 30 else self.question
        return f"{self.user.email} - {short_q}"