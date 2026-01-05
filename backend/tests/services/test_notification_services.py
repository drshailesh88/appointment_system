"""
Comprehensive tests for Notification Services.

Tests cover:
1. Push Notifications Service (Firebase)
2. Daily Digest Service
3. OTP Service
4. Realtime WebSocket Service
"""
import asyncio
import pytest
from datetime import datetime, date, timedelta, timezone
from unittest.mock import MagicMock, AsyncMock, patch, Mock
from uuid import uuid4, UUID

from firebase_admin import messaging

from app.services.push_notifications import (
    PushNotificationService,
    NotificationType,
    NotificationTemplate,
)
from app.services.daily_digest import DailyDigestService
from app.services.otp_service import OTPService
from app.services.realtime import (
    RealtimeService,
    EventType,
    AppointmentEventData,
    WaitlistEventData,
    NotificationEventData,
    get_realtime_service,
)
from app.models.device_token import DeviceToken, DevicePlatform
from app.models.otp import OTP
from app.models.insight import UserDigestPreferences


# ==============================================================================
# Push Notifications Service Tests
# ==============================================================================


class TestNotificationTemplate:
    """Tests for NotificationTemplate."""

    def test_get_content_appointment_reminder(self):
        """Test getting appointment reminder content."""
        content = NotificationTemplate.get_content(
            NotificationType.APPOINTMENT_REMINDER,
            doctor_name="Dr. Smith",
            appointment_time="2:00 PM",
        )

        assert content["title"] == "Appointment Reminder"
        assert "Dr. Smith" in content["body"]
        assert "2:00 PM" in content["body"]

    def test_get_content_payment_received(self):
        """Test getting payment received content."""
        content = NotificationTemplate.get_content(
            NotificationType.PAYMENT_RECEIVED,
            amount=500,
        )

        assert content["title"] == "Payment Received"
        assert "₹500" in content["body"]

    def test_get_content_missing_variable(self):
        """Test error when template variable is missing."""
        with pytest.raises(ValueError, match="Missing template variable"):
            NotificationTemplate.get_content(
                NotificationType.APPOINTMENT_REMINDER,
                doctor_name="Dr. Smith",
                # Missing appointment_time
            )

    def test_get_content_unknown_type(self):
        """Test error for unknown notification type."""
        with pytest.raises(ValueError, match="Unknown notification type"):
            NotificationTemplate.get_content(
                "invalid_type",
            )


