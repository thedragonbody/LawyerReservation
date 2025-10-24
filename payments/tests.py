from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from payments.models import Payment, Wallet
from users.models import User


class WalletIntegrationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone_number="09120000000", password="pass1234", is_active=True)
        self.client.force_authenticate(self.user)

    def test_wallet_top_up_increases_balance(self):
        url = reverse("payments:wallet-top-up")
        response = self.client.post(url, {"amount": "100000"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        wallet = Wallet.objects.get(user=self.user)
        self.assertEqual(wallet.balance, Decimal("100000"))
        self.assertEqual(wallet.reserved_balance, Decimal("0"))
        self.assertEqual(response.data["balance"], "100000.00")
        self.assertEqual(response.data["available_balance"], "100000.00")

    def test_reserve_capture_and_refund_flow(self):
        # Top-up first
        topup_url = reverse("payments:wallet-top-up")
        self.client.post(topup_url, {"amount": "150000"}, format="json")

        payment = Payment.objects.create(
            user=self.user,
            amount=Decimal("50000"),
            payment_method=Payment.Method.WALLET,
        )

        reserve_url = reverse("payments:wallet-reserve")
        response = self.client.post(reserve_url, {"payment_id": payment.id}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["reserved_amount"], "50000.00")

        wallet = Wallet.objects.get(user=self.user)
        self.assertEqual(wallet.balance, Decimal("150000"))
        self.assertEqual(wallet.reserved_balance, Decimal("50000"))
        self.assertEqual(wallet.available_balance, Decimal("100000"))

        payment.refresh_from_db()
        self.assertEqual(payment.wallet_reserved_amount, Decimal("50000"))

        # Capture funds when payment is completed
        payment.mark_completed()
        wallet.refresh_from_db()
        self.assertEqual(wallet.balance, Decimal("100000"))
        self.assertEqual(wallet.reserved_balance, Decimal("0"))

        # Refund payment back to wallet
        payment.mark_refunded()
        wallet.refresh_from_db()
        self.assertEqual(wallet.balance, Decimal("150000"))
        self.assertEqual(wallet.reserved_balance, Decimal("0"))
