from django.urls import path

from payments.views import (
    CreatePaymentView,
    IDPayCallbackView,
    VerifyPaymentView,
    WalletDetailView,
    WalletReserveView,
    WalletTopUpView,
)

app_name = "payments"

urlpatterns = [
    path("create/", CreatePaymentView.as_view(), name="payment-create"),
    path("verify/", VerifyPaymentView.as_view(), name="payment-verify"),
    path("idpay/callback/", IDPayCallbackView.as_view(), name="idpay-callback"),
    path("wallet/", WalletDetailView.as_view(), name="wallet-detail"),
    path("wallet/top-up/", WalletTopUpView.as_view(), name="wallet-top-up"),
    path("wallet/reserve/", WalletReserveView.as_view(), name="wallet-reserve"),
]