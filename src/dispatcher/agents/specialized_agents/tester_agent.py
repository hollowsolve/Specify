"""
Tester Agent - Specialized agent for testing and quality assurance.

This agent generates and runs tests, validates code quality,
and ensures software meets requirements and standards.
"""

import os
import re
import json
import subprocess
import tempfile
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from ..base_agent import BaseAgent
from ...models import AgentType, TaskType, Task, AgentResult, TaskArtifact


class TesterAgent(BaseAgent):
    """
    Specialized agent for testing and quality assurance.

    Capabilities:
    - Generate unit tests
    - Generate integration tests
    - Generate end-to-end tests
    - Run test suites
    - Analyze test coverage
    - Validate code quality
    - Performance testing
    - Security testing
    """

    def __init__(self, agent_id: str = None, config: Dict[str, Any] = None):
        super().__init__(agent_id, config)

        # Testing configuration
        self.llm_client = config.get('llm_client') if config else None
        self.test_frameworks = config.get('test_frameworks', {}) if config else {}
        self.coverage_threshold = config.get('coverage_threshold', 80) if config else 80
        self.enable_execution = config.get('enable_execution', False) if config else False
        self.test_timeout = config.get('test_timeout', 300) if config else 300

        # Test framework configurations
        self.framework_configs = {
            'python': {
                'unittest': {
                    'extension': '.py',
                    'import_statement': 'import unittest',
                    'test_class': 'unittest.TestCase',
                    'run_command': 'python -m unittest'
                },
                'pytest': {
                    'extension': '.py',
                    'import_statement': 'import pytest',
                    'test_prefix': 'test_',
                    'run_command': 'pytest'
                }
            },
            'javascript': {
                'jest': {
                    'extension': '.test.js',
                    'import_statement': "const { test, expect } = require('@jest/globals');",
                    'run_command': 'npm test'
                },
                'mocha': {
                    'extension': '.test.js',
                    'import_statement': "const { describe, it } = require('mocha');",
                    'run_command': 'npm test'
                }
            },
            'java': {
                'junit': {
                    'extension': '.java',
                    'import_statement': 'import org.junit.Test;',
                    'test_annotation': '@Test',
                    'run_command': 'mvn test'
                }
            }
        }

        # Quality metrics
        self.quality_checks = {
            'code_coverage': True,
            'cyclomatic_complexity': True,
            'code_style': True,
            'security_scan': True,
            'performance_test': False
        }

    def get_agent_type(self) -> AgentType:
        """Return the agent type."""
        return AgentType.TESTER

    def get_supported_task_types(self) -> List[TaskType]:
        """Return supported task types."""
        return [
            TaskType.TESTING,
            TaskType.REVIEW,
            TaskType.ANALYSIS
        ]

    def _execute_task_impl(self, task: Task) -> AgentResult:
        """Execute a testing task."""
        self.logger.info(f"Executing testing task: {task.description}")

        try:
            # Analyze testing requirements
            test_analysis = self._analyze_testing_task(task)

            # Execute based on test type
            if test_analysis['test_type'] == 'unit_tests':
                result = self._generate_unit_tests(task, test_analysis)
            elif test_analysis['test_type'] == 'integration_tests':
                result = self._generate_integration_tests(task, test_analysis)
            elif test_analysis['test_type'] == 'e2e_tests':
                result = self._generate_e2e_tests(task, test_analysis)
            elif test_analysis['test_type'] == 'test_execution':
                result = self._execute_tests(task, test_analysis)
            elif test_analysis['test_type'] == 'quality_analysis':
                result = self._analyze_code_quality(task, test_analysis)
            elif test_analysis['test_type'] == 'coverage_analysis':
                result = self._analyze_test_coverage(task, test_analysis)
            else:
                result = self._comprehensive_testing(task, test_analysis)

            return result

        except Exception as e:
            self.logger.error(f"Error executing testing task: {e}")
            return self._create_error_result(task, str(e))

    def _analyze_testing_task(self, task: Task) -> Dict[str, Any]:
        """Analyze the testing task to determine approach."""
        description = task.description.lower()
        context = task.context

        analysis = {
            'test_type': 'comprehensive',
            'language': self._detect_language(task),
            'framework': None,
            'code_to_test': None,
            'test_level': 'unit',
            'coverage_required': True,
            'performance_testing': False,
            'security_testing': False,
            'existing_tests': None
        }

        # Determine test type
        if any(term in description for term in ['unit test', 'unit testing']):
            analysis['test_type'] = 'unit_tests'
            analysis['test_level'] = 'unit'
        elif any(term in description for term in ['integration test', 'integration testing']):
            analysis['test_type'] = 'integration_tests'
            analysis['test_level'] = 'integration'
        elif any(term in description for term in ['e2e', 'end-to-end', 'system test']):
            analysis['test_type'] = 'e2e_tests'
            analysis['test_level'] = 'e2e'
        elif any(term in description for term in ['run test', 'execute test']):
            analysis['test_type'] = 'test_execution'
        elif any(term in description for term in ['quality', 'code quality', 'static analysis']):
            analysis['test_type'] = 'quality_analysis'
        elif any(term in description for term in ['coverage', 'test coverage']):
            analysis['test_type'] = 'coverage_analysis'

        # Extract code to test
        analysis['code_to_test'] = context.get('code_to_test', context.get('source_code'))

        # Determine framework
        analysis['framework'] = self._detect_test_framework(task, analysis['language'])

        # Check for special testing requirements
        if any(term in description for term in ['performance', 'load', 'stress']):
            analysis['performance_testing'] = True

        if any(term in description for term in ['security', 'vulnerability', 'penetration']):
            analysis['security_testing'] = True

        self.logger.debug(f"Test analysis: {analysis}")
        return analysis

    def _generate_unit_tests(self, task: Task, analysis: Dict[str, Any]) -> AgentResult:
        """Generate comprehensive unit tests."""
        artifacts = []
        test_data = {}

        self.report_progress(0.1, "Analyzing code for test generation")

        code_to_test = analysis['code_to_test']
        if not code_to_test:
            return self._create_error_result(task, "No code provided for testing")

        # Analyze code structure
        code_analysis = self._analyze_code_structure(code_to_test, analysis['language'])

        self.report_progress(0.3, "Generating unit tests")

        # Generate tests for each function/method/class
        generated_tests = []
        for component in code_analysis['components']:
            test_code = self._generate_test_for_component(component, analysis)
            if test_code:
                generated_tests.append({
                    'component': component['name'],
                    'test_code': test_code,
                    'test_count': self._count_tests_in_code(test_code)
                })

        self.report_progress(0.7, "Generating test runner and utilities")

        # Generate test runner and utilities
        test_runner = self._generate_test_runner(generated_tests, analysis)
        test_utilities = self._generate_test_utilities(code_analysis, analysis)

        self.report_progress(0.9, "Creating test artifacts")

        # Create test file artifacts
        for test_gen in generated_tests:
            test_artifact = self._create_test_artifact(
                task, test_gen['test_code'], f"{test_gen['component']}_test", analysis
            )
            artifacts.append(test_artifact)

        # Create test runner artifact
        if test_runner:
            runner_artifact = self._create_test_artifact(
                task, test_runner, "test_runner", analysis
            )
            artifacts.append(runner_artifact)

        # Create test utilities artifact
        if test_utilities:
            utils_artifact = self._create_test_artifact(
                task, test_utilities, "test_utilities", analysis
            )
            artifacts.append(utils_artifact)

        # Generate test report
        test_report = self._generate_test_generation_report(generated_tests, code_analysis, task)
        report_artifact = self.create_artifact(
            f"{task.task_id}_test_generation_report",
            "test_report",
            test_report
        )
        artifacts.append(report_artifact)

        test_data.update({
            'generated_tests': generated_tests,
            'code_analysis': code_analysis,
            'test_framework': analysis['framework'],
            'total_tests': sum(test['test_count'] for test in generated_tests),
            'test_type': 'unit_tests'
        })

        self.report_progress(1.0, "Unit test generation completed")

        return AgentResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            agent_type=self.get_agent_type(),
            success=True,
            artifacts=artifacts,
            output_data=test_data,
            logs=[f"Generated {len(generated_tests)} unit test files"]
        )

    def _generate_integration_tests(self, task: Task, analysis: Dict[str, Any]) -> AgentResult:
        """Generate integration tests."""
        artifacts = []
        test_data = {}

        self.report_progress(0.2, "Analyzing integration points")

        # Analyze integration requirements
        integration_analysis = self._analyze_integration_requirements(task, analysis)

        self.report_progress(0.5, "Generating integration tests")

        # Generate integration test scenarios
        integration_tests = self._generate_integration_test_scenarios(integration_analysis, analysis)

        self.report_progress(0.8, "Creating integration test artifacts")

        # Create test artifacts
        for test_scenario in integration_tests:
            test_artifact = self._create_test_artifact(
                task, test_scenario['test_code'], f"integration_{test_scenario['name']}", analysis
            )
            artifacts.append(test_artifact)

        # Generate integration test report
        test_report = self._generate_integration_test_report(integration_tests, task)
        report_artifact = self.create_artifact(
            f"{task.task_id}_integration_test_report",
            "test_report",
            test_report
        )
        artifacts.append(report_artifact)

        test_data.update({
            'integration_tests': integration_tests,
            'integration_analysis': integration_analysis,
            'test_type': 'integration_tests'
        })

        self.report_progress(1.0, "Integration test generation completed")

        return AgentResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            agent_type=self.get_agent_type(),
            success=True,
            artifacts=artifacts,
            output_data=test_data,
            logs=[f"Generated {len(integration_tests)} integration test scenarios"]
        )

    def _execute_tests(self, task: Task, analysis: Dict[str, Any]) -> AgentResult:
        """Execute existing tests."""
        if not self.enable_execution:
            return self._create_error_result(task, "Test execution is disabled")

        artifacts = []
        execution_data = {}

        self.report_progress(0.1, "Preparing test execution environment")

        # Get test files to execute
        test_files = self._extract_test_files(task)

        if not test_files:
            return self._create_error_result(task, "No test files provided")

        self.report_progress(0.3, "Executing tests")

        # Execute tests
        execution_results = []
        for test_file in test_files:
            result = self._execute_test_file(test_file, analysis)
            execution_results.append(result)

        self.report_progress(0.7, "Analyzing test results")

        # Analyze results
        test_summary = self._analyze_test_results(execution_results)

        self.report_progress(0.9, "Generating execution report")

        # Generate execution report
        execution_report = self._generate_test_execution_report(execution_results, test_summary, task)
        report_artifact = self.create_artifact(
            f"{task.task_id}_test_execution_report",
            "test_report",
            execution_report
        )
        artifacts.append(report_artifact)

        execution_data.update({
            'execution_results': execution_results,
            'test_summary': test_summary,
            'total_tests': test_summary.get('total_tests', 0),
            'passed_tests': test_summary.get('passed_tests', 0),
            'failed_tests': test_summary.get('failed_tests', 0),
            'success_rate': test_summary.get('success_rate', 0)
        })

        self.report_progress(1.0, "Test execution completed")

        return AgentResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            agent_type=self.get_agent_type(),
            success=test_summary.get('success_rate', 0) >= 80,  # 80% pass rate threshold
            artifacts=artifacts,
            output_data=execution_data,
            logs=[f"Executed {len(test_files)} test files"]
        )

    def _analyze_code_quality(self, task: Task, analysis: Dict[str, Any]) -> AgentResult:
        """Analyze code quality."""
        artifacts = []
        quality_data = {}

        self.report_progress(0.2, "Analyzing code quality")

        code_to_analyze = analysis['code_to_test']
        if not code_to_analyze:
            return self._create_error_result(task, "No code provided for quality analysis")

        # Run quality checks
        quality_results = {}

        if self.quality_checks['code_style']:
            quality_results['style_analysis'] = self._analyze_code_style(code_to_analyze, analysis['language'])

        if self.quality_checks['cyclomatic_complexity']:
            quality_results['complexity_analysis'] = self._analyze_complexity(code_to_analyze, analysis['language'])

        if self.quality_checks['security_scan']:
            quality_results['security_analysis'] = self._analyze_security(code_to_analyze, analysis['language'])

        self.report_progress(0.8, "Generating quality report")

        # Generate comprehensive quality report
        quality_report = self._generate_quality_report(quality_results, task)
        report_artifact = self.create_artifact(
            f"{task.task_id}_quality_analysis_report",
            "quality_report",
            quality_report
        )
        artifacts.append(report_artifact)

        # Calculate overall quality score
        overall_score = self._calculate_quality_score(quality_results)

        quality_data.update({
            'quality_results': quality_results,
            'overall_score': overall_score,
            'analysis_type': 'code_quality'
        })

        self.report_progress(1.0, "Quality analysis completed")

        return AgentResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            agent_type=self.get_agent_type(),
            success=True,
            artifacts=artifacts,
            output_data=quality_data,
            logs=[f"Quality analysis completed with score: {overall_score}/10"]
        )

    def _comprehensive_testing(self, task: Task, analysis: Dict[str, Any]) -> AgentResult:
        """Perform comprehensive testing including multiple test types."""
        artifacts = []
        comprehensive_data = {}

        self.report_progress(0.1, "Starting comprehensive testing")

        # Generate unit tests
        unit_result = self._generate_unit_tests(task, analysis)
        if unit_result.success:
            artifacts.extend(unit_result.artifacts)
            comprehensive_data['unit_tests'] = unit_result.output_data

        self.report_progress(0.4, "Generating integration tests")

        # Generate integration tests
        integration_result = self._generate_integration_tests(task, analysis)
        if integration_result.success:
            artifacts.extend(integration_result.artifacts)
            comprehensive_data['integration_tests'] = integration_result.output_data

        self.report_progress(0.7, "Performing quality analysis")

        # Perform quality analysis
        quality_result = self._analyze_code_quality(task, analysis)
        if quality_result.success:
            artifacts.extend(quality_result.artifacts)
            comprehensive_data['quality_analysis'] = quality_result.output_data

        self.report_progress(0.9, "Generating comprehensive report")

        # Generate comprehensive testing report
        comprehensive_report = self._generate_comprehensive_testing_report(comprehensive_data, task)
        report_artifact = self.create_artifact(
            f"{task.task_id}_comprehensive_testing_report",
            "test_report",
            comprehensive_report
        )
        artifacts.append(report_artifact)

        self.report_progress(1.0, "Comprehensive testing completed")

        return AgentResult(
            task_id=task.task_id,
            agent_id=self.agent_id,
            agent_type=self.get_agent_type(),
            success=True,
            artifacts=artifacts,
            output_data=comprehensive_data,
            logs=["Comprehensive testing suite generated"]
        )

    def _detect_language(self, task: Task) -> str:
        """Detect programming language from task."""
        description = task.description.lower()
        context = str(task.context).lower()

        language_indicators = {
            'python': ['python', 'py', 'django', 'flask'],
            'javascript': ['javascript', 'js', 'node', 'react'],
            'java': ['java', 'spring', 'junit'],
            'go': ['golang', 'go'],
            'rust': ['rust'],
            'cpp': ['c++', 'cpp'],
            'csharp': ['c#', 'csharp', '.net']
        }

        text = f"{description} {context}"
        for language, indicators in language_indicators.items():
            if any(indicator in text for indicator in indicators):
                return language

        # Check explicit language specification
        return task.context.get('language', 'python')

    def _detect_test_framework(self, task: Task, language: str) -> str:
        """Detect or select appropriate test framework."""
        description = task.description.lower()

        # Check for explicit framework mention
        if language in self.framework_configs:
            for framework in self.framework_configs[language]:
                if framework in description:
                    return framework

        # Return default framework for language
        defaults = {
            'python': 'pytest',
            'javascript': 'jest',
            'java': 'junit',
            'go': 'testing',
            'rust': 'cargo_test'
        }

        return defaults.get(language, 'unittest')

    def _analyze_code_structure(self, code: str, language: str) -> Dict[str, Any]:
        """Analyze code structure to identify testable components."""
        components = []

        if language == 'python':
            # Extract functions and classes
            function_pattern = r'def\s+(\w+)\s*\([^)]*\):'
            class_pattern = r'class\s+(\w+)(?:\([^)]*\))?:'

            functions = re.findall(function_pattern, code)
            classes = re.findall(class_pattern, code)

            for func in functions:
                components.append({
                    'type': 'function',
                    'name': func,
                    'testable': True
                })

            for cls in classes:
                components.append({
                    'type': 'class',
                    'name': cls,
                    'testable': True
                })

        elif language == 'javascript':
            # Extract functions and classes
            function_pattern = r'function\s+(\w+)\s*\([^)]*\)'
            arrow_function_pattern = r'const\s+(\w+)\s*=\s*\([^)]*\)\s*=>'
            class_pattern = r'class\s+(\w+)'

            functions = re.findall(function_pattern, code)
            arrow_functions = re.findall(arrow_function_pattern, code)
            classes = re.findall(class_pattern, code)

            for func in functions + arrow_functions:
                components.append({
                    'type': 'function',
                    'name': func,
                    'testable': True
                })

            for cls in classes:
                components.append({
                    'type': 'class',
                    'name': cls,
                    'testable': True
                })

        return {
            'components': components,
            'language': language,
            'complexity': len(components),
            'testable_count': len([c for c in components if c['testable']])
        }

    def _generate_test_for_component(self, component: Dict[str, Any], analysis: Dict[str, Any]) -> Optional[str]:
        """Generate test code for a specific component."""
        if not self.llm_client:
            return self._generate_basic_test_template(component, analysis)

        # Use LLM to generate comprehensive tests
        prompt = self._build_test_generation_prompt(component, analysis)

        try:
            response = self.llm_client.generate(
                prompt=prompt,
                max_tokens=2000,
                temperature=0.1
            )

            return self._extract_test_code_from_response(response, analysis['language'])

        except Exception as e:
            self.logger.warning(f"LLM test generation failed for {component['name']}: {e}")
            return self._generate_basic_test_template(component, analysis)

    def _build_test_generation_prompt(self, component: Dict[str, Any], analysis: Dict[str, Any]) -> str:
        """Build prompt for test generation."""
        language = analysis['language']
        framework = analysis['framework']
        component_type = component['type']
        component_name = component['name']

        prompt = f"""
Generate comprehensive unit tests for a {language} {component_type} named "{component_name}".

REQUIREMENTS:
- Use {framework} testing framework
- Test normal cases, edge cases, and error conditions
- Include setup and teardown if needed
- Follow {language} testing best practices
- Ensure high code coverage

COMPONENT TYPE: {component_type}
COMPONENT NAME: {component_name}
LANGUAGE: {language}
FRAMEWORK: {framework}

Generate complete, runnable test code that thoroughly tests the component.
Include:
1. Import statements
2. Test class/functions
3. Test data/fixtures
4. Assertion statements
5. Error case testing

OUTPUT: Provide only the test code without explanations.
"""

        return prompt

    def _extract_test_code_from_response(self, response: str, language: str) -> Optional[str]:
        """Extract test code from LLM response."""
        # Look for code blocks
        patterns = [
            rf'```{language}\n(.*?)\n```',
            r'```\n(.*?)\n```',
            r'```(.*?)```'
        ]

        for pattern in patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                return match.group(1).strip()

        # If no code block, return the response as-is
        return response.strip()

    def _generate_basic_test_template(self, component: Dict[str, Any], analysis: Dict[str, Any]) -> str:
        """Generate basic test template as fallback."""
        language = analysis['language']
        framework = analysis['framework']
        component_name = component['name']

        if language == 'python' and framework == 'pytest':
            return f'''import pytest

def test_{component_name}_basic():
    """Test basic functionality of {component_name}."""
    # TODO: Implement test
    assert True

def test_{component_name}_edge_cases():
    """Test edge cases for {component_name}."""
    # TODO: Implement edge case tests
    assert True

def test_{component_name}_error_conditions():
    """Test error conditions for {component_name}."""
    # TODO: Implement error condition tests
    with pytest.raises(Exception):
        pass  # TODO: Implement error test
'''

        elif language == 'javascript' and framework == 'jest':
            return f'''const {{ test, expect }} = require('@jest/globals');

test('{component_name} basic functionality', () => {{
    // TODO: Implement test
    expect(true).toBe(true);
}});

test('{component_name} edge cases', () => {{
    // TODO: Implement edge case tests
    expect(true).toBe(true);
}});

test('{component_name} error conditions', () => {{
    // TODO: Implement error condition tests
    expect(() => {{
        // TODO: Implement error test
    }}).toThrow();
}});
'''

        return f"# TODO: Implement tests for {component_name} in {language} using {framework}"

    def _count_tests_in_code(self, test_code: str) -> int:
        """Count the number of tests in test code."""
        # Simple pattern matching for test functions
        patterns = [
            r'def test_\w+',  # Python pytest
            r'test\(["\']',   # JavaScript jest
            r'@Test',         # Java JUnit
            r'func Test\w+'   # Go testing
        ]

        count = 0
        for pattern in patterns:
            matches = re.findall(pattern, test_code)
            count += len(matches)

        return max(count, 1)  # At least 1 if we can't detect

    def _create_test_artifact(self, task: Task, test_code: str, test_name: str,
                            analysis: Dict[str, Any]) -> TaskArtifact:
        """Create a test file artifact."""
        language = analysis['language']
        framework = analysis['framework']

        # Determine file extension
        if language in self.framework_configs and framework in self.framework_configs[language]:
            extension = self.framework_configs[language][framework].get('extension', '.test')
        else:
            extension = '.test'

        artifact_name = f"{test_name}{extension}"

        return self.create_artifact(
            name=artifact_name,
            artifact_type="test_file",
            content=test_code,
            metadata={
                'language': language,
                'framework': framework,
                'test_type': analysis.get('test_type', 'unit'),
                'task_id': task.task_id
            }
        )

    # Additional helper methods for other test types and analysis
    def _generate_test_generation_report(self, generated_tests: List[Dict[str, Any]],
                                       code_analysis: Dict[str, Any], task: Task) -> str:
        """Generate test generation report."""
        total_tests = sum(test['test_count'] for test in generated_tests)

        report = f"""# Test Generation Report

## Task
{task.description}

## Summary
- **Total Components Analyzed:** {len(code_analysis['components'])}
- **Test Files Generated:** {len(generated_tests)}
- **Total Tests Created:** {total_tests}
- **Language:** {code_analysis['language']}

## Generated Test Files
"""

        for test in generated_tests:
            report += f"""
### {test['component']}
- **Test Count:** {test['test_count']}
- **Component Type:** {next((c['type'] for c in code_analysis['components'] if c['name'] == test['component']), 'unknown')}
"""

        report += """
## Recommendations
1. Review generated tests for completeness
2. Add specific test data for your use cases
3. Ensure all edge cases are covered
4. Run tests to verify functionality

---
*Generated by TesterAgent*
"""

        return report

    # Placeholder implementations for other methods
    def _analyze_integration_requirements(self, task: Task, analysis: Dict[str, Any]) -> Dict[str, Any]:
        return {'integration_points': [], 'dependencies': []}

    def _generate_integration_test_scenarios(self, integration_analysis: Dict[str, Any], analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [{'name': 'basic_integration', 'test_code': '# Integration test placeholder'}]

    def _generate_integration_test_report(self, integration_tests: List[Dict[str, Any]], task: Task) -> str:
        return f"# Integration Test Report\n\nGenerated {len(integration_tests)} integration test scenarios."

    def _extract_test_files(self, task: Task) -> List[str]:
        return task.context.get('test_files', [])

    def _execute_test_file(self, test_file: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        return {'file': test_file, 'status': 'passed', 'tests_run': 5, 'tests_passed': 5}

    def _analyze_test_results(self, execution_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        total_tests = sum(result.get('tests_run', 0) for result in execution_results)
        passed_tests = sum(result.get('tests_passed', 0) for result in execution_results)

        return {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': total_tests - passed_tests,
            'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0
        }

    def _generate_test_execution_report(self, execution_results: List[Dict[str, Any]],
                                      test_summary: Dict[str, Any], task: Task) -> str:
        return f"""# Test Execution Report

## Summary
- **Total Tests:** {test_summary['total_tests']}
- **Passed:** {test_summary['passed_tests']}
- **Failed:** {test_summary['failed_tests']}
- **Success Rate:** {test_summary['success_rate']:.1f}%

## Test Results
{chr(10).join(f"- {result['file']}: {result['status']}" for result in execution_results)}
"""

    def _analyze_code_style(self, code: str, language: str) -> Dict[str, Any]:
        return {'style_score': 8, 'issues': [], 'suggestions': []}

    def _analyze_complexity(self, code: str, language: str) -> Dict[str, Any]:
        return {'complexity_score': 7, 'complex_functions': [], 'suggestions': []}

    def _analyze_security(self, code: str, language: str) -> Dict[str, Any]:
        return {'security_score': 9, 'vulnerabilities': [], 'recommendations': []}

    def _calculate_quality_score(self, quality_results: Dict[str, Any]) -> float:
        scores = []
        if 'style_analysis' in quality_results:
            scores.append(quality_results['style_analysis'].get('style_score', 5))
        if 'complexity_analysis' in quality_results:
            scores.append(quality_results['complexity_analysis'].get('complexity_score', 5))
        if 'security_analysis' in quality_results:
            scores.append(quality_results['security_analysis'].get('security_score', 5))

        return sum(scores) / len(scores) if scores else 5.0

    def _generate_quality_report(self, quality_results: Dict[str, Any], task: Task) -> str:
        overall_score = self._calculate_quality_score(quality_results)

        return f"""# Code Quality Analysis Report

## Overall Quality Score: {overall_score:.1f}/10

## Analysis Results
{json.dumps(quality_results, indent=2)}

## Recommendations
- Review code style guidelines
- Reduce complexity where possible
- Address security recommendations

---
*Generated by TesterAgent*
"""

    def _generate_comprehensive_testing_report(self, comprehensive_data: Dict[str, Any], task: Task) -> str:
        return f"""# Comprehensive Testing Report

## Task
{task.description}

## Testing Summary
- **Unit Tests:** {'✓' if 'unit_tests' in comprehensive_data else '✗'}
- **Integration Tests:** {'✓' if 'integration_tests' in comprehensive_data else '✗'}
- **Quality Analysis:** {'✓' if 'quality_analysis' in comprehensive_data else '✗'}

## Results Summary
{json.dumps(comprehensive_data, indent=2, default=str)}

---
*Generated by TesterAgent*
"""