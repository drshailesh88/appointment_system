"""
Push Notifications API endpoints.

Manage device registration and push notifications.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, DbSession
from app.models.device_token import DevicePlatform, DeviceToken
from app.services.push_notifications import (
    NotificationType,
    PushNotificationService,
    get_push_notification_service,
)

router = APIRouter()


class DeviceRegistrationRequest(BaseModel):
    """Request to register a device token."""

    device_token: str = Field(..., min_length=10, max_length=500)
    platform: DevicePlatform
    device_name: Optional[str] = Field(None, max_length=200)


class DeviceTokenModel(BaseModel):
    """Device token response model."""

    id: str
    user_id: str
    device_token: str
    platform: str
    device_name: Optional[str]
    is_active: bool
    created_at: str


class NotificationSendRequest(BaseModel):
    """Request to send a test notification."""

    user_id: UUID
    notification_type: NotificationType
    template_vars: dict = Field(default_factory=dict)
    data: Optional[dict] = None


class TopicSubscriptionRequest(BaseModel):
    """Request to subscribe to a topic."""

    topic: str = Field(..., min_length=1, max_length=100)


def token_to_model(token: DeviceToken) -> DeviceTokenModel:
    """Convert DeviceToken to response model."""
    return DeviceTokenModel(
        id=str(token.id),
        user_id=str(token.user_id),
        device_token=token.device_token,
        platform=token.platform,
        device_name=token.device_name,
        is_active=token.is_active,
        created_at=token.created_at.isoformat(),
    )


@router.post("/register", response_model=DeviceTokenModel, status_code=status.HTTP_201_CREATED)
async def register_device_token(
    request: DeviceRegistrationRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Register a device token for push notifications.

    Call this when the app starts and gets an FCM token.
    """
    service = get_push_notification_service(db)

    try:
        token = await service.register_device(
            user_id=current_user.id,
            device_token=request.device_token,
            platform=request.platform,
            device_name=request.device_name,
        )
        return token_to_model(token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to register device: {str(e)}",
        )


@router.delete("/unregister", status_code=status.HTTP_204_NO_CONTENT)
async def unregister_device_token(
    db: DbSession,
    current_user: CurrentUser,
    device_token: str = Query(..., min_length=10),
):
    """
    Unregister a device token.

    Call this when the user logs out or when FCM token is invalidated.
    """
    service = get_push_notification_service(db)

    success = await service.unregister_device(
        user_id=current_user.id,
        device_token=device_token,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device token not found",
        )


@router.get("/devices", response_model=list[DeviceTokenModel])
async def get_my_devices(
    db: DbSession,
    current_user: CurrentUser,
    active_only: bool = Query(True),
):
    """
    Get all registered devices for the current user.

    Useful for showing a list of devices in settings.
    """
    from sqlalchemy import and_, select

    filters = [DeviceToken.user_id == current_user.id]
    if active_only:
        filters.append(DeviceToken.is_active == True)

    result = await db.execute(
        select(DeviceToken)
        .where(and_(*filters))
        .order_by(DeviceToken.created_at.desc())
    )
    tokens = list(result.scalars().all())

    return [token_to_model(t) for t in tokens]


@router.delete("/devices/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_device(
    device_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Remove a specific device by ID.

    Useful for removing old/inactive devices from settings.
    """
    token = await db.get(DeviceToken, device_id)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    if token.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to remove this device",
        )

    await db.delete(token)
    await db.commit()


@router.post("/send", status_code=status.HTTP_200_OK)
async def send_notification(
    request: NotificationSendRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Send a push notification to a user.

    This is primarily for testing. In production, notifications are sent
    automatically by the system (e.g., appointment reminders, slot offers).

    Only admins can send test notifications to other users.
    """
    # Check authorization
    if request.user_id != current_user.id and current_user.role not in ["admin", "owner"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to send notifications to other users",
        )

    service = get_push_notification_service(db)

    try:
        result = await service.send_to_user(
            user_id=request.user_id,
            notification_type=request.notification_type,
            data=request.data,
            **request.template_vars,
        )

        return {
            "message": "Notification sent",
            "success_count": result["success"],
            "failed_count": result["failed"],
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send notification: {str(e)}",
        )


@router.post("/topics/subscribe", status_code=status.HTTP_200_OK)
async def subscribe_to_topic(
    request: TopicSubscriptionRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Subscribe to a notification topic.

    Topics are used for clinic-wide broadcasts (e.g., 'clinic_12345').
    Users are typically auto-subscribed to their clinic topic on login.
    """
    service = get_push_notification_service(db)

    try:
        result = await service.subscribe_to_topic(
            user_id=current_user.id,
            topic=request.topic,
        )

        return {
            "message": f"Subscribed to topic '{request.topic}'",
            "success_count": result["success"],
            "failed_count": result["failed"],
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to subscribe: {str(e)}",
        )


@router.post("/topics/unsubscribe", status_code=status.HTTP_200_OK)
async def unsubscribe_from_topic(
    request: TopicSubscriptionRequest,
    db: DbSession,
    current_user: CurrentUser,
):
    """
    Unsubscribe from a notification topic.

    Call this when leaving a clinic or when user disables clinic broadcasts.
    """
    service = get_push_notification_service(db)

    try:
        result = await service.unsubscribe_from_topic(
            user_id=current_user.id,
            topic=request.topic,
        )

        return {
            "message": f"Unsubscribed from topic '{request.topic}'",
            "success_count": result["success"],
            "failed_count": result["failed"],
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unsubscribe: {str(e)}",
        )


@router.get("/test", status_code=status.HTTP_200_OK)
async def test_notification_system(
    current_user: CurrentUser,
):
    """
    Test if Firebase is properly configured.

    Returns configuration status without sending actual notifications.
    """
    from app.services.push_notifications import PushNotificationService

    is_configured = PushNotificationService._initialized

    return {
        "firebase_configured": is_configured,
        "message": (
            "Firebase is properly configured"
            if is_configured
            else "Firebase not configured. Set FIREBASE_CREDENTIALS_PATH environment variable."
        ),
    }
