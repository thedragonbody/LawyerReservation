from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import AIQuestion
from .serializers import AIQuestionSerializer
from .utils import ask_ai

class AskAIView(generics.CreateAPIView):
    queryset = AIQuestion.objects.all()
    serializer_class = AIQuestionSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        question = self.request.data.get("question", "")
        persona = self.request.data.get("persona", None)

        user_role = None
        if hasattr(self.request.user, "lawyer_profile"):
            user_role = "lawyer"
        elif hasattr(self.request.user, "client_profile"):
            user_role = "client"

        # 📜 تاریخچه آخرین 5 گفتگو برای context
        history = AIQuestion.objects.filter(user=self.request.user).order_by("-created_at")[:5]
        history_data = [{"question": h.question, "answer": h.answer} for h in reversed(history)]

        # ✨ پاسخ از AI
        answer = ask_ai(question, user_role=user_role, persona=persona, history=history_data)

        serializer.save(
            user=self.request.user,
            answer=answer,
            persona=persona if persona else "assistant",
            answered_at=timezone.now()
        )


class AIQuestionListView(generics.ListAPIView):
    queryset = AIQuestion.objects.all()
    serializer_class = AIQuestionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return AIQuestion.objects.filter(user=self.request.user).order_by("-created_at")