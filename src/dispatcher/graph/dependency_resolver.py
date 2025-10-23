"""
Dependency Resolver - Smart detection and resolution of task dependencies.

This module analyzes tasks to automatically identify dependencies using
both heuristic rules and LLM reasoning, while minimizing dependencies
to maximize parallel execution opportunities.
"""

import re
from typing import List, Dict, Set, Tuple, Optional, Any
from collections import defaultdict
from dataclasses import dataclass

from ..models import (
    Task, TaskDependency, DependencyType, TaskType, AgentType
)


@dataclass
class DependencyRule:
    """Rule for detecting dependencies between tasks."""
    name: str
    source_pattern: str  # Pattern to match in source task
    target_pattern: str  # Pattern to match in target task
    dependency_type: DependencyType
    confidence: float  # 0.0 to 1.0
    description: str


class DependencyResolver:
    """
    Analyzes tasks to identify and resolve dependencies automatically.

    Features:
    - Heuristic-based dependency detection
    - LLM-powered intelligent analysis
    - Circular dependency detection and resolution
    - Dependency optimization for maximum parallelism
    - Multiple dependency types (data, logical, resource)
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.dependency_rules = self._initialize_dependency_rules()
        self.task_precedence_matrix = self._initialize_precedence_matrix()

    def resolve_dependencies(self, tasks: List[Task]) -> List[TaskDependency]:
        """
        Analyze tasks and generate dependencies between them.

        Args:
            tasks: List of Task objects to analyze

        Returns:
            List of TaskDependency objects
        """
        # Create task lookup for quick access
        task_map = {task.task_id: task for task in tasks}

        # Detect dependencies using multiple strategies
        detected_deps = []

        # 1. Rule-based detection
        rule_deps = self._detect_rule_based_dependencies(tasks)
        detected_deps.extend(rule_deps)

        # 2. LLM-based detection (if available)
        if self.llm_client:
            llm_deps = self._detect_llm_dependencies(tasks)
            detected_deps.extend(llm_deps)

        # 3. Type-based dependencies
        type_deps = self._detect_type_based_dependencies(tasks)
        detected_deps.extend(type_deps)

        # 4. Artifact-based dependencies
        artifact_deps = self._detect_artifact_dependencies(tasks)
        detected_deps.extend(artifact_deps)

        # Remove duplicates and conflicts
        resolved_deps = self._resolve_conflicts(detected_deps, task_map)

        # Optimize for parallelism
        optimized_deps = self._optimize_for_parallelism(resolved_deps, tasks)

        # Validate for cycles
        final_deps = self._validate_and_fix_cycles(optimized_deps, tasks)

        return final_deps

    def _detect_rule_based_dependencies(self, tasks: List[Task]) -> List[TaskDependency]:
        """Detect dependencies using predefined rules."""
        dependencies = []

        for source_task in tasks:
            for target_task in tasks:
                if source_task.task_id == target_task.task_id:
                    continue

                # Check each rule
                for rule in self.dependency_rules:
                    if self._rule_matches(rule, source_task, target_task):
                        dependency = TaskDependency(
                            source_task_id=source_task.task_id,
                            target_task_id=target_task.task_id,
                            dependency_type=rule.dependency_type,
                            description=f"Rule: {rule.name} - {rule.description}"
                        )
                        dependencies.append(dependency)

        return dependencies

    def _detect_llm_dependencies(self, tasks: List[Task]) -> List[TaskDependency]:
        """Use LLM to detect complex dependencies."""
        if not self.llm_client or len(tasks) > 20:  # Avoid overwhelming the LLM
            return []

        try:
            prompt = self._build_dependency_analysis_prompt(tasks)
            response = self.llm_client.generate(
                prompt=prompt,
                max_tokens=3000,
                temperature=0.1
            )

            dependencies = self._parse_llm_dependencies(response, tasks)
            return dependencies

        except Exception as e:
            print(f"LLM dependency analysis failed: {e}")
            return []

    def _detect_type_based_dependencies(self, tasks: List[Task]) -> List[TaskDependency]:
        """Detect dependencies based on task types and typical workflows."""
        dependencies = []
        task_groups = self._group_tasks_by_type(tasks)

        # Define typical dependency patterns
        type_dependencies = {
            # Research usually comes first
            TaskType.RESEARCH: [],
            # Code writing depends on research and design
            TaskType.CODE_WRITING: [TaskType.RESEARCH],
            # Testing depends on code
            TaskType.TESTING: [TaskType.CODE_WRITING],
            # Review depends on code and tests
            TaskType.REVIEW: [TaskType.CODE_WRITING, TaskType.TESTING],
            # Documentation can depend on code and testing
            TaskType.DOCUMENTATION: [TaskType.CODE_WRITING, TaskType.TESTING],
            # Debugging depends on testing
            TaskType.DEBUGGING: [TaskType.TESTING],
        }

        for task_type, dependency_types in type_dependencies.items():
            if task_type not in task_groups:
                continue

            target_tasks = task_groups[task_type]

            for dep_type in dependency_types:
                if dep_type not in task_groups:
                    continue

                source_tasks = task_groups[dep_type]

                # Create dependencies between groups
                for source_task in source_tasks:
                    for target_task in target_tasks:
                        # Add some intelligence to avoid unnecessary dependencies
                        if self._should_create_type_dependency(source_task, target_task):
                            dependency = TaskDependency(
                                source_task_id=source_task.task_id,
                                target_task_id=target_task.task_id,
                                dependency_type=DependencyType.LOGICAL,
                                description=f"Type-based: {dep_type.value} → {task_type.value}"
                            )
                            dependencies.append(dependency)

        return dependencies

    def _detect_artifact_dependencies(self, tasks: List[Task]) -> List[TaskDependency]:
        """Detect dependencies based on input/output artifacts."""
        dependencies = []
        artifact_producers = defaultdict(list)  # artifact_name -> [task_ids]

        # Map which tasks produce which artifacts
        for task in tasks:
            for artifact in task.output_artifacts:
                artifact_producers[artifact].append(task.task_id)

        # Find tasks that need artifacts produced by other tasks
        for task in tasks:
            for required_input in task.input_requirements:
                # Check if any other task produces this artifact
                producers = artifact_producers.get(required_input, [])
                for producer_id in producers:
                    if producer_id != task.task_id:
                        dependency = TaskDependency(
                            source_task_id=producer_id,
                            target_task_id=task.task_id,
                            dependency_type=DependencyType.DATA,
                            description=f"Artifact dependency: {required_input}",
                            required_artifacts=[required_input]
                        )
                        dependencies.append(dependency)

        return dependencies

    def _rule_matches(self, rule: DependencyRule, source_task: Task, target_task: Task) -> bool:
        """Check if a dependency rule matches between two tasks."""
        source_text = f"{source_task.description} {' '.join(source_task.output_artifacts)}"
        target_text = f"{target_task.description} {' '.join(target_task.input_requirements)}"

        source_match = re.search(rule.source_pattern, source_text, re.IGNORECASE)
        target_match = re.search(rule.target_pattern, target_text, re.IGNORECASE)

        return source_match is not None and target_match is not None

    def _group_tasks_by_type(self, tasks: List[Task]) -> Dict[TaskType, List[Task]]:
        """Group tasks by their type."""
        groups = defaultdict(list)
        for task in tasks:
            groups[task.task_type].append(task)
        return groups

    def _should_create_type_dependency(self, source_task: Task, target_task: Task) -> bool:
        """Determine if a type-based dependency should be created."""
        # Avoid creating dependencies between unrelated domains
        source_domain = self._extract_domain_from_description(source_task.description)
        target_domain = self._extract_domain_from_description(target_task.description)

        # If domains are completely different, don't create dependency
        if source_domain and target_domain and source_domain != target_domain:
            unrelated_pairs = [
                ('frontend', 'backend'),
                ('ui', 'database'),
                ('styling', 'api')
            ]

            for domain1, domain2 in unrelated_pairs:
                if ((domain1 in source_domain and domain2 in target_domain) or
                    (domain2 in source_domain and domain1 in target_domain)):
                    return False

        return True

    def _extract_domain_from_description(self, description: str) -> Optional[str]:
        """Extract the primary domain from a task description."""
        description_lower = description.lower()

        domain_keywords = {
            'frontend': ['ui', 'frontend', 'component', 'interface', 'styling'],
            'backend': ['api', 'backend', 'server', 'endpoint', 'service'],
            'database': ['database', 'schema', 'data', 'model', 'storage'],
            'testing': ['test', 'testing', 'spec', 'verification'],
            'deployment': ['deploy', 'deployment', 'infrastructure', 'hosting']
        }

        for domain, keywords in domain_keywords.items():
            if any(keyword in description_lower for keyword in keywords):
                return domain

        return None

    def _resolve_conflicts(self, dependencies: List[TaskDependency],
                          task_map: Dict[str, Task]) -> List[TaskDependency]:
        """Resolve conflicts and remove duplicate dependencies."""
        # Remove exact duplicates
        unique_deps = {}
        for dep in dependencies:
            key = f"{dep.source_task_id}->{dep.target_task_id}"
            if key not in unique_deps:
                unique_deps[key] = dep
            else:
                # Keep the dependency with higher priority/confidence
                existing = unique_deps[key]
                if self._dependency_priority(dep) > self._dependency_priority(existing):
                    unique_deps[key] = dep

        return list(unique_deps.values())

    def _dependency_priority(self, dependency: TaskDependency) -> int:
        """Calculate priority of a dependency for conflict resolution."""
        priority_map = {
            DependencyType.DATA: 3,      # Highest priority
            DependencyType.LOGICAL: 2,
            DependencyType.RESOURCE: 1   # Lowest priority
        }
        return priority_map.get(dependency.dependency_type, 0)

    def _optimize_for_parallelism(self, dependencies: List[TaskDependency],
                                 tasks: List[Task]) -> List[TaskDependency]:
        """Optimize dependencies to maximize parallel execution opportunities."""
        # Remove redundant transitive dependencies
        optimized = self._remove_transitive_dependencies(dependencies)

        # Remove low-confidence dependencies that reduce parallelism significantly
        further_optimized = self._remove_parallelism_blockers(optimized, tasks)

        return further_optimized

    def _remove_transitive_dependencies(self, dependencies: List[TaskDependency]) -> List[TaskDependency]:
        """Remove transitive dependencies (A->B, B->C, A->C becomes A->B, B->C)."""
        # Build adjacency list
        graph = defaultdict(set)
        all_deps = {(dep.source_task_id, dep.target_task_id): dep for dep in dependencies}

        for dep in dependencies:
            graph[dep.source_task_id].add(dep.target_task_id)

        # Find transitive dependencies
        transitive_deps = set()
        for source in graph:
            for intermediate in graph[source]:
                for target in graph[intermediate]:
                    if target in graph[source]:
                        # This is a transitive dependency
                        transitive_deps.add((source, target))

        # Remove transitive dependencies
        filtered_deps = []
        for dep in dependencies:
            key = (dep.source_task_id, dep.target_task_id)
            if key not in transitive_deps:
                filtered_deps.append(dep)

        return filtered_deps

    def _remove_parallelism_blockers(self, dependencies: List[TaskDependency],
                                   tasks: List[Task]) -> List[TaskDependency]:
        """Remove dependencies that significantly reduce parallelism."""
        # Calculate parallelism impact of each dependency
        task_count_by_type = defaultdict(int)
        for task in tasks:
            task_count_by_type[task.task_type] += 1

        filtered_deps = []
        for dep in dependencies:
            # Keep high-priority dependencies
            if dep.dependency_type == DependencyType.DATA:
                filtered_deps.append(dep)
                continue

            # Evaluate impact on parallelism
            if not self._significantly_reduces_parallelism(dep, tasks):
                filtered_deps.append(dep)

        return filtered_deps

    def _significantly_reduces_parallelism(self, dependency: TaskDependency,
                                         tasks: List[Task]) -> bool:
        """Check if a dependency significantly reduces parallelism."""
        # Simple heuristic: if it creates a long chain of dependencies,
        # it might be reducing parallelism
        return False  # Placeholder - would implement more sophisticated logic

    def _validate_and_fix_cycles(self, dependencies: List[TaskDependency],
                                tasks: List[Task]) -> List[TaskDependency]:
        """Detect and resolve circular dependencies."""
        # Build graph for cycle detection
        from ..graph.execution_graph import ExecutionGraph

        temp_graph = ExecutionGraph()

        # Add all tasks
        for task in tasks:
            temp_graph.add_task(task)

        # Try adding dependencies one by one
        valid_dependencies = []
        for dep in dependencies:
            if temp_graph.add_dependency(dep):
                valid_dependencies.append(dep)
            else:
                print(f"Skipping dependency that would create cycle: {dep.source_task_id} -> {dep.target_task_id}")

        return valid_dependencies

    def _build_dependency_analysis_prompt(self, tasks: List[Task]) -> str:
        """Build prompt for LLM dependency analysis."""
        task_descriptions = []
        for i, task in enumerate(tasks):
            task_descriptions.append(
                f"{i+1}. {task.task_id}: {task.description} "
                f"(Type: {task.task_type.value}, Agent: {task.required_agent_type.value})"
            )

        prompt = f"""
