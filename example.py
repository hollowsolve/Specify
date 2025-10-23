#!/usr/bin/env python3
"""
Example usage of the PromptAnalyzer.

This script demonstrates how to use the prompt analyzer to analyze
a sample prompt and display the results.
"""

import sys
import os

# Add src to path so we can import the analyzer
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from analyzer import PromptAnalyzer, AnalysisResult


def main():
    """Example usage of the prompt analyzer."""

    # Sample prompt to analyze
    sample_prompt = """
    Build a web application for managing customer orders. It should have
    user authentication, a dashboard for viewing orders, and the ability
    to create new orders. Make it responsive and fast.
    """

    try:
        # Initialize the analyzer
        analyzer = PromptAnalyzer()

        # Analyze the prompt
        print("Analyzing prompt...")
        result = analyzer.analyze(sample_prompt)

        # Display results
        print("\n" + "="*50)
        print("PROMPT ANALYSIS RESULTS")
        print("="*50)

        print(f"\nINTENT:")
        print(f"  {result.intent}")

        print(f"\nEXPLICIT REQUIREMENTS ({len(result.explicit_requirements)}):")
        for i, req in enumerate(result.explicit_requirements, 1):
            print(f"  {i}. {req}")

        print(f"\nIMPLICIT ASSUMPTIONS ({len(result.implicit_assumptions)}):")
        for i, assumption in enumerate(result.implicit_assumptions, 1):
            print(f"  {i}. {assumption}")

        print(f"\nAMBIGUITIES ({len(result.ambiguities)}):")
        for i, ambiguity in enumerate(result.ambiguities, 1):
            print(f"  {i}. {ambiguity}")

        print("\n" + "="*50)

    except ValueError as e:
        print(f"Configuration error: {e}")
        print("Make sure to set your ANTHROPIC_API_KEY in a .env file")
    except Exception as e:
        print(f"Analysis failed: {e}")


if __name__ == "__main__":
    main()