# payments/urls.py
from django.urls import path
from .views import PaymentCreateView, PaymentVerifyView, PaymentCancelView, PaymentListView

urlpatterns = [
    path("create/<int:appointment_id>/", PaymentCreateView.as_view(), name="payment-create"),
    path("verify/", PaymentVerifyView.as_view(), name="payment-verify"),
    path("list/", PaymentListView.as_view(), name="payment-list"),
    path("cancel/<int:payment_id>/", PaymentCancelView.as_view(), name="payment-cancel"),
]