from django.db import models
from django.conf import settings
from common.validators import validate_case_end_date
from lawyer_profile.models import LawyerProfile
from common.models import BaseModel
from common.choices import CaseResult
from client_profile.models import ClientProfile


class Case(models.Model):
    lawyer = models.ForeignKey(LawyerProfile, on_delete=models.CASCADE, related_name="cases")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to="cases/files/", blank=True, null=True)
    result = models.CharField(max_length=20, choices=CaseResult.choices, default=CaseResult.PENDING)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_public = models.BooleanField(default=True)  # نمایش برای همه یا نه
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        validate_case_end_date(self.result, self.end_date)

    def __str__(self):
        return self.title


class CaseComment(models.Model):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="replies"
    )

    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.user.email}: {self.content[:20]}"

    def can_reply(self, current_user):
        """
        فقط:
        - اگه کاربر خودش نویسنده کامنت باشه (صاحب کامنت)
        - یا یک کاربر دیگه (مثلاً وکیل/کلاینت) باشه
        اجازه ریپلای می‌دیم
        """
        return current_user.is_authenticated