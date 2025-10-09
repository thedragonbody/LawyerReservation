from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from .models import AIQuestion
from .serializers import AIQuestionSerializer
from .utils import ask_ai, format_ai_output
import logging

# تنظیم logger
logger = logging.getLogger("ai_assistant")
logger.setLevel(logging.INFO)

class AskAIView(generics.CreateAPIView):
    queryset = AIQuestion.objects.all()
    serializer_class = AIQuestionSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        question = self.request.data.get("question", "")
        persona = self.request.data.get("persona", "assistant")  # پیش‌فرض assistant

        user_role = None
        if hasattr(self.request.user, "lawyer_profile"):
            user_role = "lawyer"
        elif hasattr(self.request.user, "client_profile"):
            user_role = "client"

        # 📜 Memory پیشرفته: آخرین 10 گفتگو
        history = AIQuestion.objects.filter(user=self.request.user).order_by("-created_at")[:10]
        history_data = [{"question": h.question, "answer": h.answer} for h in reversed(history)]

        # ✨ پاسخ AI با Multi-turn و Persona
        try:
            answer = ask_ai(question, user_role=user_role, persona=persona, history=history_data)
            answer = format_ai_output(answer)
        except Exception as e:
            logger.error(f"Error in AskAIView: {e}")
            answer = f"AI service error: {e}"

        serializer.save(
            user=self.request.user,
            answer=answer,
            persona=persona,
            answered_at=timezone.now()
        )


class AIQuestionPagination(PageNumberPagination):
    page_size = 20  # تعداد سوال در هر صفحه
    page_size_query_param = "page_size"
    max_page_size = 100


class AIQuestionListView(generics.ListAPIView):
    serializer_class = AIQuestionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = AIQuestionPagination

    def get_queryset(self):
        return AIQuestion.objects.filter(user=self.request.user).order_by("-created_at")