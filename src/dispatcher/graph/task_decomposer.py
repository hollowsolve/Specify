"""
Task Decomposer - Intelligent breakdown of specifications into atomic tasks.

This module uses LLM reasoning to decompose complex specifications into
manageable, atomic tasks that can be executed by specialized agents.
"""

import json
import re
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import asdict

from ..models import (
    Task, TaskType, AgentType, TaskStatus
)
from ...refinement.models import FinalizedSpecification


class TaskDecomposer:
    """
    Decomposes complex specifications into atomic, executable tasks.

    Features:
    - LLM-powered intelligent decomposition
    - Task type classification
    - Complexity estimation
    - Requirement analysis
    - Context preservation
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.decomposition_patterns = self._load_decomposition_patterns()
        self.task_templates = self._load_task_templates()

    def decompose_specification(self, spec) -> List[Task]:
        """
        Decompose a finalized specification into atomic tasks.

        Args:
            spec: FinalizedSpecification object

        Returns:
            List of atomic Task objects
        """
        # Analyze the specification to understand its scope
        analysis = self._analyze_specification(spec)

        # Generate tasks using LLM reasoning
        if self.llm_client:
            tasks = self._llm_decompose(spec, analysis)
        else:
            tasks = self._pattern_based_decompose(spec, analysis)

        # Post-process and validate tasks
        validated_tasks = self._validate_and_refine_tasks(tasks, spec)

        return validated_tasks

    def _analyze_specification(self, spec) -> Dict[str, Any]:
        """Analyze specification to determine decomposition strategy."""
        analysis = {
            'complexity_score': self._estimate_complexity(spec),
            'primary_domains': self._identify_domains(spec),
            'has_ui_components': self._has_ui_components(spec),
            'has_backend_logic': self._has_backend_logic(spec),
            'has_data_layer': self._has_data_layer(spec),
            'has_integrations': self._has_integrations(spec),
            'testing_requirements': self._analyze_testing_needs(spec),
            'documentation_needs': self._analyze_documentation_needs(spec)
        }

        return analysis

    def _llm_decompose(self, spec, analysis: Dict[str, Any]) -> List[Task]:
        """Use LLM to intelligently decompose the specification."""

        decomposition_prompt = self._build_decomposition_prompt(spec, analysis)

        try:
            response = self.llm_client.generate(
                prompt=decomposition_prompt,
                max_tokens=4000,
                temperature=0.1
            )

            tasks_data = self._parse_llm_response(response)
            tasks = self._convert_to_task_objects(tasks_data, spec)

            return tasks

        except Exception as e:
            # Fallback to pattern-based decomposition
            print(f"LLM decomposition failed: {e}. Using pattern-based fallback.")
            return self._pattern_based_decompose(spec, analysis)

    def _build_decomposition_prompt(self, spec, analysis: Dict[str, Any]) -> str:
        """Build a comprehensive prompt for LLM decomposition."""

        prompt = f"""
You are an expert software architect tasked with decomposing a software specification into atomic, executable tasks.

SPECIFICATION TO DECOMPOSE:
Title: {getattr(spec, 'title', 'N/A')}
Description: {getattr(spec, 'description', 'N/A')}

Requirements: {getattr(spec, 'requirements', [])}
Technical Constraints: {getattr(spec, 'technical_constraints', [])}
Success Criteria: {getattr(spec, 'success_criteria', [])}

ANALYSIS CONTEXT:
Complexity Score: {analysis['complexity_score']}/10
Primary Domains: {analysis['primary_domains']}
Has UI Components: {analysis['has_ui_components']}
Has Backend Logic: {analysis['has_backend_logic']}
Has Data Layer: {analysis['has_data_layer']}
Has Integrations: {analysis['has_integrations']}

DECOMPOSITION GUIDELINES:
1. Create ATOMIC tasks - each task should be completable by a single specialist agent
2. Tasks should be specific, measurable, and have clear success criteria
3. Consider these task types: {[t.value for t in TaskType]}
4. Agent types available: {[a.value for a in AgentType]}
5. Estimate complexity on scale 1-5 (1=simple, 5=very complex)
6. Identify clear input requirements and expected outputs
7. Consider task dependencies but don't specify them yet (that's done separately)

