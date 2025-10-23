"""
Prompt analyzer package for multi-pass LLM analysis.

This package provides tools for analyzing prompts using multiple passes
with the Anthropic Claude API to extract intent, requirements, assumptions,
and identify ambiguities.
"""

from .parser import PromptAnalyzer
from .models import AnalysisResult

__all__ = ["PromptAnalyzer", "AnalysisResult"]
__version__ = "1.0.0"