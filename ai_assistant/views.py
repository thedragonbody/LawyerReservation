from rest_framework import generics, status, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from django.utils import timezone
from .models import AIQuestion, AIErrorLog
from .serializers import AIQuestionSerializer
from .utils import ask_ai_with_retry, format_ai_output
from .limits import can_user_ask, increment_usage
import logging

# تنظیم logger برای AI assistant
logger = logging.getLogger("ai_assistant")


class AskAIView(generics.CreateAPIView):
    """
    ویو برای پرسش به AI
    - بررسی quota و سهمیه کاربر
    - ارسال آخرین ۱۰ پرسش مهم (importance) برای multi-turn
    - فراخوانی AI با retry هوشمند
    - ذخیره خطا در مدل AIErrorLog
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
            return Response(
                {"detail": "Quota exceeded", "type": reason},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

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