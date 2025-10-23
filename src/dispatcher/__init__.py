"""
Multi-Agent Dispatcher System

A sophisticated orchestration system that converts finalized specifications
into working code through coordinated multi-agent execution.

Main Components:
- AgentDispatcher: Main orchestrator
- ExecutionGraph: DAG-based task management
- TaskDecomposer: Intelligent requirement breakdown
- DependencyResolver: Smart dependency detection
- AgentFactory: Specialized agent creation and management
- Coordinator: Parallel execution management
- MessageBus: Inter-agent communication
- StateManager: Execution state tracking

Usage:
    from src.dispatcher import AgentDispatcher

    config = {
        'llm_client': your_llm_client,
        'max_parallel_agents': 4,
        'enable_parallel_execution': True
    }

    dispatcher = AgentDispatcher(config)
    result = dispatcher.dispatch(specification)
"""

from .agent_dispatcher import AgentDispatcher
from .models import (
    ExecutionResult, ExecutionStatus, Task, TaskType, AgentType,
    TaskStatus, AgentResult, ExecutionMetrics
)

__version__ = "1.0.0"
__author__ = "Specify AI System"

__all__ = [
    'AgentDispatcher',
    'ExecutionResult',
    'ExecutionStatus',
    'Task',
    'TaskType',
    'AgentType',
    'TaskStatus',
    'AgentResult',
    'ExecutionMetrics'
]