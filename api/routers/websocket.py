"""
WebSocket router for real-time updates.

Handles WebSocket connections for live updates during all phases
of the Specify system execution.
"""

import asyncio
import json
import logging
from typing import Dict, Set, List
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from fastapi.websockets import WebSocketState

from api.schemas.request_schemas import WebSocketMessage, WebSocketMessageType
from api.schemas.response_schemas import WebSocketEvent
from api.services import SessionManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])


class ConnectionManager:
    """Manages WebSocket connections and broadcasting."""

    def __init__(self):
        # Active connections by session_id
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Connection subscriptions (session_id -> event_types)
        self.subscriptions: Dict[str, Set[str]] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept WebSocket connection and register it."""
        await websocket.accept()

        if session_id not in self.active_connections:
            self.active_connections[session_id] = set()
            self.subscriptions[session_id] = set()

        self.active_connections[session_id].add(websocket)
        logger.info(f"WebSocket connected for session {session_id}")

    def disconnect(self, websocket: WebSocket, session_id: str):
        """Remove WebSocket connection."""
        if session_id in self.active_connections:
            self.active_connections[session_id].discard(websocket)

            # Clean up empty sessions
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]
                if session_id in self.subscriptions:
                    del self.subscriptions[session_id]

        logger.info(f"WebSocket disconnected for session {session_id}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send message to specific WebSocket."""
        if websocket.client_state == WebSocketState.CONNECTED:
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error(f"Error sending personal message: {e}")

    async def broadcast_to_session(self, session_id: str, message: str):
        """Broadcast message to all connections in a session."""
        if session_id in self.active_connections:
            disconnected = []

            for websocket in self.active_connections[session_id]:
                try:
                    if websocket.client_state == WebSocketState.CONNECTED:
                        await websocket.send_text(message)
                    else:
                        disconnected.append(websocket)
                except Exception as e:
                    logger.error(f"Error broadcasting to session {session_id}: {e}")
                    disconnected.append(websocket)

            # Clean up disconnected sockets
            for websocket in disconnected:
                self.disconnect(websocket, session_id)

    async def broadcast_event(self, event: WebSocketEvent):
        """Broadcast event to subscribed connections."""
        message = event.json()
        session_id = event.session_id

        # Check if any connections are subscribed to this event type
        if session_id in self.subscriptions and event.type in self.subscriptions[session_id]:
            await self.broadcast_to_session(session_id, message)

    def subscribe_to_events(self, session_id: str, event_types: List[str]):
        """Subscribe session to specific event types."""
        if session_id not in self.subscriptions:
            self.subscriptions[session_id] = set()

        self.subscriptions[session_id].update(event_types)
        logger.info(f"Session {session_id} subscribed to events: {event_types}")

    def unsubscribe_from_events(self, session_id: str, event_types: List[str]):
        """Unsubscribe session from specific event types."""
        if session_id in self.subscriptions:
            self.subscriptions[session_id].difference_update(event_types)
            logger.info(f"Session {session_id} unsubscribed from events: {event_types}")


# Global connection manager
connection_manager = ConnectionManager()


def get_session_manager() -> SessionManager:
    """Dependency to get session manager."""
    from api.main import app
    return app.state.session_manager


@router.websocket("/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    session_manager: SessionManager = Depends(get_session_manager)
):
    """
    WebSocket endpoint for real-time communication.

    Supports bidirectional communication for:
    - Live updates during analysis, specification, refinement, and execution
    - Interactive feedback during refinement
    - Progress updates and notifications
    - Error reporting and status changes
    """
    await connection_manager.connect(websocket, session_id)

    try:
        # Verify session exists or create it
        session = await session_manager.get_session(session_id)
        if not session:
            session = await session_manager.create_session()
            logger.info(f"Created new session for WebSocket: {session.id}")

        # Send connection confirmation
        welcome_event = WebSocketEvent(
            type="connection_established",
            session_id=session_id,
            data={
                "message": "WebSocket connection established",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }
        )
        await connection_manager.send_personal_message(welcome_event.json(), websocket)

        # Handle incoming messages
        while True:
            try:
                # Receive message
                data = await websocket.receive_text()
                message_data = json.loads(data)

                # Parse message
                message = WebSocketMessage.parse_obj(message_data)

                # Process message based on type
                await handle_websocket_message(websocket, session_id, message)

            except json.JSONDecodeError:
                error_event = WebSocketEvent(
                    type="error",
                    session_id=session_id,
                    data={"error": "Invalid JSON format"}
                )
                await connection_manager.send_personal_message(error_event.json(), websocket)

            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
                error_event = WebSocketEvent(
                    type="error",
                    session_id=session_id,
                    data={"error": f"Message processing error: {str(e)}"}
                )
                await connection_manager.send_personal_message(error_event.json(), websocket)

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.exception(f"WebSocket error for session {session_id}: {e}")
    finally:
        connection_manager.disconnect(websocket, session_id)