REQUIRED OUTPUT FORMAT (JSON):
{{
  "tasks": [
    {{
      "description": "Clear, specific description of what needs to be done",
      "task_type": "one of: {[t.value for t in TaskType]}",
      "required_agent_type": "one of: {[a.value for a in AgentType]}",
      "estimated_complexity": 1-5,
      "priority": 0-10 (10=highest),
      "input_requirements": ["what this task needs to start"],
      "output_artifacts": ["what this task will produce"],
      "context": {{
        "related_requirements": ["requirement IDs this task addresses"],
        "acceptance_criteria": ["specific criteria for task completion"],
        "technical_notes": "additional technical context"
      }}
    }}
  ],
  "decomposition_rationale": "Explanation of your decomposition strategy"
}}

EXAMPLES OF GOOD ATOMIC TASKS:
- "Create user authentication API endpoint with JWT token generation"
- "Design and implement database schema for user profiles"
- "Write unit tests for payment processing service"
- "Research and evaluate React component libraries for data visualization"
- "Implement responsive navigation component with mobile menu"

AVOID VAGUE TASKS LIKE:
- "Build the frontend" (too broad)
- "Handle user authentication" (not specific enough)
- "Make it work" (not measurable)

Focus on creating tasks that a specialist agent can understand and complete independently.
"""

        return prompt

    def _pattern_based_decompose(self, spec, analysis: Dict[str, Any]) -> List[Task]:
        """Fallback pattern-based decomposition when LLM is unavailable."""

        tasks = []
        task_counter = 0

        # Always start with research tasks
        if analysis['complexity_score'] > 6:
            tasks.append(self._create_task(
                f"research_{task_counter}",
                "Research technical requirements and architecture patterns",
                TaskType.RESEARCH,
                AgentType.RESEARCHER,
                complexity=2,
                context={'phase': 'initial_research'}
            ))
            task_counter += 1

        # UI/Frontend tasks
        if analysis['has_ui_components']:
            tasks.extend(self._create_ui_tasks(spec, task_counter))
            task_counter += len([t for t in tasks if 'ui' in t.task_id])

        # Backend/API tasks
        if analysis['has_backend_logic']:
            tasks.extend(self._create_backend_tasks(spec, task_counter))
            task_counter += len([t for t in tasks if 'backend' in t.task_id])

        # Data layer tasks
        if analysis['has_data_layer']:
            tasks.extend(self._create_data_tasks(spec, task_counter))
            task_counter += len([t for t in tasks if 'data' in t.task_id])

        # Integration tasks
        if analysis['has_integrations']:
            tasks.extend(self._create_integration_tasks(spec, task_counter))
            task_counter += len([t for t in tasks if 'integration' in t.task_id])

        # Testing tasks
        if analysis['testing_requirements']['needs_testing']:
            tasks.extend(self._create_testing_tasks(spec, analysis, task_counter))
            task_counter += len([t for t in tasks if 'test' in t.task_id])

        # Documentation tasks
        if analysis['documentation_needs']['needs_docs']:
            tasks.extend(self._create_documentation_tasks(spec, task_counter))

        return tasks

    def _create_ui_tasks(self, spec, start_counter: int) -> List[Task]:
        """Create UI-related tasks."""
        tasks = []

        # Component design and implementation
        tasks.append(self._create_task(
            f"ui_design_{start_counter}",
            "Design UI component architecture and wireframes",
            TaskType.CODE_WRITING,
            AgentType.CODE_WRITER,
            complexity=3
        ))

        tasks.append(self._create_task(
            f"ui_components_{start_counter + 1}",
            "Implement core UI components and layouts",
            TaskType.CODE_WRITING,
            AgentType.CODE_WRITER,
            complexity=4
        ))

        tasks.append(self._create_task(
            f"ui_styling_{start_counter + 2}",
            "Implement responsive styling and theme system",
            TaskType.CODE_WRITING,
            AgentType.CODE_WRITER,
            complexity=3
        ))

        return tasks

    def _create_backend_tasks(self, spec, start_counter: int) -> List[Task]:
        """Create backend-related tasks."""
        tasks = []

        tasks.append(self._create_task(
            f"backend_api_{start_counter}",
            "Design and implement core API endpoints",
            TaskType.CODE_WRITING,
            AgentType.CODE_WRITER,
            complexity=4
        ))

        tasks.append(self._create_task(
            f"backend_auth_{start_counter + 1}",
            "Implement authentication and authorization system",
            TaskType.CODE_WRITING,
            AgentType.CODE_WRITER,
            complexity=4
        ))

        tasks.append(self._create_task(
            f"backend_business_logic_{start_counter + 2}",
            "Implement core business logic and services",
            TaskType.CODE_WRITING,
            AgentType.CODE_WRITER,
            complexity=5
        ))

        return tasks

    def _create_data_tasks(self, spec, start_counter: int) -> List[Task]:
        """Create data layer tasks."""
        tasks = []

        tasks.append(self._create_task(
            f"data_schema_{start_counter}",
            "Design and implement database schema",
            TaskType.CODE_WRITING,
            AgentType.CODE_WRITER,
            complexity=3
        ))

        tasks.append(self._create_task(
            f"data_access_{start_counter + 1}",
            "Implement data access layer and repositories",
            TaskType.CODE_WRITING,
            AgentType.CODE_WRITER,
            complexity=3
        ))

        return tasks

    def _create_integration_tasks(self, spec, start_counter: int) -> List[Task]:
        """Create integration tasks."""
        tasks = []

        tasks.append(self._create_task(
            f"integration_research_{start_counter}",
            "Research and evaluate external service integrations",
            TaskType.RESEARCH,
            AgentType.RESEARCHER,
            complexity=2
        ))

        tasks.append(self._create_task(
            f"integration_impl_{start_counter + 1}",
            "Implement external service integrations",
            TaskType.CODE_WRITING,
            AgentType.CODE_WRITER,
            complexity=4
        ))

        return tasks

    def _create_testing_tasks(self, spec, analysis: Dict[str, Any], start_counter: int) -> List[Task]:
        """Create testing tasks."""
        tasks = []

        if analysis['testing_requirements']['needs_unit_tests']:
            tasks.append(self._create_task(
                f"test_unit_{start_counter}",
                "Write comprehensive unit tests for core functionality",
                TaskType.TESTING,
                AgentType.TESTER,
                complexity=3
            ))

        if analysis['testing_requirements']['needs_integration_tests']:
            tasks.append(self._create_task(
                f"test_integration_{start_counter + len(tasks)}",
                "Write integration tests for API endpoints and services",
                TaskType.TESTING,
                AgentType.TESTER,
                complexity=4
            ))

        if analysis['testing_requirements']['needs_e2e_tests']:
            tasks.append(self._create_task(
                f"test_e2e_{start_counter + len(tasks)}",
                "Write end-to-end tests for critical user workflows",
                TaskType.TESTING,
                AgentType.TESTER,
                complexity=5
            ))

        return tasks

    def _create_documentation_tasks(self, spec, start_counter: int) -> List[Task]:
        """Create documentation tasks."""
        tasks = []

        tasks.append(self._create_task(
            f"docs_api_{start_counter}",
            "Generate API documentation and examples",
            TaskType.DOCUMENTATION,
            AgentType.DOCUMENTER,
            complexity=2
        ))

        tasks.append(self._create_task(
            f"docs_user_{start_counter + 1}",
            "Create user documentation and setup guides",
            TaskType.DOCUMENTATION,
            AgentType.DOCUMENTER,
            complexity=3
        ))

        return tasks

    def _create_task(self, task_id: str, description: str, task_type: TaskType,
                    agent_type: AgentType, complexity: int = 3, priority: int = 5,
                    context: Dict[str, Any] = None) -> Task:
        """Helper to create a task object."""
        return Task(
            task_id=task_id,
            description=description,
            task_type=task_type,
            required_agent_type=agent_type,
            estimated_complexity=float(complexity),
            priority=priority,
            context=context or {}
        )

    def _parse_llm_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse LLM response into task data."""
        try:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                data = json.loads(json_str)
                return data.get('tasks', [])
        except json.JSONDecodeError:
            pass

        # Fallback: try to parse structured text
        return self._parse_structured_text(response)

    def _parse_structured_text(self, text: str) -> List[Dict[str, Any]]:
        """Fallback parser for structured text responses."""
        tasks = []
        # Implementation would parse text-based task descriptions
        # This is a simplified version
        return tasks

    def _convert_to_task_objects(self, tasks_data: List[Dict[str, Any]], spec) -> List[Task]:
        """Convert parsed task data to Task objects."""
        tasks = []

        for i, task_data in enumerate(tasks_data):
            try:
                task = Task(
                    task_id=f"task_{i}_{task_data.get('task_type', 'unknown')}",
                    description=task_data.get('description', ''),
                    task_type=TaskType(task_data.get('task_type', 'code_writing')),
                    required_agent_type=AgentType(task_data.get('required_agent_type', 'code_writer')),
                    estimated_complexity=float(task_data.get('estimated_complexity', 3)),
                    priority=int(task_data.get('priority', 5)),
                    input_requirements=task_data.get('input_requirements', []),
                    output_artifacts=task_data.get('output_artifacts', []),
                    context=task_data.get('context', {})
                )
                tasks.append(task)
            except (ValueError, KeyError) as e:
                print(f"Warning: Skipping invalid task data: {e}")
                continue

        return tasks

    def _validate_and_refine_tasks(self, tasks: List[Task], spec) -> List[Task]:
        """Validate and refine the generated tasks."""
        validated_tasks = []

        for task in tasks:
            # Validate task completeness
            if not task.description or not task.task_type:
                continue

            # Refine complexity estimates
            task.estimated_complexity = self._refine_complexity_estimate(task)

            # Add missing context
            if not task.context:
                task.context = self._generate_task_context(task, spec)

            # Ensure unique task IDs
            task.task_id = self._ensure_unique_task_id(task.task_id, validated_tasks)

            validated_tasks.append(task)

        return validated_tasks

    def _estimate_complexity(self, spec) -> float:
        """Estimate overall specification complexity (1-10 scale)."""
        complexity = 3.0  # Base complexity

        # Check requirements count and complexity
        requirements = getattr(spec, 'requirements', [])
        complexity += min(len(requirements) * 0.5, 3.0)

        # Check for complex features
        spec_text = str(spec).lower()

        complex_features = [
            'authentication', 'real-time', 'scalability', 'performance',
            'integration', 'api', 'database', 'security', 'testing'
        ]

        for feature in complex_features:
            if feature in spec_text:
                complexity += 0.5

        return min(complexity, 10.0)

    def _identify_domains(self, spec) -> List[str]:
        """Identify primary domains/areas of the specification."""
        domains = []
        spec_text = str(spec).lower()

        domain_keywords = {
            'frontend': ['ui', 'interface', 'frontend', 'react', 'vue', 'angular'],
            'backend': ['api', 'server', 'backend', 'service', 'endpoint'],
            'database': ['database', 'db', 'storage', 'data', 'schema'],
            'authentication': ['auth', 'login', 'user', 'authentication'],
            'testing': ['test', 'testing', 'qa', 'quality'],
            'deployment': ['deploy', 'hosting', 'production', 'infrastructure'],
            'integration': ['integration', 'external', 'third-party', 'webhook']
        }

        for domain, keywords in domain_keywords.items():
            if any(keyword in spec_text for keyword in keywords):
                domains.append(domain)

        return domains

    def _has_ui_components(self, spec) -> bool:
        """Check if specification involves UI components."""
        ui_keywords = ['ui', 'interface', 'frontend', 'component', 'page', 'screen', 'form']
        spec_text = str(spec).lower()
        return any(keyword in spec_text for keyword in ui_keywords)

    def _has_backend_logic(self, spec) -> bool:
        """Check if specification involves backend logic."""
        backend_keywords = ['api', 'server', 'backend', 'service', 'endpoint', 'logic']
        spec_text = str(spec).lower()
        return any(keyword in spec_text for keyword in backend_keywords)

    def _has_data_layer(self, spec) -> bool:
        """Check if specification involves data layer."""
        data_keywords = ['database', 'data', 'storage', 'model', 'schema']
        spec_text = str(spec).lower()
        return any(keyword in spec_text for keyword in data_keywords)

    def _has_integrations(self, spec) -> bool:
        """Check if specification involves external integrations."""
        integration_keywords = ['integration', 'external', 'third-party', 'api', 'webhook']
        spec_text = str(spec).lower()
        return any(keyword in spec_text for keyword in integration_keywords)

    def _analyze_testing_needs(self, spec) -> Dict[str, bool]:
        """Analyze what types of testing are needed."""
        spec_text = str(spec).lower()

        return {
            'needs_testing': 'test' in spec_text or 'quality' in spec_text,
            'needs_unit_tests': True,  # Always needed
            'needs_integration_tests': 'api' in spec_text or 'integration' in spec_text,
            'needs_e2e_tests': 'ui' in spec_text or 'user' in spec_text
        }

    def _analyze_documentation_needs(self, spec) -> Dict[str, bool]:
        """Analyze documentation requirements."""
        return {
            'needs_docs': True,  # Always need some documentation
            'needs_api_docs': self._has_backend_logic(spec),
            'needs_user_docs': self._has_ui_components(spec)
        }

    def _refine_complexity_estimate(self, task: Task) -> float:
        """Refine complexity estimate based on task analysis."""
        base_complexity = task.estimated_complexity

        # Adjust based on task type
        complexity_modifiers = {
            TaskType.RESEARCH: 0.8,
            TaskType.CODE_WRITING: 1.0,
            TaskType.TESTING: 0.9,
            TaskType.REVIEW: 0.7,
            TaskType.DOCUMENTATION: 0.6,
            TaskType.DEBUGGING: 1.2
        }

        modifier = complexity_modifiers.get(task.task_type, 1.0)
        return max(1.0, min(5.0, base_complexity * modifier))

    def _generate_task_context(self, task: Task, spec) -> Dict[str, Any]:
        """Generate context for a task based on the specification."""
        return {
            'specification_id': getattr(spec, 'spec_id', 'unknown'),
            'related_requirements': [],  # Would analyze which requirements this task addresses
            'generated_by': 'task_decomposer',
            'generation_timestamp': str(datetime.now())
        }

    def _ensure_unique_task_id(self, task_id: str, existing_tasks: List[Task]) -> str:
        """Ensure task ID is unique among existing tasks."""
        existing_ids = {task.task_id for task in existing_tasks}

        if task_id not in existing_ids:
            return task_id

        counter = 1
        while f"{task_id}_{counter}" in existing_ids:
            counter += 1

        return f"{task_id}_{counter}"

    def _load_decomposition_patterns(self) -> Dict[str, Any]:
        """Load predefined decomposition patterns."""
        return {
            'web_application': {
                'phases': ['research', 'design', 'implementation', 'testing', 'deployment'],
                'typical_tasks': ['ui_design', 'api_development', 'database_design', 'testing']
            },
            'api_service': {
                'phases': ['design', 'implementation', 'testing', 'documentation'],
                'typical_tasks': ['endpoint_design', 'business_logic', 'data_layer', 'testing']
            }
        }

    def _load_task_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load task templates for common patterns."""
        return {
            'ui_component': {
                'task_type': TaskType.CODE_WRITING,
                'agent_type': AgentType.CODE_WRITER,
                'estimated_complexity': 3.0,
                'output_artifacts': ['component_file', 'style_file', 'test_file']
            },
            'api_endpoint': {
                'task_type': TaskType.CODE_WRITING,
                'agent_type': AgentType.CODE_WRITER,
                'estimated_complexity': 3.5,
                'output_artifacts': ['endpoint_implementation', 'validation_schema', 'tests']
            }
        }