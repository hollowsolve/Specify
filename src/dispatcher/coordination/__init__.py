"""
Coordination system for managing distributed execution.

Components:
- Coordinator: Manages parallel agent execution
- MessageBus: Inter-agent communication system
- StateManager: Execution state tracking and persistence
"""

from .coordinator import Coordinator
from .message_bus import MessageBus
from .state_manager import StateManager

__all__ = ['Coordinator', 'MessageBus', 'StateManager']