from decimal import Decimal
from typing import Union

import logging
import requests
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction

logger = logging.getLogger("payments")

BASE = getattr(settings, "IDPAY_API_URL", "https://api.idpay.ir/v1.1")
API_KEY = getattr(settings, "IDPAY_API_KEY", None)
IS_SANDBOX = getattr(settings, "IDPAY_SANDBOX", True)
HEADERS = {
    "X-API-KEY": API_KEY,
    "X-SANDBOX": "1" if IS_SANDBOX else "0",
    "Content-Type": "application/json"
}

def create_payment_request(order_id: str, amount: int, callback: str, phone=None, mail=None, desc=None, timeout=10):
    """
    Create payment on IDPay. returns dict with provider response.
    amount should be integer according to provider (check docs — ممکن است ریال/تومان نیاز باشد).
    """
    payload = {
        "order_id": str(order_id),
        "amount": amount,
        "name": None,
        "phone": phone or "",
        "mail": mail or "",
        "desc": desc or f"Order {order_id}",
        "callback": callback
    }
    try:
        resp = requests.post(f"{BASE}/payment", json=payload, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.exception("create_payment_request failed: %s", e)
        raise

def verify_payment_request(payment_id: str, timeout=10):
    """
    Verify payment by ID (server-to-server). Returns provider json.
    """
    try:
        payload = {"id": payment_id}
        resp = requests.post(f"{BASE}/payment/verify", json=payload, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.exception("verify_payment_request failed: %s", e)
        raise


# -----------------------------
# Wallet helpers
# -----------------------------
from payments.models import Payment, Wallet, WalletTransaction


NumberLike = Union[Decimal, float, int, str]


def _ensure_decimal(value: NumberLike) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _get_wallet_for_update(user) -> Wallet:
    wallet, _ = Wallet.objects.select_for_update().get_or_create(user=user)
    return wallet


def increase_wallet_balance(*, user, amount, description: str = "") -> Wallet:
    amount = _ensure_decimal(amount)
    if amount <= 0:
        raise ValidationError("Amount must be greater than zero.")

    with transaction.atomic():
        wallet = _get_wallet_for_update(user)
        wallet.balance += amount
        wallet.save(update_fields=["balance", "updated_at"])
        WalletTransaction.objects.create(
            wallet=wallet,
            payment=None,
            type=WalletTransaction.Type.DEPOSIT,
            amount=amount,
            description=description or "Manual top-up",
        )
    return wallet


def reserve_wallet_funds(*, payment: Payment, amount=None) -> Wallet:
    amount = _ensure_decimal(amount if amount is not None else payment.amount)
    if amount <= 0:
        raise ValidationError("Amount must be greater than zero.")
    if payment.payment_method != Payment.Method.WALLET:
        raise ValidationError("Payment method is not wallet.")
    if payment.wallet_reserved_amount > 0:
        raise ValidationError("Wallet already reserved for this payment.")

    with transaction.atomic():
        wallet = _get_wallet_for_update(payment.user)
        if wallet.available_balance < amount:
            raise ValidationError("Insufficient wallet balance.")

        wallet.reserved_balance += amount
        wallet.save(update_fields=["reserved_balance", "updated_at"])

        WalletTransaction.objects.create(
            wallet=wallet,
            payment=payment,
            type=WalletTransaction.Type.RESERVE,
            amount=amount,
            description=f"Reserved for payment {payment.id}",
        )

        payment.wallet_reserved_amount = amount
        payment.save(update_fields=["wallet_reserved_amount", "updated_at"])

    return wallet


def release_wallet_reservation(payment: Payment) -> None:
    if payment.wallet_reserved_amount <= 0:
        return
    if payment.payment_method != Payment.Method.WALLET:
        return

    with transaction.atomic():
        wallet = _get_wallet_for_update(payment.user)
        amount = payment.wallet_reserved_amount
        wallet.reserved_balance = max(Decimal("0.00"), wallet.reserved_balance - amount)
        wallet.save(update_fields=["reserved_balance", "updated_at"])

        WalletTransaction.objects.create(
            wallet=wallet,
            payment=payment,
            type=WalletTransaction.Type.RELEASE,
            amount=amount,
            description=f"Release reservation for payment {payment.id}",
        )

        payment.wallet_reserved_amount = Decimal("0.00")
        payment.save(update_fields=["wallet_reserved_amount", "updated_at"])


def capture_wallet_payment(payment: Payment) -> None:
    if payment.payment_method != Payment.Method.WALLET:
        return

    amount = payment.wallet_reserved_amount or payment.amount
    amount = _ensure_decimal(amount)
    if amount <= 0:
        raise ValidationError("Payment amount must be greater than zero.")

    with transaction.atomic():
        wallet = _get_wallet_for_update(payment.user)
        if wallet.reserved_balance < amount:
            raise ValidationError("Reserved balance is insufficient for capture.")
        if wallet.balance < amount:
            raise ValidationError("Wallet balance is insufficient for capture.")

        wallet.balance -= amount
        wallet.reserved_balance -= amount
        wallet.save(update_fields=["balance", "reserved_balance", "updated_at"])

        WalletTransaction.objects.create(
            wallet=wallet,
            payment=payment,
            type=WalletTransaction.Type.DEBIT,
            amount=amount,
            description=f"Captured for payment {payment.id}",
        )

        payment.wallet_reserved_amount = Decimal("0.00")
        payment.save(update_fields=["wallet_reserved_amount", "updated_at"])


def refund_wallet_payment(payment: Payment) -> None:
    if payment.payment_method != Payment.Method.WALLET:
        return

    amount = _ensure_decimal(payment.amount)
    if amount <= 0:
        return

    with transaction.atomic():
        wallet = _get_wallet_for_update(payment.user)
        wallet.balance += amount
        wallet.save(update_fields=["balance", "updated_at"])

        WalletTransaction.objects.create(
            wallet=wallet,
            payment=payment,
            type=WalletTransaction.Type.REFUND,
            amount=amount,
            description=f"Refund for payment {payment.id}",
        )