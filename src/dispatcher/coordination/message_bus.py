"""
Message Bus - Inter-agent communication system.

This module implements a publish-subscribe message bus for communication
between agents and system components, with support for event replay,
filtering, and monitoring.
"""

import asyncio
import threading
import time
from typing import Dict, List, Callable, Any, Optional, Set
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json

from ..models import AgentMessage


class MessagePriority(Enum):
    """Message priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class MessageStatus(Enum):
    """Message delivery status."""
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class EnhancedMessage(AgentMessage):
    """Enhanced message with additional metadata."""
    priority: MessagePriority = MessagePriority.NORMAL
    expires_at: Optional[datetime] = None
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    status: MessageStatus = MessageStatus.PENDING
    delivered_to: Set[str] = field(default_factory=set)

    def is_expired(self) -> bool:
        """Check if message has expired."""
        return self.expires_at is not None and datetime.now() > self.expires_at

    def should_retry(self) -> bool:
        """Check if message should be retried."""
        return self.retry_count < self.max_retries and not self.is_expired()


@dataclass
class Subscription:
    """Represents a subscription to a message topic."""
    subscriber_id: str
    topic_pattern: str
    callback: Callable[[EnhancedMessage], None]
    filter_func: Optional[Callable[[EnhancedMessage], bool]] = None
    created_at: datetime = field(default_factory=datetime.now)
    message_count: int = 0
    last_message_at: Optional[datetime] = None


class MessageBus:
    """
    High-performance message bus for inter-agent communication.

    Features:
    - Publish-subscribe pattern
    - Topic-based routing with wildcard support
    - Message priorities and expiration
    - Event replay and history
    - Message filtering
    - Delivery guarantees and retries
    - Performance monitoring
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

        # Core messaging
        self.subscriptions: Dict[str, List[Subscription]] = defaultdict(list)
        self.message_history: deque = deque(maxlen=self.config.get('max_history', 10000))
        self.pending_messages: Dict[str, EnhancedMessage] = {}

        # Threading and async support
        self.lock = threading.RLock()
        self.running = False
        self.worker_thread: Optional[threading.Thread] = None

        # Performance tracking
        self.stats = {
            'messages_published': 0,
            'messages_delivered': 0,
            'messages_failed': 0,
            'subscriptions_count': 0,
            'topics_count': 0
        }

        # Configuration
        self.enable_history = self.config.get('enable_history', True)
        self.enable_retry = self.config.get('enable_retry', True)
        self.worker_interval = self.config.get('worker_interval', 0.1)
        self.max_delivery_time = self.config.get('max_delivery_time', 30.0)

    def start(self):
        """Start the message bus worker thread."""
        if self.running:
            return

        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

    def stop(self):
        """Stop the message bus."""
        self.running = False
        if self.worker_thread:
            self.worker_thread.join(timeout=5.0)

    def publish(self, topic: str, message_type: str, data: Dict[str, Any],
               sender_id: str = "system", priority: MessagePriority = MessagePriority.NORMAL,
               expires_in_seconds: Optional[float] = None,
               correlation_id: Optional[str] = None) -> str:
        """
        Publish a message to a topic.

        Args:
            topic: Topic to publish to
            message_type: Type of message
            data: Message data
            sender_id: ID of the sender
            priority: Message priority
            expires_in_seconds: Message expiration time
            correlation_id: Correlation ID for request-response patterns

        Returns:
            Message ID
        """
        # Create enhanced message
        expires_at = None
        if expires_in_seconds:
            expires_at = datetime.now().timestamp() + expires_in_seconds
            expires_at = datetime.fromtimestamp(expires_at)

        message = EnhancedMessage(
            sender_id=sender_id,
            message_type=message_type,
            data=data,
            priority=priority,
            expires_at=expires_at,
            correlation_id=correlation_id
        )

        with self.lock:
            # Add to pending messages for delivery
            self.pending_messages[message.message_id] = message

            # Add to history if enabled
            if self.enable_history:
                self.message_history.append({
                    'message_id': message.message_id,
                    'topic': topic,
                    'message': message,
                    'published_at': datetime.now(),
                    'delivered_to': []
                })

            # Update stats
            self.stats['messages_published'] += 1

        # Trigger immediate delivery attempt
        self._deliver_message(topic, message)

        return message.message_id

    def subscribe(self, subscriber_id: str, topic_pattern: str,
                 callback: Callable[[EnhancedMessage], None],
                 filter_func: Optional[Callable[[EnhancedMessage], bool]] = None) -> str:
        """
        Subscribe to messages on a topic pattern.

        Args:
            subscriber_id: ID of the subscriber
            topic_pattern: Topic pattern (supports wildcards)
            callback: Function to call when message arrives
            filter_func: Optional filter function

        Returns:
            Subscription ID
        """
        subscription = Subscription(
            subscriber_id=subscriber_id,
            topic_pattern=topic_pattern,
            callback=callback,
            filter_func=filter_func
        )

        with self.lock:
            self.subscriptions[topic_pattern].append(subscription)
            self.stats['subscriptions_count'] += 1

            # Update topics count
            self.stats['topics_count'] = len(self.subscriptions)

        return f"{subscriber_id}:{topic_pattern}:{subscription.created_at.timestamp()}"

    def unsubscribe(self, subscriber_id: str, topic_pattern: str = None):
        """
        Unsubscribe from topics.

        Args:
            subscriber_id: ID of the subscriber
            topic_pattern: Specific topic pattern, or None to unsubscribe from all
        """
        with self.lock:
            if topic_pattern:
                # Unsubscribe from specific topic
                if topic_pattern in self.subscriptions:
                    self.subscriptions[topic_pattern] = [
                        sub for sub in self.subscriptions[topic_pattern]
                        if sub.subscriber_id != subscriber_id
                    ]
                    if not self.subscriptions[topic_pattern]:
                        del self.subscriptions[topic_pattern]
            else:
                # Unsubscribe from all topics
                for topic in list(self.subscriptions.keys()):
                    self.subscriptions[topic] = [
                        sub for sub in self.subscriptions[topic]
                        if sub.subscriber_id != subscriber_id
                    ]
                    if not self.subscriptions[topic]:
                        del self.subscriptions[topic]

            # Update stats
            self.stats['subscriptions_count'] = sum(
                len(subs) for subs in self.subscriptions.values()
            )
            self.stats['topics_count'] = len(self.subscriptions)

    def replay_messages(self, subscriber_id: str, topic_pattern: str,
                       since: datetime = None, message_filter: Callable = None) -> int:
        """
        Replay historical messages to a subscriber.

        Args:
            subscriber_id: ID of the subscriber
            topic_pattern: Topic pattern to replay
            since: Only replay messages since this time
            message_filter: Optional filter function

        Returns:
            Number of messages replayed
        """
        if not self.enable_history:
            return 0

        replayed = 0
        subscriptions = self._find_matching_subscriptions(topic_pattern)

        for hist_entry in self.message_history:
            message = hist_entry['message']
            topic = hist_entry['topic']
            published_at = hist_entry['published_at']

            # Check time filter
            if since and published_at < since:
                continue

            # Check message filter
            if message_filter and not message_filter(message):
                continue

            # Deliver to matching subscriptions
            for subscription in subscriptions:
                if subscription.subscriber_id == subscriber_id:
                    try:
                        subscription.callback(message)
                        replayed += 1
                    except Exception as e:
                        print(f"Error replaying message to {subscriber_id}: {e}")

        return replayed

    def get_message_history(self, topic_pattern: str = None,
                          since: datetime = None) -> List[Dict[str, Any]]:
        """
        Get message history.

        Args:
            topic_pattern: Filter by topic pattern
            since: Only include messages since this time

        Returns:
            List of historical messages
        """
        if not self.enable_history:
            return []

        history = []
        for entry in self.message_history:
            topic = entry['topic']
            published_at = entry['published_at']

            # Check topic filter
            if topic_pattern and not self._topic_matches_pattern(topic, topic_pattern):
                continue

            # Check time filter
            if since and published_at < since:
                continue

            history.append({
                'message_id': entry['message_id'],
                'topic': topic,
                'message_type': entry['message'].message_type,
                'sender_id': entry['message'].sender_id,
                'published_at': published_at.isoformat(),
                'delivered_to': list(entry['delivered_to']),
                'data': entry['message'].data
            })

        return history

    def _worker_loop(self):
        """Main worker loop for message processing."""
        while self.running:
            try:
                self._process_pending_messages()
                self._cleanup_expired_messages()
                time.sleep(self.worker_interval)
            except Exception as e:
                print(f"Error in message bus worker: {e}")

    def _process_pending_messages(self):
        """Process pending messages for retry delivery."""
        if not self.enable_retry:
            return

        with self.lock:
            expired_messages = []
            for message_id, message in list(self.pending_messages.items()):
                if message.is_expired():
                    message.status = MessageStatus.EXPIRED
                    expired_messages.append(message_id)
                elif message.should_retry():
                    # Attempt redelivery
                    self._deliver_message_to_subscribers(message)

            # Remove expired messages
            for message_id in expired_messages:
                if message_id in self.pending_messages:
                    del self.pending_messages[message_id]
                self.stats['messages_failed'] += 1

    def _cleanup_expired_messages(self):
        """Clean up expired and delivered messages."""
        current_time = datetime.now()

        with self.lock:
            # Remove messages that have been pending too long
            to_remove = []
            for message_id, message in self.pending_messages.items():
                age = (current_time - message.timestamp).total_seconds()
                if age > self.max_delivery_time:
                    to_remove.append(message_id)

            for message_id in to_remove:
                del self.pending_messages[message_id]

    def _deliver_message(self, topic: str, message: EnhancedMessage):
        """Deliver a message to all matching subscribers."""
        subscriptions = self._find_matching_subscriptions(topic)

        if not subscriptions:
            # No subscribers, mark as delivered
            message.status = MessageStatus.DELIVERED
            with self.lock:
                if message.message_id in self.pending_messages:
                    del self.pending_messages[message.message_id]
            return

        self._deliver_message_to_subscribers(message, subscriptions)

    def _deliver_message_to_subscribers(self, message: EnhancedMessage,
                                      subscriptions: List[Subscription] = None):
        """Deliver message to specific subscribers."""
        if subscriptions is None:
            # Find all matching subscriptions (for retries)
            subscriptions = []
            for topic_pattern in self.subscriptions:
                if self._topic_matches_pattern(topic_pattern, topic_pattern):  # Need topic from context
                    subscriptions.extend(self.subscriptions[topic_pattern])

        delivered_count = 0
        failed_deliveries = []

        for subscription in subscriptions:
            # Apply filter if present
            if subscription.filter_func and not subscription.filter_func(message):
                continue

            try:
                subscription.callback(message)
                message.delivered_to.add(subscription.subscriber_id)
                subscription.message_count += 1
                subscription.last_message_at = datetime.now()
                delivered_count += 1

            except Exception as e:
                failed_deliveries.append((subscription.subscriber_id, str(e)))
                print(f"Failed to deliver message {message.message_id} to {subscription.subscriber_id}: {e}")

        # Update message status
        if delivered_count > 0:
            message.status = MessageStatus.DELIVERED
            self.stats['messages_delivered'] += 1

            # Remove from pending if fully delivered
            with self.lock:
                if message.message_id in self.pending_messages:
                    del self.pending_messages[message.message_id]

        elif failed_deliveries and message.should_retry():
            message.retry_count += 1
            message.status = MessageStatus.PENDING

        else:
            message.status = MessageStatus.FAILED
            self.stats['messages_failed'] += 1
            with self.lock:
                if message.message_id in self.pending_messages:
                    del self.pending_messages[message.message_id]

    def _find_matching_subscriptions(self, topic: str) -> List[Subscription]:
        """Find all subscriptions that match a topic."""
        matching = []

        for topic_pattern, subscriptions in self.subscriptions.items():
            if self._topic_matches_pattern(topic, topic_pattern):
                matching.extend(subscriptions)

        return matching

    def _topic_matches_pattern(self, topic: str, pattern: str) -> bool:
        """Check if a topic matches a pattern (with wildcard support)."""
        # Simple wildcard matching
        if pattern == "*":
            return True

        if "*" not in pattern:
            return topic == pattern

        # Convert pattern to regex
        import re
        regex_pattern = pattern.replace("*", ".*")
        return re.match(f"^{regex_pattern}$", topic) is not None

    def get_stats(self) -> Dict[str, Any]:
        """Get message bus statistics."""
        with self.lock:
            stats = self.stats.copy()
            stats.update({
                'pending_messages': len(self.pending_messages),
                'history_size': len(self.message_history),
                'worker_running': self.running,
                'subscriptions_by_topic': {
                    topic: len(subs) for topic, subs in self.subscriptions.items()
                }
            })

        return stats

    def get_subscription_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get detailed subscription statistics."""
        stats = {}

        with self.lock:
            for topic_pattern, subscriptions in self.subscriptions.items():
                topic_stats = {
                    'subscriber_count': len(subscriptions),
                    'subscribers': []
                }

                for sub in subscriptions:
                    topic_stats['subscribers'].append({
                        'subscriber_id': sub.subscriber_id,
                        'created_at': sub.created_at.isoformat(),
                        'message_count': sub.message_count,
                        'last_message_at': sub.last_message_at.isoformat() if sub.last_message_at else None
                    })

                stats[topic_pattern] = topic_stats

        return stats

    def clear_history(self):
        """Clear message history."""
        with self.lock:
            self.message_history.clear()

    def reset_stats(self):
        """Reset statistics counters."""
        with self.lock:
            self.stats = {
                'messages_published': 0,
                'messages_delivered': 0,
                'messages_failed': 0,
                'subscriptions_count': len([sub for subs in self.subscriptions.values() for sub in subs]),
                'topics_count': len(self.subscriptions)
            }