"""
WebSocket endpoint for real-time updates.

Provides WebSocket connections for real-time notifications about appointments,
waitlist updates, and general system events.

Features:
- Room-based subscriptions (by clinic_id)
- JWT authentication via query parameters
- Heartbeat/ping-pong for connection health
- Graceful disconnection handling
- Broadcast helpers for clinic-wide updates
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from fastapi.exceptions import WebSocketException

from app.core.security import decode_token

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """
    Manages WebSocket connections and message broadcasting.

    Connections are organized by clinic_id for efficient room-based messaging.
    Supports multiple connections per user and graceful disconnection handling.
    """

    def __init__(self):
        """Initialize the connection manager."""
        # Store active connections: {clinic_id: {connection_id: (websocket, user_id)}}
        self.active_connections: dict[UUID, dict[str, tuple[WebSocket, UUID]]] = {}
        # Heartbeat tasks for each connection
        self.heartbeat_tasks: dict[str, asyncio.Task] = {}
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    async def connect(
        self,
        websocket: WebSocket,
        clinic_id: UUID,
        user_id: UUID,
        connection_id: str,
    ) -> None:
        """
        Accept and register a new WebSocket connection.

        Args:
            websocket: WebSocket instance
            clinic_id: Clinic ID for room-based subscriptions
            user_id: Authenticated user ID
            connection_id: Unique connection identifier
        """
        await websocket.accept()

        async with self._lock:
            if clinic_id not in self.active_connections:
                self.active_connections[clinic_id] = {}

            self.active_connections[clinic_id][connection_id] = (websocket, user_id)

        logger.info(
            f"WebSocket connected: user={user_id}, clinic={clinic_id}, "
            f"connection={connection_id}"
        )

        # Start heartbeat for this connection
        self.heartbeat_tasks[connection_id] = asyncio.create_task(
            self._heartbeat(websocket, connection_id)
        )

        # Send welcome message
        await self._send_to_connection(
            websocket,
            {
                "event_type": "connected",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "clinic_id": str(clinic_id),
                    "user_id": str(user_id),
                    "connection_id": connection_id,
                },
            },
        )

    async def disconnect(self, clinic_id: UUID, connection_id: str) -> None:
        """
        Remove a WebSocket connection.

        Args:
            clinic_id: Clinic ID
            connection_id: Connection identifier to remove
        """
        async with self._lock:
            if clinic_id in self.active_connections:
                if connection_id in self.active_connections[clinic_id]:
                    del self.active_connections[clinic_id][connection_id]

                # Clean up empty clinic rooms
                if not self.active_connections[clinic_id]:
                    del self.active_connections[clinic_id]

        # Cancel heartbeat task
        if connection_id in self.heartbeat_tasks:
            self.heartbeat_tasks[connection_id].cancel()
            del self.heartbeat_tasks[connection_id]

        logger.info(f"WebSocket disconnected: clinic={clinic_id}, connection={connection_id}")

    async def broadcast_to_clinic(
        self,
        clinic_id: UUID,
        message: dict[str, Any],
    ) -> None:
        """
        Broadcast a message to all connections in a clinic.

        Args:
            clinic_id: Clinic ID to broadcast to
            message: Message dictionary to send
        """
        if clinic_id not in self.active_connections:
            return

        # Get all connections for this clinic
        connections = list(self.active_connections[clinic_id].items())

        # Send to all connections (non-blocking)
        tasks = []
        for connection_id, (websocket, _) in connections:
            tasks.append(self._send_to_connection(websocket, message, connection_id))

        # Wait for all sends to complete
        await asyncio.gather(*tasks, return_exceptions=True)

    async def broadcast_to_all(self, message: dict[str, Any]) -> None:
        """
        Broadcast a message to all connected clients.

        Args:
            message: Message dictionary to send
        """
        tasks = []

        for clinic_id in list(self.active_connections.keys()):
            connections = list(self.active_connections[clinic_id].items())
            for connection_id, (websocket, _) in connections:
                tasks.append(self._send_to_connection(websocket, message, connection_id))

        # Wait for all sends to complete
        await asyncio.gather(*tasks, return_exceptions=True)

    async def send_to_user(
        self,
        user_id: UUID,
        clinic_id: UUID,
        message: dict[str, Any],
    ) -> None:
        """
        Send a message to a specific user's connections.

        Args:
            user_id: User ID to send to
            clinic_id: Clinic ID where user is connected
            message: Message dictionary to send
        """
        if clinic_id not in self.active_connections:
            return

        # Find all connections for this user in the clinic
        tasks = []
        for connection_id, (websocket, ws_user_id) in self.active_connections[
            clinic_id
        ].items():
            if ws_user_id == user_id:
                tasks.append(self._send_to_connection(websocket, message, connection_id))

        # Wait for all sends to complete
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _send_to_connection(
        self,
        websocket: WebSocket,
        message: dict[str, Any],
        connection_id: str | None = None,
    ) -> None:
        """
        Send a message to a specific WebSocket connection.

        Args:
            websocket: WebSocket instance
            message: Message to send
            connection_id: Optional connection ID for logging
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(
                f"Failed to send message to connection {connection_id}: {e}",
                exc_info=True,
            )

    async def _heartbeat(self, websocket: WebSocket, connection_id: str) -> None:
        """
        Send periodic heartbeat pings to keep connection alive.

        Args:
            websocket: WebSocket instance
            connection_id: Connection identifier
        """
        try:
            while True:
                await asyncio.sleep(30)  # Ping every 30 seconds
                try:
                    await websocket.send_json(
                        {
                            "event_type": "ping",
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )
                except Exception:
                    # Connection lost, will be cleaned up by disconnect handler
                    break
        except asyncio.CancelledError:
            # Task cancelled, connection closing
            pass

    def get_connection_count(self, clinic_id: UUID | None = None) -> int:
        """
        Get the number of active connections.

        Args:
            clinic_id: Optional clinic ID to count specific clinic connections

        Returns:
            Number of active connections
        """
        if clinic_id:
            return len(self.active_connections.get(clinic_id, {}))
        return sum(len(conns) for conns in self.active_connections.values())


# Global connection manager instance
connection_manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """
    Get the global connection manager instance.

    Returns:
        ConnectionManager instance
    """
    return connection_manager


async def authenticate_websocket(websocket: WebSocket, token: str) -> dict[str, Any]:
    """
    Authenticate a WebSocket connection using JWT token.

    Args:
        websocket: WebSocket instance
        token: JWT token from query parameters

    Returns:
        Token payload with user information

    Raises:
        WebSocketException: If authentication fails
    """
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Missing authentication token",
        )

    payload = decode_token(token)
    if payload is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid authentication token",
        )

    # Check token type
    if payload.get("type") != "access":
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid token type",
        )

    return payload


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str,
    clinic_id: str,
) -> None:
    """
    WebSocket endpoint for real-time updates.

    Clients connect with JWT authentication and subscribe to clinic-specific events.

    Query Parameters:
        token: JWT access token for authentication
        clinic_id: Clinic UUID to subscribe to

    Message Format (Incoming):
        {
            "type": "pong",  // Response to ping
            "timestamp": "2024-01-01T12:00:00"
        }

    Message Format (Outgoing):
        {
            "event_type": "appointment_updated",
            "timestamp": "2024-01-01T12:00:00",
            "clinic_id": "uuid",
            "data": {...},
            "metadata": {...}
        }

    Error Codes:
        1008: Policy violation (authentication failed)
        1000: Normal closure
        1001: Going away (server shutdown)
    """
    # Authenticate the connection
    try:
        payload = await authenticate_websocket(websocket, token)
        user_id = UUID(payload.get("sub"))
        clinic_uuid = UUID(clinic_id)
    except (ValueError, WebSocketException) as e:
        logger.warning(f"WebSocket authentication failed: {e}")
        return

    # Generate unique connection ID
    connection_id = f"{user_id}_{datetime.utcnow().timestamp()}"

    # Register the connection
    await connection_manager.connect(
        websocket=websocket,
        clinic_id=clinic_uuid,
        user_id=user_id,
        connection_id=connection_id,
    )

    try:
        # Listen for client messages
        while True:
            data = await websocket.receive_text()

            try:
                message = json.loads(data)

                # Handle pong responses
                if message.get("type") == "pong":
                    logger.debug(f"Received pong from connection {connection_id}")
                    continue

                # Handle other message types as needed
                logger.debug(f"Received message from {connection_id}: {message}")

            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from {connection_id}: {data}")
                continue

    except WebSocketDisconnect:
        logger.info(f"Client {connection_id} disconnected normally")
    except Exception as e:
        logger.error(f"WebSocket error for {connection_id}: {e}", exc_info=True)
    finally:
        # Clean up the connection
        await connection_manager.disconnect(clinic_uuid, connection_id)
