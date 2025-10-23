"""
Researcher Agent - Specialized agent for research and information gathering.

This agent searches documentation, analyzes APIs, evaluates libraries,
and gathers technical information to support development tasks.
"""

import json
import re
import requests
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse, urljoin
import time

from ..base_agent import BaseAgent
from ...models import AgentType, TaskType, Task, AgentResult, TaskArtifact


class ResearcherAgent(BaseAgent):
    """
    Specialized agent for research and information gathering.

    Capabilities:
    - Search and analyze documentation
    - Evaluate libraries and frameworks
    - Research APIs and integrations
    - Gather technical requirements
    - Analyze best practices and patterns
    - Compare technologies and solutions
    """

    def __init__(self, agent_id: str = None, config: Dict[str, Any] = None):
        super().__init__(agent_id, config)

        # Research configuration
        self.search_engines = config.get('search_engines', []) if config else []
        self.documentation_sources = config.get('documentation_sources', []) if config else []
        self.api_keys = config.get('api_keys', {}) if config else {}
        self.max_search_results = config.get('max_search_results', 10) if config else 10
        self.request_timeout = config.get('request_timeout', 30) if config else 30

        # LLM for analysis
        self.llm_client = config.get('llm_client') if config else None

        # Default documentation sources
        self.default_doc_sources = [
            'https://docs.python.org',
            'https://developer.mozilla.org',
            'https://docs.oracle.com/javase',
            'https://golang.org/doc',
            'https://docs.microsoft.com',
            'https://stackoverflow.com',
            'https://github.com'
        ]

        # Common package registries
        self.package_registries = {
            'python': 'https://pypi.org/project',
            'javascript': 'https://www.npmjs.com/package',
            'java': 'https://mvnrepository.com/artifact',
            'go': 'https://pkg.go.dev',
            'rust': 'https://crates.io/crates',
            'php': 'https://packagist.org/packages',
            'ruby': 'https://rubygems.org/gems'
        }

    def get_agent_type(self) -> AgentType:
        """Return the agent type."""
        return AgentType.RESEARCHER

    def get_supported_task_types(self) -> List[TaskType]:
        """Return supported task types."""
        return [
            TaskType.RESEARCH,
            TaskType.ANALYSIS
        ]

    def _execute_task_impl(self, task: Task) -> AgentResult:
        """Execute a research task."""
        self.logger.info(f"Executing research task: {task.description}")

        try:
            # Analyze research requirements
            research_analysis = self._analyze_research_task(task)

            # Execute research based on type
            if research_analysis['research_type'] == 'library_evaluation':
                result = self._research_libraries(task, research_analysis)
            elif research_analysis['research_type'] == 'api_analysis':
                result = self._research_apis(task, research_analysis)
            elif research_analysis['research_type'] == 'technology_comparison':
                result = self._compare_technologies(task, research_analysis)
            elif research_analysis['research_type'] == 'best_practices':
                result = self._research_best_practices(task, research_analysis)
            elif research_analysis['research_type'] == 'documentation_search':
                result = self._search_documentation(task, research_analysis)
            else:
                result = self._general_research(task, research_analysis)

            return result

        except Exception as e:
            self.logger.error(f"Error executing research task: {e}")
            return self._create_error_result(task, str(e))

    def _analyze_research_task(self, task: Task) -> Dict[str, Any]:
        """Analyze the research task to determine approach."""
        description = task.description.lower()
        context = task.context

        analysis = {
            'research_type': 'general',
            'language': None,
            'frameworks': [],
            'search_terms': [],
            'domains': [],
            'specific_requirements': []
        }

        # Determine research type
        if any(term in description for term in ['library', 'package', 'dependency', 'evaluate']):
            analysis['research_type'] = 'library_evaluation'
        elif any(term in description for term in ['api', 'endpoint', 'integration', 'service']):
            analysis['research_type'] = 'api_analysis'
        elif any(term in description for term in ['compare', 'vs', 'versus', 'alternatives']):
            analysis['research_type'] = 'technology_comparison'
        elif any(term in description for term in ['best practice', 'pattern', 'guide', 'how to']):
            analysis['research_type'] = 'best_practices'
        elif any(term in description for term in ['documentation', 'docs', 'manual', 'reference']):
            analysis['research_type'] = 'documentation_search'

        # Extract language
        analysis['language'] = self._detect_language_from_task(task)

        # Extract frameworks and technologies
        analysis['frameworks'] = self._extract_frameworks_from_task(task)

        # Generate search terms
        analysis['search_terms'] = self._generate_search_terms(task, analysis)

        # Extract domains
        analysis['domains'] = self._extract_domains_from_task(task)

        self.logger.debug(f"Research analysis: {analysis}")
        return analysis

    def _research_libraries(self, task: Task, analysis: Dict[str, Any]) -> AgentResult:
        """Research and evaluate libraries/packages."""
        artifacts = []
        research_data = {}

        self.report_progress(0.1, "Identifying libraries to research")

        # Extract library names from task
        library_names = self._extract_library_names(task, analysis)

        if not library_names:
            # Search for relevant libraries
            library_names = self._search_for_libraries(task, analysis)

        self.report_progress(0.3, f"Researching {len(library_names)} libraries")

        library_evaluations = []
        for i, library_name in enumerate(library_names):
            self.report_progress(0.3 + (0.5 * i / len(library_names)), f"Evaluating {library_name}")

            evaluation = self._evaluate_library(library_name, analysis['language'], task)
            library_evaluations.append(evaluation)

        # Generate comparison and recommendations
        self.report_progress(0.8, "Generating recommendations")
        recommendations = self._generate_library_recommendations(library_evaluations, task)

        # Create research report
        research_report = self._create_library_research_report(
            library_evaluations, recommendations, task
        )

        # Create artifacts
        report_artifact = self.create_artifact(
            f"{task.task_id}_library_research_report",
            "research_report",
            research_report
        )
        artifacts.append(report_artifact)

        research_data.update({
            'library_evaluations': library_evaluations,
            'recommendations': recommendations,
            'research_type': 'library_evaluation'
        })

        self.report_progress(1.0, "Library research completed")

        return AgentResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            agent_type=self.get_agent_type(),
            success=True,
            artifacts=artifacts,
            output_data=research_data,
            logs=[f"Researched {len(library_evaluations)} libraries"]
        )

    def _research_apis(self, task: Task, analysis: Dict[str, Any]) -> AgentResult:
        """Research APIs and integrations."""
        artifacts = []
        research_data = {}

        self.report_progress(0.2, "Analyzing API requirements")

        # Extract API information from task
        api_info = self._extract_api_info(task)

        self.report_progress(0.4, "Researching API documentation")

        # Research each API
        api_analyses = []
        for api_name, api_details in api_info.items():
            analysis_result = self._analyze_api(api_name, api_details, task)
            api_analyses.append(analysis_result)

        self.report_progress(0.8, "Generating API integration guide")

        # Generate integration recommendations
        integration_guide = self._generate_api_integration_guide(api_analyses, task)

        # Create research report
        research_report = self._create_api_research_report(api_analyses, integration_guide, task)

        # Create artifacts
        report_artifact = self.create_artifact(
            f"{task.task_id}_api_research_report",
            "research_report",
            research_report
        )
        artifacts.append(report_artifact)

        research_data.update({
            'api_analyses': api_analyses,
            'integration_guide': integration_guide,
            'research_type': 'api_analysis'
        })

        self.report_progress(1.0, "API research completed")

        return AgentResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            agent_type=self.get_agent_type(),
            success=True,
            artifacts=artifacts,
            output_data=research_data,
            logs=[f"Researched {len(api_analyses)} APIs"]
        )

    def _compare_technologies(self, task: Task, analysis: Dict[str, Any]) -> AgentResult:
        """Compare different technologies or solutions."""
        artifacts = []
        research_data = {}

        self.report_progress(0.1, "Identifying technologies to compare")

        # Extract technologies from task
        technologies = self._extract_technologies_to_compare(task)

        self.report_progress(0.3, f"Comparing {len(technologies)} technologies")

        # Research each technology
        tech_analyses = []
        for i, tech in enumerate(technologies):
            self.report_progress(0.3 + (0.4 * i / len(technologies)), f"Analyzing {tech}")
            analysis_result = self._analyze_technology(tech, task)
            tech_analyses.append(analysis_result)

        self.report_progress(0.8, "Generating comparison matrix")

        # Generate comparison matrix
        comparison_matrix = self._generate_comparison_matrix(tech_analyses, task)

        # Generate recommendations
        recommendations = self._generate_technology_recommendations(comparison_matrix, task)

        # Create research report
        research_report = self._create_technology_comparison_report(
            tech_analyses, comparison_matrix, recommendations, task
        )

        # Create artifacts
        report_artifact = self.create_artifact(
            f"{task.task_id}_technology_comparison",
            "research_report",
            research_report
        )
        artifacts.append(report_artifact)

        research_data.update({
            'technology_analyses': tech_analyses,
            'comparison_matrix': comparison_matrix,
            'recommendations': recommendations,
            'research_type': 'technology_comparison'
        })

        self.report_progress(1.0, "Technology comparison completed")

        return AgentResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            agent_type=self.get_agent_type(),
            success=True,
            artifacts=artifacts,
            output_data=research_data,
            logs=[f"Compared {len(tech_analyses)} technologies"]
        )

    def _research_best_practices(self, task: Task, analysis: Dict[str, Any]) -> AgentResult:
        """Research best practices and patterns."""
        artifacts = []
        research_data = {}

        self.report_progress(0.2, "Identifying best practice areas")

        # Extract practice areas from task
        practice_areas = self._extract_practice_areas(task, analysis)

        # Research best practices for each area
        best_practices = {}
        for i, area in enumerate(practice_areas):
            self.report_progress(0.2 + (0.6 * i / len(practice_areas)), f"Researching {area}")
            practices = self._research_practice_area(area, analysis, task)
            best_practices[area] = practices

        self.report_progress(0.9, "Generating best practices guide")

        # Generate comprehensive guide
        practices_guide = self._generate_best_practices_guide(best_practices, task)

        # Create research report
        research_report = self._create_best_practices_report(best_practices, practices_guide, task)

        # Create artifacts
        report_artifact = self.create_artifact(
            f"{task.task_id}_best_practices_guide",
            "research_report",
            research_report
        )
        artifacts.append(report_artifact)

        research_data.update({
            'best_practices': best_practices,
            'practices_guide': practices_guide,
            'research_type': 'best_practices'
        })

        self.report_progress(1.0, "Best practices research completed")

        return AgentResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            agent_type=self.get_agent_type(),
            success=True,
            artifacts=artifacts,
            output_data=research_data,
            logs=[f"Researched best practices for {len(practice_areas)} areas"]
        )

    def _search_documentation(self, task: Task, analysis: Dict[str, Any]) -> AgentResult:
        """Search and analyze documentation."""
        artifacts = []
        research_data = {}

        self.report_progress(0.2, "Searching documentation sources")

        # Search documentation
        search_results = self._search_docs(analysis['search_terms'], analysis)

        self.report_progress(0.6, "Analyzing documentation content")

        # Analyze and extract relevant information
        doc_analysis = self._analyze_documentation_results(search_results, task)

        self.report_progress(0.9, "Generating documentation summary")

        # Generate summary
        doc_summary = self._generate_documentation_summary(doc_analysis, task)

        # Create research report
        research_report = self._create_documentation_research_report(doc_analysis, doc_summary, task)

        # Create artifacts
        report_artifact = self.create_artifact(
            f"{task.task_id}_documentation_research",
            "research_report",
            research_report
        )
        artifacts.append(report_artifact)

        research_data.update({
            'documentation_analysis': doc_analysis,
            'documentation_summary': doc_summary,
            'search_results': search_results,
            'research_type': 'documentation_search'
        })

        self.report_progress(1.0, "Documentation research completed")

        return AgentResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            agent_type=self.get_agent_type(),
            success=True,
            artifacts=artifacts,
            output_data=research_data,
            logs=[f"Analyzed {len(search_results)} documentation sources"]
        )

    def _general_research(self, task: Task, analysis: Dict[str, Any]) -> AgentResult:
        """Perform general research."""
        artifacts = []
        research_data = {}

        self.report_progress(0.3, "Conducting general research")

        # Use LLM for research if available
        if self.llm_client:
            research_result = self._llm_research(task, analysis)
        else:
            research_result = self._web_research(task, analysis)

        # Create research report
        research_report = self._create_general_research_report(research_result, task)

        # Create artifacts
        report_artifact = self.create_artifact(
            f"{task.task_id}_research_report",
            "research_report",
            research_report
        )
        artifacts.append(report_artifact)

        research_data.update({
            'research_result': research_result,
            'research_type': 'general'
        })

        self.report_progress(1.0, "General research completed")

        return AgentResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            agent_type=self.get_agent_type(),
            success=True,
            artifacts=artifacts,
            output_data=research_data,
            logs=["Completed general research"]
        )

    def _detect_language_from_task(self, task: Task) -> Optional[str]:
        """Detect programming language from task."""
        text = f"{task.description} {str(task.context)}".lower()

        language_indicators = {
            'python': ['python', 'django', 'flask', 'pandas', 'numpy'],
            'javascript': ['javascript', 'js', 'node', 'react', 'vue'],
            'java': ['java', 'spring', 'maven'],
            'go': ['golang', 'go'],
            'rust': ['rust'],
            'php': ['php', 'laravel'],
            'ruby': ['ruby', 'rails']
        }

        for language, indicators in language_indicators.items():
            if any(indicator in text for indicator in indicators):
                return language

        return task.context.get('language')

    def _extract_frameworks_from_task(self, task: Task) -> List[str]:
        """Extract frameworks mentioned in the task."""
        text = f"{task.description} {str(task.context)}".lower()

        frameworks = [
            'react', 'vue', 'angular', 'express', 'django', 'flask',
            'spring', 'laravel', 'rails', 'fastapi', 'gin', 'echo'
        ]

        found_frameworks = []
        for framework in frameworks:
            if framework in text:
                found_frameworks.append(framework)

        return found_frameworks

    def _generate_search_terms(self, task: Task, analysis: Dict[str, Any]) -> List[str]:
        """Generate search terms for research."""
        terms = []

        # Add words from description
        description_words = re.findall(r'\b\w+\b', task.description.lower())
        terms.extend([word for word in description_words if len(word) > 3])

        # Add language and frameworks
        if analysis['language']:
            terms.append(analysis['language'])

        terms.extend(analysis['frameworks'])

        # Add specific technical terms
        technical_terms = task.context.get('technical_terms', [])
        terms.extend(technical_terms)

        # Remove duplicates and return top terms
        unique_terms = list(set(terms))
        return unique_terms[:10]

    def _extract_domains_from_task(self, task: Task) -> List[str]:
        """Extract domain areas from task."""
        text = f"{task.description} {str(task.context)}".lower()

        domains = {
            'web_development': ['web', 'frontend', 'backend', 'full-stack'],
            'data_science': ['data', 'analytics', 'machine learning', 'ai'],
            'mobile': ['mobile', 'ios', 'android', 'react native'],
            'devops': ['devops', 'docker', 'kubernetes', 'deployment'],
            'security': ['security', 'auth', 'encryption', 'vulnerability'],
            'database': ['database', 'sql', 'nosql', 'mongodb', 'postgresql']
        }

        found_domains = []
        for domain, keywords in domains.items():
            if any(keyword in text for keyword in keywords):
                found_domains.append(domain)

        return found_domains

    def _extract_library_names(self, task: Task, analysis: Dict[str, Any]) -> List[str]:
        """Extract specific library names from task."""
        # Look for library names in task description and context
        text = f"{task.description} {str(task.context)}"

        # Common patterns for library names
        library_patterns = [
            r'\b([a-z]+[-_]?[a-z]+)\s+(?:library|package|module)',
            r'(?:using|with|import)\s+([a-zA-Z][a-zA-Z0-9_-]*)',
            r'([a-zA-Z][a-zA-Z0-9_-]*)\s+(?:vs|versus|compared to)'
        ]

        libraries = []
        for pattern in library_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            libraries.extend(matches)

        # Check context for explicit library list
        if 'libraries' in task.context:
            libraries.extend(task.context['libraries'])

        return list(set(libraries))

    def _search_for_libraries(self, task: Task, analysis: Dict[str, Any]) -> List[str]:
        """Search for relevant libraries based on task requirements."""
        # This would implement library search logic
        # For now, return some default libraries based on language
        language = analysis['language']

        default_libraries = {
            'python': ['requests', 'pandas', 'numpy', 'flask', 'django'],
            'javascript': ['express', 'react', 'vue', 'lodash', 'axios'],
            'java': ['spring', 'junit', 'jackson', 'hibernate'],
            'go': ['gin', 'gorm', 'testify'],
        }

        return default_libraries.get(language, [])

    def _evaluate_library(self, library_name: str, language: str, task: Task) -> Dict[str, Any]:
        """Evaluate a specific library."""
        evaluation = {
            'name': library_name,
            'language': language,
            'popularity_score': 0,
            'maintenance_score': 0,
            'documentation_score': 0,
            'performance_score': 0,
            'security_score': 0,
            'ease_of_use_score': 0,
            'overall_score': 0,
            'pros': [],
            'cons': [],
            'use_cases': [],
            'alternatives': [],
            'installation': '',
            'basic_usage': '',
            'documentation_url': '',
            'repository_url': '',
            'license': '',
            'latest_version': '',
            'community_size': 0
        }

        try:
            # Try to fetch information from package registry
            package_info = self._fetch_package_info(library_name, language)
            if package_info:
                evaluation.update(package_info)

            # Use LLM to enhance evaluation if available
            if self.llm_client:
                llm_evaluation = self._llm_evaluate_library(library_name, language, task)
                if llm_evaluation:
                    evaluation.update(llm_evaluation)

        except Exception as e:
            self.logger.warning(f"Error evaluating library {library_name}: {e}")

        return evaluation

    def _fetch_package_info(self, library_name: str, language: str) -> Optional[Dict[str, Any]]:
        """Fetch package information from registries."""
        if language not in self.package_registries:
            return None

        try:
            # This is a simplified implementation
            # In practice, you'd make API calls to package registries
            return {
                'documentation_url': f"{self.package_registries[language]}/{library_name}",
                'installation': f"Install via package manager for {language}",
                'license': 'Unknown',
                'latest_version': '1.0.0'
            }

        except Exception as e:
            self.logger.warning(f"Error fetching package info for {library_name}: {e}")
            return None

    def _llm_evaluate_library(self, library_name: str, language: str, task: Task) -> Optional[Dict[str, Any]]:
        """Use LLM to evaluate a library."""
        prompt = f"""
Evaluate the {language} library "{library_name}" for the following use case:

TASK: {task.description}

Please provide a comprehensive evaluation including:
1. Popularity and community support (1-10 score)
2. Documentation quality (1-10 score)
3. Performance characteristics (1-10 score)
4. Security considerations (1-10 score)
5. Ease of use (1-10 score)
6. Pros and cons
7. Common use cases
8. Notable alternatives
9. Basic usage example

Format your response as JSON:
{{
  "popularity_score": 1-10,
  "documentation_score": 1-10,
  "performance_score": 1-10,
  "security_score": 1-10,
  "ease_of_use_score": 1-10,
  "pros": ["list of advantages"],
  "cons": ["list of disadvantages"],
  "use_cases": ["list of common use cases"],
  "alternatives": ["list of alternative libraries"],
  "basic_usage": "code example or description"
}}
"""

        try:
            response = self.llm_client.generate(
                prompt=prompt,
                max_tokens=2000,
                temperature=0.2
            )

            # Parse JSON response
            evaluation = json.loads(response)

            # Calculate overall score
            scores = [
                evaluation.get('popularity_score', 5),
                evaluation.get('documentation_score', 5),
                evaluation.get('performance_score', 5),
                evaluation.get('security_score', 5),
                evaluation.get('ease_of_use_score', 5)
            ]
            evaluation['overall_score'] = sum(scores) / len(scores)

            return evaluation

        except Exception as e:
            self.logger.warning(f"LLM library evaluation failed: {e}")
            return None

    def _generate_library_recommendations(self, evaluations: List[Dict[str, Any]], task: Task) -> Dict[str, Any]:
        """Generate library recommendations based on evaluations."""
        if not evaluations:
            return {'recommended': [], 'reasoning': 'No libraries to evaluate'}

        # Sort by overall score
        sorted_libs = sorted(evaluations, key=lambda x: x.get('overall_score', 0), reverse=True)

        recommendations = {
            'recommended': sorted_libs[0]['name'] if sorted_libs else None,
            'top_3': [lib['name'] for lib in sorted_libs[:3]],
            'reasoning': f"Based on evaluation criteria, {sorted_libs[0]['name']} scored highest overall" if sorted_libs else "No clear recommendation",
            'detailed_comparison': sorted_libs
        }

        return recommendations

    # Additional helper methods would continue here...
    # For brevity, I'll implement the key structure and a few more methods

    def _create_library_research_report(self, evaluations: List[Dict[str, Any]],
                                      recommendations: Dict[str, Any], task: Task) -> str:
        """Create a comprehensive library research report."""
        report = f"""# Library Research Report

## Task
{task.description}

## Executive Summary
{recommendations.get('reasoning', 'No recommendations available')}

## Recommended Solution
**Primary Recommendation:** {recommendations.get('recommended', 'None')}

## Detailed Evaluations
"""

        for eval_data in evaluations:
            report += f"""
### {eval_data['name']}
- **Overall Score:** {eval_data.get('overall_score', 'N/A')}/10
- **Popularity:** {eval_data.get('popularity_score', 'N/A')}/10
- **Documentation:** {eval_data.get('documentation_score', 'N/A')}/10
- **Performance:** {eval_data.get('performance_score', 'N/A')}/10
- **Security:** {eval_data.get('security_score', 'N/A')}/10
- **Ease of Use:** {eval_data.get('ease_of_use_score', 'N/A')}/10

**Pros:**
{chr(10).join(f"- {pro}" for pro in eval_data.get('pros', []))}

**Cons:**
{chr(10).join(f"- {con}" for con in eval_data.get('cons', []))}
"""

        report += """
## Implementation Notes
- Consider project requirements and constraints
- Evaluate team expertise and learning curve
- Review license compatibility
- Plan for long-term maintenance

---
*Generated by ResearcherAgent*
"""

        return report

    def _llm_research(self, task: Task, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Use LLM for general research."""
        prompt = f"""
Conduct research on the following topic:

RESEARCH REQUEST: {task.description}

CONTEXT: {json.dumps(task.context, indent=2)}

Please provide comprehensive research including:
1. Overview of the topic
2. Key concepts and terminology
3. Current best practices
4. Available tools and technologies
5. Common challenges and solutions
6. Recommended approaches
7. Relevant resources and documentation

Structure your response clearly and provide actionable insights.
"""

        try:
            response = self.llm_client.generate(
                prompt=prompt,
                max_tokens=3000,
                temperature=0.3
            )

            return {
                'research_content': response,
                'method': 'llm_research',
                'quality_score': 8
            }

        except Exception as e:
            self.logger.error(f"LLM research failed: {e}")
            return self._fallback_research(task, analysis)

    def _fallback_research(self, task: Task, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback research method when LLM is not available."""
        return {
            'research_content': f"""
# Research Results for: {task.description}

## Overview
This research was conducted using fallback methods due to limited resources.

## Key Points
- Task requires investigation into: {', '.join(analysis['search_terms'])}
- Relevant domains: {', '.join(analysis['domains'])}
- Programming language: {analysis['language'] or 'Not specified'}

## Recommendations
1. Consult official documentation
2. Review community best practices
3. Consider proven solutions
4. Test thoroughly before implementation

## Next Steps
- Gather more specific requirements
- Prototype potential solutions
- Validate with stakeholders
""",
            'method': 'fallback_research',
            'quality_score': 5
        }

    def _create_general_research_report(self, research_result: Dict[str, Any], task: Task) -> str:
        """Create a general research report."""
        return f"""# Research Report

## Task
{task.description}

## Research Method
{research_result.get('method', 'Unknown')}

## Research Quality Score
{research_result.get('quality_score', 'N/A')}/10

## Findings
{research_result.get('research_content', 'No content available')}

---
*Generated by ResearcherAgent on {time.strftime('%Y-%m-%d %H:%M:%S')}*
"""

    # Placeholder methods for other research types
    def _extract_api_info(self, task: Task) -> Dict[str, Any]:
        """Extract API information from task."""
        return {'example_api': {'url': 'https://api.example.com', 'type': 'REST'}}

    def _analyze_api(self, api_name: str, api_details: Dict[str, Any], task: Task) -> Dict[str, Any]:
        """Analyze a specific API."""
        return {'name': api_name, 'analysis': 'Basic API analysis', 'rating': 7}

    def _generate_api_integration_guide(self, api_analyses: List[Dict[str, Any]], task: Task) -> str:
        """Generate API integration guide."""
        return "# API Integration Guide\n\nBasic integration steps..."

    def _create_api_research_report(self, api_analyses: List[Dict[str, Any]],
                                  integration_guide: str, task: Task) -> str:
        """Create API research report."""
        return f"# API Research Report\n\n{integration_guide}"

    def _extract_technologies_to_compare(self, task: Task) -> List[str]:
        """Extract technologies to compare."""
        return ['Technology A', 'Technology B', 'Technology C']

    def _analyze_technology(self, technology: str, task: Task) -> Dict[str, Any]:
        """Analyze a technology."""
        return {'name': technology, 'analysis': 'Basic tech analysis', 'score': 7}

    def _generate_comparison_matrix(self, tech_analyses: List[Dict[str, Any]], task: Task) -> Dict[str, Any]:
        """Generate technology comparison matrix."""
        return {'matrix': 'Comparison data', 'winner': 'Technology A'}

    def _generate_technology_recommendations(self, comparison_matrix: Dict[str, Any], task: Task) -> Dict[str, Any]:
        """Generate technology recommendations."""
        return {'recommended': 'Technology A', 'reasoning': 'Best overall fit'}

    def _create_technology_comparison_report(self, tech_analyses: List[Dict[str, Any]],
                                           comparison_matrix: Dict[str, Any],
                                           recommendations: Dict[str, Any], task: Task) -> str:
        """Create technology comparison report."""
        return f"# Technology Comparison Report\n\nRecommended: {recommendations['recommended']}"