"""
Suggestion Generator - LLM-powered intelligent suggestions for specification improvements.

This module generates context-aware suggestions for handling edge cases, resolving
contradictions, filling completeness gaps, and refining compressed requirements.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import uuid
from datetime import datetime
import re


@dataclass
class Suggestion:
    """Represents a single improvement suggestion."""
    id: str
    type: str  # edge_case_handling, contradiction_resolution, etc.
    title: str
    description: str
    content: Dict[str, Any]
    confidence: float  # 0.0 to 1.0
    impact: str  # high, medium, low
    effort: str  # low, medium, high
    rationale: str
    examples: Optional[List[str]] = None
    related_items: Optional[List[str]] = None


class SuggestionGenerator:
    """
    Generates intelligent, context-aware suggestions for specification improvements.

    Uses LLM-powered analysis to provide actionable recommendations that feel like
    advice from a senior architect who understands the domain and context.
    """

    def __init__(self, llm_client=None):
        self.llm_client = llm_client  # Placeholder for LLM integration
        self.suggestion_templates = self._load_suggestion_templates()
        self.domain_patterns = self._load_domain_patterns()

    def suggest_edge_case_handling(self, edge_cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate suggestions for handling identified edge cases."""
        suggestions = []

        for edge_case in edge_cases:
            if edge_case.get('handled'):
                continue  # Skip already handled cases

            # Analyze the edge case to determine handling strategy
            handling_suggestions = self._analyze_edge_case_handling(edge_case)

            for handling in handling_suggestions:
                suggestion = Suggestion(
                    id=str(uuid.uuid4()),
                    type="edge_case_handling",
                    title=f"Handle: {edge_case.get('description', 'Unknown case')[:50]}...",
                    description=handling['description'],
                    content={
                        'edge_case_id': edge_case.get('id'),
                        'edge_case': edge_case,
                        'handling_strategy': handling['strategy'],
                        'implementation': handling['implementation']
                    },
                    confidence=handling['confidence'],
                    impact=handling['impact'],
                    effort=handling['effort'],
                    rationale=handling['rationale'],
                    examples=handling.get('examples'),
                    related_items=handling.get('related_items')
                )

                suggestions.append(suggestion.__dict__)

        return suggestions

    def suggest_contradiction_resolutions(self, contradictions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate suggestions for resolving contradictions."""
        suggestions = []

        for contradiction in contradictions:
            if contradiction.get('resolved'):
                continue  # Skip already resolved contradictions

            # Analyze the contradiction to determine resolution strategies
            resolution_suggestions = self._analyze_contradiction_resolution(contradiction)

            for resolution in resolution_suggestions:
                suggestion = Suggestion(
                    id=str(uuid.uuid4()),
                    type="contradiction_resolution",
                    title=f"Resolve: {contradiction.get('description', 'Unknown contradiction')[:50]}...",
                    description=resolution['description'],
                    content={
                        'contradiction_id': contradiction.get('id'),
                        'contradiction': contradiction,
                        'resolution_strategy': resolution['strategy'],
                        'resolution_details': resolution['details'],
                        'affected_requirements': resolution.get('affected_requirements', [])
                    },
                    confidence=resolution['confidence'],
                    impact=resolution['impact'],
                    effort=resolution['effort'],
                    rationale=resolution['rationale'],
                    examples=resolution.get('examples'),
                    related_items=resolution.get('related_items')
                )

                suggestions.append(suggestion.__dict__)

        return suggestions

    def suggest_completeness_improvements(self, gaps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate suggestions for filling completeness gaps."""
        suggestions = []

        for gap in gaps:
            # Analyze the gap to suggest specific requirements
            improvement_suggestions = self._analyze_completeness_gap(gap)

            for improvement in improvement_suggestions:
                suggestion = Suggestion(
                    id=str(uuid.uuid4()),
                    type="completeness_addition",
                    title=f"Add: {improvement['title']}",
                    description=improvement['description'],
                    content={
                        'gap_id': gap.get('id'),
                        'gap': gap,
                        'new_requirement': improvement['requirement'],
                        'requirement_type': improvement['requirement_type'],
                        'justification': improvement['justification']
                    },
                    confidence=improvement['confidence'],
                    impact=improvement['impact'],
                    effort=improvement['effort'],
                    rationale=improvement['rationale'],
                    examples=improvement.get('examples'),
                    related_items=improvement.get('related_items')
                )

                suggestions.append(suggestion.__dict__)

        return suggestions

    def suggest_compression_refinements(self, compressed: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate suggestions for refining compressed requirements."""
        suggestions = []

        for compression in compressed:
            # Analyze compression quality and suggest improvements
            refinement_suggestions = self._analyze_compression_refinement(compression)

            for refinement in refinement_suggestions:
                suggestion = Suggestion(
                    id=str(uuid.uuid4()),
                    type="compression_refinement",
                    title=f"Refine: {refinement['title']}",
                    description=refinement['description'],
                    content={
                        'compression_id': compression.get('id'),
                        'original_compression': compression,
                        'refined_requirement': refinement['refined_requirement'],
                        'improvement_type': refinement['improvement_type'],
                        'quality_gain': refinement['quality_gain']
                    },
                    confidence=refinement['confidence'],
                    impact=refinement['impact'],
                    effort=refinement['effort'],
                    rationale=refinement['rationale'],
                    examples=refinement.get('examples'),
                    related_items=refinement.get('related_items')
                )

                suggestions.append(suggestion.__dict__)

        return suggestions

    def rank_suggestions(self, suggestions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Rank suggestions by confidence, impact, and effort to prioritize user review.

        Uses a weighted scoring system to surface the most valuable suggestions first.
        """
        scored_suggestions = []

        for suggestion in suggestions:
            score = self._calculate_suggestion_score(suggestion)
            suggestion['score'] = score
            suggestion['rank_rationale'] = self._get_ranking_rationale(suggestion, score)
            scored_suggestions.append(suggestion)

        # Sort by score (highest first)
        ranked_suggestions = sorted(scored_suggestions, key=lambda x: x['score'], reverse=True)

        # Add rank information
        for i, suggestion in enumerate(ranked_suggestions):
            suggestion['rank'] = i + 1

        return ranked_suggestions

    def _analyze_edge_case_handling(self, edge_case: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze an edge case and suggest handling strategies."""
        handling_strategies = []

        case_description = edge_case.get('description', '').lower()
        case_context = edge_case.get('context', '').lower()
        case_impact = edge_case.get('impact', 'medium')

        # Pattern-based strategy selection
        if any(keyword in case_description for keyword in ['null', 'empty', 'missing']):
            handling_strategies.extend(self._suggest_null_handling(edge_case))

        if any(keyword in case_description for keyword in ['boundary', 'limit', 'range']):
            handling_strategies.extend(self._suggest_boundary_handling(edge_case))

        if any(keyword in case_description for keyword in ['concurrent', 'parallel', 'race']):
            handling_strategies.extend(self._suggest_concurrency_handling(edge_case))

        if any(keyword in case_description for keyword in ['network', 'timeout', 'connection']):
            handling_strategies.extend(self._suggest_network_handling(edge_case))

        if any(keyword in case_description for keyword in ['user', 'input', 'validation']):
            handling_strategies.extend(self._suggest_validation_handling(edge_case))

        # If no specific patterns match, provide generic strategies
        if not handling_strategies:
            handling_strategies.extend(self._suggest_generic_handling(edge_case))

        return handling_strategies

    def _suggest_null_handling(self, edge_case: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Suggest strategies for null/empty/missing value edge cases."""
        return [{
            'strategy': 'null_value_handling',
            'description': 'Implement comprehensive null/empty value handling',
            'implementation': 'Add validation and default value mechanisms',
            'confidence': 0.85,
            'impact': 'high',
            'effort': 'low',
            'rationale': 'Null/empty values are common sources of errors and should be handled explicitly',
            'examples': [
                'Validate input parameters before processing',
                'Provide sensible defaults for optional fields',
                'Return clear error messages for required missing values'
            ]
        }, {
            'strategy': 'graceful_degradation',
            'description': 'Implement graceful degradation for missing data',
            'implementation': 'Design fallback behavior when data is unavailable',
            'confidence': 0.75,
            'impact': 'medium',
            'effort': 'medium',
            'rationale': 'System should continue functioning even with partial data',
            'examples': [
                'Use cached data when fresh data is unavailable',
                'Display partial results with appropriate warnings',
                'Implement retry mechanisms with exponential backoff'
            ]
        }]

    def _suggest_boundary_handling(self, edge_case: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Suggest strategies for boundary/limit edge cases."""
        return [{
            'strategy': 'boundary_validation',
            'description': 'Implement strict boundary validation and limits',
            'implementation': 'Add input validation for all boundary conditions',
            'confidence': 0.90,
            'impact': 'high',
            'effort': 'low',
            'rationale': 'Boundary conditions are critical for system stability and security',
            'examples': [
                'Validate array indices before access',
                'Check memory limits before allocation',
                'Implement rate limiting for API calls'
            ]
        }, {
            'strategy': 'dynamic_scaling',
            'description': 'Implement dynamic scaling for resource limits',
            'implementation': 'Design system to handle varying load conditions',
            'confidence': 0.70,
            'impact': 'high',
            'effort': 'high',
            'rationale': 'Dynamic scaling provides better resource utilization and user experience',
            'examples': [
                'Auto-scale server capacity based on demand',
                'Implement pagination for large data sets',
                'Use streaming for large file processing'
            ]
        }]

    def _suggest_concurrency_handling(self, edge_case: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Suggest strategies for concurrency edge cases."""
        return [{
            'strategy': 'synchronization',
            'description': 'Implement proper synchronization mechanisms',
            'implementation': 'Add locks, semaphores, or atomic operations',
            'confidence': 0.80,
            'impact': 'high',
            'effort': 'medium',
            'rationale': 'Concurrency issues can lead to data corruption and system instability',
            'examples': [
                'Use database transactions for data consistency',
                'Implement optimistic locking for concurrent updates',
                'Add mutex locks for shared resource access'
            ]
        }, {
            'strategy': 'immutable_design',
            'description': 'Design with immutable data structures',
            'implementation': 'Use immutable objects to prevent race conditions',
            'confidence': 0.75,
            'impact': 'medium',
            'effort': 'high',
            'rationale': 'Immutable design eliminates many concurrency issues at the architectural level',
            'examples': [
                'Use immutable data structures in multi-threaded code',
                'Implement event sourcing for state changes',
                'Design stateless services where possible'
            ]
        }]

    def _suggest_network_handling(self, edge_case: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Suggest strategies for network-related edge cases."""
        return [{
            'strategy': 'timeout_and_retry',
            'description': 'Implement timeout and retry mechanisms',
            'implementation': 'Add configurable timeouts and exponential backoff',
            'confidence': 0.85,
            'impact': 'high',
            'effort': 'low',
            'rationale': 'Network issues are common and require robust error handling',
            'examples': [
                'Set appropriate timeouts for all network calls',
                'Implement exponential backoff for retries',
                'Add circuit breaker pattern for failing services'
            ]
        }, {
            'strategy': 'offline_capability',
            'description': 'Implement offline capability and data synchronization',
            'implementation': 'Add local caching and sync mechanisms',
            'confidence': 0.70,
            'impact': 'medium',
            'effort': 'high',
            'rationale': 'Offline capability improves user experience during network issues',
            'examples': [
                'Cache data locally for offline access',
                'Implement conflict resolution for sync',
                'Provide clear offline mode indicators'
            ]
        }]

    def _suggest_validation_handling(self, edge_case: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Suggest strategies for user input validation edge cases."""
        return [{
            'strategy': 'comprehensive_validation',
            'description': 'Implement comprehensive input validation',
            'implementation': 'Add validation at all system boundaries',
            'confidence': 0.90,
            'impact': 'high',
            'effort': 'medium',
            'rationale': 'Input validation is critical for security and data integrity',
            'examples': [
                'Validate all user inputs on both client and server',
                'Sanitize inputs to prevent injection attacks',
                'Provide clear validation error messages'
            ]
        }, {
            'strategy': 'progressive_validation',
            'description': 'Implement progressive validation and user guidance',
            'implementation': 'Add real-time validation with helpful feedback',
            'confidence': 0.75,
            'impact': 'medium',
            'effort': 'medium',
            'rationale': 'Progressive validation improves user experience and reduces errors',
            'examples': [
                'Show validation errors as user types',
                'Provide suggestions for valid inputs',
                'Use progressive disclosure for complex forms'
            ]
        }]

    def _suggest_generic_handling(self, edge_case: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Suggest generic strategies for unclassified edge cases."""
        return [{
            'strategy': 'defensive_programming',
            'description': 'Implement defensive programming practices',
            'implementation': 'Add comprehensive error checking and logging',
            'confidence': 0.70,
            'impact': 'medium',
            'effort': 'low',
            'rationale': 'Defensive programming helps catch and handle unexpected conditions',
            'examples': [
                'Add assertions for critical assumptions',
                'Implement comprehensive logging',
                'Add health checks and monitoring'
            ]
        }, {
            'strategy': 'graceful_error_handling',
            'description': 'Implement graceful error handling and recovery',
            'implementation': 'Add user-friendly error handling with recovery options',
            'confidence': 0.75,
            'impact': 'medium',
            'effort': 'medium',
            'rationale': 'Good error handling improves user experience and system reliability',
            'examples': [
                'Provide clear error messages to users',
                'Implement automatic recovery where possible',
                'Add manual recovery options for users'
            ]
        }]

    def _analyze_contradiction_resolution(self, contradiction: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze a contradiction and suggest resolution strategies."""
        conflicting_reqs = contradiction.get('conflicting_requirements', [])
        description = contradiction.get('description', '').lower()

        resolutions = []

        # Pattern-based resolution strategies
        if 'priority' in description or 'precedence' in description:
            resolutions.append(self._suggest_priority_resolution(contradiction))

        if 'performance' in description and 'security' in description:
            resolutions.append(self._suggest_performance_security_balance(contradiction))

        if 'user' in description and ('admin' in description or 'system' in description):
            resolutions.append(self._suggest_role_based_resolution(contradiction))

        # Generic resolution strategies
        resolutions.append(self._suggest_requirements_merge(contradiction))
        resolutions.append(self._suggest_conditional_requirements(contradiction))

        return resolutions

    def _suggest_priority_resolution(self, contradiction: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest priority-based resolution for contradictions."""
        return {
            'strategy': 'priority_hierarchy',
            'description': 'Establish clear priority hierarchy for conflicting requirements',
            'details': 'Define which requirement takes precedence in conflict situations',
            'confidence': 0.80,
            'impact': 'high',
            'effort': 'low',
            'rationale': 'Clear priorities help resolve conflicts consistently',
            'examples': [
                'Security requirements override performance requirements',
                'User safety takes precedence over convenience features',
                'Core functionality priority over nice-to-have features'
            ]
        }

    def _suggest_performance_security_balance(self, contradiction: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest balanced approach for performance vs security contradictions."""
        return {
            'strategy': 'configurable_balance',
            'description': 'Implement configurable balance between performance and security',
            'details': 'Allow system configuration to adjust performance/security trade-offs',
            'confidence': 0.75,
            'impact': 'medium',
            'effort': 'high',
            'rationale': 'Different environments may require different performance/security balances',
            'examples': [
                'Configurable encryption levels',
                'Performance vs security profiles',
                'Runtime security policy adjustments'
            ]
        }

    def _suggest_role_based_resolution(self, contradiction: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest role-based resolution for user vs admin contradictions."""
        return {
            'strategy': 'role_based_requirements',
            'description': 'Implement role-based requirement differentiation',
            'details': 'Define different requirements for different user roles',
            'confidence': 0.85,
            'impact': 'medium',
            'effort': 'medium',
            'rationale': 'Different user roles often have legitimately different requirements',
            'examples': [
                'Admin users have access to advanced features',
                'Regular users have simplified interfaces',
                'Power users get configurable options'
            ]
        }

    def _suggest_requirements_merge(self, contradiction: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest merging contradictory requirements into a unified requirement."""
        return {
            'strategy': 'unified_requirement',
            'description': 'Merge contradictory requirements into unified requirement',
            'details': 'Combine the best aspects of conflicting requirements',
            'confidence': 0.70,
            'impact': 'medium',
            'effort': 'medium',
            'rationale': 'Sometimes contradictions can be resolved by finding a unified approach',
            'examples': [
                'Combine fast and secure by using optimized secure algorithms',
                'Merge simple and powerful by providing layered interfaces',
                'Unite flexible and consistent through configuration templates'
            ]
        }

    def _suggest_conditional_requirements(self, contradiction: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest conditional resolution for contradictions."""
        return {
            'strategy': 'conditional_logic',
            'description': 'Implement conditional logic to handle conflicting requirements',
            'details': 'Apply different requirements based on context or conditions',
            'confidence': 0.75,
            'impact': 'medium',
            'effort': 'medium',
            'rationale': 'Context-sensitive requirements can resolve many contradictions',
            'examples': [
                'Different behavior for different environments',
                'Time-based requirement activation',
                'Load-based performance adjustments'
            ]
        }

    def _analyze_completeness_gap(self, gap: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze a completeness gap and suggest specific requirements."""
        gap_description = gap.get('description', '').lower()
        gap_category = gap.get('category', 'general')

        improvements = []

        # Pattern-based gap analysis
        if 'error' in gap_description or 'exception' in gap_description:
            improvements.append(self._suggest_error_handling_requirement(gap))

        if 'security' in gap_description or 'auth' in gap_description:
            improvements.append(self._suggest_security_requirement(gap))

        if 'performance' in gap_description or 'scalability' in gap_description:
            improvements.append(self._suggest_performance_requirement(gap))

        if 'usability' in gap_description or 'accessibility' in gap_description:
            improvements.append(self._suggest_usability_requirement(gap))

        if 'monitoring' in gap_description or 'logging' in gap_description:
            improvements.append(self._suggest_observability_requirement(gap))

        # Generic gap filling
        if not improvements:
            improvements.append(self._suggest_generic_requirement(gap))

        return improvements

    def _suggest_error_handling_requirement(self, gap: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest error handling requirements for gaps."""
        return {
            'title': 'Comprehensive Error Handling',
            'description': 'Add comprehensive error handling and recovery mechanisms',
            'requirement': {
                'type': 'error_handling',
                'content': 'System must implement comprehensive error handling with clear error messages, logging, and recovery mechanisms',
                'priority': 'high',
                'category': 'reliability'
            },
            'requirement_type': 'non_functional',
            'justification': 'Proper error handling is essential for system reliability and user experience',
            'confidence': 0.85,
            'impact': 'high',
            'effort': 'medium',
            'rationale': 'Missing error handling leads to poor user experience and difficult debugging',
            'examples': [
                'Implement global exception handling',
                'Add structured error logging',
                'Provide user-friendly error messages'
            ]
        }

    def _suggest_security_requirement(self, gap: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest security requirements for gaps."""
        return {
            'title': 'Security and Authentication',
            'description': 'Add comprehensive security and authentication requirements',
            'requirement': {
                'type': 'security',
                'content': 'System must implement secure authentication, authorization, and data protection mechanisms',
                'priority': 'high',
                'category': 'security'
            },
            'requirement_type': 'non_functional',
            'justification': 'Security is critical for protecting user data and system integrity',
            'confidence': 0.90,
            'impact': 'high',
            'effort': 'high',
            'rationale': 'Security gaps expose the system to significant risks',
            'examples': [
                'Implement multi-factor authentication',
                'Add role-based access control',
                'Encrypt sensitive data at rest and in transit'
            ]
        }

    def _suggest_performance_requirement(self, gap: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest performance requirements for gaps."""
        return {
            'title': 'Performance and Scalability',
            'description': 'Add specific performance and scalability requirements',
            'requirement': {
                'type': 'performance',
                'content': 'System must meet specific performance benchmarks and scale to handle expected load',
                'priority': 'medium',
                'category': 'performance'
            },
            'requirement_type': 'non_functional',
            'justification': 'Performance requirements ensure good user experience under load',
            'confidence': 0.80,
            'impact': 'medium',
            'effort': 'medium',
            'rationale': 'Performance gaps lead to poor user experience and scalability issues',
            'examples': [
                'Response time under 200ms for common operations',
                'Support for 10,000 concurrent users',
                'Database queries optimized for performance'
            ]
        }

    def _suggest_usability_requirement(self, gap: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest usability requirements for gaps."""
        return {
            'title': 'Usability and Accessibility',
            'description': 'Add usability and accessibility requirements',
            'requirement': {
                'type': 'usability',
                'content': 'System must provide intuitive user interface and meet accessibility standards',
                'priority': 'medium',
                'category': 'usability'
            },
            'requirement_type': 'non_functional',
            'justification': 'Usability requirements ensure the system is accessible to all users',
            'confidence': 0.75,
            'impact': 'medium',
            'effort': 'medium',
            'rationale': 'Usability gaps make the system difficult to use and potentially inaccessible',
            'examples': [
                'Meet WCAG 2.1 accessibility standards',
                'Intuitive navigation and user flows',
                'Responsive design for mobile devices'
            ]
        }

    def _suggest_observability_requirement(self, gap: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest observability requirements for gaps."""
        return {
            'title': 'Monitoring and Observability',
            'description': 'Add comprehensive monitoring and observability requirements',
            'requirement': {
                'type': 'observability',
                'content': 'System must provide comprehensive monitoring, logging, and alerting capabilities',
                'priority': 'medium',
                'category': 'operational'
            },
            'requirement_type': 'non_functional',
            'justification': 'Observability is essential for maintaining and debugging the system',
            'confidence': 0.80,
            'impact': 'medium',
            'effort': 'low',
            'rationale': 'Missing observability makes the system difficult to maintain and debug',
            'examples': [
                'Structured application logging',
                'Performance and health monitoring',
                'Automated alerting for critical issues'
            ]
        }

    def _suggest_generic_requirement(self, gap: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest generic requirements for unclassified gaps."""
        gap_description = gap.get('description', 'Missing requirement')

        return {
            'title': f"Address: {gap_description[:50]}...",
            'description': f"Add requirement to address identified gap: {gap_description}",
            'requirement': {
                'type': 'functional',
                'content': f"System must address the following requirement: {gap_description}",
                'priority': gap.get('priority', 'medium'),
                'category': gap.get('category', 'general')
            },
            'requirement_type': 'functional',
            'justification': 'Addresses identified completeness gap in specification',
            'confidence': 0.60,
            'impact': gap.get('impact', 'medium'),
            'effort': 'medium',
            'rationale': 'Completeness gaps should be addressed to ensure comprehensive coverage',
            'examples': []
        }

    def _analyze_compression_refinement(self, compression: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze compressed requirements and suggest refinements."""
        compressed_req = compression.get('compressed_requirement', '')
        original_reqs = compression.get('original_requirements', [])
        confidence = compression.get('confidence', 0.5)

        refinements = []

        # Check if compression is too aggressive (low confidence)
        if confidence < 0.7:
            refinements.append(self._suggest_decompress_refinement(compression))

        # Check if important details were lost
        if self._check_detail_loss(original_reqs, compressed_req):
            refinements.append(self._suggest_detail_recovery(compression))

        # Check if compression can be improved
        if self._check_clarity_improvement(compressed_req):
            refinements.append(self._suggest_clarity_improvement(compression))

        return refinements

    def _suggest_decompress_refinement(self, compression: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest decompressing overly aggressive compression."""
        return {
            'title': 'Reduce Compression',
            'description': 'Expand compressed requirement to preserve important details',
            'refined_requirement': self._expand_compressed_requirement(compression),
            'improvement_type': 'detail_preservation',
            'quality_gain': 'Better preserves original intent and details',
            'confidence': 0.75,
            'impact': 'medium',
            'effort': 'low',
            'rationale': 'Overly aggressive compression can lose important details'
        }

    def _suggest_detail_recovery(self, compression: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest recovering lost details from compression."""
        return {
            'title': 'Recover Lost Details',
            'description': 'Add back important details that were lost in compression',
            'refined_requirement': self._recover_lost_details(compression),
            'improvement_type': 'detail_recovery',
            'quality_gain': 'Restores important details while maintaining conciseness',
            'confidence': 0.80,
            'impact': 'medium',
            'effort': 'low',
            'rationale': 'Important details should not be lost during compression'
        }

    def _suggest_clarity_improvement(self, compression: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest improving clarity of compressed requirement."""
        return {
            'title': 'Improve Clarity',
            'description': 'Improve clarity and readability of compressed requirement',
            'refined_requirement': self._improve_compression_clarity(compression),
            'improvement_type': 'clarity_improvement',
            'quality_gain': 'Better readability and understanding',
            'confidence': 0.70,
            'impact': 'low',
            'effort': 'low',
            'rationale': 'Clear requirements are easier to understand and implement'
        }

    def _calculate_suggestion_score(self, suggestion: Dict[str, Any]) -> float:
        """Calculate a composite score for suggestion ranking."""
        confidence = suggestion.get('confidence', 0.5)

        # Impact scoring
        impact_scores = {'high': 1.0, 'medium': 0.6, 'low': 0.3}
        impact_score = impact_scores.get(suggestion.get('impact', 'medium'), 0.6)

        # Effort scoring (lower effort = higher score)
        effort_scores = {'low': 1.0, 'medium': 0.7, 'high': 0.4}
        effort_score = effort_scores.get(suggestion.get('effort', 'medium'), 0.7)

        # Type priority scoring
        type_scores = {
            'contradiction_resolution': 1.0,  # Highest priority
            'edge_case_handling': 0.8,
            'completeness_addition': 0.6,
            'compression_refinement': 0.4    # Lowest priority
        }
        type_score = type_scores.get(suggestion.get('type', 'completeness_addition'), 0.6)

        # Weighted composite score
        score = (
            confidence * 0.3 +      # 30% weight on confidence
            impact_score * 0.4 +    # 40% weight on impact
            effort_score * 0.2 +    # 20% weight on effort (inverted)
            type_score * 0.1        # 10% weight on type priority
        )

        return round(score, 3)

    def _get_ranking_rationale(self, suggestion: Dict[str, Any], score: float) -> str:
        """Generate explanation for suggestion ranking."""
        confidence = suggestion.get('confidence', 0.5)
        impact = suggestion.get('impact', 'medium')
        effort = suggestion.get('effort', 'medium')
        suggestion_type = suggestion.get('type', 'unknown')

        rationale_parts = []

        if confidence >= 0.8:
            rationale_parts.append("high confidence")
        elif confidence >= 0.6:
            rationale_parts.append("medium confidence")
        else:
            rationale_parts.append("lower confidence")

        rationale_parts.append(f"{impact} impact")
        rationale_parts.append(f"{effort} effort")

        if suggestion_type == 'contradiction_resolution':
            rationale_parts.append("critical contradiction")
        elif suggestion_type == 'edge_case_handling':
            rationale_parts.append("important edge case")

        return f"Ranked due to: {', '.join(rationale_parts)} (score: {score})"

    def _check_detail_loss(self, original_reqs: List[Dict[str, Any]], compressed_req: str) -> bool:
        """Check if important details were lost in compression."""
        # Simple heuristic: if compressed requirement is much shorter, details might be lost
        original_length = sum(len(req.get('content', '')) for req in original_reqs)
        compressed_length = len(compressed_req)

        # If compression is more than 70%, might have lost details
        return compressed_length < (original_length * 0.3)

    def _check_clarity_improvement(self, compressed_req: str) -> bool:
        """Check if clarity of compressed requirement can be improved."""
        # Simple heuristics for clarity issues
        clarity_issues = [
            len(compressed_req.split()) > 50,  # Too long
            compressed_req.count(',') > 5,     # Too many clauses
            ' and ' in compressed_req and ' or ' in compressed_req,  # Mixed logic
            not compressed_req.strip().endswith('.'),  # No proper ending
        ]

        return any(clarity_issues)

    def _expand_compressed_requirement(self, compression: Dict[str, Any]) -> str:
        """Expand an overly compressed requirement."""
        original_reqs = compression.get('original_requirements', [])
        compressed_req = compression.get('compressed_requirement', '')

        # Simple expansion strategy: add back key details from originals
        key_details = []
        for req in original_reqs:
            content = req.get('content', '')
            # Extract key phrases (very simplified)
            if 'must' in content.lower():
                key_details.append(content)

        if key_details:
            return f"{compressed_req} Specifically: {'; '.join(key_details[:2])}"
        else:
            return compressed_req

    def _recover_lost_details(self, compression: Dict[str, Any]) -> str:
        """Recover lost details from compression."""
        # Placeholder implementation - in practice would use more sophisticated analysis
        compressed_req = compression.get('compressed_requirement', '')
        return f"{compressed_req} [Details recovered from original requirements]"

    def _improve_compression_clarity(self, compression: Dict[str, Any]) -> str:
        """Improve clarity of compressed requirement."""
        compressed_req = compression.get('compressed_requirement', '')

        # Simple clarity improvements
        improved = compressed_req

        # Add proper punctuation
        if not improved.strip().endswith('.'):
            improved += '.'

        # Break up long sentences
        if len(improved.split()) > 30:
            # Find a good break point (very simplified)
            words = improved.split()
            mid_point = len(words) // 2
            improved = ' '.join(words[:mid_point]) + '. ' + ' '.join(words[mid_point:])

        return improved

    def _load_suggestion_templates(self) -> Dict[str, Any]:
        """Load suggestion templates for different types of improvements."""
        # Placeholder - in practice would load from configuration
        return {}

    def _load_domain_patterns(self) -> Dict[str, Any]:
        """Load domain-specific patterns for suggestion generation."""
        # Placeholder - in practice would load domain-specific knowledge
        return {}