from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from .models import AIUsage, AIPlan, Subscription

def get_active_plan_for_user(user):
    """
    بازگرداندن پلن فعال کاربر، اگر نداشته باشد پلن 'free' یا مقادیر پیش‌فرض settings
    """
    sub = Subscription.objects.filter(user=user, active=True).order_by("-ends_at").first()
    if sub and sub.plan:
        return sub.plan

    plan = AIPlan.objects.filter(name__iexact="free").first()
    return plan

def _get_limits_for_user(user):
    """
    بازگرداندن (daily_limit, monthly_limit) برای کاربر
    """
    plan = get_active_plan_for_user(user)
    if plan:
        return plan.daily_limit, plan.monthly_limit

    return getattr(settings, "AI_FREE_DAILY_LIMIT", 10), getattr(settings, "AI_FREE_MONTHLY_LIMIT", 300)

def can_user_ask(user, cost=1):
    """
    بررسی امکان ارسال سوال
    بازگرداندن tuple: (allowed: bool, reason: Optional[str])
    reason می‌تواند 'daily' یا 'monthly' یا None باشد
    """
    if user.is_staff:
        return True, None

    daily_limit, monthly_limit = _get_limits_for_user(user)
    today = timezone.now().date()

    # بررسی مصرف روزانه
    usage = AIUsage.objects.filter(user=user, date=today).first()
    daily_count = usage.daily_count if usage else 0

    # بررسی مصرف ماهانه
    month_total = AIUsage.objects.filter(
        user=user,
        date__year=today.year,
        date__month=today.month
    ).aggregate(total=Sum("daily_count"))["total"] or 0

    if daily_count + cost > daily_limit:
        return False, "daily"
    if month_total + cost > monthly_limit:
        return False, "monthly"

    return True, None

def increment_usage(user, cost=1):
    """
    افزایش مصرف روزانه و ماهانه به صورت safe
    """
    today = timezone.now().date()
    with transaction.atomic():
        usage, created = AIUsage.objects.select_for_update().get_or_create(
            user=user, 
            date=today, 
            defaults={"daily_count": 0, "monthly_count": 0}
        )
        usage.daily_count += cost
        usage.monthly_count += cost
        usage.save(update_fields=["daily_count", "monthly_count"])
        return usage