"""
Interactive Refinement Loop - Phase 3 of the Specify system.

This package implements a sophisticated human-in-the-loop system for refining
specifications. It presents findings, collects user feedback, and iteratively
improves specifications until the user is satisfied.

Key Components:
- RefinementLoop: Core orchestration class
- FindingPresenter: Rich formatting and presentation
- SuggestionGenerator: LLM-powered intelligent suggestions
- ApprovalHandler: Interactive user decision workflow
- CLI: Beautiful command-line interface

Design Philosophy:
Make specification refinement feel like collaborating with a senior architect
who's thinking through edge cases and improvements with the user.
"""

from .interactive_loop import RefinementLoop
from .models import (
    RefinementSession,
    RefinementIteration,
    UserFeedback,
    UserDecision,
    UserDecisionAction,
    FinalizedSpecification
)
from .presenters.finding_presenter import FindingPresenter
from .presenters.suggestion_generator import SuggestionGenerator
from .presenters.approval_handler import ApprovalHandler
from .ui.cli import RefinementCLI, refinement_cli

__all__ = [
    # Core components
    'RefinementLoop',
    'FindingPresenter',
    'SuggestionGenerator',
    'ApprovalHandler',

    # Data models
    'RefinementSession',
    'RefinementIteration',
    'UserFeedback',
    'UserDecision',
    'UserDecisionAction',
    'FinalizedSpecification',

    # CLI interface
    'RefinementCLI',
    'refinement_cli'
]

# Version information
__version__ = "1.0.0"
__author__ = "Specify Development Team"
__description__ = "Interactive specification refinement with human-in-the-loop feedback"