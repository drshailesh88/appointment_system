"""
Push Notification Service using Firebase Cloud Messaging (FCM).

Handles sending push notifications to registered devices:
- Send to single device
- Send to topic (clinic-based broadcasts)
- Template-based notification content
- Automatic token cleanup on failure
"""

import logging
import os
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional
from uuid import UUID

from firebase_admin import credentials, initialize_app, messaging
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device_token import DeviceToken, DevicePlatform
from app.models.user import User

logger = logging.getLogger(__name__)


class NotificationType(str, Enum):
    """Push notification types."""

    APPOINTMENT_REMINDER = "appointment_reminder"
    APPOINTMENT_CONFIRMED = "appointment_confirmed"
    APPOINTMENT_CANCELLED = "appointment_cancelled"
    APPOINTMENT_RESCHEDULED = "appointment_rescheduled"
    SLOT_OFFER = "slot_offer"
    PAYMENT_RECEIVED = "payment_received"
    PAYMENT_PENDING = "payment_pending"
    WAITLIST_POSITION_UPDATE = "waitlist_position_update"
    GENERAL_ANNOUNCEMENT = "general_announcement"


class NotificationTemplate:
    """Notification content templates."""

    TEMPLATES = {
        NotificationType.APPOINTMENT_REMINDER: {
            "title": "Appointment Reminder",
            "body": "Your appointment with Dr. {doctor_name} is scheduled for {appointment_time}",
        },
        NotificationType.APPOINTMENT_CONFIRMED: {
            "title": "Appointment Confirmed",
            "body": "Your appointment with Dr. {doctor_name} on {appointment_date} has been confirmed",
        },
        NotificationType.APPOINTMENT_CANCELLED: {
            "title": "Appointment Cancelled",
            "body": "Your appointment with Dr. {doctor_name} on {appointment_date} has been cancelled",
        },
        NotificationType.APPOINTMENT_RESCHEDULED: {
            "title": "Appointment Rescheduled",
            "body": "Your appointment has been rescheduled to {new_appointment_time}",
        },
        NotificationType.SLOT_OFFER: {
            "title": "Slot Available!",
            "body": "Good news! A slot is available with Dr. {doctor_name} on {slot_time}. Tap to confirm.",
        },
        NotificationType.PAYMENT_RECEIVED: {
            "title": "Payment Received",
            "body": "Payment of ₹{amount} received successfully. Thank you!",
        },
        NotificationType.PAYMENT_PENDING: {
            "title": "Payment Pending",
            "body": "Please complete payment of ₹{amount} for your appointment on {appointment_date}",
        },
        NotificationType.WAITLIST_POSITION_UPDATE: {
            "title": "Waitlist Update",
            "body": "You are now #{position} in the waitlist. Estimated wait: {wait_time}",
        },
        NotificationType.GENERAL_ANNOUNCEMENT: {
            "title": "{title}",
            "body": "{message}",
        },
    }

    @classmethod
    def get_content(
        cls,
        notification_type: NotificationType,
        **kwargs,
    ) -> dict[str, str]:
        """
        Get notification content from template.

        Args:
            notification_type: Type of notification
            **kwargs: Template variables

        Returns:
            Dict with 'title' and 'body' keys
        """
        template = cls.TEMPLATES.get(notification_type)
        if not template:
            raise ValueError(f"Unknown notification type: {notification_type}")

        try:
            return {
                "title": template["title"].format(**kwargs),
                "body": template["body"].format(**kwargs),
            }
        except KeyError as e:
            raise ValueError(f"Missing template variable: {e}")