Analyze the following software development tasks and identify logical dependencies between them.

TASKS:
{chr(10).join(task_descriptions)}

DEPENDENCY ANALYSIS GUIDELINES:
1. Identify tasks that must complete before others can start
2. Look for data dependencies (output of one task needed as input for another)
3. Consider logical workflow dependencies (design before implementation, implementation before testing)
4. Avoid creating unnecessary dependencies that would reduce parallelism
5. Focus on essential dependencies only

OUTPUT FORMAT (JSON):
{{
  "dependencies": [
    {{
      "source_task_id": "task_that_must_complete_first",
      "target_task_id": "task_that_depends_on_source",
      "dependency_type": "data|logical|resource",
      "description": "Why this dependency exists",
      "confidence": 0.0-1.0
    }}
  ],
  "analysis": "Brief explanation of your dependency reasoning"
}}

DEPENDENCY TYPES:
- data: Output of source task is input to target task
- logical: Source task must logically complete before target can start
- resource: Tasks compete for the same resource and cannot run simultaneously

Focus on creating the minimum set of dependencies necessary for correct execution.
"""

        return prompt

    def _parse_llm_dependencies(self, response: str, tasks: List[Task]) -> List[TaskDependency]:
        """Parse LLM response into TaskDependency objects."""
        import json
        import re

        dependencies = []
        task_ids = {task.task_id for task in tasks}

        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                deps_data = data.get('dependencies', [])

                for dep_data in deps_data:
                    source_id = dep_data.get('source_task_id')
                    target_id = dep_data.get('target_task_id')

                    # Validate task IDs exist
                    if source_id in task_ids and target_id in task_ids:
                        dependency = TaskDependency(
                            source_task_id=source_id,
                            target_task_id=target_id,
                            dependency_type=DependencyType(dep_data.get('dependency_type', 'logical')),
                            description=dep_data.get('description', 'LLM-detected dependency')
                        )
                        dependencies.append(dependency)

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"Failed to parse LLM dependencies: {e}")

        return dependencies

    def _initialize_dependency_rules(self) -> List[DependencyRule]:
        """Initialize predefined dependency detection rules."""
        rules = [
            # Research before implementation
            DependencyRule(
                name="research_before_implementation",
                source_pattern=r"research|investigate|analyze|study",
                target_pattern=r"implement|create|build|develop",
                dependency_type=DependencyType.LOGICAL,
                confidence=0.8,
                description="Research tasks should complete before implementation"
            ),

            # Design before implementation
            DependencyRule(
                name="design_before_implementation",
                source_pattern=r"design|architect|plan|wireframe",
                target_pattern=r"implement|create|build|code",
                dependency_type=DependencyType.LOGICAL,
                confidence=0.9,
                description="Design tasks should complete before implementation"
            ),

            # Implementation before testing
            DependencyRule(
                name="implementation_before_testing",
                source_pattern=r"implement|create|build|develop|code",
                target_pattern=r"test|verify|validate|check",
                dependency_type=DependencyType.LOGICAL,
                confidence=0.9,
                description="Implementation should complete before testing"
            ),

            # Database schema before data access
            DependencyRule(
                name="schema_before_data_access",
                source_pattern=r"schema|database.*design|table.*create",
                target_pattern=r"data.*access|repository|dao|orm",
                dependency_type=DependencyType.DATA,
                confidence=0.9,
                description="Database schema must exist before data access implementation"
            ),

            # API design before client implementation
            DependencyRule(
                name="api_before_client",
                source_pattern=r"api.*design|endpoint.*design|service.*interface",
                target_pattern=r"client|frontend|ui.*integration",
                dependency_type=DependencyType.DATA,
                confidence=0.8,
                description="API design should complete before client implementation"
            ),

            # Authentication before protected features
            DependencyRule(
                name="auth_before_protected",
                source_pattern=r"authentication|auth.*system|login",
                target_pattern=r"protected|secure|authorized|user.*profile",
                dependency_type=DependencyType.LOGICAL,
                confidence=0.8,
                description="Authentication system needed before protected features"
            ),

            # Component library before complex UI
            DependencyRule(
                name="components_before_ui",
                source_pattern=r"component.*library|ui.*components|design.*system",
                target_pattern=r"page|screen|complex.*ui|dashboard",
                dependency_type=DependencyType.DATA,
                confidence=0.7,
                description="Component library should exist before complex UI implementation"
            ),

            # Unit tests before integration tests
            DependencyRule(
                name="unit_before_integration_tests",
                source_pattern=r"unit.*test|component.*test",
                target_pattern=r"integration.*test|e2e.*test|system.*test",
                dependency_type=DependencyType.LOGICAL,
                confidence=0.8,
                description="Unit tests should be written before integration tests"
            )
        ]

        return rules

    def _initialize_precedence_matrix(self) -> Dict[Tuple[TaskType, TaskType], float]:
        """Initialize task type precedence matrix."""
        # Matrix of precedence weights between task types
        # Higher weight means stronger precedence
        matrix = {}

        # Research typically comes first
        matrix[(TaskType.RESEARCH, TaskType.CODE_WRITING)] = 0.8
        matrix[(TaskType.RESEARCH, TaskType.TESTING)] = 0.6
        matrix[(TaskType.RESEARCH, TaskType.DOCUMENTATION)] = 0.5

        # Code writing before testing
        matrix[(TaskType.CODE_WRITING, TaskType.TESTING)] = 0.9
        matrix[(TaskType.CODE_WRITING, TaskType.REVIEW)] = 0.8
        matrix[(TaskType.CODE_WRITING, TaskType.DOCUMENTATION)] = 0.7

        # Testing before review
        matrix[(TaskType.TESTING, TaskType.REVIEW)] = 0.7

        # Analysis before implementation
        matrix[(TaskType.ANALYSIS, TaskType.CODE_WRITING)] = 0.8

        return matrix

    def get_dependency_suggestions(self, tasks: List[Task]) -> Dict[str, List[str]]:
        """Get human-readable dependency suggestions for review."""
        dependencies = self.resolve_dependencies(tasks)
        suggestions = defaultdict(list)

        for dep in dependencies:
            source_task = next((t for t in tasks if t.task_id == dep.source_task_id), None)
            target_task = next((t for t in tasks if t.task_id == dep.target_task_id), None)

            if source_task and target_task:
                suggestion = f"{source_task.description} → {target_task.description} ({dep.dependency_type.value})"
                suggestions[dep.dependency_type.value].append(suggestion)

        return dict(suggestions)