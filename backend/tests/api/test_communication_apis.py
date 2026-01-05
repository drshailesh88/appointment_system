"""
Integration tests for communication API endpoints.

Tests cover:
- Notifications API (push notifications, device management)
- WhatsApp API (webhook, messaging, reminders)
- Voice API (STT, TTS, voice agent sessions)
- Voice Bot API (Twilio webhooks, WebSocket, call management)
"""
import base64
import json
from datetime import datetime, timedelta
from io import BytesIO
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import WebSocket
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device_token import DevicePlatform, DeviceToken
from app.models.phone_call import CallStatus, CallTranscriptSegment, PhoneCall
from app.models.waitlist import Waitlist
from sqlalchemy import select


# ============================================================================
# NOTIFICATIONS API TESTS
# ============================================================================


class TestNotificationsAPI:
    """Test push notification endpoints."""

    @pytest.mark.asyncio

    async def test_register_device_token(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db: AsyncSession,
    ):
        """Test registering a device token for push notifications."""
        response = await client.post(
            "/api/v1/notifications/register",
            headers=auth_headers,
            json={
                "device_token": "test_fcm_token_12345",
                "platform": "android",
                "device_name": "Pixel 7",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["device_token"] == "test_fcm_token_12345"
        assert data["platform"] == "android"
        assert data["device_name"] == "Pixel 7"
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio

    async def test_register_device_token_duplicate(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user,
        db: AsyncSession,
    ):
        """Test registering same device token updates existing record."""
        # First registration
        response1 = await client.post(
            "/api/v1/notifications/register",
            headers=auth_headers,
            json={
                "device_token": "duplicate_token_123",
                "platform": "ios",
            },
        )
        assert response1.status_code == 201

        # Second registration with same token
        response2 = await client.post(
            "/api/v1/notifications/register",
            headers=auth_headers,
            json={
                "device_token": "duplicate_token_123",
                "platform": "ios",
                "device_name": "iPhone 15",
            },
        )
        assert response2.status_code == 201

        # Should update device name
        data = response2.json()
        assert data["device_name"] == "iPhone 15"

    @pytest.mark.asyncio

    async def test_register_device_token_invalid_platform(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test registering device with invalid platform."""
        response = await client.post(
            "/api/v1/notifications/register",
            headers=auth_headers,
            json={
                "device_token": "test_token",
                "platform": "windows",  # Invalid
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio

    async def test_register_device_token_short_token(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test validation for token length."""
        response = await client.post(
            "/api/v1/notifications/register",
            headers=auth_headers,
            json={
                "device_token": "short",  # Too short (< 10 chars)
                "platform": "android",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio

    async def test_unregister_device_token(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user,
        db: AsyncSession,
    ):
        """Test unregistering a device token."""
        # Register first
        register_response = await client.post(
            "/api/v1/notifications/register",
            headers=auth_headers,
            json={
                "device_token": "token_to_unregister",
                "platform": "android",
            },
        )
        assert register_response.status_code == 201

        # Unregister
        response = await client.delete(
            "/api/v1/notifications/unregister",
            headers=auth_headers,
            params={"device_token": "token_to_unregister"},
        )
        assert response.status_code == 204

    @pytest.mark.asyncio

    async def test_unregister_nonexistent_token(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test unregistering non-existent token returns 404."""
        response = await client.delete(
            "/api/v1/notifications/unregister",
            headers=auth_headers,
            params={"device_token": "nonexistent_token_123"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio

    async def test_get_my_devices(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user,
        db: AsyncSession,
    ):
        """Test getting all registered devices for current user."""
        # Register multiple devices
        await client.post(
            "/api/v1/notifications/register",
            headers=auth_headers,
            json={"device_token": "device1", "platform": "android"},
        )
        await client.post(
            "/api/v1/notifications/register",
            headers=auth_headers,
            json={"device_token": "device2", "platform": "ios"},
        )

        # Get devices
        response = await client.get(
            "/api/v1/notifications/devices",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        assert all(d["is_active"] for d in data)

    @pytest.mark.asyncio

    async def test_get_my_devices_include_inactive(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user,
        db: AsyncSession,
    ):
        """Test getting devices including inactive ones."""
        # Register a device
        response = await client.post(
            "/api/v1/notifications/register",
            headers=auth_headers,
            json={"device_token": "device_active", "platform": "android"},
        )
        device_id = response.json()["id"]

        # Manually mark as inactive
        result = await db.execute(select(DeviceToken).where(DeviceToken.id == device_id))
        token = result.scalar_one_or_none()
        token.is_active = False
        await db.commit()

        # Get only active (default)
        response_active = await client.get(
            "/api/v1/notifications/devices",
            headers=auth_headers,
            params={"active_only": True},
        )
        assert response_active.status_code == 200
        active_devices = response_active.json()
        assert len(active_devices) == 0

        # Get all devices
        response_all = await client.get(
            "/api/v1/notifications/devices",
            headers=auth_headers,
            params={"active_only": False},
        )
        assert response_all.status_code == 200
        all_devices = response_all.json()
        assert len(all_devices) >= 1

    @pytest.mark.asyncio

    async def test_remove_device_by_id(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user,
        db: AsyncSession,
    ):
        """Test removing a specific device by ID."""
        # Register device
        register_response = await client.post(
            "/api/v1/notifications/register",
            headers=auth_headers,
            json={"device_token": "device_to_remove", "platform": "android"},
        )
        device_id = register_response.json()["id"]

        # Remove device
        response = await client.delete(
            f"/api/v1/notifications/devices/{device_id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

        # Verify removed
        verify_response = await client.get(
            "/api/v1/notifications/devices",
            headers=auth_headers,
            params={"active_only": False},
        )
        devices = verify_response.json()
        device_ids = [d["id"] for d in devices]
        assert device_id not in device_ids

    @pytest.mark.asyncio

    async def test_remove_device_not_owned(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user,
        db: AsyncSession,
    ):
        """Test cannot remove device belonging to another user."""
        # Create another user's device
        other_user_id = uuid4()
        device = DeviceToken(
            id=uuid4(),
            user_id=other_user_id,
            device_token="other_user_device",
            platform=DevicePlatform.ANDROID,
        )
        db.add(device)
        await db.commit()

        # Try to remove other user's device
        response = await client.delete(
            f"/api/v1/notifications/devices/{device.id}",
            headers=auth_headers,
        )
        assert response.status_code == 403

    @pytest.mark.asyncio

    async def test_remove_nonexistent_device(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test removing non-existent device returns 404."""
        fake_device_id = uuid4()
        response = await client.delete(
            f"/api/v1/notifications/devices/{fake_device_id}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @patch("app.services.push_notifications.PushNotificationService.send_to_user")
    @pytest.mark.asyncio
    async def test_send_notification_to_self(
        self,
        mock_send: AsyncMock,
        client: AsyncClient,
        auth_headers: dict,
        test_user,
    ):
        """Test sending notification to self."""
        mock_send.return_value = {"success": 1, "failed": 0}

        response = await client.post(
            "/api/v1/notifications/send",
            headers=auth_headers,
            json={
                "user_id": str(test_user.id),
                "notification_type": "appointment_reminder",
                "template_vars": {"doctor_name": "Dr. Smith", "time": "3:00 PM"},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 1
        assert data["failed_count"] == 0

    @patch("app.services.push_notifications.PushNotificationService.send_to_user")
    @pytest.mark.asyncio
    async def test_send_notification_to_other_non_admin(
        self,
        mock_send: AsyncMock,
        client: AsyncClient,
        auth_headers: dict,
        test_user,
        db: AsyncSession,
    ):
        """Test non-admin cannot send notifications to other users."""
        # Change user role to staff
        result = await db.execute(select(type(test_user)).filter_by(id=test_user.id))
        user = result.scalar_one_or_none()
        user.role = "staff"
        await db.commit()

        other_user_id = uuid4()
        response = await client.post(
            "/api/v1/notifications/send",
            headers=auth_headers,
            json={
                "user_id": str(other_user_id),
                "notification_type": "appointment_reminder",
            },
        )
        assert response.status_code == 403

    @patch("app.services.push_notifications.PushNotificationService.subscribe_to_topic")
    @pytest.mark.asyncio
    async def test_subscribe_to_topic(
        self,
        mock_subscribe: AsyncMock,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test subscribing to notification topic."""
        mock_subscribe.return_value = {"success": 1, "failed": 0}

        response = await client.post(
            "/api/v1/notifications/topics/subscribe",
            headers=auth_headers,
            json={"topic": "clinic_12345"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "Subscribed to topic" in data["message"]
        assert data["success_count"] == 1

    @patch("app.services.push_notifications.PushNotificationService.unsubscribe_from_topic")
    @pytest.mark.asyncio
    async def test_unsubscribe_from_topic(
        self,
        mock_unsubscribe: AsyncMock,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test unsubscribing from notification topic."""
        mock_unsubscribe.return_value = {"success": 1, "failed": 0}

        response = await client.post(
            "/api/v1/notifications/topics/unsubscribe",
            headers=auth_headers,
            json={"topic": "clinic_12345"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "Unsubscribed from topic" in data["message"]

    @pytest.mark.asyncio

    async def test_test_notification_system(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test checking Firebase configuration status."""
        response = await client.get(
            "/api/v1/notifications/test",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "firebase_configured" in data
        assert "message" in data


# ============================================================================
# WHATSAPP API TESTS
# ============================================================================


class TestWhatsAppAPI:
    """Test WhatsApp bot endpoints."""

    @patch("app.integrations.whatsapp_bot.WhatsAppBot.verify_webhook")
    @pytest.mark.asyncio
    async def test_verify_webhook(
        self,
        mock_verify: MagicMock,
        client: AsyncClient,
    ):
        """Test WhatsApp webhook verification."""
        mock_verify.return_value = "1234567890"

        response = await client.get(
            "/api/v1/whatsapp/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "test_token",
                "hub.challenge": "1234567890",
            },
        )
        assert response.status_code == 200
        assert response.json() == 1234567890

    @patch("app.integrations.whatsapp_bot.WhatsAppBot.verify_webhook")
    @pytest.mark.asyncio
    async def test_verify_webhook_invalid_token(
        self,
        mock_verify: MagicMock,
        client: AsyncClient,
    ):
        """Test webhook verification with invalid token."""
        mock_verify.return_value = None

        response = await client.get(
            "/api/v1/whatsapp/webhook",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong_token",
                "hub.challenge": "1234567890",
            },
        )
        assert response.status_code == 403

    @patch("app.integrations.whatsapp_bot.WhatsAppBot.parse_webhook")
    @patch("app.integrations.whatsapp_bot.WhatsAppBot.handle_message")
    @patch("app.integrations.whatsapp_bot.WhatsAppBot.send_message")
    @pytest.mark.asyncio
    async def test_receive_webhook_message(
        self,
        mock_send: AsyncMock,
        mock_handle: AsyncMock,
        mock_parse: MagicMock,
        client: AsyncClient,
        test_patient,
        db: AsyncSession,
    ):
        """Test receiving incoming WhatsApp message."""
        # Mock parsed message
        mock_message = Mock()
        mock_message.from_phone = test_patient.phone
        mock_message.text = "Book appointment"
        mock_parse.return_value = mock_message

        mock_handle.return_value = "Sure! I can help you book an appointment."
        mock_send.return_value = True

        response = await client.post(
            "/api/v1/whatsapp/webhook",
            json={
                "object": "whatsapp_business_account",
                "entry": [
                    {
                        "changes": [
                            {
                                "value": {
                                    "messages": [
                                        {
                                            "from": test_patient.phone,
                                            "text": {"body": "Book appointment"},
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                ],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processed"

    @pytest.mark.asyncio

    async def test_receive_webhook_non_whatsapp(
        self,
        client: AsyncClient,
    ):
        """Test webhook ignores non-WhatsApp messages."""
        response = await client.post(
            "/api/v1/whatsapp/webhook",
            json={
                "object": "instagram",
                "entry": [],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ignored"

    @patch("app.integrations.whatsapp_bot.WhatsAppBot.send_message")
    @pytest.mark.asyncio
    async def test_send_message(
        self,
        mock_send: AsyncMock,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test sending WhatsApp message manually."""
        mock_send.return_value = True

        response = await client.post(
            "/api/v1/whatsapp/send",
            headers=auth_headers,
            params={
                "to_phone": "+919876543210",
                "message": "Hello from clinic!",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio

    async def test_send_message_unauthorized(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user,
        db: AsyncSession,
    ):
        """Test only staff/admin can send messages."""
        # Change user role to patient
        result = await db.execute(select(type(test_user)).filter_by(id=test_user.id))
        user = result.scalar_one_or_none()
        user.role = "patient"
        await db.commit()

        response = await client.post(
            "/api/v1/whatsapp/send",
            headers=auth_headers,
            params={
                "to_phone": "+919876543210",
                "message": "Test",
            },
        )
        assert response.status_code == 403

    @patch("app.integrations.whatsapp_bot.WhatsAppBot.send_interactive_buttons")
    @pytest.mark.asyncio
    async def test_send_buttons(
        self,
        mock_send_buttons: AsyncMock,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test sending interactive buttons."""
        mock_send_buttons.return_value = True

        response = await client.post(
            "/api/v1/whatsapp/send-buttons",
            headers=auth_headers,
            params={
                "to_phone": "+919876543210",
                "body": "Choose an option:",
                "buttons": '[{"id": "1", "title": "Book"}, {"id": "2", "title": "Cancel"}]',
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio

    async def test_send_buttons_too_many(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test sending more than 3 buttons returns error."""
        response = await client.post(
            "/api/v1/whatsapp/send-buttons",
            headers=auth_headers,
            params={
                "to_phone": "+919876543210",
                "body": "Choose:",
                "buttons": '[{"id": "1", "title": "Button 1"}, {"id": "2", "title": "Button 2"}, {"id": "3", "title": "Button 3"}, {"id": "4", "title": "Button 4"}]',
            },
        )
        assert response.status_code == 400

    @patch("app.integrations.whatsapp_bot.WhatsAppBot.send_message")
    @pytest.mark.asyncio
    async def test_send_appointment_reminder(
        self,
        mock_send: AsyncMock,
        client: AsyncClient,
        auth_headers: dict,
        test_appointment,
        test_patient,
    ):
        """Test sending appointment reminder via WhatsApp."""
        mock_send.return_value = True

        response = await client.post(
            "/api/v1/whatsapp/send-appointment-reminder",
            headers=auth_headers,
            params={"appointment_id": str(test_appointment.id)},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["patient"] == test_patient.full_name
        assert data["phone"] == test_patient.phone

    @pytest.mark.asyncio

    async def test_send_appointment_reminder_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test sending reminder for non-existent appointment."""
        fake_id = uuid4()
        response = await client.post(
            "/api/v1/whatsapp/send-appointment-reminder",
            headers=auth_headers,
            params={"appointment_id": str(fake_id)},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio

    @pytest.mark.skip(reason="Patient phone is NOT NULL in database schema")
    async def test_send_appointment_reminder_no_phone(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_appointment,
        test_patient,
        db: AsyncSession,
    ):
        """Test sending reminder when patient has no phone."""
        # NOTE: This test is skipped because the patient.phone field has a NOT NULL constraint
        # Remove patient phone
        result = await db.execute(select(type(test_patient)).filter_by(id=test_patient.id))
        patient = result.scalar_one_or_none()
        patient.phone = None
        await db.commit()

        response = await client.post(
            "/api/v1/whatsapp/send-appointment-reminder",
            headers=auth_headers,
            params={"appointment_id": str(test_appointment.id)},
        )
        assert response.status_code == 400

    @patch("app.integrations.whatsapp_bot.WhatsAppBot.send_message")
    @pytest.mark.asyncio
    async def test_send_waitlist_notification(
        self,
        mock_send: AsyncMock,
        client: AsyncClient,
        auth_headers: dict,
        test_clinic,
        test_doctor,
        db: AsyncSession,
    ):
        """Test sending waitlist slot notification."""
        mock_send.return_value = True

        # Create waitlist entry
        waitlist = Waitlist(
            id=uuid4(),
            clinic_id=test_clinic.id,
            doctor_id=test_doctor.id,
            patient_name="Test Patient",
            patient_phone="+919876543210",
            preferred_date=datetime.now().date(),
            priority="normal",
            status="waiting",
        )
        db.add(waitlist)
        await db.commit()

        response = await client.post(
            "/api/v1/whatsapp/send-waitlist-notification",
            headers=auth_headers,
            params={
                "waitlist_id": str(waitlist.id),
                "slot_time": "3:00 PM",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["patient"] == "Test Patient"


# ============================================================================
# VOICE API TESTS
# ============================================================================


class TestVoiceAPI:
    """Test voice agent endpoints."""

    @patch("app.voice.agent.VoiceAgent.process_audio")
    @pytest.mark.asyncio
    async def test_process_audio(
        self,
        mock_process: AsyncMock,
        client: AsyncClient,
        auth_headers: dict,
        test_clinic,
    ):
        """Test processing audio for voice booking."""
        # Mock voice response
        mock_response = Mock()
        mock_response.text = "I can help you book an appointment."
        mock_response.audio = b"fake_audio_data"
        mock_response.state = Mock(value="greeting")
        mock_response.booking_complete = False
        mock_response.appointment_id = None
        mock_response.next_action = "ask_doctor"
        mock_response.metadata = {}
        mock_process.return_value = mock_response

        # Create fake audio file
        audio_data = b"fake_audio_content"
        files = {"audio_file": ("test.wav", BytesIO(audio_data), "audio/wav")}

        response = await client.post(
            "/api/v1/voice/process-audio",
            headers=auth_headers,
            files=files,
            data={"clinic_id": str(test_clinic.id)},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "I can help you book an appointment."
        assert data["state"] == "greeting"
        assert data["booking_complete"] is False
        assert "audio_base64" in data
        assert "session_id" in data

    @patch("app.voice.agent.VoiceAgent.process_text")
    @pytest.mark.asyncio
    async def test_process_text(
        self,
        mock_process: AsyncMock,
        client: AsyncClient,
        auth_headers: dict,
        test_clinic,
    ):
        """Test processing text input for voice booking."""
        mock_response = Mock()
        mock_response.text = "Which doctor would you like to see?"
        mock_response.audio = None
        mock_response.state = Mock(value="asking_doctor")
        mock_response.booking_complete = False
        mock_response.appointment_id = None
        mock_response.next_action = "collect_doctor"
        mock_response.metadata = {}
        mock_process.return_value = mock_response

        response = await client.post(
            "/api/v1/voice/process-text",
            headers=auth_headers,
            json={
                "text": "I want to book an appointment",
                "clinic_id": str(test_clinic.id),
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "Which doctor would you like to see?"
        assert data["state"] == "asking_doctor"
        assert data["audio_base64"] is None

    @patch("app.voice.agent.VoiceAgent.get_session")
    @pytest.mark.asyncio
    async def test_get_session_status(
        self,
        mock_get_session: MagicMock,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test getting voice booking session status."""
        mock_session = Mock()
        mock_session.state = Mock(value="collecting_info")
        mock_session.doctor_name = "Dr. Smith"
        mock_session.appointment_date = datetime(2026, 1, 10)
        mock_session.appointment_time = datetime(2026, 1, 10, 14, 0)
        mock_session.patient_name = "John Doe"
        mock_session.reason = "Checkup"
        mock_session.conversation_history = ["Hi", "Book appointment"]
        mock_session.created_at = datetime(2026, 1, 5, 10, 0)
        mock_session.last_activity = datetime(2026, 1, 5, 10, 5)
        mock_get_session.return_value = mock_session

        session_id = "test_session_123"
        response = await client.get(
            f"/api/v1/voice/session/{session_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert data["state"] == "collecting_info"
        assert data["doctor_name"] == "Dr. Smith"
        assert data["patient_name"] == "John Doe"
        assert data["conversation_turns"] == 2

    @patch("app.voice.agent.VoiceAgent.get_session")
    @pytest.mark.asyncio
    async def test_get_session_not_found(
        self,
        mock_get_session: MagicMock,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test getting non-existent session returns 404."""
        mock_get_session.return_value = None

        response = await client.get(
            "/api/v1/voice/session/nonexistent_session",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @patch("app.voice.agent.VoiceAgent.get_session")
    @patch("app.voice.agent.VoiceAgent._cleanup_session")
    @pytest.mark.asyncio
    async def test_cancel_session(
        self,
        mock_cleanup: MagicMock,
        mock_get_session: MagicMock,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test cancelling a voice booking session."""
        mock_session = Mock()
        mock_get_session.return_value = mock_session

        session_id = "session_to_cancel"
        response = await client.delete(
            f"/api/v1/voice/session/{session_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Session cancelled"
        assert data["session_id"] == session_id
        mock_cleanup.assert_called_once_with(session_id)

    @patch("app.voice.tts.TextToSpeechAsync.synthesize")
    @pytest.mark.asyncio
    async def test_synthesize_speech(
        self,
        mock_synthesize: AsyncMock,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test text-to-speech synthesis."""
        mock_audio = b"synthesized_audio_data"
        mock_synthesize.return_value = mock_audio

        response = await client.post(
            "/api/v1/voice/synthesize",
            headers=auth_headers,
            params={
                "text": "Hello, how can I help you?",
                "language": "en",
                "speed": 1.0,
                "exaggeration": 0.5,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "Hello, how can I help you?"
        assert data["language"] == "en"
        assert data["exaggeration"] == 0.5
        assert "audio_base64" in data
        assert data["format"] == "wav"

    @patch("app.voice.tts.ChatterboxTTS.clone_voice_from_bytes")
    @pytest.mark.asyncio
    async def test_clone_voice(
        self,
        mock_clone: MagicMock,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test uploading voice sample for cloning."""
        mock_clone.return_value = "/path/to/voice_sample.wav"

        audio_data = b"fake_voice_sample_data" * 100
        files = {"voice_sample": ("sample.wav", BytesIO(audio_data), "audio/wav")}

        response = await client.post(
            "/api/v1/voice/clone-voice",
            headers=auth_headers,
            files=files,
        )
        assert response.status_code == 200
        data = response.json()
        assert "Voice sample uploaded successfully" in data["message"]
        assert "voice_path" in data
        assert data["file_size_bytes"] > 0

    @pytest.mark.asyncio

    async def test_clone_voice_invalid_format(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test voice cloning rejects invalid file format."""
        files = {"voice_sample": ("sample.txt", BytesIO(b"text"), "text/plain")}

        response = await client.post(
            "/api/v1/voice/clone-voice",
            headers=auth_headers,
            files=files,
        )
        assert response.status_code == 400
        assert "must be WAV, MP3, M4A, or OGG" in response.json()["detail"]

    @pytest.mark.asyncio

    async def test_clone_voice_file_too_large(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test voice cloning rejects files over 10MB."""
        # Create 11MB file
        large_data = b"x" * (11 * 1024 * 1024)
        files = {"voice_sample": ("large.wav", BytesIO(large_data), "audio/wav")}

        response = await client.post(
            "/api/v1/voice/clone-voice",
            headers=auth_headers,
            files=files,
        )
        assert response.status_code == 400
        assert "too large" in response.json()["detail"]

    @patch("app.voice.tts.TextToSpeechAsync.synthesize")
    @pytest.mark.asyncio
    async def test_synthesize_with_cloned_voice(
        self,
        mock_synthesize: AsyncMock,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test synthesizing speech with cloned voice."""
        mock_audio = b"cloned_voice_audio"
        mock_synthesize.return_value = mock_audio

        voice_data = b"voice_sample_data" * 50
        files = {
            "voice_sample": ("sample.wav", BytesIO(voice_data), "audio/wav"),
        }

        response = await client.post(
            "/api/v1/voice/synthesize-with-voice",
            headers=auth_headers,
            files=files,
            params={
                "text": "Test with cloned voice",
                "language": "en",
                "exaggeration": "0.7",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "Test with cloned voice"
        assert data["voice_cloned"] is True
        assert "audio_base64" in data

    @patch("app.voice.stt.SpeechToTextAsync.transcribe")
    @pytest.mark.asyncio
    async def test_transcribe_audio(
        self,
        mock_transcribe: AsyncMock,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test speech-to-text transcription."""
        mock_transcribe.return_value = {
            "text": "I need an appointment",
            "language": "en",
            "confidence": 0.95,
            "duration": 2.5,
            "segments": [
                {"start": 0.0, "end": 2.5, "text": "I need an appointment"}
            ],
        }

        audio_data = b"audio_to_transcribe"
        files = {"audio_file": ("speech.wav", BytesIO(audio_data), "audio/wav")}

        response = await client.post(
            "/api/v1/voice/transcribe",
            headers=auth_headers,
            files=files,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["text"] == "I need an appointment"
        assert data["language"] == "en"
        assert data["confidence"] == 0.95
        assert len(data["segments"]) == 1


# ============================================================================
# VOICE BOT API TESTS
# ============================================================================


class TestVoiceBotAPI:
    """Test Twilio voice bot endpoints."""

    @patch("app.services.voice_bot.TelephonyService.generate_twiml_connect")
    @pytest.mark.asyncio
    async def test_incoming_call_webhook(
        self,
        mock_twiml: MagicMock,
        client: AsyncClient,
        test_clinic,
        db: AsyncSession,
    ):
        """Test Twilio incoming call webhook."""
        mock_twiml.return_value = '<?xml version="1.0"?><Response><Connect><Stream url="wss://..." /></Connect></Response>'

        form_data = {
            "CallSid": "CA1234567890",
            "From": "+919876543210",
            "To": "+911234567890",
            "CallStatus": "ringing",
        }

        response = await client.post(
            "/api/v1/voice-bot/incoming",
            data=form_data,
        )
        assert response.status_code == 200
        assert "Response" in response.text
        assert "Connect" in response.text or "Say" in response.text

        # Verify call record created
        result = await db.execute(select(PhoneCall).where(PhoneCall.call_sid == "CA1234567890"))
        call = result.scalar_one_or_none()
        assert call is not None
        assert call.from_number == "+919876543210"
        assert call.direction == "inbound"

    @pytest.mark.asyncio

    async def test_incoming_call_no_clinic(
        self,
        client: AsyncClient,
        db: AsyncSession,
    ):
        """Test incoming call to unconfigured number."""
        # Use a number that doesn't map to any clinic
        form_data = {
            "CallSid": "CA_NO_CLINIC",
            "From": "+919999999999",
            "To": "+919999999999",
        }

        response = await client.post(
            "/api/v1/voice-bot/incoming",
            data=form_data,
        )
        assert response.status_code == 200
        assert "not configured" in response.text.lower()

    @pytest.mark.asyncio

    async def test_call_status_callback(
        self,
        client: AsyncClient,
        test_clinic,
        db: AsyncSession,
    ):
        """Test Twilio call status callback."""
        # Create initial call record
        call = PhoneCall(
            id=uuid4(),
            call_sid="CA_STATUS_TEST",
            from_number="+919876543210",
            to_number="+911234567890",
            direction="inbound",
            status=CallStatus.RINGING,
            clinic_id=test_clinic.id,
        )
        db.add(call)
        await db.commit()

        # Status callback
        form_data = {
            "CallSid": "CA_STATUS_TEST",
            "CallStatus": "completed",
            "CallDuration": "120",
        }

        response = await client.post(
            "/api/v1/voice-bot/status",
            data=form_data,
        )
        assert response.status_code == 200

        # Verify status updated
        result = await db.execute(select(PhoneCall).where(PhoneCall.call_sid == "CA_STATUS_TEST"))
        updated_call = result.scalar_one_or_none()
        assert updated_call.status == "completed"
        assert updated_call.duration_seconds == 120

    @patch("app.services.voice_bot.TelephonyService.initiate_outbound_call")
    @pytest.mark.asyncio
    async def test_initiate_outbound_call(
        self,
        mock_initiate: AsyncMock,
        client: AsyncClient,
        auth_headers: dict,
        test_clinic,
        test_appointment,
    ):
        """Test initiating outbound call."""
        mock_initiate.return_value = {
            "call_sid": "CA_OUTBOUND_123",
            "from_number": "+911234567890",
            "to_number": "+919876543210",
            "status": "queued",
        }

        response = await client.post(
            "/api/v1/voice-bot/outbound",
            headers=auth_headers,
            json={
                "to_number": "+919876543210",
                "clinic_id": str(test_clinic.id),
                "purpose": "appointment_reminder",
                "appointment_id": str(test_appointment.id),
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["call_sid"] == "CA_OUTBOUND_123"
        assert data["status"] == "queued"
        assert "call_id" in data

    @pytest.mark.asyncio

    async def test_list_calls(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_clinic,
        db: AsyncSession,
    ):
        """Test listing phone calls."""
        # Create test calls
        for i in range(3):
            call = PhoneCall(
                id=uuid4(),
                call_sid=f"CA_LIST_{i}",
                from_number=f"+9198765432{i}0",
                to_number="+911234567890",
                direction="inbound",
                status=CallStatus.COMPLETED,
                clinic_id=test_clinic.id,
            )
            db.add(call)
        await db.commit()

        response = await client.get(
            "/api/v1/voice-bot/calls",
            headers=auth_headers,
            params={"clinic_id": str(test_clinic.id)},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 3

    @pytest.mark.asyncio

    async def test_get_call_details(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_clinic,
        db: AsyncSession,
    ):
        """Test getting call details including transcript."""
        call = PhoneCall(
            id=uuid4(),
            call_sid="CA_DETAILS_TEST",
            from_number="+919876543210",
            to_number="+911234567890",
            direction="inbound",
            status=CallStatus.COMPLETED,
            clinic_id=test_clinic.id,
            transcript="Full conversation transcript",
        )
        db.add(call)
        await db.commit()

        response = await client.get(
            f"/api/v1/voice-bot/calls/{call.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["call_sid"] == "CA_DETAILS_TEST"
        assert data["transcript"] == "Full conversation transcript"

    @pytest.mark.asyncio

    async def test_get_call_details_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test getting non-existent call returns 404."""
        fake_id = uuid4()
        response = await client.get(
            f"/api/v1/voice-bot/calls/{fake_id}",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio

    async def test_get_call_transcript(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_clinic,
        db: AsyncSession,
    ):
        """Test getting full call transcript segments."""
        call = PhoneCall(
            id=uuid4(),
            call_sid="CA_TRANSCRIPT",
            from_number="+919876543210",
            to_number="+911234567890",
            direction="inbound",
            status=CallStatus.COMPLETED,
            clinic_id=test_clinic.id,
        )
        db.add(call)
        await db.commit()

        # Add transcript segments
        segments = [
            CallTranscriptSegment(
                id=uuid4(),
                call_id=call.id,
                speaker="bot",
                text="Hello, how can I help?",
                start_time_ms=0,
                end_time_ms=2000,
            ),
            CallTranscriptSegment(
                id=uuid4(),
                call_id=call.id,
                speaker="caller",
                text="I need an appointment",
                start_time_ms=2000,
                end_time_ms=4000,
            ),
        ]
        for seg in segments:
            db.add(seg)
        await db.commit()

        response = await client.get(
            f"/api/v1/voice-bot/calls/{call.id}/transcript",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["speaker"] == "bot"
        assert data[1]["speaker"] == "caller"

    @pytest.mark.asyncio

    async def test_get_call_stats(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_clinic,
        db: AsyncSession,
    ):
        """Test getting call statistics."""
        # Create various calls
        calls_data = [
            {"direction": "inbound", "status": CallStatus.COMPLETED, "duration": 120, "intent": "book_appointment"},
            {"direction": "inbound", "status": CallStatus.COMPLETED, "duration": 90, "intent": "check_status"},
            {"direction": "outbound", "status": CallStatus.COMPLETED, "duration": 60, "intent": "appointment_reminder"},
            {"direction": "inbound", "status": CallStatus.FAILED, "duration": None, "intent": None},
        ]

        for call_data in calls_data:
            call = PhoneCall(
                id=uuid4(),
                call_sid=f"CA_STATS_{uuid4()}",
                from_number="+919876543210",
                to_number="+911234567890",
                direction=call_data["direction"],
                status=call_data["status"],
                duration_seconds=call_data["duration"],
                intent_detected=call_data["intent"],
                clinic_id=test_clinic.id,
                language_detected="en",
            )
            db.add(call)
        await db.commit()

        response = await client.get(
            "/api/v1/voice-bot/stats",
            headers=auth_headers,
            params={"clinic_id": str(test_clinic.id)},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_calls"] >= 4
        assert data["inbound_calls"] >= 3
        assert data["outbound_calls"] >= 1
        assert data["completed_calls"] >= 3
        assert data["failed_calls"] >= 1
        assert data["average_duration_seconds"] > 0
        assert "languages" in data
        assert "intents" in data


# ============================================================================
# WEBSOCKET TESTS
# ============================================================================


class TestVoiceBotWebSocket:
    """Test WebSocket endpoint for real-time audio streaming."""

    @pytest.mark.skip(reason="AsyncClient does not support WebSocket connections")
    @pytest.mark.asyncio
    @patch("app.services.voice_bot.AppointmentBookingBot")
    async def test_voice_bot_websocket_connection(
        self,
        mock_bot_class: MagicMock,
        client: AsyncClient,
        test_clinic,
        db: AsyncSession,
    ):
        """Test WebSocket connection for voice bot."""
        # NOTE: This test is skipped because AsyncClient doesn't support websocket_connect
        # WebSocket testing requires a different test setup (e.g., using TestClient from starlette)
        # Create call record
        call = PhoneCall(
            id=uuid4(),
            call_sid="CA_WS_TEST",
            from_number="+919876543210",
            to_number="+911234567890",
            direction="inbound",
            status=CallStatus.RINGING,
            clinic_id=test_clinic.id,
        )
        db.add(call)
        await db.commit()

        # Mock bot instance
        mock_bot = AsyncMock()
        mock_bot.handle_call_start.return_value = "Hello, how can I help?"
        mock_bot.tts.synthesize.return_value = b"greeting_audio"
        mock_bot.state.language = "en"
        mock_bot_class.return_value = mock_bot

        # Test WebSocket connection
        with client.websocket_connect(f"/api/v1/voice-bot/ws/CA_WS_TEST") as websocket:
            # Should receive greeting
            data = websocket.receive_json()
            assert data["event"] == "media"

            # Send connected event
            websocket.send_json({"event": "connected"})

            # Send stop event
            websocket.send_json({"event": "stop"})

        # Verify call updated
        result = await db.execute(select(PhoneCall).where(PhoneCall.call_sid == "CA_WS_TEST"))
        updated_call = result.scalar_one_or_none()
        assert updated_call.status == CallStatus.COMPLETED


# ============================================================================
# RATE LIMITING & ERROR HANDLING TESTS
# ============================================================================


class TestCommunicationAPIErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio

    async def test_unauthorized_access(self, client: AsyncClient):
        """Test endpoints require authentication."""
        endpoints = [
            ("/api/v1/notifications/register", "post"),
            ("/api/v1/notifications/devices", "get"),
            ("/api/v1/voice/process-text", "post"),
            ("/api/v1/voice-bot/calls", "get"),
        ]

        for endpoint, method in endpoints:
            if method == "post":
                response = await client.post(endpoint, json={})
            else:
                response = await client.get(endpoint)
            assert response.status_code == 401

    @patch("app.integrations.whatsapp_bot.WhatsAppBot.send_message")
    @pytest.mark.asyncio
    async def test_whatsapp_rate_limiting(
        self,
        mock_send: AsyncMock,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test WhatsApp message rate limiting (if implemented)."""
        mock_send.return_value = True

        # Send multiple messages rapidly
        for i in range(5):
            response = await client.post(
                "/api/v1/whatsapp/send",
                headers=auth_headers,
                params={
                    "to_phone": "+919876543210",
                    "message": f"Message {i}",
                },
            )
            # All should succeed unless rate limiting is active
            # If rate limiting exists, some requests might return 429
            assert response.status_code in [200, 429]

    @pytest.mark.asyncio

    async def test_invalid_uuid_parameters(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test endpoints handle invalid UUID parameters gracefully."""
        response = await client.get(
            "/api/v1/voice-bot/calls/not-a-valid-uuid",
            headers=auth_headers,
        )
        assert response.status_code == 422

    @patch("app.voice.agent.VoiceAgent.process_text")
    @pytest.mark.asyncio
    async def test_voice_agent_error_handling(
        self,
        mock_process: AsyncMock,
        client: AsyncClient,
        auth_headers: dict,
        test_clinic,
    ):
        """Test voice agent handles processing errors."""
        mock_process.side_effect = Exception("Processing failed")

        response = await client.post(
            "/api/v1/voice/process-text",
            headers=auth_headers,
            json={
                "text": "Book appointment",
                "clinic_id": str(test_clinic.id),
            },
        )
        # Should handle error gracefully
        assert response.status_code in [500, 400]

    @pytest.mark.asyncio

    async def test_whatsapp_webhook_malformed_payload(
        self,
        client: AsyncClient,
    ):
        """Test WhatsApp webhook handles malformed payload."""
        response = await client.post(
            "/api/v1/whatsapp/webhook",
            json={"invalid": "payload"},
        )
        assert response.status_code == 200
        # Should not crash, returns error status
        data = response.json()
        assert "status" in data

