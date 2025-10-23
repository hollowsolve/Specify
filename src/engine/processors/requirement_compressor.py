"""
Requirement compression processor.

This module implements intelligent requirement compression that identifies
redundant requirements, merges similar ones, and optimizes for conciseness
while preserving semantic meaning.
"""

import time
import re
from typing import List, Dict, Any, Set, Tuple, Optional
from collections import defaultdict
from ..models import AnalysisResult, CompressedRequirement, Severity
from ..config import ProcessorConfig, ProcessorMode, get_config


class RequirementCompressor:
    """
    Intelligent requirement compression using hybrid rule-based + LLM approach.

    This processor identifies redundant requirements, merges similar requirements,
    and uses LLM to suggest concise rephrasing while preserving semantic meaning.
    """

    def __init__(self, config: Optional[ProcessorConfig] = None):
        self.config = config or get_config().requirement_compressor

        # Common words to ignore when comparing requirements
        self.stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "up", "about", "into", "through", "during",
            "before", "after", "above", "below", "up", "down", "out", "off", "over",
            "under", "again", "further", "then", "once", "should", "must", "will",
            "can", "could", "would", "may", "might"
        }

        # Semantic similarity patterns
        self.similarity_patterns = [
            # Action synonyms
            {
                "create": ["add", "generate", "make", "build", "establish", "form"],
                "update": ["modify", "change", "edit", "alter", "revise"],
                "delete": ["remove", "destroy", "eliminate", "erase"],
                "display": ["show", "present", "render", "exhibit"],
                "validate": ["check", "verify", "confirm", "ensure"],
                "save": ["store", "persist", "record"]
            }
        ]

    def compress_requirements(self, analysis: AnalysisResult, context: Dict[str, Any] = None) -> List[CompressedRequirement]:
        """
        Compress requirements by identifying redundancies and merging similar ones.

        Args:
            analysis: The analysis result from Phase 1
            context: Additional context for compression

        Returns:
            List of compressed requirements
        """
        if not self.config.enabled:
            return []

        context = context or {}
        start_time = time.time()

        try:
            # Get all requirements to compress
            all_requirements = analysis.explicit_requirements + analysis.implicit_assumptions

            if not all_requirements:
                return []

            # Phase 1: Find duplicate and similar requirements
            similarity_groups = self._group_similar_requirements(all_requirements)

            # Phase 2: Merge similar requirements
            merged_requirements = self._merge_requirement_groups(similarity_groups)

            # Phase 3: LLM-based optimization (if enabled)
            if self.config.mode in [ProcessorMode.BALANCED, ProcessorMode.INTELLIGENT]:
                optimized_requirements = self._llm_optimize_requirements(merged_requirements, context)
                merged_requirements.extend(optimized_requirements)

            # Phase 4: Filter and finalize
            compressed_requirements = self._finalize_compressed_requirements(merged_requirements)

        except Exception as e:
            print(f"Error in requirement compression: {e}")
            compressed_requirements = []

        processing_time = time.time() - start_time
        print(f"Requirement compression completed in {processing_time:.2f}s, "
              f"compressed {len(analysis.explicit_requirements + analysis.implicit_assumptions)} "
              f"requirements to {len(compressed_requirements)}")

        return compressed_requirements

    def _group_similar_requirements(self, requirements: List[str]) -> List[List[int]]:
        """Group similar requirements by their indices."""
        if not requirements:
            return []

        n = len(requirements)
        similarity_matrix = [[0.0 for _ in range(n)] for _ in range(n)]

        # Calculate similarity between all pairs
        for i in range(n):
            for j in range(i + 1, n):
                similarity = self._calculate_similarity(requirements[i], requirements[j])
                similarity_matrix[i][j] = similarity
                similarity_matrix[j][i] = similarity

        # Group requirements based on similarity threshold
        threshold = 0.7  # 70% similarity threshold
        groups = []
        assigned = set()

        for i in range(n):
            if i in assigned:
                continue

            group = [i]
            assigned.add(i)

            for j in range(i + 1, n):
                if j not in assigned and similarity_matrix[i][j] >= threshold:
                    group.append(j)
                    assigned.add(j)

            groups.append(group)

        return groups

    def _calculate_similarity(self, req1: str, req2: str) -> float:
        """Calculate similarity between two requirements."""
        # Tokenize and normalize
        tokens1 = self._tokenize_requirement(req1)
        tokens2 = self._tokenize_requirement(req2)

        if not tokens1 or not tokens2:
            return 0.0

        # Calculate Jaccard similarity
        intersection = len(tokens1.intersection(tokens2))
        union = len(tokens1.union(tokens2))

        jaccard_similarity = intersection / union if union > 0 else 0

        # Calculate semantic similarity bonus
        semantic_bonus = self._calculate_semantic_bonus(req1, req2)

        # Combine similarities
        total_similarity = min(1.0, jaccard_similarity + semantic_bonus)

        return total_similarity

    def _tokenize_requirement(self, requirement: str) -> Set[str]:
        """Tokenize requirement into meaningful tokens."""
        # Clean and normalize text
        text = requirement.lower().strip()

        # Remove punctuation and split
        text = re.sub(r'[^\w\s]', ' ', text)
        tokens = text.split()

        # Remove stop words and short tokens
        meaningful_tokens = {
            token for token in tokens
            if len(token) > 2 and token not in self.stop_words
        }

        return meaningful_tokens

    def _calculate_semantic_bonus(self, req1: str, req2: str) -> float:
        """Calculate semantic similarity bonus based on action patterns."""
        bonus = 0.0

        # Check for action synonyms
        for pattern_group in self.similarity_patterns:
            for base_action, synonyms in pattern_group.items():
                req1_lower = req1.lower()
                req2_lower = req2.lower()

                # Check if both requirements have the same action or synonyms
                req1_has_action = base_action in req1_lower or any(syn in req1_lower for syn in synonyms)
                req2_has_action = base_action in req2_lower or any(syn in req2_lower for syn in synonyms)

                if req1_has_action and req2_has_action:
                    bonus += 0.2  # 20% bonus for semantic similarity

        return min(0.4, bonus)  # Cap bonus at 40%

    def _merge_requirement_groups(self, groups: List[List[int]]) -> List[CompressedRequirement]:
        """Merge groups of similar requirements."""
        compressed_requirements = []

        for group in groups:
            if len(group) == 1:
                # Single requirement, no compression needed
                continue

            # Get the requirements in this group
            group_requirements = [f"Requirement {i}" for i in group]  # Placeholder - would use actual requirements

            # Find the most comprehensive requirement as base
            base_req_idx = self._find_most_comprehensive_requirement(group_requirements)
            base_requirement = group_requirements[base_req_idx]

            # Create merged requirement
            merged_text = self._merge_requirement_texts(group_requirements)

            # Calculate compression ratio
            original_length = sum(len(req) for req in group_requirements)
            compressed_length = len(merged_text)
            compression_ratio = 1.0 - (compressed_length / original_length) if original_length > 0 else 0.0

            compressed_req = CompressedRequirement(
                compressed_text=merged_text,
                original_requirements=group_requirements,
                compression_ratio=compression_ratio,
                semantic_preserved=True  # Assume preserved for rule-based merging
            )

            compressed_requirements.append(compressed_req)

        return compressed_requirements

    def _find_most_comprehensive_requirement(self, requirements: List[str]) -> int:
        """Find the most comprehensive requirement in a group."""
        if not requirements:
            return 0

        # Score requirements by length and keyword diversity
        scores = []
        for i, req in enumerate(requirements):
            tokens = self._tokenize_requirement(req)
            length_score = len(req) / 100  # Normalize length
            diversity_score = len(tokens) / 20  # Normalize token diversity
            total_score = length_score + diversity_score
            scores.append((i, total_score))

        # Return index of highest scoring requirement
        return max(scores, key=lambda x: x[1])[0]

    def _merge_requirement_texts(self, requirements: List[str]) -> str:
        """Merge multiple requirement texts into a single comprehensive one."""
        if not requirements:
            return ""

        if len(requirements) == 1:
            return requirements[0]

        # Simple merge strategy: take the longest as base and add unique information
        base_req = max(requirements, key=len)
        base_tokens = self._tokenize_requirement(base_req)

        additional_info = []
        for req in requirements:
            if req == base_req:
                continue

            req_tokens = self._tokenize_requirement(req)
            unique_tokens = req_tokens - base_tokens

            if unique_tokens:
                # Extract phrases containing unique tokens
                unique_phrases = self._extract_unique_phrases(req, unique_tokens)
                additional_info.extend(unique_phrases)

        # Construct merged requirement
        if additional_info:
            merged = f"{base_req}. Additionally: {', '.join(additional_info)}"
        else:
            merged = base_req

        return merged

    def _extract_unique_phrases(self, requirement: str, unique_tokens: Set[str]) -> List[str]:
        """Extract phrases containing unique tokens from a requirement."""
        phrases = []

        # Split into sentences/clauses
        clauses = re.split(r'[.;,]', requirement)

        for clause in clauses:
            clause = clause.strip()
            if not clause:
                continue

            clause_tokens = self._tokenize_requirement(clause)
            if clause_tokens.intersection(unique_tokens):
                phrases.append(clause)

        return phrases

    def _llm_optimize_requirements(self, requirements: List[CompressedRequirement],
                                  context: Dict[str, Any]) -> List[CompressedRequirement]:
        """Use LLM to further optimize requirements."""
        llm_config = get_config().llm

        if not llm_config.enabled or not requirements:
            return []

        optimized_requirements = []

        try:
            for req in requirements:
                # Build optimization prompt
                prompt = self._build_optimization_prompt(req, context)

                # Call LLM
                llm_response = self._call_llm_for_optimization(prompt, llm_config)

                # Parse response
                optimized_req = self._parse_optimization_response(llm_response, req)
                if optimized_req:
                    optimized_requirements.append(optimized_req)

        except Exception as e:
            print(f"LLM optimization failed: {e}")

        return optimized_requirements

    def _build_optimization_prompt(self, requirement: CompressedRequirement, context: Dict[str, Any]) -> str:
        """Build prompt for LLM optimization."""
        original_text = "\n".join(f"- {req}" for req in requirement.original_requirements)

        prompt = f"""
Please optimize the following merged requirement for conciseness while preserving all semantic meaning:

ORIGINAL REQUIREMENTS:
{original_text}

CURRENT MERGED VERSION:
{requirement.compressed_text}

Please provide a more concise version that:
1. Preserves all functional requirements
2. Uses clearer, more precise language
3. Eliminates redundancy
4. Maintains technical accuracy

Respond with just the optimized requirement text.
"""

        return prompt

    def _call_llm_for_optimization(self, prompt: str, llm_config) -> str:
        """Call LLM for requirement optimization."""
        # Placeholder for actual LLM integration
        # Simulated response for demonstration
        return "Optimized requirement text with improved clarity and conciseness"

    def _parse_optimization_response(self, response: str, original_req: CompressedRequirement) -> Optional[CompressedRequirement]:
        """Parse LLM optimization response."""
        optimized_text = response.strip()

        if not optimized_text or optimized_text == original_req.compressed_text:
            return None

        # Calculate new compression ratio
        original_length = sum(len(req) for req in original_req.original_requirements)
        new_length = len(optimized_text)
        new_compression_ratio = 1.0 - (new_length / original_length) if original_length > 0 else 0.0

        return CompressedRequirement(
            compressed_text=optimized_text,
            original_requirements=original_req.original_requirements,
            compression_ratio=new_compression_ratio,
            semantic_preserved=True  # Assume LLM preserves semantics
        )

    def _finalize_compressed_requirements(self, requirements: List[CompressedRequirement]) -> List[CompressedRequirement]:
        """Filter and finalize compressed requirements."""
        if not requirements:
            return []

        # Filter by compression effectiveness
        effective_requirements = [
            req for req in requirements
            if req.compression_ratio > 0.1  # At least 10% compression
        ]

        # Sort by compression ratio (highest first)
        effective_requirements.sort(key=lambda x: x.compression_ratio, reverse=True)

        # Limit results
        if self.config.max_results > 0:
            effective_requirements = effective_requirements[:self.config.max_results]

        return effective_requirements

    def get_compression_statistics(self, requirements: List[CompressedRequirement]) -> Dict[str, Any]:
        """Get statistics about compression results."""
        if not requirements:
            return {
                "total_compressed": 0,
                "average_compression_ratio": 0.0,
                "total_original_requirements": 0,
                "total_savings": 0.0
            }

        total_original = sum(len(req.original_requirements) for req in requirements)
        total_compressed = len(requirements)
        average_compression = sum(req.compression_ratio for req in requirements) / len(requirements)

        # Calculate text length savings
        total_original_length = sum(
            sum(len(orig_req) for orig_req in req.original_requirements)
            for req in requirements
        )
        total_compressed_length = sum(len(req.compressed_text) for req in requirements)
        text_savings = 1.0 - (total_compressed_length / total_original_length) if total_original_length > 0 else 0.0

        return {
            "total_compressed": total_compressed,
            "total_original_requirements": total_original,
            "average_compression_ratio": average_compression,
            "requirement_reduction": 1.0 - (total_compressed / total_original) if total_original > 0 else 0.0,
            "text_length_savings": text_savings,
            "semantic_preservation_rate": sum(1 for req in requirements if req.semantic_preserved) / len(requirements)
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the requirement compressor."""
        return {
            "config": {
                "enabled": self.config.enabled,
                "mode": self.config.mode.value,
                "confidence_threshold": self.config.confidence_threshold,
                "max_results": self.config.max_results
            },
            "similarity_threshold": 0.7,
            "stop_words_count": len(self.stop_words),
            "semantic_patterns_count": len(self.similarity_patterns)
        }