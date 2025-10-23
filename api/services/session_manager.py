"""
Session management for the Specify API.

Handles session creation, tracking, expiration, and cleanup.
Supports both in-memory and Redis-based session storage.
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import logging

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from api.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class SessionData:
    """Session data structure."""
    id: str
    user_id: Optional[str]
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    metadata: Dict[str, Any]
    active_operations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        data['created_at'] = self.created_at.isoformat()
        data['last_activity'] = self.last_activity.isoformat()
        data['expires_at'] = self.expires_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionData':
        """Create from dictionary."""
        # Convert ISO strings back to datetime objects
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['last_activity'] = datetime.fromisoformat(data['last_activity'])
        data['expires_at'] = datetime.fromisoformat(data['expires_at'])
        return cls(**data)

    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.now() > self.expires_at

    def extend_expiration(self, minutes: int = None) -> None:
        """Extend session expiration."""
        settings = get_settings()
        timeout_minutes = minutes or settings.session_timeout_minutes
        self.expires_at = datetime.now() + timedelta(minutes=timeout_minutes)
        self.last_activity = datetime.now()


class InMemorySessionStore:
    """In-memory session storage."""

    def __init__(self):
        self._sessions: Dict[str, SessionData] = {}
        self._user_sessions: Dict[str, List[str]] = {}  # user_id -> session_ids

    async def create_session(
        self,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SessionData:
        """Create a new session."""
        settings = get_settings()
        session_id = str(uuid.uuid4())
        now = datetime.now()

        session = SessionData(
            id=session_id,
            user_id=user_id,
            created_at=now,
            last_activity=now,
            expires_at=now + timedelta(minutes=settings.session_timeout_minutes),
            metadata=metadata or {},
            active_operations=[]
        )

        self._sessions[session_id] = session

        # Track user sessions
        if user_id:
            if user_id not in self._user_sessions:
                self._user_sessions[user_id] = []
            self._user_sessions[user_id].append(session_id)

            # Enforce max sessions per user
            user_session_ids = self._user_sessions[user_id]
            if len(user_session_ids) > settings.max_sessions_per_user:
                # Remove oldest sessions
                sessions_to_remove = len(user_session_ids) - settings.max_sessions_per_user
                for _ in range(sessions_to_remove):
                    old_session_id = user_session_ids.pop(0)
                    if old_session_id in self._sessions:
                        del self._sessions[old_session_id]

        return session

    async def get_session(self, session_id: str) -> Optional[SessionData]:
        """Get session by ID."""
        session = self._sessions.get(session_id)
        if session and session.is_expired():
            await self.delete_session(session_id)
            return None
        return session

    async def update_session(
        self,
        session_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        extend_timeout: bool = True
    ) -> Optional[SessionData]:
        """Update session data."""
        session = self._sessions.get(session_id)
        if not session or session.is_expired():
            return None

        if metadata:
            session.metadata.update(metadata)

        if extend_timeout:
            session.extend_expiration()

        return session

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        session = self._sessions.get(session_id)
        if not session:
            return False

        # Remove from user sessions tracking
        if session.user_id and session.user_id in self._user_sessions:
            user_sessions = self._user_sessions[session.user_id]
            if session_id in user_sessions:
                user_sessions.remove(session_id)
            if not user_sessions:
                del self._user_sessions[session.user_id]

        del self._sessions[session_id]
        return True

    async def list_user_sessions(self, user_id: str) -> List[SessionData]:
        """List all sessions for a user."""
        session_ids = self._user_sessions.get(user_id, [])
        sessions = []
        for session_id in session_ids:
            session = await self.get_session(session_id)
            if session:
                sessions.append(session)
        return sessions

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        expired_session_ids = []
        for session_id, session in self._sessions.items():
            if session.is_expired():
                expired_session_ids.append(session_id)

        for session_id in expired_session_ids:
            await self.delete_session(session_id)

        return len(expired_session_ids)

    async def get_all_sessions(self) -> List[SessionData]:
        """Get all active sessions."""
        active_sessions = []
        for session in self._sessions.values():
            if not session.is_expired():
                active_sessions.append(session)
        return active_sessions


class RedisSessionStore:
    """Redis-based session storage."""

    def __init__(self, redis_url: str):
        self._redis_url = redis_url
        self._redis: Optional[redis.Redis] = None

    async def connect(self):
        """Connect to Redis."""
        if not REDIS_AVAILABLE:
            raise RuntimeError("Redis is not available. Install with: pip install redis")

        self._redis = redis.from_url(self._redis_url)
        await self._redis.ping()

    async def disconnect(self):
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.close()

    def _session_key(self, session_id: str) -> str:
        """Generate Redis key for session."""
        return f"specify:session:{session_id}"

    def _user_sessions_key(self, user_id: str) -> str:
        """Generate Redis key for user sessions."""
        return f"specify:user_sessions:{user_id}"

    async def create_session(
        self,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SessionData:
        """Create a new session."""
        settings = get_settings()
        session_id = str(uuid.uuid4())
        now = datetime.now()

        session = SessionData(
            id=session_id,
            user_id=user_id,
            created_at=now,
            last_activity=now,
            expires_at=now + timedelta(minutes=settings.session_timeout_minutes),
            metadata=metadata or {},
            active_operations=[]
        )

        # Store session in Redis
        session_key = self._session_key(session_id)
        await self._redis.setex(
            session_key,
            timedelta(minutes=settings.session_timeout_minutes),
            json.dumps(session.to_dict())
        )

        # Track user sessions
        if user_id:
            user_sessions_key = self._user_sessions_key(user_id)
            await self._redis.lpush(user_sessions_key, session_id)
            await self._redis.expire(user_sessions_key, settings.session_timeout_minutes * 60)

            # Enforce max sessions per user
            session_count = await self._redis.llen(user_sessions_key)
            if session_count > settings.max_sessions_per_user:
                # Remove oldest sessions
                sessions_to_remove = session_count - settings.max_sessions_per_user
                for _ in range(sessions_to_remove):
                    old_session_id = await self._redis.rpop(user_sessions_key)
                    if old_session_id:
                        old_session_key = self._session_key(old_session_id.decode())
                        await self._redis.delete(old_session_key)

        return session

    async def get_session(self, session_id: str) -> Optional[SessionData]:
        """Get session by ID."""
        session_key = self._session_key(session_id)
        session_data = await self._redis.get(session_key)

        if not session_data:
            return None

        try:
            session_dict = json.loads(session_data)
            return SessionData.from_dict(session_dict)
        except (json.JSONDecodeError, KeyError, ValueError):
            logger.error(f"Failed to parse session data for {session_id}")
            await self._redis.delete(session_key)
            return None

    async def update_session(
        self,
        session_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        extend_timeout: bool = True
    ) -> Optional[SessionData]:
        """Update session data."""
        session = await self.get_session(session_id)
        if not session:
            return None

        if metadata:
            session.metadata.update(metadata)

        if extend_timeout:
            session.extend_expiration()

        # Update in Redis
        settings = get_settings()
        session_key = self._session_key(session_id)
        await self._redis.setex(
            session_key,
            timedelta(minutes=settings.session_timeout_minutes),
            json.dumps(session.to_dict())
        )

        return session

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        session_key = self._session_key(session_id)
        result = await self._redis.delete(session_key)

        # Also remove from user sessions (best effort)
        # This is less efficient but ensures cleanup
        return result > 0

    async def list_user_sessions(self, user_id: str) -> List[SessionData]:
        """List all sessions for a user."""
        user_sessions_key = self._user_sessions_key(user_id)
        session_ids = await self._redis.lrange(user_sessions_key, 0, -1)

        sessions = []
        for session_id_bytes in session_ids:
            session_id = session_id_bytes.decode()
            session = await self.get_session(session_id)
            if session:
                sessions.append(session)

        return sessions


class SessionManager:
    """Main session manager that handles both in-memory and Redis storage."""

    def __init__(self):
        self._store = None
        self._cleanup_task: Optional[asyncio.Task] = None

    async def initialize(self):
        """Initialize the session manager."""
        settings = get_settings()

        if settings.redis_enabled and settings.redis_url:
            logger.info("Initializing Redis session store")
            self._store = RedisSessionStore(settings.redis_url)
            await self._store.connect()
        else:
            logger.info("Initializing in-memory session store")
            self._store = InMemorySessionStore()

        # Start cleanup task
        if isinstance(self._store, InMemorySessionStore):
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def cleanup(self):
        """Cleanup session manager."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        if isinstance(self._store, RedisSessionStore):
            await self._store.disconnect()

    async def _cleanup_loop(self):
        """Periodic cleanup of expired sessions."""
        settings = get_settings()
        interval = settings.session_cleanup_interval_minutes * 60

        while True:
            try:
                await asyncio.sleep(interval)
                if isinstance(self._store, InMemorySessionStore):
                    cleaned = await self._store.cleanup_expired_sessions()
                    if cleaned > 0:
                        logger.info(f"Cleaned up {cleaned} expired sessions")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in session cleanup: {e}")

    async def create_session(
        self,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SessionData:
        """Create a new session."""
        return await self._store.create_session(user_id, metadata)

    async def get_session(self, session_id: str) -> Optional[SessionData]:
        """Get session by ID."""
        return await self._store.get_session(session_id)

    async def update_session(
        self,
        session_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        extend_timeout: bool = True
    ) -> Optional[SessionData]:
        """Update session data."""
        return await self._store.update_session(session_id, metadata, extend_timeout)

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        return await self._store.delete_session(session_id)

    async def list_user_sessions(self, user_id: str) -> List[SessionData]:
        """List all sessions for a user."""
        return await self._store.list_user_sessions(user_id)

    async def add_operation(self, session_id: str, operation_id: str) -> bool:
        """Add an active operation to a session."""
        session = await self.get_session(session_id)
        if not session:
            return False

        if operation_id not in session.active_operations:
            session.active_operations.append(operation_id)
            await self.update_session(session_id, extend_timeout=True)

        return True

    async def remove_operation(self, session_id: str, operation_id: str) -> bool:
        """Remove an active operation from a session."""
        session = await self.get_session(session_id)
        if not session:
            return False

        if operation_id in session.active_operations:
            session.active_operations.remove(operation_id)
            await self.update_session(session_id, extend_timeout=False)

        return True