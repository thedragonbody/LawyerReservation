from django.urls import path
from .views import SendMessageView, GetMessagesView

urlpatterns = [
    path("send/", SendMessageView.as_view(), name="send_message"),
    path("<int:lawyer_id>/<int:client_id>/", GetMessagesView.as_view(), name="get_messages"),
]