class PushNotificationService:
    """
    Firebase Cloud Messaging push notification service.

    Features:
    - Send to individual devices
    - Send to topics (clinic broadcasts)
    - Template-based content
    - Automatic token cleanup
    - Platform-specific handling
    """

    _initialized = False

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db
        self._ensure_firebase_initialized()

    @classmethod
    def _ensure_firebase_initialized(cls):
        """Initialize Firebase Admin SDK (once per app lifecycle)."""
        if cls._initialized:
            return

        try:
            # Check for Firebase credentials
            cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
            if not cred_path:
                logger.warning(
                    "FIREBASE_CREDENTIALS_PATH not set. Push notifications disabled. "
                    "Set environment variable to enable."
                )
                return

            if not Path(cred_path).exists():
                logger.warning(
                    f"Firebase credentials file not found at {cred_path}. "
                    "Push notifications disabled."
                )
                return

            # Initialize Firebase
            cred = credentials.Certificate(cred_path)
            initialize_app(cred)
            cls._initialized = True
            logger.info("Firebase Admin SDK initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            logger.warning("Push notifications will be disabled")

    async def register_device(
        self,
        user_id: UUID,
        device_token: str,
        platform: DevicePlatform,
        device_name: Optional[str] = None,
    ) -> DeviceToken:
        """
        Register a device token for push notifications.

        Args:
            user_id: User ID
            device_token: FCM registration token
            platform: Device platform (ios/android/web)
            device_name: Optional device name/model

        Returns:
            DeviceToken instance
        """
        # Check if token already exists
        result = await self.db.execute(
            select(DeviceToken).where(
                and_(
                    DeviceToken.user_id == user_id,
                    DeviceToken.device_token == device_token,
                )
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing token
            existing.is_active = True
            existing.platform = platform.value
            if device_name:
                existing.device_name = device_name
            await self.db.commit()
            await self.db.refresh(existing)
            logger.info(f"Updated device token for user {user_id}")
            return existing

        # Create new token
        token = DeviceToken(
            user_id=user_id,
            device_token=device_token,
            platform=platform.value,
            device_name=device_name,
        )
        self.db.add(token)
        await self.db.commit()
        await self.db.refresh(token)

        logger.info(f"Registered new device token for user {user_id} ({platform.value})")
        return token

    async def unregister_device(self, user_id: UUID, device_token: str) -> bool:
        """
        Unregister a device token.

        Args:
            user_id: User ID
            device_token: FCM token to remove

        Returns:
            True if token was removed, False if not found
        """
        result = await self.db.execute(
            select(DeviceToken).where(
                and_(
                    DeviceToken.user_id == user_id,
                    DeviceToken.device_token == device_token,
                )
            )
        )
        token = result.scalar_one_or_none()

        if not token:
            return False

        await self.db.delete(token)
        await self.db.commit()
        logger.info(f"Unregistered device token for user {user_id}")
        return True

    async def send_to_user(
        self,
        user_id: UUID,
        notification_type: NotificationType,
        data: Optional[dict] = None,
        **template_vars,
    ) -> dict[str, int]:
        """
        Send notification to all active devices of a user.

        Args:
            user_id: User ID
            notification_type: Type of notification
            data: Additional data payload
            **template_vars: Variables for notification template

        Returns:
            Dict with 'success' and 'failed' counts
        """
        if not self._initialized:
            logger.warning("Firebase not initialized. Skipping notification.")
            return {"success": 0, "failed": 0}

        # Get user's active device tokens
        result = await self.db.execute(
            select(DeviceToken).where(
                and_(
                    DeviceToken.user_id == user_id,
                    DeviceToken.is_active == True,
                )
            )
        )
        tokens = list(result.scalars().all())

        if not tokens:
            logger.info(f"No active device tokens for user {user_id}")
            return {"success": 0, "failed": 0}

        # Get notification content
        content = NotificationTemplate.get_content(notification_type, **template_vars)

        # Prepare data payload
        payload = {
            "type": notification_type.value,
            "timestamp": datetime.utcnow().isoformat(),
            **(data or {}),
        }

        # Send to each device
        success_count = 0
        failed_count = 0

        for token in tokens:
            try:
                await self._send_to_token(
                    token.device_token,
                    content["title"],
                    content["body"],
                    payload,
                    platform=DevicePlatform(token.platform),
                )
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to send to token {token.id}: {e}")
                failed_count += 1
                # Deactivate invalid tokens
                if "not-found" in str(e).lower() or "invalid" in str(e).lower():
                    token.deactivate()
                    await self.db.commit()

        logger.info(
            f"Sent notification to user {user_id}: "
            f"{success_count} success, {failed_count} failed"
        )

        return {"success": success_count, "failed": failed_count}

    async def send_to_device(
        self,
        device_token: str,
        notification_type: NotificationType,
        data: Optional[dict] = None,
        **template_vars,
    ) -> bool:
        """
        Send notification to a specific device token.

        Args:
            device_token: FCM device token
            notification_type: Type of notification
            data: Additional data payload
            **template_vars: Variables for notification template

        Returns:
            True if sent successfully
        """
        if not self._initialized:
            logger.warning("Firebase not initialized. Skipping notification.")
            return False

        # Get notification content
        content = NotificationTemplate.get_content(notification_type, **template_vars)

        # Prepare data payload
        payload = {
            "type": notification_type.value,
            "timestamp": datetime.utcnow().isoformat(),
            **(data or {}),
        }

        try:
            await self._send_to_token(
                device_token,
                content["title"],
                content["body"],
                payload,
            )
            logger.info(f"Sent notification to device token")
            return True
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False

    async def send_to_topic(
        self,
        topic: str,
        notification_type: NotificationType,
        data: Optional[dict] = None,
        **template_vars,
    ) -> bool:
        """
        Send notification to a topic (e.g., all users in a clinic).

        Args:
            topic: Topic name (e.g., 'clinic_12345')
            notification_type: Type of notification
            data: Additional data payload
            **template_vars: Variables for notification template

        Returns:
            True if sent successfully
        """
        if not self._initialized:
            logger.warning("Firebase not initialized. Skipping notification.")
            return False

        # Get notification content
        content = NotificationTemplate.get_content(notification_type, **template_vars)

        # Prepare data payload
        payload = {
            "type": notification_type.value,
            "timestamp": datetime.utcnow().isoformat(),
            **(data or {}),
        }

        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=content["title"],
                    body=content["body"],
                ),
                data=payload,
                topic=topic,
            )
            response = messaging.send(message)
            logger.info(f"Sent notification to topic '{topic}': {response}")
            return True
        except Exception as e:
            logger.error(f"Failed to send to topic '{topic}': {e}")
            return False

    async def _send_to_token(
        self,
        token: str,
        title: str,
        body: str,
        data: dict,
        platform: Optional[DevicePlatform] = None,
    ):
        """
        Internal method to send notification to a single token.

        Args:
            token: FCM device token
            title: Notification title
            body: Notification body
            data: Data payload
            platform: Device platform for platform-specific config
        """
        # Platform-specific configuration
        android_config = None
        apns_config = None

        if platform == DevicePlatform.ANDROID:
            android_config = messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    sound="default",
                    color="#1976D2",  # App primary color
                ),
            )
        elif platform == DevicePlatform.IOS:
            apns_config = messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        sound="default",
                        badge=1,
                    )
                )
            )

        # Create message
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data,
            token=token,
            android=android_config,
            apns=apns_config,
        )

        # Send
        response = messaging.send(message)
        logger.debug(f"FCM response: {response}")

    async def subscribe_to_topic(
        self,
        user_id: UUID,
        topic: str,
    ) -> dict[str, int]:
        """
        Subscribe all user's devices to a topic.

        Args:
            user_id: User ID
            topic: Topic name

        Returns:
            Dict with 'success' and 'failed' counts
        """
        if not self._initialized:
            return {"success": 0, "failed": 0}

        # Get user's active tokens
        result = await self.db.execute(
            select(DeviceToken.device_token).where(
                and_(
                    DeviceToken.user_id == user_id,
                    DeviceToken.is_active == True,
                )
            )
        )
        tokens = [row[0] for row in result.all()]

        if not tokens:
            return {"success": 0, "failed": 0}

        try:
            response = messaging.subscribe_to_topic(tokens, topic)
            logger.info(
                f"Subscribed user {user_id} to topic '{topic}': "
                f"{response.success_count} success, {response.failure_count} failed"
            )
            return {
                "success": response.success_count,
                "failed": response.failure_count,
            }
        except Exception as e:
            logger.error(f"Failed to subscribe to topic '{topic}': {e}")
            return {"success": 0, "failed": len(tokens)}

    async def unsubscribe_from_topic(
        self,
        user_id: UUID,
        topic: str,
    ) -> dict[str, int]:
        """
        Unsubscribe all user's devices from a topic.

        Args:
            user_id: User ID
            topic: Topic name

        Returns:
            Dict with 'success' and 'failed' counts
        """
        if not self._initialized:
            return {"success": 0, "failed": 0}

        # Get user's active tokens
        result = await self.db.execute(
            select(DeviceToken.device_token).where(
                and_(
                    DeviceToken.user_id == user_id,
                    DeviceToken.is_active == True,
                )
            )
        )
        tokens = [row[0] for row in result.all()]

        if not tokens:
            return {"success": 0, "failed": 0}

        try:
            response = messaging.unsubscribe_from_topic(tokens, topic)
            logger.info(
                f"Unsubscribed user {user_id} from topic '{topic}': "
                f"{response.success_count} success, {response.failure_count} failed"
            )
            return {
                "success": response.success_count,
                "failed": response.failure_count,
            }
        except Exception as e:
            logger.error(f"Failed to unsubscribe from topic '{topic}': {e}")
            return {"success": 0, "failed": len(tokens)}


def get_push_notification_service(db: AsyncSession) -> PushNotificationService:
    """Factory function for push notification service."""
    return PushNotificationService(db)
