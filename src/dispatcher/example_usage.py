"""
Example usage of the AgentDispatcher system.

This example demonstrates how to use the multi-agent orchestration system
to convert a specification into working code.
"""

import json
from dataclasses import dataclass
from typing import Dict, Any, List

from .agent_dispatcher import AgentDispatcher
from .models import ExecutionStatus


@dataclass
class ExampleSpecification:
    """Example specification for demonstration."""
    spec_id: str
    title: str
    description: str
    requirements: List[str]
    technical_constraints: List[str]
    success_criteria: List[str]


def create_example_specification() -> ExampleSpecification:
    """Create an example specification for a simple web API."""
    return ExampleSpecification(
        spec_id="example_web_api_001",
        title="Simple Task Management API",
        description="Create a RESTful API for managing tasks with CRUD operations",
        requirements=[
            "Create API endpoints for task management (GET, POST, PUT, DELETE)",
            "Implement data validation for task inputs",
            "Add authentication middleware",
            "Include comprehensive error handling",
            "Write unit tests for all endpoints",
            "Generate API documentation"
        ],
        technical_constraints=[
            "Use Python with Flask framework",
            "Use SQLite for data storage",
            "Follow REST API best practices",
            "Include proper HTTP status codes",
            "Ensure 80%+ test coverage"
        ],
        success_criteria=[
            "All API endpoints work correctly",
            "All tests pass",
            "API documentation is complete",
            "Code follows PEP 8 style guidelines",
            "Proper error handling implemented"
        ]
    )


def setup_dispatcher_config() -> Dict[str, Any]:
    """Setup configuration for the dispatcher."""
    return {
        # LLM client would be configured here
        'llm_client': None,  # Would use actual LLM client in production

        # Agent factory configuration
        'agent_factory': {
            'default_pool_size': 2,
            'max_total_agents': 10,
            'enable_pooling': True,
            'code_writer_config': {
                'default_language': 'python',
                'include_tests': True,
                'include_docs': True
            },
            'researcher_config': {
                'max_search_results': 10
            },
            'tester_config': {
                'coverage_threshold': 80,
                'enable_execution': False  # Disabled for safety in example
            }
        },

        # Coordinator configuration
        'coordinator': {
            'max_workers': 4,
            'max_concurrent_tasks': 6,
            'monitor_interval': 2.0
        },

        # Message bus configuration
        'message_bus': {
            'enable_history': True,
            'max_history': 1000
        },

        # State manager configuration
        'state_manager': {
            'enable_persistence': True,
            'checkpoint_dir': './checkpoints',
            'auto_checkpoint_interval': 60
        },

        # Dispatcher configuration
        'enable_parallel_execution': True,
        'max_execution_time': 1800,  # 30 minutes
        'checkpoint_interval': 300   # 5 minutes
    }


def setup_callbacks(dispatcher: AgentDispatcher):
    """Setup callbacks for monitoring execution."""

    def on_progress(progress_data: Dict[str, Any]):
        """Handle progress updates."""
        completion = progress_data.get('progress_percentage', 0)
        completed = progress_data.get('completed_tasks', 0)
        total = progress_data.get('total_tasks', 0)
        print(f"Progress: {completion:.1f}% ({completed}/{total} tasks completed)")

    def on_completion(execution_result):
        """Handle execution completion."""
        status = execution_result.status.value
        success_rate = execution_result.success_rate()
        duration = execution_result.metrics.total_execution_time

        print(f"Execution completed with status: {status}")
        print(f"Success rate: {success_rate:.1f}%")
        print(f"Duration: {duration:.1f} seconds")

        # Print artifact summary
        artifact_count = len(execution_result.final_artifacts)
        print(f"Generated {artifact_count} artifacts")

    def on_error(error_message: str, error: Exception):
        """Handle execution errors."""
        print(f"Execution error: {error_message}")
        print(f"Error type: {type(error).__name__}")

    # Register callbacks
    dispatcher.add_progress_callback(on_progress)
    dispatcher.add_completion_callback(on_completion)
    dispatcher.add_error_callback(on_error)


def main():
    """Main example execution."""
    print("=== AgentDispatcher Example ===")
    print()

    # Create example specification
    specification = create_example_specification()
    print(f"Specification: {specification.title}")
    print(f"Requirements: {len(specification.requirements)} items")
    print(f"Constraints: {len(specification.technical_constraints)} items")
    print()

    # Setup dispatcher
    config = setup_dispatcher_config()
    dispatcher = AgentDispatcher(config)

    # Setup monitoring callbacks
    setup_callbacks(dispatcher)

    print("Starting execution...")
    print()

    try:
        # Execute the specification
        result = dispatcher.dispatch(specification)

        print()
        print("=== Execution Summary ===")
        print(f"Execution ID: {result.execution_id}")
        print(f"Status: {result.status.value}")
        print(f"Total Tasks: {result.metrics.total_tasks}")
        print(f"Completed Tasks: {result.metrics.completed_tasks}")
        print(f"Failed Tasks: {result.metrics.failed_tasks}")
        print(f"Success Rate: {result.success_rate():.1f}%")
        print(f"Execution Time: {result.metrics.total_execution_time:.1f} seconds")

        if result.final_artifacts:
            print()
            print("Generated Artifacts:")
            for artifact in result.final_artifacts:
                print(f"  - {artifact.name} ({artifact.type})")

        if result.warnings:
            print()
            print("Warnings:")
            for warning in result.warnings:
                print(f"  - {warning}")

        if result.error_summary:
            print()
            print("Errors:")
            for error in result.error_summary:
                print(f"  - {error}")

        # Display system metrics
        print()
        print("=== System Metrics ===")
        system_metrics = dispatcher.get_system_metrics()
        print(f"Total Executions: {system_metrics['dispatcher']['total_executions']}")

        agent_stats = system_metrics['agent_factory']
        print(f"Total Agents Created: {agent_stats['total_agents_created']}")
        print(f"Agent Utilization: {agent_stats['overall_utilization']:.1f}%")

        message_stats = system_metrics['message_bus']
        print(f"Messages Published: {message_stats['messages_published']}")
        print(f"Messages Delivered: {message_stats['messages_delivered']}")

    except Exception as e:
        print(f"Execution failed: {e}")

    finally:
        # Cleanup
        dispatcher.shutdown()
        print()
        print("Dispatcher shutdown complete")


def demonstrate_monitoring():
    """Demonstrate real-time monitoring capabilities."""
    print("\n=== Monitoring Example ===")

    config = setup_dispatcher_config()
    dispatcher = AgentDispatcher(config)

    # Start a simple execution
    spec = ExampleSpecification(
        spec_id="monitor_test",
        title="Monitoring Test",
        description="Simple test to demonstrate monitoring",
        requirements=["Create a simple function", "Write tests for it"],
        technical_constraints=["Use Python"],
        success_criteria=["Function works correctly"]
    )

    # Monitor execution status
    result = dispatcher.dispatch(spec)

    print("Real-time status monitoring:")
    while not result.is_complete():
        status = dispatcher.get_execution_status()
        print(f"Status: {status.get('status', 'unknown')}")
        print(f"Progress: {status.get('progress', {}).get('progress_percentage', 0):.1f}%")

        import time
        time.sleep(2)

    dispatcher.shutdown()


if __name__ == "__main__":
    # Run the main example
    main()

    # Optionally run monitoring demonstration
    # demonstrate_monitoring()