from rest_framework import generics, status, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from django.utils import timezone
from .models import AIQuestion, AIErrorLog, AIPlan, Subscription # 💡 Subscription و AIPlan هم اضافه شد
from .serializers import AIQuestionSerializer
from .utils import ask_ai_with_retry, format_ai_output
from .limits import can_user_ask, increment_usage
from payments.utils import create_payment_request
from rest_framework.views import APIView
from django.db import transaction
from django.shortcuts import get_object_or_404
from payments.models import Payment
from django.conf import settings

import logging # 💡 مشکل اینجا بود: این import اضافه شد

# تنظیم logger برای AI assistant
logger = logging.getLogger("ai_assistant")


class AskAIView(generics.CreateAPIView):
    """
    ویو برای پرسش به AI
    ... (ادامه کلاس بدون تغییر) ...
    """
    queryset = AIQuestion.objects.all()
    serializer_class = AIQuestionSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        question = self.request.data.get("question", "")
        persona = self.request.data.get("persona", "assistant")
        importance = int(self.request.data.get("importance", 1))

        # تعیین نقش کاربر
        user_role = None
        if hasattr(self.request.user, "lawyer_profile"):
            user_role = "lawyer"
        elif hasattr(self.request.user, "client_profile"):
            user_role = "client"

        # 🔹 بررسی quota
        allowed, reason = can_user_ask(self.request.user, cost=1)
        if not allowed:
            # 💡 بهبود: شما نمی‌توانید از داخل perform_create یک Response برگردانید
            # این متد برای برگرداندن Response طراحی نشده و باعث خطا می‌شود.
            # باید این منطق را به متد create منتقل کنیم.
            raise serializers.ValidationError({"detail": "Quota exceeded", "type": reason})

        # 🔹 آماده‌سازی history برای multi-turn
        history_qs = AIQuestion.objects.filter(user=self.request.user).order_by("-created_at")[:10]
        history_data = [
            {
                "question": h.question,
                "answer": h.answer,
                "importance": getattr(h, "importance", 1),
                "created_at": h.created_at
            }
            for h in reversed(history_qs)
        ]

        try:
            # 🔹 فراخوانی AI با retry هوشمند
            answer = ask_ai_with_retry(
                self.request.user,
                question,
                user_role=user_role,
                persona=persona,
                history=history_data
            )

            # 🔹 فرمت پاسخ در صورت JSON بودن
            answer = format_ai_output(answer)

            # 🔹 افزایش مصرف quota بعد از موفقیت
            increment_usage(self.request.user, cost=1)

            serializer.save(
                user=self.request.user,
                answer=answer,
                persona=persona,
                importance=importance,
                answered_at=timezone.now()
            )

        except Exception as e:
            # 🔹 ثبت خطا در مدل AIErrorLog
            AIErrorLog.objects.create(
                user=self.request.user,
                question=question,
                error=str(e)
            )
            logger.error(f"AI ask failed for user {self.request.user}: {e}")
            raise serializers.ValidationError({"detail": f"AI error: {e}"})

    # 💡 بهبود ۲: انتقال منطق چک کردن Quota به متد create
    def create(self, request, *args, **kwargs):
        allowed, reason = can_user_ask(request.user, cost=1)
        if not allowed:
            return Response(
                {"detail": "Quota exceeded", "type": reason},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        # اگر مجاز بود، ادامه فرایند create (که perform_create را صدا می‌زند)
        try:
            return super().create(request, *args, **kwargs)
        except serializers.ValidationError as e:
            # خطاهایی که از perform_create می‌آیند (مثل خطای AI)
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)


class AIQuestionPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class AIQuestionListView(generics.ListAPIView):
    """
    لیست تمام سوالات کاربر با pagination
    """
    serializer_class = AIQuestionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = AIQuestionPagination

    def get_queryset(self):
        return AIQuestion.objects.filter(user=self.request.user).order_by("-created_at")
    
class CreateSubscriptionPaymentView(APIView):
    """
    ویو برای ایجاد پرداخت جهت خرید یا تمدید اشتراک AI.
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        plan_id = request.data.get("plan_id")
        if not plan_id:
            return Response({"detail": "plan_id الزامی است."}, status=status.HTTP_400_BAD_REQUEST)

        plan = get_object_or_404(AIPlan, id=plan_id)
        user = request.user

        # ۱. ایجاد اشتراک (غیرفعال تا زمان پرداخت)
        subscription = Subscription.objects.create(
            user=user,
            plan=plan,
            active=False # در انتظار پرداخت
        )

        # ۲. ایجاد رکورد پرداخت در انتظار
        multiplier = getattr(settings, "PAYMENT_AMOUNT_MULTIPLIER", 1)
        amount_to_pay = plan.price_cents * multiplier 

        payment = Payment.objects.create(
            user=user,
            amount=amount_to_pay,
            subscription=subscription, 
            status=Payment.Status.PENDING,
            payment_method="idpay" 
        )

        # ۳. ایجاد درخواست در درگاه (IDPay)
        try:
            provider_data = create_payment_request(
                order_id=str(payment.id),
                amount=int(amount_to_pay),
                callback=settings.IDPAY_CALLBACK_URL,
                phone=user.phone_number,
                desc=f"خرید اشتراک {plan.name}"
            )
            
            payment.transaction_id = provider_data.get('id')
            payment.save(update_fields=['transaction_id'])

            return Response({
                "payment_id": payment.id,
                "payment_link": provider_data.get('link'),
                "transaction_id": provider_data.get('id')
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Subscription payment creation failed for user {user.id}: {e}")
            transaction.set_rollback(True)
            return Response({"detail": f"خطا در ایجاد پرداخت: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)