class TestPushNotificationService:
    """Tests for PushNotificationService."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create push notification service with mocks."""
        # Prevent actual Firebase initialization
        with patch.object(PushNotificationService, '_ensure_firebase_initialized'):
            service = PushNotificationService(mock_db)
            service._initialized = True  # Mock as initialized
        return service

    @pytest.mark.asyncio
    async def test_register_device_new_token(self, service, mock_db):
        """Test registering a new device token."""
        user_id = uuid4()
        device_token = "fcm_token_12345"
        platform = DevicePlatform.ANDROID

        # Mock no existing token
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Mock refresh
        mock_db.refresh = AsyncMock()

        token = await service.register_device(
            user_id=user_id,
            device_token=device_token,
            platform=platform,
            device_name="Samsung Galaxy S21",
        )

        # Verify device token was added
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        assert mock_db.refresh.call_count == 1

    @pytest.mark.asyncio
    async def test_register_device_update_existing(self, service, mock_db):
        """Test updating an existing device token."""
        user_id = uuid4()
        device_token = "fcm_token_12345"

        # Mock existing token
        existing_token = MagicMock(spec=DeviceToken)
        existing_token.is_active = False
        existing_token.platform = "ios"
        existing_token.device_name = "Old iPhone"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_token
        mock_db.execute.return_value = mock_result

        # Mock refresh
        mock_db.refresh = AsyncMock()

        token = await service.register_device(
            user_id=user_id,
            device_token=device_token,
            platform=DevicePlatform.ANDROID,
            device_name="Samsung Galaxy S21",
        )

        # Verify token was updated
        assert existing_token.is_active is True
        assert existing_token.platform == "android"
        assert existing_token.device_name == "Samsung Galaxy S21"
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_unregister_device_success(self, service, mock_db):
        """Test unregistering a device token."""
        user_id = uuid4()
        device_token = "fcm_token_12345"

        # Mock existing token
        existing_token = MagicMock(spec=DeviceToken)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_token
        mock_db.execute.return_value = mock_result

        result = await service.unregister_device(user_id, device_token)

        assert result is True
        mock_db.delete.assert_called_once_with(existing_token)
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_unregister_device_not_found(self, service, mock_db):
        """Test unregistering non-existent device token."""
        user_id = uuid4()
        device_token = "fcm_token_12345"

        # Mock no token found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.unregister_device(user_id, device_token)

        assert result is False
        mock_db.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_to_user_success(self, service, mock_db):
        """Test sending notification to user's devices."""
        user_id = uuid4()

        # Mock user's device tokens
        token1 = MagicMock(spec=DeviceToken)
        token1.id = uuid4()
        token1.device_token = "fcm_token_1"
        token1.platform = "android"

        token2 = MagicMock(spec=DeviceToken)
        token2.id = uuid4()
        token2.device_token = "fcm_token_2"
        token2.platform = "ios"

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [token1, token2]
        mock_db.execute.return_value = mock_result

        # Mock FCM send
        with patch.object(service, '_send_to_token', new=AsyncMock()) as mock_send:
            result = await service.send_to_user(
                user_id=user_id,
                notification_type=NotificationType.APPOINTMENT_CONFIRMED,
                doctor_name="Dr. Smith",
                appointment_date="Jan 10, 2026",
            )

        assert result["success"] == 2
        assert result["failed"] == 0
        assert mock_send.call_count == 2

    @pytest.mark.asyncio
    async def test_send_to_user_no_devices(self, service, mock_db):
        """Test sending to user with no registered devices."""
        user_id = uuid4()

        # Mock no device tokens
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = await service.send_to_user(
            user_id=user_id,
            notification_type=NotificationType.APPOINTMENT_CONFIRMED,
            doctor_name="Dr. Smith",
            appointment_date="Jan 10, 2026",
        )

        assert result["success"] == 0
        assert result["failed"] == 0

    @pytest.mark.asyncio
    async def test_send_to_user_with_failures(self, service, mock_db):
        """Test sending to user with some device failures."""
        user_id = uuid4()

        # Mock user's device tokens
        token1 = MagicMock(spec=DeviceToken)
        token1.id = uuid4()
        token1.device_token = "fcm_token_1"
        token1.platform = "android"
        token1.deactivate = MagicMock()

        token2 = MagicMock(spec=DeviceToken)
        token2.id = uuid4()
        token2.device_token = "fcm_token_2"
        token2.platform = "ios"

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [token1, token2]
        mock_db.execute.return_value = mock_result

        # Mock FCM send - first fails, second succeeds
        async def mock_send_side_effect(*args, **kwargs):
            if args[0] == "fcm_token_1":
                raise Exception("Registration token not found")
            # Second call succeeds (no exception)

        with patch.object(service, '_send_to_token', new=AsyncMock(side_effect=mock_send_side_effect)):
            result = await service.send_to_user(
                user_id=user_id,
                notification_type=NotificationType.APPOINTMENT_CONFIRMED,
                doctor_name="Dr. Smith",
                appointment_date="Jan 10, 2026",
            )

        assert result["success"] == 1
        assert result["failed"] == 1
        # Verify token was deactivated
        token1.deactivate.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_to_device_success(self, service, mock_db):
        """Test sending notification to specific device."""
        device_token = "fcm_token_12345"

        with patch.object(service, '_send_to_token', new=AsyncMock()) as mock_send:
            result = await service.send_to_device(
                device_token=device_token,
                notification_type=NotificationType.SLOT_OFFER,
                doctor_name="Dr. Smith",
                slot_time="2:00 PM",
            )

        assert result is True
        mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_to_topic_success(self, service):
        """Test sending notification to a topic."""
        with patch('firebase_admin.messaging.send') as mock_send:
            mock_send.return_value = "message-id-123"

            result = await service.send_to_topic(
                topic="clinic_12345",
                notification_type=NotificationType.GENERAL_ANNOUNCEMENT,
                title="Clinic Closed",
                message="Clinic will be closed on Jan 15",
            )

        assert result is True
        mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_subscribe_to_topic_success(self, service, mock_db):
        """Test subscribing user's devices to topic."""
        user_id = uuid4()
        topic = "clinic_12345"

        # Mock user's tokens
        mock_result = MagicMock()
        mock_result.all.return_value = [
            ("fcm_token_1",),
            ("fcm_token_2",),
        ]
        mock_db.execute.return_value = mock_result

        with patch('firebase_admin.messaging.subscribe_to_topic') as mock_subscribe:
            mock_response = MagicMock()
            mock_response.success_count = 2
            mock_response.failure_count = 0
            mock_subscribe.return_value = mock_response

            result = await service.subscribe_to_topic(user_id, topic)

        assert result["success"] == 2
        assert result["failed"] == 0
        mock_subscribe.assert_called_once()

    @pytest.mark.asyncio
    async def test_firebase_not_initialized(self, mock_db):
        """Test behavior when Firebase is not initialized."""
        with patch.object(PushNotificationService, '_ensure_firebase_initialized'):
            service = PushNotificationService(mock_db)
            service._initialized = False  # Not initialized

        # Should return zero counts without sending
        result = await service.send_to_user(
            user_id=uuid4(),
            notification_type=NotificationType.APPOINTMENT_CONFIRMED,
            doctor_name="Dr. Smith",
            appointment_date="Jan 10",
        )

        assert result["success"] == 0
        assert result["failed"] == 0


