"""
Razorpay Payment Integration.

Razorpay is India's leading payment gateway supporting:
- UPI (Google Pay, PhonePe, Paytm, etc.)
- Credit/Debit Cards
- Net Banking
- Wallets
- EMI
"""

import hashlib
import hmac
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class PaymentStatus(str, Enum):
    """Razorpay payment status."""

    CREATED = "created"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    REFUNDED = "refunded"
    FAILED = "failed"


@dataclass
class RazorpayOrder:
    """Razorpay order details."""

    order_id: str
    amount: int  # In paise
    currency: str
    receipt: str
    status: str
    created_at: datetime


@dataclass
class RazorpayPayment:
    """Razorpay payment details."""

    payment_id: str
    order_id: str
    amount: int
    currency: str
    status: str
    method: str
    email: Optional[str]
    contact: Optional[str]
    vpa: Optional[str]  # UPI VPA
    captured: bool
    created_at: datetime


@dataclass
class RefundResult:
    """Refund operation result."""

    success: bool
    refund_id: Optional[str] = None
    amount: Optional[int] = None
    status: Optional[str] = None
    error: Optional[str] = None


class RazorpayService:
    """
    Razorpay payment gateway integration.

    Handles:
    - Order creation
    - Payment verification
    - Refunds
    - Webhooks
    """

    def __init__(
        self,
        key_id: Optional[str] = None,
        key_secret: Optional[str] = None,
    ):
        """
        Initialize Razorpay service.

        Args:
            key_id: Razorpay Key ID
            key_secret: Razorpay Key Secret
        """
        self.key_id = key_id or settings.razorpay_key_id
        self.key_secret = key_secret or settings.razorpay_key_secret
        self.base_url = "https://api.razorpay.com/v1"

        self._client: Optional[httpx.AsyncClient] = None

    def is_configured(self) -> bool:
        """Check if Razorpay is configured."""
        return bool(self.key_id and self.key_secret)

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with auth."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                auth=(self.key_id, self.key_secret),
                headers={"Content-Type": "application/json"},
            )
        return self._client

    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    # ==================
    # Orders
    # ==================

    async def create_order(
        self,
        amount: Decimal,
        currency: str = "INR",
        receipt: Optional[str] = None,
        notes: Optional[dict] = None,
    ) -> Optional[RazorpayOrder]:
        """
        Create a Razorpay order.

        Args:
            amount: Amount in rupees (will be converted to paise)
            currency: Currency code (default: INR)
            receipt: Unique receipt ID
            notes: Additional notes

        Returns:
            RazorpayOrder or None if failed
        """
        if not self.is_configured():
            logger.error("Razorpay not configured")
            return None

        # Convert to paise (Razorpay uses smallest currency unit)
        amount_paise = int(amount * 100)

        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/orders",
                json={
                    "amount": amount_paise,
                    "currency": currency,
                    "receipt": receipt or f"rcpt_{datetime.now().timestamp()}",
                    "notes": notes or {},
                },
            )

            if response.status_code == 200:
                data = response.json()
                return RazorpayOrder(
                    order_id=data["id"],
                    amount=data["amount"],
                    currency=data["currency"],
                    receipt=data["receipt"],
                    status=data["status"],
                    created_at=datetime.fromtimestamp(
                        data["created_at"], tz=timezone.utc
                    ),
                )
            else:
                logger.error(f"Order creation failed: {response.text}")
                return None

        except Exception as e:
            logger.error(f"Order creation error: {e}")
            return None

    async def get_order(self, order_id: str) -> Optional[RazorpayOrder]:
        """Fetch order details."""
        if not self.is_configured():
            return None

        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/orders/{order_id}")

            if response.status_code == 200:
                data = response.json()
                return RazorpayOrder(
                    order_id=data["id"],
                    amount=data["amount"],
                    currency=data["currency"],
                    receipt=data["receipt"],
                    status=data["status"],
                    created_at=datetime.fromtimestamp(
                        data["created_at"], tz=timezone.utc
                    ),
                )
            return None

        except Exception as e:
            logger.error(f"Get order error: {e}")
            return None

    # ==================
    # Payments
    # ==================

    def verify_payment_signature(
        self,
        order_id: str,
        payment_id: str,
        signature: str,
    ) -> bool:
        """
        Verify Razorpay payment signature.

        This MUST be called after payment to ensure authenticity.

        Args:
            order_id: Razorpay order ID
            payment_id: Razorpay payment ID
            signature: Signature from Razorpay checkout

        Returns:
            True if signature is valid
        """
        if not self.key_secret:
            return False

        try:
            message = f"{order_id}|{payment_id}"
            expected_signature = hmac.new(
                self.key_secret.encode(),
                message.encode(),
                hashlib.sha256,
            ).hexdigest()

            return hmac.compare_digest(expected_signature, signature)

        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            return False

    async def get_payment(self, payment_id: str) -> Optional[RazorpayPayment]:
        """Fetch payment details."""
        if not self.is_configured():
            return None

        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/payments/{payment_id}")

            if response.status_code == 200:
                data = response.json()
                return RazorpayPayment(
                    payment_id=data["id"],
                    order_id=data.get("order_id", ""),
                    amount=data["amount"],
                    currency=data["currency"],
                    status=data["status"],
                    method=data.get("method", ""),
                    email=data.get("email"),
                    contact=data.get("contact"),
                    vpa=data.get("vpa"),  # UPI VPA
                    captured=data.get("captured", False),
                    created_at=datetime.fromtimestamp(
                        data["created_at"], tz=timezone.utc
                    ),
                )
            return None

        except Exception as e:
            logger.error(f"Get payment error: {e}")
            return None

    async def capture_payment(
        self,
        payment_id: str,
        amount: Optional[int] = None,
        currency: str = "INR",
    ) -> bool:
        """
        Capture an authorized payment.

        Required if using auto-capture = false.

        Args:
            payment_id: Payment to capture
            amount: Amount in paise (optional, captures full amount if not specified)
            currency: Currency code

        Returns:
            True if captured successfully
        """
        if not self.is_configured():
            return False

        try:
            client = await self._get_client()

            payload = {"currency": currency}
            if amount:
                payload["amount"] = amount

            response = await client.post(
                f"{self.base_url}/payments/{payment_id}/capture",
                json=payload,
            )

            return response.status_code == 200

        except Exception as e:
            logger.error(f"Capture payment error: {e}")
            return False

    # ==================
    # Refunds
    # ==================

    async def create_refund(
        self,
        payment_id: str,
        amount: Optional[Decimal] = None,
        notes: Optional[dict] = None,
    ) -> RefundResult:
        """
        Create a refund for a payment.

        Args:
            payment_id: Payment to refund
            amount: Amount in rupees (partial refund). Full refund if None.
            notes: Additional notes

        Returns:
            RefundResult with status
        """
        if not self.is_configured():
            return RefundResult(success=False, error="Razorpay not configured")

        try:
            client = await self._get_client()

            payload = {"notes": notes or {}}
            if amount:
                payload["amount"] = int(amount * 100)

            response = await client.post(
                f"{self.base_url}/payments/{payment_id}/refund",
                json=payload,
            )

            if response.status_code == 200:
                data = response.json()
                return RefundResult(
                    success=True,
                    refund_id=data["id"],
                    amount=data["amount"],
                    status=data["status"],
                )
            else:
                return RefundResult(
                    success=False,
                    error=f"Refund failed: {response.text}",
                )

        except Exception as e:
            logger.error(f"Refund error: {e}")
            return RefundResult(success=False, error=str(e))

    async def get_refund(
        self,
        payment_id: str,
        refund_id: str,
    ) -> Optional[dict]:
        """Fetch refund details."""
        if not self.is_configured():
            return None

        try:
            client = await self._get_client()
            response = await client.get(
                f"{self.base_url}/payments/{payment_id}/refunds/{refund_id}"
            )

            if response.status_code == 200:
                return response.json()
            return None

        except Exception as e:
            logger.error(f"Get refund error: {e}")
            return None

    # ==================
    # Webhooks
    # ==================

    def verify_webhook_signature(
        self,
        body: bytes,
        signature: str,
        webhook_secret: str,
    ) -> bool:
        """
        Verify Razorpay webhook signature.

        Args:
            body: Raw request body
            signature: X-Razorpay-Signature header
            webhook_secret: Webhook secret from Razorpay dashboard

        Returns:
            True if signature is valid
        """
        try:
            expected_signature = hmac.new(
                webhook_secret.encode(),
                body,
                hashlib.sha256,
            ).hexdigest()

            return hmac.compare_digest(expected_signature, signature)

        except Exception as e:
            logger.error(f"Webhook signature verification error: {e}")
            return False

    # ==================
    # Helper Methods
    # ==================

    def get_checkout_options(
        self,
        order: RazorpayOrder,
        customer_name: str,
        customer_email: str,
        customer_phone: str,
        description: str = "DocAssist Payment",
        prefill_upi: Optional[str] = None,
    ) -> dict:
        """
        Get options for Razorpay checkout.

        Returns options to pass to Razorpay.open() in frontend.
        """
        options = {
            "key": self.key_id,
            "amount": order.amount,
            "currency": order.currency,
            "order_id": order.order_id,
            "name": "DocAssist",
            "description": description,
            "prefill": {
                "name": customer_name,
                "email": customer_email,
                "contact": customer_phone,
            },
            "theme": {
                "color": "#1976D2",  # Primary brand color
            },
            "modal": {
                "ondismiss": "handlePaymentDismiss",
            },
        }

        if prefill_upi:
            options["prefill"]["vpa"] = prefill_upi

        return options


# Singleton instance
_razorpay_service: Optional[RazorpayService] = None


def get_razorpay_service() -> RazorpayService:
    """Get Razorpay service singleton."""
    global _razorpay_service
    if _razorpay_service is None:
        _razorpay_service = RazorpayService()
    return _razorpay_service
