# payments/urls.py
from django.urls import path
from .views import (
    PaymentCreateView,
    PaymentVerifyView,
    PaymentCancelView,
    PaymentListView,
    CreateSubscriptionPaymentView,
    PaymentCallbackView,

)

urlpatterns = [
    path("create/<int:appointment_id>/", PaymentCreateView.as_view(), name="payment-create"),
    path("verify/", PaymentVerifyView.as_view(), name="payment-verify"),
    path("list/", PaymentListView.as_view(), name="payment-list"),
    path("cancel/<int:payment_id>/", PaymentCancelView.as_view(), name="payment-cancel"),
    # subscriptions
    path("subscription/create-payment/", CreateSubscriptionPaymentView.as_view(), name="create-subscription-payment"),
    path("subscription/payment-callback/", PaymentCallbackView.as_view(), name="subscription-payment-callback"),

]