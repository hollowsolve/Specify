"""
Execution Graph - Directed Acyclic Graph (DAG) for task execution.

This module implements a sophisticated execution graph that represents tasks
and their dependencies as a DAG, with capabilities for topological sorting,
parallel execution detection, critical path analysis, and visualization.
"""

import networkx as nx
from typing import Dict, List, Set, Tuple, Optional, Any
from collections import defaultdict, deque
import json
from datetime import datetime

from ..models import (
    Task, TaskDependency, DependencyType, TaskStatus, ExecutionPlan,
    TaskType, AgentType
)


class ExecutionGraph:
    """
    Directed Acyclic Graph for managing task execution with dependencies.

    Features:
    - DAG validation and cycle detection
    - Topological sorting for execution order
    - Parallel execution opportunity detection
    - Critical path analysis
    - Dynamic graph modification
    - Visualization export
    """

    def __init__(self, graph_id: str = None):
        self.graph_id = graph_id or f"exec_graph_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.graph = nx.DiGraph()
        self.tasks: Dict[str, Task] = {}
        self.dependencies: Dict[str, TaskDependency] = {}
        self._execution_phases: Optional[List[List[str]]] = None
        self._critical_path: Optional[List[str]] = None
        self._is_dirty = True  # Track if graph needs recomputation

    def add_task(self, task: Task) -> bool:
        """
        Add a task to the execution graph.

        Args:
            task: Task to add

        Returns:
            bool: True if task was added successfully
        """
        if task.task_id in self.tasks:
            return False

        self.tasks[task.task_id] = task
        self.graph.add_node(
            task.task_id,
            task=task,
            complexity=task.estimated_complexity,
            task_type=task.task_type.value,
            agent_type=task.required_agent_type.value,
            priority=task.priority
        )
        self._mark_dirty()
        return True

    def add_dependency(self, dependency: TaskDependency) -> bool:
        """
        Add a dependency between two tasks.

        Args:
            dependency: TaskDependency object

        Returns:
            bool: True if dependency was added successfully
        """
        source_id = dependency.source_task_id
        target_id = dependency.target_task_id

        # Validate tasks exist
        if source_id not in self.tasks or target_id not in self.tasks:
            return False

        # Check for self-dependency
        if source_id == target_id:
            return False

        # Add edge to graph
        self.graph.add_edge(
            source_id,
            target_id,
            dependency=dependency,
            weight=self.tasks[source_id].estimated_complexity
        )

        # Update task dependency lists
        if target_id not in self.tasks[source_id].dependents:
            self.tasks[source_id].dependents.append(target_id)
        if source_id not in self.tasks[target_id].dependencies:
            self.tasks[target_id].dependencies.append(source_id)

        # Store dependency
        dep_key = f"{source_id}->{target_id}"
        self.dependencies[dep_key] = dependency

        self._mark_dirty()

        # Validate DAG property
        if not self.is_dag():
            # Remove the dependency that created the cycle
            self.remove_dependency(source_id, target_id)
            return False

        return True

    def remove_task(self, task_id: str) -> bool:
        """Remove a task and all its dependencies."""
        if task_id not in self.tasks:
            return False

        # Remove all dependencies involving this task
        dependencies_to_remove = []
        for dep_key, dep in self.dependencies.items():
            if dep.source_task_id == task_id or dep.target_task_id == task_id:
                dependencies_to_remove.append(dep_key)

        for dep_key in dependencies_to_remove:
            dep = self.dependencies[dep_key]
            self.remove_dependency(dep.source_task_id, dep.target_task_id)

        # Remove from graph and tasks
        self.graph.remove_node(task_id)
        del self.tasks[task_id]
        self._mark_dirty()
        return True

    def remove_dependency(self, source_id: str, target_id: str) -> bool:
        """Remove a dependency between two tasks."""
        if not self.graph.has_edge(source_id, target_id):
            return False

        # Remove from graph
        self.graph.remove_edge(source_id, target_id)

        # Update task dependency lists
        if target_id in self.tasks[source_id].dependents:
            self.tasks[source_id].dependents.remove(target_id)
        if source_id in self.tasks[target_id].dependencies:
            self.tasks[target_id].dependencies.remove(source_id)

        # Remove stored dependency
        dep_key = f"{source_id}->{target_id}"
        if dep_key in self.dependencies:
            del self.dependencies[dep_key]

        self._mark_dirty()
        return True

    def is_dag(self) -> bool:
        """Check if the graph is a valid DAG (no cycles)."""
        return nx.is_directed_acyclic_graph(self.graph)

    def find_cycles(self) -> List[List[str]]:
        """Find all cycles in the graph."""
        try:
            cycles = list(nx.simple_cycles(self.graph))
            return cycles
        except nx.NetworkXError:
            return []

    def get_executable_tasks(self, completed_tasks: Set[str]) -> List[str]:
        """
        Get tasks that are ready to execute (all dependencies satisfied).

        Args:
            completed_tasks: Set of completed task IDs

        Returns:
            List of task IDs ready for execution
        """
        executable = []

        for task_id, task in self.tasks.items():
            if (task.status in [TaskStatus.PENDING, TaskStatus.READY] and
                task.is_ready(completed_tasks)):
                executable.append(task_id)

        # Sort by priority (higher priority first)
        executable.sort(key=lambda tid: self.tasks[tid].priority, reverse=True)
        return executable

    def topological_sort(self) -> List[str]:
        """
        Return tasks in topological order.

        Returns:
            List of task IDs in dependency order
        """
        if not self.is_dag():
            raise ValueError("Cannot perform topological sort on graph with cycles")

        return list(nx.topological_sort(self.graph))

    def get_execution_phases(self) -> List[List[str]]:
        """
        Get tasks grouped by execution phases (parallel execution opportunities).

        Returns:
            List of phases, each containing task IDs that can run in parallel
        """
        if self._execution_phases is None or self._is_dirty:
            self._compute_execution_phases()
        return self._execution_phases

    def _compute_execution_phases(self):
        """Compute execution phases for parallel execution."""
        if not self.is_dag():
            raise ValueError("Cannot compute execution phases for graph with cycles")

        phases = []
        remaining_tasks = set(self.tasks.keys())
        completed_tasks = set()

        while remaining_tasks:
            # Find tasks with no incomplete dependencies
            ready_tasks = []
            for task_id in remaining_tasks:
                task = self.tasks[task_id]
                if task.is_ready(completed_tasks):
                    ready_tasks.append(task_id)

            if not ready_tasks:
                # Should not happen in a valid DAG
                raise ValueError("Graph appears to have unresolvable dependencies")

            # Sort by priority within the phase
            ready_tasks.sort(key=lambda tid: self.tasks[tid].priority, reverse=True)
            phases.append(ready_tasks)

            # Mark these tasks as completed for next iteration
            for task_id in ready_tasks:
                remaining_tasks.remove(task_id)
                completed_tasks.add(task_id)

        self._execution_phases = phases

    def get_critical_path(self) -> Tuple[List[str], float]:
        """
        Find the critical path (longest path) through the execution graph.

        Returns:
            Tuple of (task_ids_in_critical_path, total_duration)
        """
        if self._critical_path is None or self._is_dirty:
            self._compute_critical_path()

        total_duration = sum(self.tasks[task_id].estimated_complexity
                           for task_id in self._critical_path)
        return self._critical_path, total_duration

    def _compute_critical_path(self):
        """Compute the critical path using longest path algorithm."""
        if not self.is_dag():
            raise ValueError("Cannot compute critical path for graph with cycles")

        # Use negative weights to find longest path with shortest path algorithm
        graph_copy = self.graph.copy()
        for u, v, data in graph_copy.edges(data=True):
            graph_copy[u][v]['weight'] = -data.get('weight', 1)

        # Find the path with maximum total complexity
        try:
            # Get all possible paths and find the longest
            topo_order = list(nx.topological_sort(graph_copy))

            # Find start nodes (no predecessors)
            start_nodes = [n for n in graph_copy.nodes() if graph_copy.in_degree(n) == 0]
            # Find end nodes (no successors)
            end_nodes = [n for n in graph_copy.nodes() if graph_copy.out_degree(n) == 0]

            longest_path = []
            max_length = 0

            for start in start_nodes:
                for end in end_nodes:
                    try:
                        path_length = nx.shortest_path_length(
                            graph_copy, start, end, weight='weight'
                        )
                        if -path_length > max_length:
                            max_length = -path_length
                            longest_path = nx.shortest_path(
                                graph_copy, start, end, weight='weight'
                            )
                    except nx.NetworkXNoPath:
                        continue

            self._critical_path = longest_path

        except Exception:
            # Fallback: just use topological order
            self._critical_path = list(nx.topological_sort(self.graph))

    def get_parallel_execution_stats(self) -> Dict[str, Any]:
        """Get statistics about parallel execution opportunities."""
        phases = self.get_execution_phases()

        total_tasks = len(self.tasks)
        max_parallel = max(len(phase) for phase in phases) if phases else 0
        avg_parallel = sum(len(phase) for phase in phases) / len(phases) if phases else 0

        # Calculate theoretical vs actual execution time
        sequential_time = sum(task.estimated_complexity for task in self.tasks.values())

        parallel_time = 0
        for phase in phases:
            phase_time = max(self.tasks[task_id].estimated_complexity
                           for task_id in phase) if phase else 0
            parallel_time += phase_time

        efficiency = (sequential_time - parallel_time) / sequential_time if sequential_time > 0 else 0

        return {
            'total_tasks': total_tasks,
            'execution_phases': len(phases),
            'max_parallel_tasks': max_parallel,
            'avg_parallel_tasks': avg_parallel,
            'sequential_execution_time': sequential_time,
            'parallel_execution_time': parallel_time,
            'parallelization_efficiency': efficiency,
            'time_savings': sequential_time - parallel_time
        }

    def get_task_dependencies(self, task_id: str) -> Dict[str, List[str]]:
        """Get all dependencies and dependents for a task."""
        if task_id not in self.tasks:
            return {'dependencies': [], 'dependents': []}

        dependencies = list(self.graph.predecessors(task_id))
        dependents = list(self.graph.successors(task_id))

        return {
            'dependencies': dependencies,
            'dependents': dependents
        }

    def can_execute_in_parallel(self, task_ids: List[str]) -> bool:
        """Check if a set of tasks can be executed in parallel."""
        # Tasks can run in parallel if none depend on each other
        for i, task1 in enumerate(task_ids):
            for task2 in task_ids[i+1:]:
                if (nx.has_path(self.graph, task1, task2) or
                    nx.has_path(self.graph, task2, task1)):
                    return False
        return True

    def estimate_execution_time(self, max_parallel_agents: int = 4) -> float:
        """Estimate total execution time given parallel execution constraints."""
        phases = self.get_execution_phases()
        total_time = 0.0

        for phase in phases:
            if len(phase) <= max_parallel_agents:
                # All tasks in phase can run in parallel
                phase_time = max(self.tasks[task_id].estimated_complexity
                               for task_id in phase)
            else:
                # Need to batch tasks within the phase
                batches = [phase[i:i+max_parallel_agents]
                          for i in range(0, len(phase), max_parallel_agents)]
                phase_time = 0
                for batch in batches:
                    batch_time = max(self.tasks[task_id].estimated_complexity
                                   for task_id in batch)
                    phase_time += batch_time

            total_time += phase_time

        return total_time

    def get_resource_requirements(self) -> Dict[AgentType, int]:
        """Get the maximum concurrent resource requirements by agent type."""
        phases = self.get_execution_phases()
        max_requirements = defaultdict(int)

        for phase in phases:
            phase_requirements = defaultdict(int)
            for task_id in phase:
                agent_type = self.tasks[task_id].required_agent_type
                phase_requirements[agent_type] += 1

            for agent_type, count in phase_requirements.items():
                max_requirements[agent_type] = max(max_requirements[agent_type], count)

        return dict(max_requirements)

    def validate_graph(self) -> Tuple[bool, List[str]]:
        """
        Validate the graph for common issues.

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        # Check if it's a DAG
        if not self.is_dag():
            cycles = self.find_cycles()
            issues.append(f"Graph contains cycles: {cycles}")

        # Check for orphaned tasks (no dependencies or dependents)
        orphaned = [task_id for task_id in self.tasks.keys()
                   if (self.graph.in_degree(task_id) == 0 and
                       self.graph.out_degree(task_id) == 0 and
                       len(self.tasks) > 1)]
        if orphaned:
            issues.append(f"Orphaned tasks found: {orphaned}")

        # Check for missing task references in dependencies
        for dep in self.dependencies.values():
            if dep.source_task_id not in self.tasks:
                issues.append(f"Dependency references missing source task: {dep.source_task_id}")
            if dep.target_task_id not in self.tasks:
                issues.append(f"Dependency references missing target task: {dep.target_task_id}")

        return len(issues) == 0, issues

    def to_mermaid(self) -> str:
        """Export graph to Mermaid diagram format."""
        lines = ["graph TD"]

        # Add nodes
        for task_id, task in self.tasks.items():
            label = f"{task.description[:30]}..."
            node_style = f"{task_id}[\"{label}\"]"
            lines.append(f"    {node_style}")

        # Add edges
        for source, target in self.graph.edges():
            lines.append(f"    {source} --> {target}")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Export graph to dictionary format."""
        return {
            'graph_id': self.graph_id,
            'tasks': {task_id: {
                'task_id': task.task_id,
                'description': task.description,
                'task_type': task.task_type.value,
                'required_agent_type': task.required_agent_type.value,
                'estimated_complexity': task.estimated_complexity,
                'priority': task.priority,
                'dependencies': task.dependencies,
                'dependents': task.dependents
            } for task_id, task in self.tasks.items()},
            'dependencies': {key: {
                'source_task_id': dep.source_task_id,
                'target_task_id': dep.target_task_id,
                'dependency_type': dep.dependency_type.value,
                'description': dep.description,
                'required_artifacts': dep.required_artifacts
            } for key, dep in self.dependencies.items()},
            'stats': self.get_parallel_execution_stats()
        }

    def is_complete(self, completed_tasks: Set[str]) -> bool:
        """Check if all tasks in the graph are completed."""
        return all(task_id in completed_tasks for task_id in self.tasks.keys())

    def _mark_dirty(self):
        """Mark graph as needing recomputation."""
        self._is_dirty = True
        self._execution_phases = None
        self._critical_path = None

    def update_task_status(self, task_id: str, status: TaskStatus):
        """Update the status of a task."""
        if task_id in self.tasks:
            self.tasks[task_id].status = status
            # Update graph node attributes
            self.graph.nodes[task_id]['status'] = status.value

    def get_blocking_tasks(self, task_id: str) -> List[str]:
        """Get tasks that are blocking the execution of the given task."""
        if task_id not in self.tasks:
            return []

        blocking = []
        for dep_task_id in self.tasks[task_id].dependencies:
            if self.tasks[dep_task_id].status not in [TaskStatus.COMPLETED]:
                blocking.append(dep_task_id)

        return blocking

    def get_next_executable_batch(self, completed_tasks: Set[str],
                                 max_batch_size: int = 4) -> List[str]:
        """Get the next batch of tasks that can be executed in parallel."""
        executable = self.get_executable_tasks(completed_tasks)

        if not executable:
            return []

        # Group by agent type to optimize resource utilization
        by_agent_type = defaultdict(list)
        for task_id in executable:
            agent_type = self.tasks[task_id].required_agent_type
            by_agent_type[agent_type].append(task_id)

        # Select tasks to maximize parallel execution
        batch = []
        for agent_type, task_list in by_agent_type.items():
            # Sort by priority within agent type
            task_list.sort(key=lambda tid: self.tasks[tid].priority, reverse=True)
            batch.extend(task_list[:max_batch_size - len(batch)])

            if len(batch) >= max_batch_size:
                break

        return batch[:max_batch_size]