"""
Data models for prompt analysis results.

This module defines the data structures used to represent the output
of prompt analysis operations.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class AnalysisResult:
    """
    Structured result of prompt analysis containing extracted insights.

    Attributes:
        intent: The primary intent or goal of the prompt
        explicit_requirements: List of clearly stated requirements
        implicit_assumptions: List of unstated assumptions inferred from the prompt
        ambiguities: List of unclear or ambiguous points that need clarification
        raw_prompt: The original prompt text that was analyzed
    """
    intent: str
    explicit_requirements: List[str]
    implicit_assumptions: List[str]
    ambiguities: List[str]
    raw_prompt: str

    def __post_init__(self) -> None:
        """Validate the analysis result after initialization."""
        if not isinstance(self.intent, str):
            raise TypeError("intent must be a string")
        if not isinstance(self.explicit_requirements, list):
            raise TypeError("explicit_requirements must be a list")
        if not isinstance(self.implicit_assumptions, list):
            raise TypeError("implicit_assumptions must be a list")
        if not isinstance(self.ambiguities, list):
            raise TypeError("ambiguities must be a list")
        if not isinstance(self.raw_prompt, str):
            raise TypeError("raw_prompt must be a string")

    def to_dict(self) -> dict:
        """Convert the analysis result to a dictionary representation."""
        return {
            "intent": self.intent,
            "explicit_requirements": self.explicit_requirements,
            "implicit_assumptions": self.implicit_assumptions,
            "ambiguities": self.ambiguities,
            "raw_prompt": self.raw_prompt
        }

    def summary(self) -> str:
        """Generate a human-readable summary of the analysis."""
        return f"""
Prompt Analysis Summary:
Intent: {self.intent}
Explicit Requirements: {len(self.explicit_requirements)} items
Implicit Assumptions: {len(self.implicit_assumptions)} items
Ambiguities: {len(self.ambiguities)} items
"""