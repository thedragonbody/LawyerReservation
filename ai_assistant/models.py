from django.db import models
from django.conf import settings
from django.utils import timezone

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
    importance = models.PositiveIntegerField(default=1, help_text="وزن یا اهمیت سوال")
    created_at = models.DateTimeField(auto_now_add=True)
    answered_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        short_q = (self.question[:30] + "...") if len(self.question) > 30 else self.question
        return f"{self.user.email} - {short_q}"


class AIErrorLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    question = models.TextField(blank=True, null=True)
    error = models.TextField()
    traceback = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"AIError @ {self.created_at} | user: {self.user}"


class AIUsage(models.Model):
    # یک رکورد برای هر روز (user+date). جمع ماهیانه از رکوردهای روزانه محاسبه می‌شود.
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True, db_index=True)
    daily_count = models.PositiveIntegerField(default=0)
    # monthly_count برای سرعت دسترسی (اختیاری) — ما از جمع روزها هم استفاده می‌کنیم
    monthly_count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("user", "date")
        ordering = ["-date"]

    def __str__(self):
        return f"{self.user.email} - {self.date} - daily:{self.daily_count} monthly:{self.monthly_count}"
    
    def increment_usage(self):
        """افزایش شمارش روزانه و ماهانه"""
        self.daily_count += 1
        self.monthly_count += 1
        self.save()

    @staticmethod
    def get_or_create_today(user):
        today = timezone.now().date()
        usage, created = AIUsage.objects.get_or_create(
            user=user,
            date=today,
            defaults={"daily_count": 0, "monthly_count": AIUsage.get_monthly_total(user)}
        )
        return usage

    @staticmethod
    def get_monthly_total(user):
        month = timezone.now().month
        year = timezone.now().year
        return AIUsage.objects.filter(
            user=user, date__month=month, date__year=year
        ).aggregate(models.Sum("daily_count"))["daily_count__sum"] or 0

# ------------ Plan & Subscription (اضافه‌شده برای محدودیت/اشتراک) -------------
class AIPlan(models.Model):
    """
    طرح‌ها (Free / Pro / ...) — می‌تونی از اینجا پنل مدیریت بسازی.
    """
    name = models.CharField(max_length=50, unique=True)
    daily_limit = models.PositiveIntegerField(default=10)
    monthly_limit = models.PositiveIntegerField(default=300)
    price_cents = models.PositiveIntegerField(default=0)  # قیمت در واحد کوچکتر (اختیاری)
    description = models.TextField(blank=True)
    duration_days = models.PositiveBigIntegerField(default=30, help_text="مدت اعتبار اشتراک(روز)")
    def __str__(self):
        return f"{self.name} (daily:{self.daily_limit} monthly:{self.monthly_limit})"


class Subscription(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ai_subscriptions")
    plan = models.ForeignKey(AIPlan, on_delete=models.PROTECT)
    active = models.BooleanField(default=True)
    starts_at = models.DateTimeField(auto_now_add=True)
    ends_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.email} -> {self.plan.name} (active={self.active})"
    