# ==============================================================================
# Daily Digest Service Tests
# ==============================================================================


class TestDailyDigestService:
    """Tests for DailyDigestService."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def mock_insights_engine(self):
        """Create mock insights engine."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db, mock_insights_engine):
        """Create daily digest service with mocks."""
        service = DailyDigestService(mock_db)
        service.insights_engine = mock_insights_engine
        return service

    @pytest.mark.asyncio
    async def test_generate_digest_success(self, service, mock_db, mock_insights_engine):
        """Test generating daily digest."""
        clinic_id = uuid4()
        user_id = uuid4()
        target_date = date(2026, 1, 10)

        # Mock user preferences
        prefs = MagicMock(spec=UserDigestPreferences)
        prefs.enabled = True
        prefs.include_followups = True
        prefs.include_schedule_gaps = True
        prefs.include_waitlist = True

        mock_prefs_result = MagicMock()
        mock_prefs_result.scalar_one_or_none.return_value = prefs

        # Mock appointments count
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 15

        # Mock revenue
        mock_revenue_result = MagicMock()
        mock_revenue_result.scalar.return_value = 7500.0

        # Set up execute to return different results
        mock_db.execute.side_effect = [
            mock_prefs_result,  # get_user_preferences
            mock_count_result,  # appointments count
            mock_revenue_result,  # revenue
        ]

        # Mock insights
        mock_insight1 = MagicMock()
        mock_insight1.insight_type = "followup_due"
        mock_insight1.title = "Follow-up needed"

        mock_insight2 = MagicMock()
        mock_insight2.insight_type = "schedule_gap"
        mock_insight2.title = "Schedule gap at 2 PM"

        mock_insights_engine.generate_daily_insights.return_value = [
            mock_insight1,
            mock_insight2,
        ]

        digest = await service.generate_digest(clinic_id, user_id, target_date)

        assert digest.appointments_today == 15
        assert digest.revenue_yesterday == 7500.0
        assert len(digest.pending_followups) == 1
        assert len(digest.schedule_alerts) == 1

    @pytest.mark.asyncio
    async def test_generate_digest_disabled_preferences(self, service, mock_db, mock_insights_engine):
        """Test digest generation with disabled preferences."""
        clinic_id = uuid4()
        user_id = uuid4()

        # Mock user preferences (disabled)
        prefs = MagicMock(spec=UserDigestPreferences)
        prefs.enabled = False

        mock_prefs_result = MagicMock()
        mock_prefs_result.scalar_one_or_none.return_value = prefs

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 10

        mock_revenue_result = MagicMock()
        mock_revenue_result.scalar.return_value = 5000.0

        mock_db.execute.side_effect = [
            mock_prefs_result,
            mock_count_result,
            mock_revenue_result,
        ]

        # Mock insights
        mock_insight = MagicMock()
        mock_insight.insight_type = "followup_due"
        mock_insights_engine.generate_daily_insights.return_value = [mock_insight]

        digest = await service.generate_digest(clinic_id, user_id)

        # Should still generate digest but filter based on preferences
        assert digest.appointments_today == 10
        assert len(digest.pending_followups) == 0  # Filtered out

    @pytest.mark.asyncio
    async def test_get_user_preferences(self, service, mock_db):
        """Test getting user preferences."""
        user_id = uuid4()

        # Mock preferences
        prefs = MagicMock(spec=UserDigestPreferences)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = prefs
        mock_db.execute.return_value = mock_result

        result = await service.get_user_preferences(user_id)

        assert result == prefs

    @pytest.mark.asyncio
    async def test_create_preferences(self, service, mock_db):
        """Test creating new preferences."""
        user_id = uuid4()
        clinic_id = uuid4()

        # Mock no existing preferences
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        mock_db.refresh = AsyncMock()

        prefs = await service.create_or_update_preferences(
            user_id=user_id,
            clinic_id=clinic_id,
            enabled=True,
            delivery_hour=8,
            channels=["push", "email"],
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_preferences(self, service, mock_db):
        """Test updating existing preferences."""
        user_id = uuid4()
        clinic_id = uuid4()

        # Mock existing preferences
        existing_prefs = MagicMock(spec=UserDigestPreferences)
        existing_prefs.enabled = True
        existing_prefs.delivery_hour = 8

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_prefs
        mock_db.execute.return_value = mock_result

        mock_db.refresh = AsyncMock()

        prefs = await service.create_or_update_preferences(
            user_id=user_id,
            clinic_id=clinic_id,
            delivery_hour=9,  # Changed
        )

        assert existing_prefs.delivery_hour == 9
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_schedule_digest(self, service, mock_db):
        """Test scheduling daily digest."""
        user_id = uuid4()
        clinic_id = uuid4()

        # Mock no existing preferences
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        mock_db.refresh = AsyncMock()

        prefs = await service.schedule_digest(
            clinic_id=clinic_id,
            user_id=user_id,
            delivery_hour=9,
            delivery_minute=30,
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_digest_enabled(self, service, mock_db, mock_insights_engine):
        """Test sending digest when enabled."""
        clinic_id = uuid4()
        user_id = uuid4()

        # Mock preferences (enabled)
        prefs = MagicMock(spec=UserDigestPreferences)
        prefs.enabled = True
        prefs.channels = ["push"]

        mock_prefs_result = MagicMock()
        mock_prefs_result.scalar_one_or_none.return_value = prefs

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 10

        mock_revenue_result = MagicMock()
        mock_revenue_result.scalar.return_value = 5000.0

        mock_db.execute.side_effect = [
            mock_prefs_result,  # get_user_preferences
            mock_prefs_result,  # generate_digest -> get_user_preferences
            mock_count_result,  # appointments
            mock_revenue_result,  # revenue
        ]

        mock_insights_engine.generate_daily_insights.return_value = []

        with patch.object(service, '_send_push_notification', new=AsyncMock()) as mock_push:
            await service.send_digest(clinic_id, user_id)

        mock_push.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_digest_disabled(self, service, mock_db):
        """Test sending digest when disabled."""
        clinic_id = uuid4()
        user_id = uuid4()

        # Mock preferences (disabled)
        prefs = MagicMock(spec=UserDigestPreferences)
        prefs.enabled = False

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = prefs
        mock_db.execute.return_value = mock_result

        with patch.object(service, '_send_push_notification', new=AsyncMock()) as mock_push:
            await service.send_digest(clinic_id, user_id)

        # Should not send
        mock_push.assert_not_called()

    def test_format_digest_message(self, service):
        """Test formatting digest message."""
        from app.schemas.insights import DailyDigest

        mock_insight = MagicMock()
        mock_insight.title = "Important follow-up"

        digest = DailyDigest(
            date=datetime(2026, 1, 10),
            appointments_today=15,
            revenue_yesterday=7500.0,
            pending_followups=[mock_insight],
            schedule_alerts=[],
            waitlist_opportunities=[],
            key_insights=[mock_insight],
        )

        message = service._format_digest_message(digest)

        assert "Appointments Today: 15" in message
        assert "₹7,500" in message
        assert "Follow-ups Due" in message
        assert "Important follow-up" in message


# ==============================================================================
# OTP Service Tests
# ==============================================================================


class TestOTPService:
    """Tests for OTPService."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        """Create OTP service."""
        return OTPService(mock_db)

    def test_generate_otp(self, service):
        """Test OTP generation."""
        otp = service.generate_otp()

        assert len(otp) == 6
        assert otp.isdigit()
        assert 0 <= int(otp) <= 999999

    def test_generate_otp_uniqueness(self, service):
        """Test that OTPs are reasonably unique."""
        otps = [service.generate_otp() for _ in range(100)]

        # Should have at least 90% unique values
        unique_otps = set(otps)
        assert len(unique_otps) >= 90

    @pytest.mark.asyncio
    async def test_send_otp_success(self, service, mock_db):
        """Test sending OTP."""
        phone = "+919876543210"

        # Mock no existing OTPs
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        mock_db.refresh = AsyncMock()

        otp = await service.send_otp(phone)

        assert otp is not None
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_otp_invalidates_existing(self, service, mock_db):
        """Test that sending OTP invalidates existing OTPs."""
        phone = "+919876543210"

        # Mock existing OTP
        existing_otp = MagicMock(spec=OTP)
        existing_otp.is_verified = False

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [existing_otp]
        mock_db.execute.return_value = mock_result

        mock_db.refresh = AsyncMock()

        await service.send_otp(phone)

        # Existing OTP should be marked as verified (invalidated)
        assert existing_otp.is_verified is True

    @pytest.mark.asyncio
    async def test_verify_otp_success(self, service, mock_db):
        """Test successful OTP verification."""
        phone = "+919876543210"
        otp_code = "123456"

        # Mock valid OTP
        mock_otp = MagicMock(spec=OTP)
        mock_otp.phone = phone
        mock_otp.otp_code = otp_code
        mock_otp.is_verified = False
        mock_otp.attempts = 0
        mock_otp.is_valid.return_value = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_otp
        mock_db.execute.return_value = mock_result

        token = await service.verify_otp(phone, otp_code)

        assert token is not None
        assert isinstance(token, str)
        assert mock_otp.attempts == 1
        assert mock_otp.is_verified is True

    @pytest.mark.asyncio
    async def test_verify_otp_not_found(self, service, mock_db):
        """Test verifying non-existent OTP."""
        phone = "+919876543210"
        otp_code = "123456"

        # Mock no OTP found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        token = await service.verify_otp(phone, otp_code)

        assert token is None

    @pytest.mark.asyncio
    async def test_verify_otp_expired(self, service, mock_db):
        """Test verifying expired OTP."""
        phone = "+919876543210"
        otp_code = "123456"

        # Mock expired OTP
        mock_otp = MagicMock(spec=OTP)
        mock_otp.phone = phone
        mock_otp.otp_code = otp_code
        mock_otp.is_verified = False
        mock_otp.attempts = 0
        mock_otp.is_valid.return_value = False  # Expired

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_otp
        mock_db.execute.return_value = mock_result

        token = await service.verify_otp(phone, otp_code)

        assert token is None
        assert mock_otp.attempts == 1

    @pytest.mark.asyncio
    async def test_verify_otp_max_attempts(self, service, mock_db):
        """Test OTP verification with max attempts exceeded."""
        phone = "+919876543210"
        otp_code = "123456"

        # Mock OTP with max attempts
        mock_otp = MagicMock(spec=OTP)
        mock_otp.phone = phone
        mock_otp.otp_code = otp_code
        mock_otp.is_verified = False
        mock_otp.attempts = 2  # Will be 3 after increment
        mock_otp.is_valid.return_value = False  # Max attempts

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_otp
        mock_db.execute.return_value = mock_result

        token = await service.verify_otp(phone, otp_code)

        assert token is None

    def test_create_access_token(self, service):
        """Test JWT token creation."""
        phone = "+919876543210"

        token = service.create_access_token(phone)

        assert token is not None
        assert isinstance(token, str)

    def test_decode_token_success(self, service):
        """Test decoding valid JWT token."""
        phone = "+919876543210"

        token = service.create_access_token(phone)
        decoded_phone = service.decode_token(token)

        assert decoded_phone == phone

    def test_decode_token_invalid(self, service):
        """Test decoding invalid JWT token."""
        invalid_token = "invalid.token.here"

        decoded_phone = service.decode_token(invalid_token)

        assert decoded_phone is None

    def test_decode_token_wrong_type(self, service):
        """Test decoding token with wrong type."""
        from jose import jwt
        from app.core.config import settings

        # Create token with wrong type
        token = jwt.encode(
            {"sub": "+919876543210", "type": "wrong_type"},
            settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
        )

        decoded_phone = service.decode_token(token)

        assert decoded_phone is None

    def test_otp_expiry_time(self, service):
        """Test OTP expiry time is correct."""
        assert service.OTP_EXPIRY_MINUTES == 10

    def test_token_expiry_time(self, service):
        """Test token expiry time is correct."""
        assert service.TOKEN_EXPIRY_HOURS == 24


# ==============================================================================
# Realtime Service Tests
# ==============================================================================


class TestRealtimeService:
    """Tests for RealtimeService."""

    @pytest.fixture
    def service(self):
        """Create realtime service."""
        return RealtimeService()

    @pytest.fixture
    def mock_connection_manager(self):
        """Create mock connection manager."""
        manager = AsyncMock()
        manager.broadcast_to_clinic = AsyncMock()
        manager.broadcast_to_all = AsyncMock()
        return manager

    @pytest.mark.asyncio
    async def test_set_connection_manager(self, service, mock_connection_manager):
        """Test setting connection manager."""
        service.set_connection_manager(mock_connection_manager)

        assert service._connection_manager == mock_connection_manager

    @pytest.mark.asyncio
    async def test_publish_appointment_event(self, service, mock_connection_manager):
        """Test publishing appointment event."""
        service.set_connection_manager(mock_connection_manager)

        clinic_id = uuid4()
        appointment_data = AppointmentEventData(
            appointment_id=uuid4(),
            patient_id=uuid4(),
            patient_name="Test Patient",
            doctor_id=uuid4(),
            doctor_name="Dr. Smith",
            scheduled_start=datetime.now(),
            scheduled_end=datetime.now() + timedelta(minutes=30),
            status="confirmed",
            token_number=5,
        )

        await service.publish_appointment_event(
            event_type=EventType.APPOINTMENT_CONFIRMED,
            clinic_id=clinic_id,
            appointment_data=appointment_data,
        )

        mock_connection_manager.broadcast_to_clinic.assert_called_once()
        call_args = mock_connection_manager.broadcast_to_clinic.call_args
        assert call_args[1]["clinic_id"] == clinic_id
        assert "message" in call_args[1]

    @pytest.mark.asyncio
    async def test_publish_waitlist_event(self, service, mock_connection_manager):
        """Test publishing waitlist event."""
        service.set_connection_manager(mock_connection_manager)

        clinic_id = uuid4()
        waitlist_data = WaitlistEventData(
            waitlist_id=uuid4(),
            patient_name="Test Patient",
            patient_phone="+919876543210",
            priority="high",
            status="waiting",
            queue_position=3,
            preferred_date="2026-01-10",
        )

        await service.publish_waitlist_event(
            event_type=EventType.WAITLIST_JOINED,
            clinic_id=clinic_id,
            waitlist_data=waitlist_data,
        )

        mock_connection_manager.broadcast_to_clinic.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_notification_event(self, service, mock_connection_manager):
        """Test publishing notification event."""
        service.set_connection_manager(mock_connection_manager)

        clinic_id = uuid4()
        notification_data = NotificationEventData(
            notification_id="notif_123",
            title="Test Notification",
            message="This is a test",
            priority="high",
        )

        await service.publish_notification_event(
            event_type=EventType.NOTIFICATION_NEW,
            clinic_id=clinic_id,
            notification_data=notification_data,
        )

        mock_connection_manager.broadcast_to_clinic.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_system_event_to_clinic(self, service, mock_connection_manager):
        """Test publishing system event to specific clinic."""
        service.set_connection_manager(mock_connection_manager)

        clinic_id = uuid4()

        await service.publish_system_event(
            event_type=EventType.SYSTEM_MAINTENANCE,
            message="System maintenance at 2 AM",
            clinic_id=clinic_id,
            metadata={"severity": "warning"},
        )

        mock_connection_manager.broadcast_to_clinic.assert_called_once()
        mock_connection_manager.broadcast_to_all.assert_not_called()

    @pytest.mark.asyncio
    async def test_publish_system_event_to_all(self, service, mock_connection_manager):
        """Test publishing system event to all clinics."""
        service.set_connection_manager(mock_connection_manager)

        await service.publish_system_event(
            event_type=EventType.SYSTEM_UPDATE,
            message="New version available",
            clinic_id=None,  # Broadcast to all
        )

        mock_connection_manager.broadcast_to_all.assert_called_once()
        mock_connection_manager.broadcast_to_clinic.assert_not_called()

    @pytest.mark.asyncio
    async def test_publish_without_connection_manager(self, service):
        """Test publishing without connection manager (should not error)."""
        # No connection manager set

        await service.publish_appointment_event(
            event_type=EventType.APPOINTMENT_CREATED,
            clinic_id=uuid4(),
            appointment_data=AppointmentEventData(
                appointment_id=uuid4(),
                patient_id=uuid4(),
                patient_name="Test",
                doctor_id=uuid4(),
                doctor_name="Dr. Test",
                scheduled_start=datetime.now(),
                scheduled_end=datetime.now(),
                status="scheduled",
            ),
        )

        # Should not raise an error

    def test_get_realtime_service_singleton(self):
        """Test that get_realtime_service returns singleton."""
        service1 = get_realtime_service()
        service2 = get_realtime_service()

        assert service1 is service2


# ==============================================================================
# WebSocket Connection Manager Tests
# ==============================================================================


class TestConnectionManager:
    """Tests for ConnectionManager."""

    @pytest.fixture
    def manager(self):
        """Create connection manager."""
        from app.api.v1.websocket import ConnectionManager
        return ConnectionManager()

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket."""
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        ws.receive_text = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_connect(self, manager, mock_websocket):
        """Test connecting a WebSocket."""
        clinic_id = uuid4()
        user_id = uuid4()
        connection_id = "conn_123"

        await manager.connect(mock_websocket, clinic_id, user_id, connection_id)

        mock_websocket.accept.assert_called_once()
        assert clinic_id in manager.active_connections
        assert connection_id in manager.active_connections[clinic_id]
        assert connection_id in manager.heartbeat_tasks

    @pytest.mark.asyncio
    async def test_disconnect(self, manager, mock_websocket):
        """Test disconnecting a WebSocket."""
        clinic_id = uuid4()
        user_id = uuid4()
        connection_id = "conn_123"

        # Connect first
        await manager.connect(mock_websocket, clinic_id, user_id, connection_id)

        # Then disconnect
        await manager.disconnect(clinic_id, connection_id)

        assert connection_id not in manager.active_connections.get(clinic_id, {})

    @pytest.mark.asyncio
    async def test_broadcast_to_clinic(self, manager, mock_websocket):
        """Test broadcasting to clinic."""
        clinic_id = uuid4()
        user_id = uuid4()
        connection_id = "conn_123"

        # Connect WebSocket
        await manager.connect(mock_websocket, clinic_id, user_id, connection_id)

        # Broadcast message
        message = {"event": "test", "data": "hello"}
        await manager.broadcast_to_clinic(clinic_id, message)

        # Should have sent welcome message + broadcast message
        assert mock_websocket.send_json.call_count >= 2

    @pytest.mark.asyncio
    async def test_broadcast_to_all(self, manager, mock_websocket):
        """Test broadcasting to all clinics."""
        clinic1_id = uuid4()
        clinic2_id = uuid4()
        user_id = uuid4()

        # Connect to multiple clinics
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws1.send_json = AsyncMock()
        await manager.connect(ws1, clinic1_id, user_id, "conn_1")

        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock()
        await manager.connect(ws2, clinic2_id, user_id, "conn_2")

        # Broadcast to all
        message = {"event": "test", "data": "hello"}
        await manager.broadcast_to_all(message)

        # Both should receive the message (plus welcome messages)
        assert ws1.send_json.call_count >= 2
        assert ws2.send_json.call_count >= 2

    @pytest.mark.asyncio
    async def test_send_to_user(self, manager):
        """Test sending message to specific user."""
        clinic_id = uuid4()
        user_id = uuid4()
        other_user_id = uuid4()

        # Connect user's devices
        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws1.send_json = AsyncMock()
        await manager.connect(ws1, clinic_id, user_id, "conn_1")

        ws2 = AsyncMock()
        ws2.accept = AsyncMock()
        ws2.send_json = AsyncMock()
        await manager.connect(ws2, clinic_id, user_id, "conn_2")

        # Connect other user
        ws3 = AsyncMock()
        ws3.accept = AsyncMock()
        ws3.send_json = AsyncMock()
        await manager.connect(ws3, clinic_id, other_user_id, "conn_3")

        # Send to specific user
        message = {"event": "test"}
        await manager.send_to_user(user_id, clinic_id, message)

        # Only user_id's connections should receive (plus welcome messages)
        assert ws1.send_json.call_count >= 2
        assert ws2.send_json.call_count >= 2
        # Other user should only have welcome message
        assert ws3.send_json.call_count == 1

    def test_get_connection_count(self, manager):
        """Test getting connection count."""
        # Initially zero
        assert manager.get_connection_count() == 0

    @pytest.mark.asyncio
    async def test_heartbeat_cancelled_on_disconnect(self, manager, mock_websocket):
        """Test that heartbeat task is cancelled on disconnect."""
        clinic_id = uuid4()
        user_id = uuid4()
        connection_id = "conn_123"

        # Connect
        await manager.connect(mock_websocket, clinic_id, user_id, connection_id)

        # Get heartbeat task
        task = manager.heartbeat_tasks[connection_id]
        assert not task.done()

        # Disconnect
        await manager.disconnect(clinic_id, connection_id)

        # Task should be cancelled
        await asyncio.sleep(0.1)  # Give time for cancellation
        assert task.cancelled()


# ==============================================================================
# Integration Tests
# ==============================================================================


class TestNotificationServicesIntegration:
    """Integration tests for notification services working together."""

    @pytest.mark.asyncio
    async def test_digest_with_push_notifications(self):
        """Test daily digest triggering push notifications."""
        mock_db = AsyncMock()

        # Create digest service
        digest_service = DailyDigestService(mock_db)

        # Create push notification service
        with patch.object(PushNotificationService, '_ensure_firebase_initialized'):
            push_service = PushNotificationService(mock_db)
            push_service._initialized = True

        # Mock user preferences
        prefs = MagicMock(spec=UserDigestPreferences)
        prefs.enabled = True
        prefs.channels = ["push"]

        mock_prefs_result = MagicMock()
        mock_prefs_result.scalar_one_or_none.return_value = prefs

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 10

        mock_revenue_result = MagicMock()
        mock_revenue_result.scalar.return_value = 5000.0

        mock_db.execute.side_effect = [
            mock_prefs_result,
            mock_prefs_result,
            mock_count_result,
            mock_revenue_result,
        ]

        digest_service.insights_engine.generate_daily_insights = AsyncMock(return_value=[])

        # Should not raise errors
        await digest_service.send_digest(uuid4(), uuid4())

    @pytest.mark.asyncio
    async def test_realtime_appointment_notification(self):
        """Test realtime notification for appointment update."""
        realtime_service = RealtimeService()

        # Mock connection manager
        mock_manager = AsyncMock()
        mock_manager.broadcast_to_clinic = AsyncMock()
        realtime_service.set_connection_manager(mock_manager)

        # Publish appointment event
        clinic_id = uuid4()
        appointment_data = AppointmentEventData(
            appointment_id=uuid4(),
            patient_id=uuid4(),
            patient_name="Test Patient",
            doctor_id=uuid4(),
            doctor_name="Dr. Smith",
            scheduled_start=datetime.now(),
            scheduled_end=datetime.now() + timedelta(minutes=30),
            status="confirmed",
        )

        await realtime_service.publish_appointment_event(
            EventType.APPOINTMENT_CONFIRMED,
            clinic_id,
            appointment_data,
        )

        # Verify broadcast was called
        mock_manager.broadcast_to_clinic.assert_called_once()
        call_args = mock_manager.broadcast_to_clinic.call_args
        assert call_args[1]["clinic_id"] == clinic_id

        # Verify message structure
        message = call_args[1]["message"]
        assert message["event_type"] == EventType.APPOINTMENT_CONFIRMED.value
        assert "timestamp" in message
        assert "data" in message