async def handle_websocket_message(websocket: WebSocket, session_id: str, message: WebSocketMessage):
    """Handle incoming WebSocket messages."""

    if message.type == WebSocketMessageType.SUBSCRIBE:
        # Subscribe to event types
        event_types = message.data.get("event_types", [])
        connection_manager.subscribe_to_events(session_id, event_types)

        response = WebSocketEvent(
            type="subscription_confirmed",
            session_id=session_id,
            data={
                "subscribed_events": event_types,
                "message": f"Subscribed to {len(event_types)} event types"
            }
        )
        await connection_manager.send_personal_message(response.json(), websocket)

    elif message.type == WebSocketMessageType.UNSUBSCRIBE:
        # Unsubscribe from event types
        event_types = message.data.get("event_types", [])
        connection_manager.unsubscribe_from_events(session_id, event_types)

        response = WebSocketEvent(
            type="unsubscription_confirmed",
            session_id=session_id,
            data={
                "unsubscribed_events": event_types,
                "message": f"Unsubscribed from {len(event_types)} event types"
            }
        )
        await connection_manager.send_personal_message(response.json(), websocket)

    elif message.type == WebSocketMessageType.PING:
        # Respond to ping
        response = WebSocketEvent(
            type="pong",
            session_id=session_id,
            data={"timestamp": datetime.now().isoformat()}
        )
        await connection_manager.send_personal_message(response.json(), websocket)

    elif message.type == WebSocketMessageType.USER_INPUT:
        # Handle user input during interactive phases
        response = WebSocketEvent(
            type="user_input_received",
            session_id=session_id,
            data={
                "input_data": message.data,
                "message": "User input received and processed"
            }
        )
        await connection_manager.send_personal_message(response.json(), websocket)

    elif message.type == WebSocketMessageType.REFINEMENT_FEEDBACK:
        # Handle refinement feedback
        response = WebSocketEvent(
            type="refinement_feedback_received",
            session_id=session_id,
            data={
                "feedback_data": message.data,
                "message": "Refinement feedback received"
            }
        )
        await connection_manager.send_personal_message(response.json(), websocket)

    else:
        # Unknown message type
        response = WebSocketEvent(
            type="error",
            session_id=session_id,
            data={"error": f"Unknown message type: {message.type}"}
        )
        await connection_manager.send_personal_message(response.json(), websocket)


# Event broadcasting functions for use by other services
async def broadcast_analysis_progress(session_id: str, progress_data: Dict):
    """Broadcast analysis progress update."""
    event = WebSocketEvent(
        type="analysis_progress",
        session_id=session_id,
        data=progress_data
    )
    await connection_manager.broadcast_event(event)


async def broadcast_specification_update(session_id: str, specification_data: Dict):
    """Broadcast specification update."""
    event = WebSocketEvent(
        type="specification_update",
        session_id=session_id,
        data=specification_data
    )
    await connection_manager.broadcast_event(event)


async def broadcast_refinement_suggestion(session_id: str, suggestion_data: Dict):
    """Broadcast new refinement suggestion."""
    event = WebSocketEvent(
        type="refinement_suggestion",
        session_id=session_id,
        data=suggestion_data
    )
    await connection_manager.broadcast_event(event)


async def broadcast_agent_started(session_id: str, agent_data: Dict):
    """Broadcast agent start notification."""
    event = WebSocketEvent(
        type="agent_started",
        session_id=session_id,
        data=agent_data
    )
    await connection_manager.broadcast_event(event)


async def broadcast_agent_progress(session_id: str, progress_data: Dict):
    """Broadcast agent progress update."""
    event = WebSocketEvent(
        type="agent_progress",
        session_id=session_id,
        data=progress_data
    )
    await connection_manager.broadcast_event(event)


async def broadcast_agent_completed(session_id: str, completion_data: Dict):
    """Broadcast agent completion notification."""
    event = WebSocketEvent(
        type="agent_completed",
        session_id=session_id,
        data=completion_data
    )
    await connection_manager.broadcast_event(event)


async def broadcast_execution_complete(session_id: str, execution_data: Dict):
    """Broadcast execution completion notification."""
    event = WebSocketEvent(
        type="execution_complete",
        session_id=session_id,
        data=execution_data
    )
    await connection_manager.broadcast_event(event)


async def broadcast_error(session_id: str, error_data: Dict):
    """Broadcast error notification."""
    event = WebSocketEvent(
        type="error",
        session_id=session_id,
        data=error_data
    )
    await connection_manager.broadcast_event(event)


# Export the connection manager and broadcast functions for use by services
__all__ = [
    "connection_manager",
    "broadcast_analysis_progress",
    "broadcast_specification_update",
    "broadcast_refinement_suggestion",
    "broadcast_agent_started",
    "broadcast_agent_progress",
    "broadcast_agent_completed",
    "broadcast_execution_complete",
    "broadcast_error",
]