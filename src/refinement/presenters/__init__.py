"""
Presenters package for interactive refinement.

Contains modules responsible for formatting and presenting findings to users
in an intuitive, actionable way.
"""

from .finding_presenter import FindingPresenter
from .suggestion_generator import SuggestionGenerator, Suggestion
from .approval_handler import ApprovalHandler

__all__ = [
    'FindingPresenter',
    'SuggestionGenerator',
    'Suggestion',
    'ApprovalHandler'
]