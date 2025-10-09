from rest_framework import generics, status, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from django.utils import timezone
from .models import AIQuestion
from .serializers import AIQuestionSerializer
from .utils import ask_ai_with_retry, format_ai_output
from .limits import can_user_ask, increment_usage
import logging

logger = logging.getLogger("ai_assistant")

class AskAIView(generics.CreateAPIView):
    queryset = AIQuestion.objects.all()
    serializer_class = AIQuestionSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        question = self.request.data.get("question", "")
        persona = self.request.data.get("persona", "assistant")
        importance = int(self.request.data.get("importance", 1))

        user_role = None
        if hasattr(self.request.user, "lawyer_profile"):
            user_role = "lawyer"
        elif hasattr(self.request.user, "client_profile"):
            user_role = "client"

        # چک سهمیه
        allowed, reason = can_user_ask(self.request.user, cost=1)
        if not allowed:
            # برگردوندن خطای واضح
            raise serializers.ValidationError({"detail": "Quota exceeded", "type": reason})

        # history برای multi-turn (آخرین 10)
        history_qs = AIQuestion.objects.filter(user=self.request.user).order_by("-created_at")[:10]
        history_data = [{"question": h.question, "answer": h.answer, "importance": getattr(h, "importance", 1), "created_at": h.created_at} for h in reversed(history_qs)]

        # فراخوانی AI با retry
        answer = ask_ai_with_retry(self.request.user, question, user_role=user_role, persona=persona, history=history_data)

        # تبدیل فرمت در صورت نیاز
        answer = format_ai_output(answer)

        # بعد از اینکه پاسخ موفق دریافت شد (یا خطای نهایی)، مصرف را افزایش می‌دهیم
        increment_usage(self.request.user, cost=1)

        serializer.save(
            user=self.request.user,
            answer=answer,
            persona=persona,
            importance=importance,
            answered_at=timezone.now()
        )


class AIQuestionPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class AIQuestionListView(generics.ListAPIView):
    serializer_class = AIQuestionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = AIQuestionPagination

    def get_queryset(self):
        return AIQuestion.objects.filter(user=self.request.user).order_by("-created_at")