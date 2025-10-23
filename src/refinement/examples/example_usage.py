"""
Example usage of the Interactive Refinement Loop.

This demonstrates how to use Phase 3 of the Specify system to interactively
refine specifications with human-in-the-loop feedback.
"""

from pathlib import Path
import json
from datetime import datetime

from ..interactive_loop import RefinementLoop
from ..presenters.finding_presenter import FindingPresenter
from ..presenters.suggestion_generator import SuggestionGenerator
from ..presenters.approval_handler import ApprovalHandler
from ..ui.cli import RefinementCLI


def create_sample_refined_specification():
    """Create a sample RefinedSpecification for demonstration."""
    return {
        "requirements": [
            {
                "id": "req_001",
                "content": "User must be able to authenticate using email and password",
                "type": "functional",
                "priority": "high",
                "confidence": 0.9
            },
            {
                "id": "req_002",
                "content": "System must handle concurrent user sessions",
                "type": "non_functional",
                "priority": "medium",
                "confidence": 0.7
            },
            {
                "id": "req_003",
                "content": "Data must be encrypted at rest and in transit",
                "type": "security",
                "priority": "high",
                "confidence": 0.95
            }
        ],
        "edge_cases": [
            {
                "id": "edge_001",
                "description": "User attempts login with invalid credentials multiple times",
                "context": "Authentication system",
                "impact": "Security risk - potential brute force attack",
                "priority": "high",
                "handled": False
            },
            {
                "id": "edge_002",
                "description": "Database connection is lost during user session",
                "context": "Session management",
                "impact": "User experience degradation",
                "priority": "medium",
                "handled": False
            },
            {
                "id": "edge_003",
                "description": "User uploads file larger than system limit",
                "context": "File upload feature",
                "impact": "System performance",
                "priority": "low",
                "handled": True,
                "handling": "Implement file size validation and user feedback"
            }
        ],
        "contradictions": [
            {
                "id": "contradiction_001",
                "description": "Performance vs Security trade-off in authentication",
                "conflicting_requirements": [
                    "Fast authentication response (< 100ms)",
                    "Strong password hashing with high iteration count"
                ],
                "severity": "medium",
                "impact": "May need to balance security and performance",
                "resolved": False
            }
        ],
        "completeness_gaps": [
            {
                "id": "gap_001",
                "description": "Missing error handling requirements",
                "category": "error_handling",
                "priority": "high",
                "suggested_requirement": "System must provide comprehensive error handling with user-friendly messages"
            },
            {
                "id": "gap_002",
                "description": "No monitoring and logging requirements specified",
                "category": "observability",
                "priority": "medium",
                "suggested_requirement": "System must implement structured logging and performance monitoring"
            }
        ],
        "compressed_requirements": [
            {
                "id": "compression_001",
                "original_requirements": [
                    {"content": "User must be able to create account"},
                    {"content": "User must be able to verify email"},
                    {"content": "User must be able to set password"},
                    {"content": "User must be able to login"}
                ],
                "compressed_requirement": "System must provide complete user registration and authentication workflow",
                "confidence": 0.8,
                "compression_ratio": 0.75
            }
        ]
    }


def example_programmatic_usage():
    """Example of using the refinement loop programmatically."""
    print("=== Programmatic Usage Example ===\n")

    # Create sample specification
    refined_spec = create_sample_refined_specification()

    # Initialize components
    presenter = FindingPresenter()
    suggestion_generator = SuggestionGenerator()
    approval_handler = ApprovalHandler()

    # Create refinement loop
    refinement_loop = RefinementLoop(
        presenter=presenter,
        suggestion_generator=suggestion_generator,
        approval_handler=approval_handler
    )

    try:
        # Start refinement process
        print("Starting refinement process...")
        finalized_spec = refinement_loop.start_refinement(refined_spec)

        if finalized_spec:
            print("\n✅ Refinement completed successfully!")
            print(f"   Final confidence score: {finalized_spec.confidence_score:.1%}")
            print(f"   Total requirements: {len(finalized_spec.requirements)}")
            print(f"   User acceptance rate: {finalized_spec.user_acceptance_rate:.1%}")

            # Export finalized specification
            export_data = finalized_spec.to_dict()
            with open("finalized_specification.json", "w") as f:
                json.dump(export_data, f, indent=2, default=str)

            print("   Exported to: finalized_specification.json")

        else:
            print("❌ Refinement was not completed")

    except KeyboardInterrupt:
        print("\n⚠️  Refinement interrupted by user")
    except Exception as e:
        print(f"❌ Error during refinement: {e}")


