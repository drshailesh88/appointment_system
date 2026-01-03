"""
Tests for subscription service.
"""
from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import Session

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
        assert features.max_patients == 100
        assert features.max_appointments_per_day == 20
        assert features.voice_booking == False
        assert features.sms_reminders == False
        assert features.whatsapp_integration == False
        assert features.online_payments == False

    def test_starter_tier_features(self):
        """Test starter tier features."""
        features = TIER_FEATURES[SubscriptionTier.STARTER]
        assert features.max_doctors == 2
        assert features.max_patients == 500
        assert features.max_appointments_per_day == 50
        assert features.voice_booking == False
        assert features.sms_reminders == True
        assert features.whatsapp_integration == False
        assert features.online_payments == True

    def test_professional_tier_features(self):
        """Test professional tier features."""
        features = TIER_FEATURES[SubscriptionTier.PROFESSIONAL]
        assert features.max_doctors == 5
        assert features.max_patients == 2000
        assert features.max_appointments_per_day == 100
        assert features.voice_booking == True
        assert features.sms_reminders == True
        assert features.whatsapp_integration == True
        assert features.online_payments == True

    def test_clinic_tier_features(self):
        """Test clinic tier features."""
        features = TIER_FEATURES[SubscriptionTier.CLINIC]
        assert features.max_doctors == -1  # Unlimited
        assert features.max_patients == -1  # Unlimited
        assert features.max_appointments_per_day == -1  # Unlimited
        assert features.voice_booking == True
        assert features.sms_reminders == True
        assert features.whatsapp_integration == True
        assert features.online_payments == True
        assert features.custom_branding == True
        assert features.api_access == True


class TestSubscriptionService:
    """Tests for SubscriptionService class."""

    def test_get_subscription_status(self, db: Session, test_clinic):
        """Test getting subscription status."""
        service = SubscriptionService(db)
        status = service.get_subscription_status(test_clinic.id)

        assert status is not None
        assert "tier" in status
        assert "features" in status

    def test_check_feature_available(self, db: Session, test_clinic):
        """Test checking feature availability."""
        service = SubscriptionService(db)

        # Professional tier should have voice booking
        test_clinic.subscription_tier = "professional"
        db.commit()

        assert service.check_feature(test_clinic.id, "voice_booking") == True
        assert service.check_feature(test_clinic.id, "sms_reminders") == True

    def test_check_feature_not_available(self, db: Session, test_clinic):
        """Test checking unavailable feature."""
        service = SubscriptionService(db)

        # Free tier should not have voice booking
        test_clinic.subscription_tier = "free"
        db.commit()

        assert service.check_feature(test_clinic.id, "voice_booking") == False
        assert service.check_feature(test_clinic.id, "sms_reminders") == False

    def test_check_limit_under(self, db: Session, test_clinic):
        """Test checking limit when under limit."""
        service = SubscriptionService(db)

        test_clinic.subscription_tier = "starter"
        db.commit()

        # Starter tier allows 500 patients
        assert service.check_limit(test_clinic.id, "max_patients", 100) == True
        assert service.check_limit(test_clinic.id, "max_patients", 499) == True

    def test_check_limit_over(self, db: Session, test_clinic):
        """Test checking limit when over limit."""
        service = SubscriptionService(db)

        test_clinic.subscription_tier = "free"
        db.commit()

        # Free tier allows 100 patients
        assert service.check_limit(test_clinic.id, "max_patients", 100) == False
        assert service.check_limit(test_clinic.id, "max_patients", 150) == False

    def test_unlimited_limits(self, db: Session, test_clinic):
        """Test unlimited limits for clinic tier."""
        service = SubscriptionService(db)

        test_clinic.subscription_tier = "clinic"
        db.commit()

        # Clinic tier has unlimited (-1)
        assert service.check_limit(test_clinic.id, "max_patients", 10000) == True
        assert service.check_limit(test_clinic.id, "max_doctors", 100) == True


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
