# payments/urls.py
from django.urls import path
from .views import PaymentCreateView, PaymentVerifyView

urlpatterns = [
    path("create/<int:appointment_id>/", PaymentCreateView.as_view(), name="payment-create"),
    path("verify/", PaymentVerifyView.as_view(), name="payment-verify"),
]