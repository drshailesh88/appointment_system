"""
OTP Service for patient authentication.
"""

import secrets
from datetime import datetime, timedelta, timezone

from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.otp import OTP


class OTPService:
    """Service for OTP generation, sending, and verification."""

    OTP_EXPIRY_MINUTES = 10
    TOKEN_EXPIRY_HOURS = 24

    def __init__(self, db: AsyncSession):
        self.db = db

    def generate_otp(self) -> str:
        """Generate a 6-digit OTP code."""
        return f"{secrets.randbelow(1000000):06d}"

    async def send_otp(self, phone: str) -> OTP:
        """
        Generate and send OTP to phone number.

        Args:
            phone: Phone number to send OTP to

        Returns:
            OTP: Created OTP record
        """
        # Invalidate any existing OTPs for this phone
        result = await self.db.execute(
            select(OTP).where(
                OTP.phone == phone,
                OTP.is_verified == False,
            )
        )
        existing_otps = result.scalars().all()
        for otp in existing_otps:
            otp.is_verified = True  # Mark as used

        # Generate new OTP
        otp_code = self.generate_otp()
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=self.OTP_EXPIRY_MINUTES
        )

        otp = OTP(
            phone=phone,
            otp_code=otp_code,
            expires_at=expires_at,
        )
        self.db.add(otp)
        await self.db.commit()
        await self.db.refresh(otp)

        # Send OTP via SMS
        from app.services.sms_service import get_sms_service
        import logging

        logger = logging.getLogger(__name__)

        # Always log OTP in development/testing
        if not settings.sms_enabled or settings.testing:
            logger.info(
                f"[OTP] Phone: {phone}, Code: {otp_code}, "
                f"Expires: {self.OTP_EXPIRY_MINUTES}min"
            )

        # Send SMS if enabled
        if settings.sms_enabled:
            sms_service = get_sms_service()
            result = await sms_service.send_otp(
                phone=phone,
                otp=otp_code,
                validity_minutes=self.OTP_EXPIRY_MINUTES,
            )

            if not result.success:
                logger.error(f"Failed to send OTP SMS to {phone}: {result.error}")
                # Don't fail the whole operation, OTP is still logged
        else:
            logger.info(f"SMS disabled. OTP for {phone}: {otp_code}")

        return otp

    async def verify_otp(self, phone: str, otp_code: str) -> str | None:
        """
        Verify OTP and return JWT token if valid.

        Args:
            phone: Phone number
            otp_code: OTP code to verify

        Returns:
            str: JWT token if valid, None if invalid
        """
        # Find the latest valid OTP for this phone
        result = await self.db.execute(
            select(OTP)
            .where(
                OTP.phone == phone,
                OTP.otp_code == otp_code,
                OTP.is_verified == False,
            )
            .order_by(OTP.created_at.desc())
        )
        otp = result.scalar_one_or_none()

        if not otp:
            return None

        # Increment attempts
        otp.attempts += 1
        await self.db.commit()

        # Check if OTP is valid
        if not otp.is_valid():
            return None

        # Mark as verified
        otp.is_verified = True
        await self.db.commit()

        # Generate JWT token
        token = self.create_access_token(phone)
        return token

    def create_access_token(self, phone: str) -> str:
        """
        Create JWT access token for patient.

        Args:
            phone: Phone number

        Returns:
            str: JWT token
        """
        expires_delta = timedelta(hours=self.TOKEN_EXPIRY_HOURS)
        expire = datetime.now(timezone.utc) + expires_delta

        to_encode = {
            "sub": phone,
            "type": "patient_otp",
            "exp": expire,
        }

        encoded_jwt = jwt.encode(
            to_encode,
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )
        return encoded_jwt

    @staticmethod
    def decode_token(token: str) -> str | None:
        """
        Decode JWT token and return phone number.

        Args:
            token: JWT token

        Returns:
            str: Phone number if valid, None if invalid
        """
        try:
            payload = jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            )
            phone: str = payload.get("sub")
            token_type: str = payload.get("type")

            if token_type != "patient_otp":
                return None

            return phone
        except Exception:
            return None
