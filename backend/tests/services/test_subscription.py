"""
Tests for subscription service.
"""
from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.subscription import (
    SubscriptionService,
    SubscriptionTier,
    TIER_FEATURES,
)


class TestSubscriptionTiers:
    """Tests for subscription tier features."""

    def test_free_tier_features(self):
        """Test free tier features."""
        features = TIER_FEATURES[SubscriptionTier.FREE]
        assert features.max_doctors == 1
        assert features.max_appointments_per_day == 10
        assert features.sms_credits_monthly == 0
        assert features.whatsapp_enabled == False
        assert features.voice_agent_enabled == False
        assert features.emr_integration == False

    def test_starter_tier_features(self):
        """Test starter tier features."""
        features = TIER_FEATURES[SubscriptionTier.STARTER]
        assert features.max_doctors == 2
        assert features.max_appointments_per_day == 50
        assert features.sms_credits_monthly == 100
        assert features.whatsapp_enabled == False
        assert features.voice_agent_enabled == False
        assert features.emr_integration == True

    def test_professional_tier_features(self):
        """Test professional tier features."""
        features = TIER_FEATURES[SubscriptionTier.PROFESSIONAL]
        assert features.max_doctors == 5
        assert features.max_appointments_per_day == 100
        assert features.sms_credits_monthly == 300
        assert features.whatsapp_enabled == True
        assert features.voice_agent_enabled == True
        assert features.emr_integration == True

    def test_clinic_tier_features(self):
        """Test clinic tier features."""
        features = TIER_FEATURES[SubscriptionTier.CLINIC]
        assert features.max_doctors == 999  # Unlimited
        assert features.max_appointments_per_day == 999  # Unlimited
        assert features.sms_credits_monthly == 1000
        assert features.whatsapp_enabled == True
        assert features.voice_agent_enabled == True
        assert features.emr_integration == True
        assert features.custom_branding == True
        assert features.multi_location == True


class TestSubscriptionService:
    """Tests for SubscriptionService class."""

    @pytest.mark.asyncio
    async def test_get_subscription_status(self, db: AsyncSession, test_clinic):
        """Test getting subscription status."""
        service = SubscriptionService()

        # Set to free tier explicitly for testing
        test_clinic.subscription_tier = "free"
        await db.commit()

        status = await service.get_status(test_clinic.id, db)

        assert status is not None
        assert status.tier == SubscriptionTier.FREE
        assert status.features is not None
        # Free tier is always active
        assert status.is_active == True

    @pytest.mark.asyncio
    async def test_check_feature_available(self, db: AsyncSession, test_clinic):
        """Test checking feature availability."""
        from datetime import datetime, timedelta, timezone

        service = SubscriptionService()

        # Professional tier should have voice agent
        test_clinic.subscription_tier = "professional"
        # Set future expiry so subscription is active
        test_clinic.subscription_expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        await db.commit()

        has_voice = await service.check_feature(test_clinic.id, "voice_agent_enabled", db)
        has_whatsapp = await service.check_feature(test_clinic.id, "whatsapp_enabled", db)

        assert has_voice == True
        assert has_whatsapp == True

    @pytest.mark.asyncio
    async def test_check_feature_not_available(self, db: AsyncSession, test_clinic):
        """Test checking unavailable feature."""
        service = SubscriptionService()

        # Free tier should not have voice agent
        test_clinic.subscription_tier = "free"
        await db.commit()

        has_voice = await service.check_feature(test_clinic.id, "voice_agent_enabled", db)
        has_whatsapp = await service.check_feature(test_clinic.id, "whatsapp_enabled", db)

        assert has_voice == False
        assert has_whatsapp == False

    @pytest.mark.asyncio
    async def test_check_limit_doctors(self, db: AsyncSession, test_clinic):
        """Test checking doctor limit."""
        service = SubscriptionService()

        test_clinic.subscription_tier = "starter"
        await db.commit()

        # Starter tier allows 2 doctors
        within_limit, current, max_allowed = await service.check_limit(test_clinic.id, "doctors", db)
        assert within_limit == True  # Should be within limit
        assert max_allowed == 2

    @pytest.mark.asyncio
    async def test_check_limit_appointments(self, db: AsyncSession, test_clinic):
        """Test checking appointment limit."""
        service = SubscriptionService()

        test_clinic.subscription_tier = "free"
        await db.commit()

        # Free tier allows 10 appointments per day
        within_limit, current, max_allowed = await service.check_limit(test_clinic.id, "appointments_per_day", db)
        assert max_allowed == 10

    @pytest.mark.asyncio
    async def test_unlimited_limits(self, db: AsyncSession, test_clinic):
        """Test unlimited limits for clinic tier."""
        service = SubscriptionService()

        test_clinic.subscription_tier = "clinic"
        await db.commit()

        # Clinic tier has 999 (effectively unlimited)
        within_limit, current, max_allowed = await service.check_limit(test_clinic.id, "doctors", db)
        assert max_allowed == 999

        within_limit, current, max_allowed = await service.check_limit(test_clinic.id, "appointments_per_day", db)
        assert max_allowed == 999


class TestSubscriptionPricing:
    """Tests for subscription pricing."""

    def test_tier_pricing(self):
        """Test tier pricing values."""
        assert TIER_FEATURES[SubscriptionTier.FREE].price_monthly == 0
        assert TIER_FEATURES[SubscriptionTier.STARTER].price_monthly == 499
        assert TIER_FEATURES[SubscriptionTier.PROFESSIONAL].price_monthly == 999
        assert TIER_FEATURES[SubscriptionTier.CLINIC].price_monthly == 2499

    def test_tier_names(self):
        """Test tier display names."""
        assert SubscriptionTier.FREE.value == "free"
        assert SubscriptionTier.STARTER.value == "starter"
        assert SubscriptionTier.PROFESSIONAL.value == "professional"
        assert SubscriptionTier.CLINIC.value == "clinic"
