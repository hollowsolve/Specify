"""
Agent Factory - Creates and manages specialized agents.

This module implements a factory pattern for creating specialized agents
based on task requirements, with support for agent pooling, configuration,
and plugin systems.
"""

import importlib
import inspect
from typing import Dict, List, Type, Optional, Any, Set
from collections import defaultdict
from dataclasses import dataclass

from .base_agent import BaseAgent
from ..models import AgentType, TaskType, Task, AgentCapability


@dataclass
class AgentPool:
    """Manages a pool of agents of the same type."""
    agent_type: AgentType
    max_agents: int
    idle_agents: List[BaseAgent]
    busy_agents: Set[BaseAgent]
    total_created: int = 0

    def has_idle_agent(self) -> bool:
        """Check if there's an idle agent available."""
        return len(self.idle_agents) > 0

    def can_create_agent(self) -> bool:
        """Check if we can create a new agent."""
        return self.total_created < self.max_agents

    def get_idle_agent(self) -> Optional[BaseAgent]:
        """Get an idle agent from the pool."""
        if self.idle_agents:
            agent = self.idle_agents.pop()
            self.busy_agents.add(agent)
            return agent
        return None

    def return_agent(self, agent: BaseAgent):
        """Return an agent to the idle pool."""
        if agent in self.busy_agents:
            self.busy_agents.remove(agent)
            self.idle_agents.append(agent)

    def add_agent(self, agent: BaseAgent):
        """Add a new agent to the pool."""
        self.idle_agents.append(agent)
        self.total_created += 1

    def get_utilization(self) -> float:
        """Get current utilization percentage."""
        if self.total_created == 0:
            return 0.0
        return len(self.busy_agents) / self.total_created * 100.0


