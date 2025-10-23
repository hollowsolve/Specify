"""
Multi-pass LLM-based prompt analyzer.

This module provides functionality to analyze prompts using multiple passes
with the Anthropic Claude API to extract intent, requirements, assumptions,
and identify ambiguities.
"""

import os
import logging
from typing import List, Optional
import anthropic
from dotenv import load_dotenv

from .models import AnalysisResult


# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PromptAnalyzer:
    """
    Multi-pass prompt analyzer using Anthropic Claude API.

    Performs four analysis passes:
    1. Extract primary intent
    2. Extract explicit requirements
    3. Extract implicit assumptions
    4. Identify ambiguities/unclear points
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-20241022"):
        """
        Initialize the prompt analyzer.

        Args:
            api_key: Anthropic API key. If None, loads from ANTHROPIC_API_KEY env var
            model: Claude model to use for analysis

        Raises:
            ValueError: If no API key is provided or found in environment
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Anthropic API key is required. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.model = model
        self.client = anthropic.Anthropic(api_key=self.api_key)

    async def _make_llm_call(self, system_prompt: str, user_prompt: str) -> str:
        """
        Make a call to the Anthropic Claude API.

        Args:
            system_prompt: System prompt to set context
            user_prompt: User prompt containing the analysis request

        Returns:
            The response content from Claude

        Raises:
            Exception: If the API call fails
        """
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            raise

    def _make_llm_call_sync(self, system_prompt: str, user_prompt: str) -> str:
        """
        Make a synchronous call to the Anthropic Claude API.

        Args:
            system_prompt: System prompt to set context
            user_prompt: User prompt containing the analysis request

        Returns:
            The response content from Claude

        Raises:
            Exception: If the API call fails
        """
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            raise

    def _extract_intent(self, prompt: str) -> str:
        """
        Pass 1: Extract the primary intent of the prompt.

        Args:
            prompt: The input prompt to analyze

        Returns:
            A string describing the primary intent
        """
        system_prompt = """You are an expert prompt analyzer. Your task is to identify the primary intent or goal of a given prompt. Focus on what the user is ultimately trying to achieve.

Return only the intent as a clear, concise statement. Do not include explanations or additional commentary."""

        user_prompt = f"Analyze this prompt and identify its primary intent:\n\n{prompt}"

        return self._make_llm_call_sync(system_prompt, user_prompt).strip()

    def _extract_explicit_requirements(self, prompt: str) -> List[str]:
        """
        Pass 2: Extract explicit requirements from the prompt.

        Args:
            prompt: The input prompt to analyze

        Returns:
            A list of explicit requirements
        """
        system_prompt = """You are an expert prompt analyzer. Your task is to identify all explicit requirements clearly stated in the prompt. These are specific, concrete demands or specifications that the user has directly mentioned.

Return each requirement as a separate line starting with "- ". Be precise and avoid interpretation or inference."""

        user_prompt = f"Analyze this prompt and list all explicit requirements:\n\n{prompt}"

        response = self._make_llm_call_sync(system_prompt, user_prompt).strip()

        # Parse the response into a list
        requirements = []
        for line in response.split('\n'):
            line = line.strip()
            if line.startswith('- '):
                requirements.append(line[2:])
            elif line and not line.startswith('#') and not line.startswith('**'):
                # Handle cases where the model doesn't use bullet points
                requirements.append(line)

        return requirements

    def _extract_implicit_assumptions(self, prompt: str) -> List[str]:
        """
        Pass 3: Extract implicit assumptions from the prompt.

        Args:
            prompt: The input prompt to analyze

        Returns:
            A list of implicit assumptions
        """
        system_prompt = """You are an expert prompt analyzer. Your task is to identify implicit assumptions in the prompt - things that are assumed but not explicitly stated. These are underlying expectations, context, or prerequisites that the user takes for granted.

Return each assumption as a separate line starting with "- ". Focus on unstated but implied expectations."""

        user_prompt = f"Analyze this prompt and identify implicit assumptions:\n\n{prompt}"

        response = self._make_llm_call_sync(system_prompt, user_prompt).strip()

        # Parse the response into a list
        assumptions = []
        for line in response.split('\n'):
            line = line.strip()
            if line.startswith('- '):
                assumptions.append(line[2:])
            elif line and not line.startswith('#') and not line.startswith('**'):
                # Handle cases where the model doesn't use bullet points
                assumptions.append(line)

        return assumptions

    def _identify_ambiguities(self, prompt: str) -> List[str]:
        """
        Pass 4: Identify ambiguities and unclear points in the prompt.

        Args:
            prompt: The input prompt to analyze

        Returns:
            A list of ambiguities or unclear points
        """
        system_prompt = """You are an expert prompt analyzer. Your task is to identify ambiguities, unclear points, or areas that need clarification in the prompt. Look for vague language, missing details, or contradictory statements.

Return each ambiguity as a separate line starting with "- ". Focus on specific areas that could lead to misunderstanding or multiple interpretations."""

        user_prompt = f"Analyze this prompt and identify ambiguities or unclear points:\n\n{prompt}"

        response = self._make_llm_call_sync(system_prompt, user_prompt).strip()

        # Parse the response into a list
        ambiguities = []
        for line in response.split('\n'):
            line = line.strip()
            if line.startswith('- '):
                ambiguities.append(line[2:])
            elif line and not line.startswith('#') and not line.startswith('**'):
                # Handle cases where the model doesn't use bullet points
                ambiguities.append(line)

        return ambiguities

    def analyze(self, prompt: str) -> AnalysisResult:
        """
        Perform multi-pass analysis of a prompt.

        Args:
            prompt: The prompt text to analyze

        Returns:
            AnalysisResult object containing all extracted insights

        Raises:
            ValueError: If prompt is empty or None
            Exception: If any LLM API calls fail
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty or None")

        logger.info("Starting multi-pass prompt analysis")

        try:
            # Pass 1: Extract intent
            logger.info("Pass 1: Extracting primary intent")
            intent = self._extract_intent(prompt)

            # Pass 2: Extract explicit requirements
            logger.info("Pass 2: Extracting explicit requirements")
            explicit_requirements = self._extract_explicit_requirements(prompt)

            # Pass 3: Extract implicit assumptions
            logger.info("Pass 3: Extracting implicit assumptions")
            implicit_assumptions = self._extract_implicit_assumptions(prompt)

            # Pass 4: Identify ambiguities
            logger.info("Pass 4: Identifying ambiguities")
            ambiguities = self._identify_ambiguities(prompt)

            logger.info("Analysis complete")

            return AnalysisResult(
                intent=intent,
                explicit_requirements=explicit_requirements,
                implicit_assumptions=implicit_assumptions,
                ambiguities=ambiguities,
                raw_prompt=prompt
            )

        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            raise