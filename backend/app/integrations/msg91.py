"""
MSG91 SMS Gateway Integration (API v5).

MSG91 is India's leading SMS gateway supporting:
- Transactional SMS with DLT compliance
- OTP Flow API
- Promotional SMS
- WhatsApp Business API

API Documentation: https://docs.msg91.com/
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.core.config import settings

logger = logging.getLogger(__name__)


class MSG91Route(str, Enum):
    """MSG91 routing options."""

    TRANSACTIONAL = "4"  # DLT registered transactional route
    PROMOTIONAL = "1"  # Promotional SMS
    OTP = "otp"  # OTP Flow API


@dataclass
class SMSResponse:
    """Response from MSG91 SMS API."""

    success: bool
    request_id: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


class MSG91Client:
    """
    MSG91 API v5 client.

    Handles SMS and OTP sending with retry logic and rate limiting awareness.
    """

    BASE_URL = "https://control.msg91.com/api/v5"
    OTP_BASE_URL = "https://control.msg91.com/api/v5/otp"

    def __init__(
        self,
        auth_key: Optional[str] = None,
        sender_id: Optional[str] = None,
        route: str = MSG91Route.TRANSACTIONAL,
        country_code: str = "91",
    ):
        """
        Initialize MSG91 client.

        Args:
            auth_key: MSG91 authentication key
            sender_id: Sender ID (DLT registered, 6 chars)
            route: SMS route (transactional/promotional)
            country_code: Default country code (91 for India)
        """
        self.auth_key = auth_key or settings.msg91_auth_key
        self.sender_id = sender_id or settings.msg91_sender_id
        self.route = route
        self.country_code = country_code

        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                headers={
                    "authkey": self.auth_key,
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _format_phone(self, phone: str) -> str:
        """
        Format phone number for MSG91.

        Args:
            phone: Phone number in any format

        Returns:
            Formatted phone number (without +, with country code)
        """
        # Remove spaces, hyphens, and plus sign
        phone = phone.replace(" ", "").replace("-", "").replace("+", "")

        # Add country code if not present
        if not phone.startswith(self.country_code) and len(phone) == 10:
            phone = self.country_code + phone

        return phone

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
    )
    async def send_sms(
        self,
        phone: str,
        message: str,
        template_id: Optional[str] = None,
    ) -> SMSResponse:
        """
        Send SMS via MSG91 (legacy text API).

        Args:
            phone: Recipient phone number
            message: SMS message text
            template_id: DLT template ID (required for India)

        Returns:
            SMSResponse with delivery status
        """
        if not self.auth_key:
            logger.warning("MSG91 auth key not configured")
            return SMSResponse(
                success=False,
                error="MSG91 not configured",
            )

        if settings.testing and not settings.sms_enabled:
            # Mock mode for testing
            logger.info(f"[MOCK SMS] To: {phone}, Message: {message}")
            return SMSResponse(
                success=True,
                request_id="mock_" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
                message="Mock SMS sent (testing mode)",
            )

        try:
            phone = self._format_phone(phone)

            payload = {
                "sender": self.sender_id,
                "route": self.route,
                "country": self.country_code,
                "sms": [
                    {
                        "message": message,
                        "to": [phone],
                    }
                ],
            }

            # Add DLT template ID if provided (mandatory for India)
            if template_id:
                payload["DLT_TE_ID"] = template_id

            client = await self._get_client()
            response = await client.post(
                f"{self.BASE_URL}/flow/",
                json=payload,
            )

            if response.status_code == 200:
                data = response.json()
                return SMSResponse(
                    success=True,
                    request_id=data.get("request_id"),
                    message=data.get("message", "SMS sent successfully"),
                )
            else:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get("message", f"HTTP {response.status_code}")
                logger.error(f"MSG91 SMS error: {error_msg}")
                return SMSResponse(
                    success=False,
                    error=error_msg,
                )

        except httpx.TimeoutException as e:
            logger.error(f"MSG91 timeout: {e}")
            raise  # Will trigger retry
        except httpx.NetworkError as e:
            logger.error(f"MSG91 network error: {e}")
            raise  # Will trigger retry
        except Exception as e:
            logger.error(f"MSG91 unexpected error: {e}")
            return SMSResponse(
                success=False,
                error=str(e),
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
    )
    async def send_otp(
        self,
        phone: str,
        otp_length: int = 6,
        otp_expiry_minutes: int = 5,
        template_id: Optional[str] = None,
    ) -> SMSResponse:
        """
        Send OTP using MSG91 OTP Flow API.

        Args:
            phone: Recipient phone number
            otp_length: Length of OTP (4-9 digits)
            otp_expiry_minutes: OTP expiry in minutes
            template_id: DLT template ID for OTP

        Returns:
            SMSResponse with status
        """
        if not self.auth_key:
            logger.warning("MSG91 auth key not configured")
            return SMSResponse(
                success=False,
                error="MSG91 not configured",
            )

        if settings.testing and not settings.sms_enabled:
            # Mock mode for testing
            logger.info(f"[MOCK OTP] To: {phone}, Length: {otp_length}")
            return SMSResponse(
                success=True,
                request_id="mock_otp_" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
                message="Mock OTP sent (testing mode)",
            )

        try:
            phone = self._format_phone(phone)

            payload = {
                "template_id": template_id or settings.msg91_dlt_te_id,
                "mobile": phone,
                "authkey": self.auth_key,
                "otp_length": otp_length,
                "otp_expiry": otp_expiry_minutes,
            }

            client = await self._get_client()
            response = await client.post(
                f"{self.OTP_BASE_URL}/send",
                json=payload,
            )

            if response.status_code == 200:
                data = response.json()
                return SMSResponse(
                    success=True,
                    request_id=data.get("request_id"),
                    message="OTP sent successfully",
                )
            else:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get("message", f"HTTP {response.status_code}")
                logger.error(f"MSG91 OTP error: {error_msg}")
                return SMSResponse(
                    success=False,
                    error=error_msg,
                )

        except httpx.TimeoutException as e:
            logger.error(f"MSG91 OTP timeout: {e}")
            raise
        except httpx.NetworkError as e:
            logger.error(f"MSG91 OTP network error: {e}")
            raise
        except Exception as e:
            logger.error(f"MSG91 OTP unexpected error: {e}")
            return SMSResponse(
                success=False,
                error=str(e),
            )

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5),
    )
    async def verify_otp(
        self,
        phone: str,
        otp: str,
    ) -> SMSResponse:
        """
        Verify OTP using MSG91 OTP Flow API.

        Args:
            phone: Phone number
            otp: OTP code to verify

        Returns:
            SMSResponse with verification result
        """
        if not self.auth_key:
            return SMSResponse(
                success=False,
                error="MSG91 not configured",
            )

        if settings.testing and not settings.sms_enabled:
            # Mock mode - accept "123456" as valid OTP
            if otp == "123456":
                logger.info(f"[MOCK OTP VERIFY] Phone: {phone}, Valid: True")
                return SMSResponse(
                    success=True,
                    message="Mock OTP verified (testing mode)",
                )
            else:
                logger.info(f"[MOCK OTP VERIFY] Phone: {phone}, Valid: False")
                return SMSResponse(
                    success=False,
                    error="Invalid OTP (testing mode)",
                )

        try:
            phone = self._format_phone(phone)

            payload = {
                "authkey": self.auth_key,
                "mobile": phone,
                "otp": otp,
            }

            client = await self._get_client()
            response = await client.post(
                f"{self.OTP_BASE_URL}/verify",
                json=payload,
            )

            if response.status_code == 200:
                data = response.json()
                return SMSResponse(
                    success=True,
                    message=data.get("message", "OTP verified successfully"),
                )
            else:
                return SMSResponse(
                    success=False,
                    error="Invalid or expired OTP",
                )

        except Exception as e:
            logger.error(f"MSG91 OTP verify error: {e}")
            return SMSResponse(
                success=False,
                error=str(e),
            )

    async def resend_otp(
        self,
        phone: str,
        retry_type: str = "text",
    ) -> SMSResponse:
        """
        Resend OTP using MSG91.

        Args:
            phone: Phone number
            retry_type: Retry method (text/voice)

        Returns:
            SMSResponse with status
        """
        if not self.auth_key:
            return SMSResponse(
                success=False,
                error="MSG91 not configured",
            )

        if settings.testing and not settings.sms_enabled:
            logger.info(f"[MOCK OTP RESEND] To: {phone}, Type: {retry_type}")
            return SMSResponse(
                success=True,
                message="Mock OTP resent (testing mode)",
            )

        try:
            phone = self._format_phone(phone)

            payload = {
                "authkey": self.auth_key,
                "mobile": phone,
                "retrytype": retry_type,
            }

            client = await self._get_client()
            response = await client.post(
                f"{self.OTP_BASE_URL}/retry",
                json=payload,
            )

            if response.status_code == 200:
                return SMSResponse(
                    success=True,
                    message="OTP resent successfully",
                )
            else:
                return SMSResponse(
                    success=False,
                    error="Failed to resend OTP",
                )

        except Exception as e:
            logger.error(f"MSG91 OTP resend error: {e}")
            return SMSResponse(
                success=False,
                error=str(e),
            )


# Singleton instance
_msg91_client: Optional[MSG91Client] = None


def get_msg91_client() -> MSG91Client:
    """Get MSG91 client singleton."""
    global _msg91_client
    if _msg91_client is None:
        _msg91_client = MSG91Client()
    return _msg91_client