class AgentFactory:
    """
    Factory for creating and managing specialized agents.

    Features:
    - Agent type registration and creation
    - Agent pooling and reuse
    - Configuration management
    - Plugin system for custom agents
    - Resource monitoring and limits
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.agent_classes: Dict[AgentType, Type[BaseAgent]] = {}
        self.agent_pools: Dict[AgentType, AgentPool] = {}
        self.agent_capabilities: Dict[AgentType, AgentCapability] = {}

        # Configuration
        self.default_pool_size = self.config.get('default_pool_size', 2)
        self.max_total_agents = self.config.get('max_total_agents', 20)
        self.enable_pooling = self.config.get('enable_pooling', True)

        # Plugin system
        self.plugin_directories = self.config.get('plugin_directories', [])

        # Initialize built-in agent types
        self._register_builtin_agents()

        # Load plugins
        self._load_plugins()

    def register_agent_class(self, agent_type: AgentType, agent_class: Type[BaseAgent],
                           capability: AgentCapability = None):
        """
        Register an agent class for a specific agent type.

        Args:
            agent_type: Type of agent
            agent_class: Class that implements the agent
            capability: Agent capabilities description
        """
        if not issubclass(agent_class, BaseAgent):
            raise ValueError(f"Agent class must inherit from BaseAgent")

        self.agent_classes[agent_type] = agent_class

        # Create agent pool if pooling is enabled
        if self.enable_pooling:
            pool_size = self.config.get(f'{agent_type.value}_pool_size', self.default_pool_size)
            self.agent_pools[agent_type] = AgentPool(
                agent_type=agent_type,
                max_agents=pool_size,
                idle_agents=[],
                busy_agents=set()
            )

        # Register capability
        if capability:
            self.agent_capabilities[agent_type] = capability
        else:
            # Create default capability from agent class
            self.agent_capabilities[agent_type] = self._extract_capability_from_class(
                agent_class, agent_type
            )

        print(f"Registered agent class {agent_class.__name__} for type {agent_type.value}")

    def create_agent(self, agent_type: AgentType, config: Dict[str, Any] = None) -> BaseAgent:
        """
        Create an agent of the specified type.

        Args:
            agent_type: Type of agent to create
            config: Configuration for the agent

        Returns:
            Created agent instance
        """
        if agent_type not in self.agent_classes:
            raise ValueError(f"No agent class registered for type {agent_type}")

        # Check if we can get from pool
        if self.enable_pooling and agent_type in self.agent_pools:
            pool = self.agent_pools[agent_type]
            if pool.has_idle_agent():
                agent = pool.get_idle_agent()
                if config:
                    agent.update_config(config)
                return agent

        # Create new agent if pool is empty or pooling disabled
        agent_class = self.agent_classes[agent_type]
        agent_config = self._merge_config(agent_type, config)

        try:
            agent = agent_class(config=agent_config)

            # Add to pool if pooling is enabled
            if (self.enable_pooling and
                agent_type in self.agent_pools and
                self.agent_pools[agent_type].can_create_agent()):

                self.agent_pools[agent_type].add_agent(agent)

            return agent

        except Exception as e:
            raise RuntimeError(f"Failed to create agent of type {agent_type}: {e}")

    def get_agent_for_task(self, task: Task) -> Optional[BaseAgent]:
        """
        Get the best agent for executing a specific task.

        Args:
            task: Task to find agent for

        Returns:
            Agent that can handle the task, or None if not available
        """
        required_type = task.required_agent_type

        # Check if we have an agent of the required type
        if required_type not in self.agent_classes:
            return None

        # Try to get from pool first
        if self.enable_pooling and required_type in self.agent_pools:
            pool = self.agent_pools[required_type]
            if pool.has_idle_agent():
                agent = pool.get_idle_agent()
                if agent.can_handle(task):
                    return agent
                else:
                    # Return agent to pool if it can't handle the task
                    pool.return_agent(agent)

        # Create new agent if needed and possible
        try:
            agent = self.create_agent(required_type, task.agent_config)
            if agent.can_handle(task):
                return agent
        except Exception as e:
            print(f"Failed to create agent for task {task.task_id}: {e}")

        return None

    def return_agent(self, agent: BaseAgent):
        """
        Return an agent to the pool after task completion.

        Args:
            agent: Agent to return
        """
        if not self.enable_pooling:
            return

        agent_type = agent.get_agent_type()
        if agent_type in self.agent_pools:
            pool = self.agent_pools[agent_type]
            pool.return_agent(agent)

    def get_available_agent_types(self) -> List[AgentType]:
        """Get list of available agent types."""
        return list(self.agent_classes.keys())

    def get_agent_capability(self, agent_type: AgentType) -> Optional[AgentCapability]:
        """Get capability information for an agent type."""
        return self.agent_capabilities.get(agent_type)

    def estimate_resource_requirements(self, tasks: List[Task]) -> Dict[AgentType, int]:
        """
        Estimate resource requirements for a list of tasks.

        Args:
            tasks: List of tasks to analyze

        Returns:
            Dictionary mapping agent types to required counts
        """
        requirements = defaultdict(int)

        for task in tasks:
            requirements[task.required_agent_type] += 1

        return dict(requirements)

    def can_handle_workload(self, tasks: List[Task]) -> bool:
        """
        Check if the factory can handle the given workload.

        Args:
            tasks: List of tasks to check

        Returns:
            True if workload can be handled
        """
        requirements = self.estimate_resource_requirements(tasks)

        for agent_type, count in requirements.items():
            if agent_type not in self.agent_classes:
                return False

            if self.enable_pooling:
                pool = self.agent_pools.get(agent_type)
                if pool and count > pool.max_agents:
                    return False

        # Check total agent limit
        total_required = sum(requirements.values())
        if total_required > self.max_total_agents:
            return False

        return True

    def get_pool_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all agent pools."""
        status = {}

        for agent_type, pool in self.agent_pools.items():
            status[agent_type.value] = {
                'max_agents': pool.max_agents,
                'total_created': pool.total_created,
                'idle_agents': len(pool.idle_agents),
                'busy_agents': len(pool.busy_agents),
                'utilization': pool.get_utilization()
            }

        return status

    def scale_pool(self, agent_type: AgentType, new_size: int) -> bool:
        """
        Scale an agent pool to a new size.

        Args:
            agent_type: Type of agent pool to scale
            new_size: New maximum size for the pool

        Returns:
            True if scaling was successful
        """
        if agent_type not in self.agent_pools:
            return False

        pool = self.agent_pools[agent_type]

        if new_size < pool.total_created:
            # Scaling down - remove idle agents
            while len(pool.idle_agents) > new_size and pool.idle_agents:
                agent = pool.idle_agents.pop()
                agent.shutdown()
                pool.total_created -= 1

        pool.max_agents = new_size
        return True

    def shutdown_all_agents(self):
        """Shutdown all agents in all pools."""
        for pool in self.agent_pools.values():
            # Shutdown idle agents
            for agent in pool.idle_agents:
                agent.shutdown()

            # Shutdown busy agents
            for agent in pool.busy_agents:
                agent.shutdown()

            pool.idle_agents.clear()
            pool.busy_agents.clear()
            pool.total_created = 0

    def _register_builtin_agents(self):
        """Register built-in agent types."""
        try:
            # Import and register specialized agents
            from .specialized_agents.code_writer_agent import CodeWriterAgent
            from .specialized_agents.researcher_agent import ResearcherAgent
            from .specialized_agents.tester_agent import TesterAgent

            self.register_agent_class(AgentType.CODE_WRITER, CodeWriterAgent)
            self.register_agent_class(AgentType.RESEARCHER, ResearcherAgent)
            self.register_agent_class(AgentType.TESTER, TesterAgent)

        except ImportError as e:
            print(f"Warning: Could not import some built-in agents: {e}")

        # Register additional built-in agents as they become available
        self._register_additional_builtins()

    def _register_additional_builtins(self):
        """Register additional built-in agents if available."""
        builtin_agents = [
            (AgentType.REVIEWER, 'reviewer_agent', 'ReviewerAgent'),
            (AgentType.DOCUMENTER, 'documenter_agent', 'DocumenterAgent'),
            (AgentType.DEBUGGER, 'debugger_agent', 'DebuggerAgent'),
            (AgentType.ANALYZER, 'analyzer_agent', 'AnalyzerAgent')
        ]

        for agent_type, module_name, class_name in builtin_agents:
            try:
                module = importlib.import_module(f'.specialized_agents.{module_name}', __package__)
                agent_class = getattr(module, class_name)
                self.register_agent_class(agent_type, agent_class)
            except (ImportError, AttributeError):
                # Agent not implemented yet, skip
                pass

    def _load_plugins(self):
        """Load agent plugins from configured directories."""
        for plugin_dir in self.plugin_directories:
            try:
                self._load_plugins_from_directory(plugin_dir)
            except Exception as e:
                print(f"Warning: Failed to load plugins from {plugin_dir}: {e}")

    def _load_plugins_from_directory(self, plugin_dir: str):
        """Load agent plugins from a specific directory."""
        import os
        import sys

        if not os.path.isdir(plugin_dir):
            return

        # Add plugin directory to Python path
        if plugin_dir not in sys.path:
            sys.path.insert(0, plugin_dir)

        # Scan for Python files
        for filename in os.listdir(plugin_dir):
            if filename.endswith('.py') and not filename.startswith('_'):
                module_name = filename[:-3]
                try:
                    module = importlib.import_module(module_name)
                    self._register_agents_from_module(module)
                except Exception as e:
                    print(f"Warning: Failed to load plugin {module_name}: {e}")

    def _register_agents_from_module(self, module):
        """Register agent classes found in a module."""
        for name in dir(module):
            obj = getattr(module, name)

            if (inspect.isclass(obj) and
                issubclass(obj, BaseAgent) and
                obj != BaseAgent):

                # Try to determine agent type from class
                try:
                    # Instantiate temporarily to get agent type
                    temp_instance = obj()
                    agent_type = temp_instance.get_agent_type()
                    temp_instance.shutdown()

                    self.register_agent_class(agent_type, obj)

                except Exception as e:
                    print(f"Warning: Could not register agent class {name}: {e}")

    def _extract_capability_from_class(self, agent_class: Type[BaseAgent],
                                     agent_type: AgentType) -> AgentCapability:
        """Extract capability information from an agent class."""
        # Create temporary instance to get information
        try:
            temp_instance = agent_class()
            supported_types = temp_instance.get_supported_task_types()
            temp_instance.shutdown()

            return AgentCapability(
                agent_type=agent_type,
                supported_task_types=supported_types,
                max_concurrent_tasks=1,  # Default
                complexity_limit=5.0     # Default
            )

        except Exception:
            # Fallback capability
            return AgentCapability(
                agent_type=agent_type,
                supported_task_types=[],
                max_concurrent_tasks=1,
                complexity_limit=5.0
            )

    def _merge_config(self, agent_type: AgentType, task_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Merge global and task-specific configuration for an agent."""
        merged_config = {}

        # Start with global config
        merged_config.update(self.config.get('global_agent_config', {}))

        # Add agent-type specific config
        type_config_key = f'{agent_type.value}_config'
        merged_config.update(self.config.get(type_config_key, {}))

        # Add task-specific config
        if task_config:
            merged_config.update(task_config)

        return merged_config

    def get_factory_stats(self) -> Dict[str, Any]:
        """Get comprehensive factory statistics."""
        total_agents = sum(pool.total_created for pool in self.agent_pools.values())
        total_busy = sum(len(pool.busy_agents) for pool in self.agent_pools.values())
        total_idle = sum(len(pool.idle_agents) for pool in self.agent_pools.values())

        return {
            'registered_agent_types': len(self.agent_classes),
            'agent_types': [t.value for t in self.agent_classes.keys()],
            'total_agents_created': total_agents,
            'total_busy_agents': total_busy,
            'total_idle_agents': total_idle,
            'overall_utilization': (total_busy / total_agents * 100) if total_agents > 0 else 0,
            'pool_status': self.get_pool_status(),
            'max_total_agents': self.max_total_agents,
            'pooling_enabled': self.enable_pooling
        }

    def optimize_pools(self):
        """Optimize agent pools based on usage patterns."""
        # This could implement more sophisticated optimization logic
        # For now, just clean up shutdown agents
        for pool in self.agent_pools.values():
            # Remove shutdown agents from idle pool
            pool.idle_agents = [agent for agent in pool.idle_agents
                              if agent.state != 'shutdown']

            # Update count
            pool.total_created = len(pool.idle_agents) + len(pool.busy_agents)