def example_cli_usage():
    """Example of using the CLI interface."""
    print("\n=== CLI Usage Example ===\n")

    # Create sample specification file
    refined_spec = create_sample_refined_specification()
    spec_filename = "sample_specification.json"

    with open(spec_filename, "w") as f:
        json.dump(refined_spec, f, indent=2)

    print(f"Created sample specification: {spec_filename}")

    # Initialize CLI
    cli = RefinementCLI()

    print("\nTo use the CLI interface, run:")
    print(f"  python -m refinement.ui.cli refine {spec_filename}")
    print("  python -m refinement.ui.cli sessions")
    print("  python -m refinement.ui.cli resume <session-id>")
    print("  python -m refinement.ui.cli export <session-id> --format markdown")

    # Demonstrate session listing
    print("\nCurrent sessions:")
    sessions = cli.list_sessions()

    if not sessions:
        print("No existing sessions found.")


def example_custom_suggestion_generation():
    """Example of custom suggestion generation."""
    print("\n=== Custom Suggestion Generation Example ===\n")

    suggestion_generator = SuggestionGenerator()

    # Example edge cases
    edge_cases = [
        {
            "id": "edge_example",
            "description": "Network connection timeout during API call",
            "context": "External API integration",
            "impact": "Service unavailability",
            "priority": "high",
            "handled": False
        }
    ]

    # Generate suggestions
    suggestions = suggestion_generator.suggest_edge_case_handling(edge_cases)

    print("Generated suggestions for edge case handling:")
    for i, suggestion in enumerate(suggestions, 1):
        print(f"\n{i}. {suggestion['title']}")
        print(f"   Confidence: {suggestion['confidence']:.1%}")
        print(f"   Impact: {suggestion['impact']}")
        print(f"   Effort: {suggestion['effort']}")
        print(f"   Description: {suggestion['description']}")


def example_finding_presentation():
    """Example of finding presentation."""
    print("\n=== Finding Presentation Example ===\n")

    presenter = FindingPresenter()

    # Sample findings
    edge_cases = [
        {
            "description": "User session expires during form submission",
            "context": "Session management",
            "impact": "Data loss and poor user experience",
            "priority": "high",
            "handled": False
        },
        {
            "description": "File upload fails due to server disk space",
            "context": "File management",
            "impact": "Service disruption",
            "priority": "medium",
            "handled": True,
            "handling": "Implement disk space monitoring and cleanup"
        }
    ]

    contradictions = [
        {
            "description": "Caching vs Data Freshness conflict",
            "conflicting_requirements": [
                "Data must be cached for performance",
                "Data must always be up-to-date"
            ],
            "severity": "medium",
            "impact": "Performance vs accuracy trade-off",
            "resolved": False
        }
    ]

    # Present findings
    print("Presenting edge cases:")
    presenter.present_edge_cases(edge_cases)

    print("\nPresenting contradictions:")
    presenter.present_contradictions(contradictions)

    # Export findings
    presenter.export_to_json("findings_example.json")
    presenter.export_to_markdown("findings_example.md")

    print("\nFindings exported to JSON and Markdown formats")


def example_session_management():
    """Example of session management."""
    print("\n=== Session Management Example ===\n")

    # Create refinement loop
    refinement_loop = RefinementLoop(
        presenter=FindingPresenter(),
        suggestion_generator=SuggestionGenerator(),
        approval_handler=ApprovalHandler()
    )

    # List existing sessions
    sessions = refinement_loop.list_sessions()
    print(f"Found {len(sessions)} existing sessions")

    for session in sessions:
        print(f"  - {session['session_id'][:8]}... "
              f"({session['iterations']} iterations, "
              f"{'finalized' if session['is_finalized'] else 'in progress'})")

    # Example of session persistence
    print("\nSession data is automatically saved to:")
    print(f"  {refinement_loop.session_dir}")
    print("\nSessions can be resumed using their session ID")


if __name__ == "__main__":
    print("🔄 Interactive Refinement Loop - Example Usage\n")
    print("This script demonstrates various ways to use Phase 3 of the Specify system.\n")

    # Run examples
    try:
        example_finding_presentation()
        example_custom_suggestion_generation()
        example_session_management()
        example_cli_usage()

        # Uncomment to run interactive example
        # example_programmatic_usage()

        print("\n✅ All examples completed successfully!")
        print("\nTo run the interactive refinement process, uncomment the")
        print("example_programmatic_usage() call at the end of this script.")

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()