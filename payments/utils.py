import requests
import logging
from django.conf import settings

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