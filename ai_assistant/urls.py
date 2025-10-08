from django.urls import path
from .views import AskAIView, AIQuestionListView

urlpatterns = [
    path("ask/", AskAIView.as_view(), name="ask-ai"),
    path("history/", AIQuestionListView.as_view(), name="ai-history"),
]
