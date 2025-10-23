"""
Agent system for specialized task execution.

Components:
- BaseAgent: Abstract base class for all agents
- AgentFactory: Creates and manages agent instances
- Specialized agents for different task types
"""

from .base_agent import BaseAgent
from .agent_factory import AgentFactory

__all__ = ['BaseAgent', 'AgentFactory']