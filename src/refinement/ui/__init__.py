"""
UI package for interactive refinement.

Contains the command-line interface and user interaction components.
"""

from .cli import RefinementCLI, refinement_cli

__all__ = [
    'RefinementCLI',
    'refinement_cli'
]