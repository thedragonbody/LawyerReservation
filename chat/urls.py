from django.urls import path
from .views import SendMessageView, GetMessagesView, TypingIndicatorView

urlpatterns = [
    path("send/", SendMessageView.as_view(), name="send_message"),
    path("room/<int:room_id>/messages/", GetMessagesView.as_view(), name="get_messages"),
    path("room/<int:room_id>/typing/", TypingIndicatorView.as_view(), name="typing_indicator"),
]