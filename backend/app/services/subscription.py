"""
Subscription Management Service.

Handles clinic subscriptions with tiers:
- Free: Basic features
- Starter: ₹499/month
- Professional: ₹999/month
- Clinic: ₹2,499/month
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.razorpay import RazorpayService, get_razorpay_service
from app.models.clinic import Clinic

logger = logging.getLogger(__name__)


class SubscriptionTier(str, Enum):
    """Subscription tier levels."""

    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    CLINIC = "clinic"


@dataclass
class TierFeatures:
    """Features available in each tier."""

    name: str
    price_monthly: Decimal
    price_yearly: Decimal  # Annual discount
    max_doctors: int
    max_appointments_per_day: int
    sms_credits_monthly: int
    whatsapp_enabled: bool
    voice_agent_enabled: bool
    emr_integration: bool
    custom_branding: bool
    priority_support: bool
    analytics_enabled: bool
    multi_location: bool


# Tier definitions
TIER_FEATURES = {
    SubscriptionTier.FREE: TierFeatures(
        name="Free",
        price_monthly=Decimal("0"),
        price_yearly=Decimal("0"),
        max_doctors=1,
        max_appointments_per_day=10,
        sms_credits_monthly=0,
        whatsapp_enabled=False,
        voice_agent_enabled=False,
        emr_integration=False,
        custom_branding=False,
        priority_support=False,
        analytics_enabled=False,
        multi_location=False,
    ),
    SubscriptionTier.STARTER: TierFeatures(
        name="Starter",
        price_monthly=Decimal("499"),
        price_yearly=Decimal("4990"),  # 2 months free
        max_doctors=2,
        max_appointments_per_day=50,
        sms_credits_monthly=100,
        whatsapp_enabled=False,
        voice_agent_enabled=False,
        emr_integration=True,
        custom_branding=False,
        priority_support=False,
        analytics_enabled=True,
        multi_location=False,
    ),
    SubscriptionTier.PROFESSIONAL: TierFeatures(
        name="Professional",
        price_monthly=Decimal("999"),
        price_yearly=Decimal("9990"),  # 2 months free
        max_doctors=5,
        max_appointments_per_day=100,
        sms_credits_monthly=300,
        whatsapp_enabled=True,
        voice_agent_enabled=True,
        emr_integration=True,
        custom_branding=True,
        priority_support=True,
        analytics_enabled=True,
        multi_location=False,
    ),
    SubscriptionTier.CLINIC: TierFeatures(
        name="Clinic",
        price_monthly=Decimal("2499"),
        price_yearly=Decimal("24990"),  # 2 months free
        max_doctors=999,  # Unlimited
        max_appointments_per_day=999,  # Unlimited
        sms_credits_monthly=1000,
        whatsapp_enabled=True,
        voice_agent_enabled=True,
        emr_integration=True,
        custom_branding=True,
        priority_support=True,
        analytics_enabled=True,
        multi_location=True,
    ),
}


@dataclass
class SubscriptionStatus:
    """Current subscription status for a clinic."""

    clinic_id: UUID
    tier: SubscriptionTier
    features: TierFeatures
    expires_at: Optional[datetime]
    is_active: bool
    days_remaining: int
    is_trial: bool
    usage: dict  # Current usage stats


class SubscriptionService:
    """
    Subscription management service.

    Handles:
    - Tier upgrades/downgrades
    - Payment processing
    - Usage tracking
    - Feature gating
    """

    def __init__(
        self,
        razorpay: Optional[RazorpayService] = None,
    ):
        """Initialize subscription service."""
        self.razorpay = razorpay or get_razorpay_service()

    async def get_status(
        self,
        clinic_id: UUID,
        db: AsyncSession,
    ) -> SubscriptionStatus:
        """Get current subscription status for a clinic."""
        result = await db.execute(
            select(Clinic).where(Clinic.id == clinic_id)
        )
        clinic = result.scalar_one_or_none()

        if not clinic:
            raise ValueError(f"Clinic not found: {clinic_id}")

        tier = SubscriptionTier(clinic.subscription_tier or "free")
        features = TIER_FEATURES[tier]
        expires_at = clinic.subscription_expires_at

        now = datetime.now(timezone.utc)
        is_active = tier == SubscriptionTier.FREE or (
            expires_at and expires_at > now
        )

        days_remaining = 0
        if expires_at and expires_at > now:
            days_remaining = (expires_at - now).days

        # Get usage stats
        usage = await self._get_usage(clinic_id, db)

        return SubscriptionStatus(
            clinic_id=clinic_id,
            tier=tier,
            features=features,
            expires_at=expires_at,
            is_active=is_active,
            days_remaining=days_remaining,
            is_trial=False,  # TODO: Implement trial logic
            usage=usage,
        )

    async def _get_usage(
        self,
        clinic_id: UUID,
        db: AsyncSession,
    ) -> dict:
        """Get current usage stats for a clinic."""
        from app.models.doctor import Doctor
        from app.models.appointment import Appointment
        from datetime import date

        # Count doctors
        doctors_result = await db.execute(
            select(Doctor)
            .where(Doctor.clinic_id == clinic_id)
            .where(Doctor.is_active == True)
        )
        doctor_count = len(doctors_result.scalars().all())

        # Count today's appointments
        today_start = datetime.combine(date.today(), datetime.min.time())
        today_end = datetime.combine(date.today(), datetime.max.time())

        appts_result = await db.execute(
            select(Appointment)
            .join(Doctor)
            .where(Doctor.clinic_id == clinic_id)
            .where(Appointment.scheduled_start >= today_start)
            .where(Appointment.scheduled_start <= today_end)
        )
        appointment_count = len(appts_result.scalars().all())

        return {
            "doctors": doctor_count,
            "appointments_today": appointment_count,
            "sms_sent_this_month": 0,  # TODO: Track SMS usage
        }

    async def check_feature(
        self,
        clinic_id: UUID,
        feature: str,
        db: AsyncSession,
    ) -> bool:
        """Check if a feature is available for the clinic."""
        status = await self.get_status(clinic_id, db)

        if not status.is_active and status.tier != SubscriptionTier.FREE:
            return False

        return getattr(status.features, feature, False)

    async def check_limit(
        self,
        clinic_id: UUID,
        limit_type: str,
        db: AsyncSession,
    ) -> tuple[bool, int, int]:
        """
        Check if a limit is exceeded.

        Returns:
            Tuple of (within_limit, current_usage, max_allowed)
        """
        status = await self.get_status(clinic_id, db)

        if limit_type == "doctors":
            current = status.usage["doctors"]
            max_allowed = status.features.max_doctors
        elif limit_type == "appointments_per_day":
            current = status.usage["appointments_today"]
            max_allowed = status.features.max_appointments_per_day
        else:
            return (True, 0, 999)

        return (current < max_allowed, current, max_allowed)

    async def create_subscription_order(
        self,
        clinic_id: UUID,
        tier: SubscriptionTier,
        billing_period: str,  # "monthly" or "yearly"
        db: AsyncSession,
    ) -> Optional[dict]:
        """
        Create a Razorpay order for subscription.

        Returns:
            Order details for frontend checkout
        """
        if tier == SubscriptionTier.FREE:
            raise ValueError("Cannot create order for free tier")

        features = TIER_FEATURES[tier]

        if billing_period == "yearly":
            amount = features.price_yearly
        else:
            amount = features.price_monthly

        # Get clinic for customer info
        result = await db.execute(
            select(Clinic).where(Clinic.id == clinic_id)
        )
        clinic = result.scalar_one_or_none()

        if not clinic:
            raise ValueError(f"Clinic not found: {clinic_id}")

        # Create Razorpay order
        order = await self.razorpay.create_order(
            amount=amount,
            currency="INR",
            receipt=f"sub_{clinic_id}_{tier.value}",
            notes={
                "clinic_id": str(clinic_id),
                "tier": tier.value,
                "billing_period": billing_period,
            },
        )

        if not order:
            return None

        # Get checkout options
        checkout_options = self.razorpay.get_checkout_options(
            order=order,
            customer_name=clinic.name,
            customer_email=clinic.email or "",
            customer_phone=clinic.phone,
            description=f"DocAssist {features.name} - {billing_period.title()}",
        )

        return {
            "order_id": order.order_id,
            "amount": order.amount,
            "currency": order.currency,
            "tier": tier.value,
            "billing_period": billing_period,
            "checkout_options": checkout_options,
        }

    async def activate_subscription(
        self,
        clinic_id: UUID,
        tier: SubscriptionTier,
        billing_period: str,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
        db: AsyncSession,
    ) -> bool:
        """
        Activate subscription after successful payment.

        Verifies payment signature and updates clinic subscription.
        """
        # Verify signature
        if not self.razorpay.verify_payment_signature(
            razorpay_order_id,
            razorpay_payment_id,
            razorpay_signature,
        ):
            logger.error(f"Invalid payment signature for clinic {clinic_id}")
            return False

        # Calculate expiry
        now = datetime.now(timezone.utc)
        if billing_period == "yearly":
            expires_at = now + timedelta(days=365)
        else:
            expires_at = now + timedelta(days=30)

        # Update clinic
        await db.execute(
            update(Clinic)
            .where(Clinic.id == clinic_id)
            .values(
                subscription_tier=tier.value,
                subscription_expires_at=expires_at,
            )
        )
        await db.commit()

        logger.info(
            f"Activated {tier.value} subscription for clinic {clinic_id} "
            f"until {expires_at}"
        )

        return True

    async def cancel_subscription(
        self,
        clinic_id: UUID,
        db: AsyncSession,
    ) -> bool:
        """
        Cancel subscription.

        Subscription remains active until expiry, then downgrades to free.
        """
        result = await db.execute(
            select(Clinic).where(Clinic.id == clinic_id)
        )
        clinic = result.scalar_one_or_none()

        if not clinic:
            return False

        # Don't change expiry - let it run out naturally
        # Just mark as cancelled (could add a cancelled_at field)

        logger.info(
            f"Subscription cancelled for clinic {clinic_id}. "
            f"Active until {clinic.subscription_expires_at}"
        )

        return True

    async def downgrade_expired_subscriptions(
        self,
        db: AsyncSession,
    ) -> int:
        """
        Downgrade expired subscriptions to free tier.

        Should be run periodically (e.g., daily cron).
        """
        now = datetime.now(timezone.utc)

        result = await db.execute(
            select(Clinic)
            .where(Clinic.subscription_tier != SubscriptionTier.FREE.value)
            .where(Clinic.subscription_expires_at < now)
        )
        expired_clinics = result.scalars().all()

        count = 0
        for clinic in expired_clinics:
            clinic.subscription_tier = SubscriptionTier.FREE.value
            clinic.subscription_expires_at = None
            count += 1

        await db.commit()

        logger.info(f"Downgraded {count} expired subscriptions to free tier")

        return count


# Helper function for feature gating in APIs
async def require_feature(
    feature: str,
    clinic_id: UUID,
    db: AsyncSession,
) -> None:
    """
    Raise exception if feature not available.

    Usage in API:
        await require_feature("voice_agent_enabled", clinic_id, db)
    """
    from fastapi import HTTPException, status

    service = SubscriptionService()
    has_feature = await service.check_feature(clinic_id, feature, db)

    if not has_feature:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Feature '{feature}' requires a higher subscription tier",
        )


async def require_within_limit(
    limit_type: str,
    clinic_id: UUID,
    db: AsyncSession,
) -> None:
    """
    Raise exception if limit exceeded.

    Usage in API:
        await require_within_limit("appointments_per_day", clinic_id, db)
    """
    from fastapi import HTTPException, status

    service = SubscriptionService()
    within_limit, current, max_allowed = await service.check_limit(
        clinic_id, limit_type, db
    )

    if not within_limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Limit exceeded: {current}/{max_allowed} {limit_type}. Upgrade your plan.",
        )
