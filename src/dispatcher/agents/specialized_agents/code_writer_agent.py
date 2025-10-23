"""
Code Writer Agent - Specialized agent for writing code based on specifications.

This agent uses LLM capabilities to generate code, implement features,
and create software components based on task descriptions and requirements.
"""

import os
import re
import json
import tempfile
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from ..base_agent import BaseAgent
from ...models import AgentType, TaskType, Task, AgentResult, TaskArtifact


class CodeWriterAgent(BaseAgent):
    """
    Specialized agent for code writing tasks.

    Capabilities:
    - Generate code from specifications
    - Implement features and components
    - Create tests and documentation
    - Refactor and optimize code
    - Handle multiple programming languages
    """

    def __init__(self, agent_id: str = None, config: Dict[str, Any] = None):
        super().__init__(agent_id, config)

        # LLM configuration
        self.llm_client = config.get('llm_client') if config else None
        self.default_language = config.get('default_language', 'python') if config else 'python'
        self.code_style = config.get('code_style', 'pep8') if config else 'pep8'
        self.include_tests = config.get('include_tests', True) if config else True
        self.include_docs = config.get('include_docs', True) if config else True

        # Supported languages and their configurations
        self.language_configs = {
            'python': {
                'extension': '.py',
                'comment_style': '#',
                'test_framework': 'pytest',
                'style_guide': 'pep8'
            },
            'javascript': {
                'extension': '.js',
                'comment_style': '//',
                'test_framework': 'jest',
                'style_guide': 'standard'
            },
            'typescript': {
                'extension': '.ts',
                'comment_style': '//',
                'test_framework': 'jest',
                'style_guide': 'standard'
            },
            'java': {
                'extension': '.java',
                'comment_style': '//',
                'test_framework': 'junit',
                'style_guide': 'google'
            },
            'go': {
                'extension': '.go',
                'comment_style': '//',
                'test_framework': 'testing',
                'style_guide': 'gofmt'
            }
        }

    def get_agent_type(self) -> AgentType:
        """Return the agent type."""
        return AgentType.CODE_WRITER

    def get_supported_task_types(self) -> List[TaskType]:
        """Return supported task types."""
        return [
            TaskType.CODE_WRITING,
            TaskType.DEBUGGING,
            TaskType.ANALYSIS
        ]

    def _execute_task_impl(self, task: Task) -> AgentResult:
        """Execute a code writing task."""
        self.logger.info(f"Executing code writing task: {task.description}")

        try:
            # Analyze task to determine approach
            task_analysis = self._analyze_task(task)

            # Generate code based on task type and requirements
            if task.task_type == TaskType.CODE_WRITING:
                result = self._handle_code_writing_task(task, task_analysis)
            elif task.task_type == TaskType.DEBUGGING:
                result = self._handle_debugging_task(task, task_analysis)
            elif task.task_type == TaskType.ANALYSIS:
                result = self._handle_analysis_task(task, task_analysis)
            else:
                raise ValueError(f"Unsupported task type: {task.task_type}")

            return result

        except Exception as e:
            self.logger.error(f"Error executing code writing task: {e}")
            return self._create_error_result(task, str(e))

    def _analyze_task(self, task: Task) -> Dict[str, Any]:
        """Analyze the task to understand requirements and context."""
        analysis = {
            'language': self._detect_language(task),
            'complexity': task.estimated_complexity,
            'requires_tests': self._requires_tests(task),
            'requires_docs': self._requires_docs(task),
            'code_type': self._detect_code_type(task),
            'frameworks': self._detect_frameworks(task),
            'dependencies': task.input_requirements,
            'outputs': task.output_artifacts
        }

        self.logger.debug(f"Task analysis: {analysis}")
        return analysis

    def _handle_code_writing_task(self, task: Task, analysis: Dict[str, Any]) -> AgentResult:
        """Handle a code writing task."""
        artifacts = []
        output_data = {}

        # Generate main code
        self.report_progress(0.1, "Analyzing requirements")
        code_prompt = self._build_code_generation_prompt(task, analysis)

        self.report_progress(0.3, "Generating code")
        generated_code = self._generate_code_with_llm(code_prompt, analysis)

        if generated_code:
            # Create code artifact
            code_artifact = self._create_code_artifact(
                task, generated_code, analysis['language']
            )
            artifacts.append(code_artifact)
            output_data['main_code'] = generated_code

            # Generate tests if required
            if analysis['requires_tests'] and self.include_tests:
                self.report_progress(0.6, "Generating tests")
                test_code = self._generate_test_code(task, generated_code, analysis)
                if test_code:
                    test_artifact = self._create_test_artifact(
                        task, test_code, analysis['language']
                    )
                    artifacts.append(test_artifact)
                    output_data['test_code'] = test_code

            # Generate documentation if required
            if analysis['requires_docs'] and self.include_docs:
                self.report_progress(0.8, "Generating documentation")
                documentation = self._generate_documentation(task, generated_code, analysis)
                if documentation:
                    doc_artifact = self._create_documentation_artifact(task, documentation)
                    artifacts.append(doc_artifact)
                    output_data['documentation'] = documentation

            self.report_progress(1.0, "Code generation completed")

            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                agent_type=self.get_agent_type(),
                success=True,
                artifacts=artifacts,
                output_data=output_data,
                logs=[
                    f"Generated {analysis['code_type']} code in {analysis['language']}",
                    f"Created {len(artifacts)} artifacts"
                ]
            )

        else:
            return self._create_error_result(task, "Failed to generate code")

    def _handle_debugging_task(self, task: Task, analysis: Dict[str, Any]) -> AgentResult:
        """Handle a debugging task."""
        # Extract problematic code from context
        problem_code = task.context.get('problem_code', '')
        error_message = task.context.get('error_message', '')

        if not problem_code:
            return self._create_error_result(task, "No problem code provided")

        # Generate debugging prompt
        debug_prompt = self._build_debugging_prompt(task, problem_code, error_message, analysis)

        # Get solution from LLM
        self.report_progress(0.5, "Analyzing problem and generating solution")
        solution = self._generate_code_with_llm(debug_prompt, analysis)

        if solution:
            # Create fixed code artifact
            fixed_code_artifact = self._create_code_artifact(
                task, solution, analysis['language'], name_suffix="_fixed"
            )

            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                agent_type=self.get_agent_type(),
                success=True,
                artifacts=[fixed_code_artifact],
                output_data={'fixed_code': solution},
                logs=[f"Fixed {analysis['language']} code"]
            )
        else:
            return self._create_error_result(task, "Failed to generate debugging solution")

    def _handle_analysis_task(self, task: Task, analysis: Dict[str, Any]) -> AgentResult:
        """Handle a code analysis task."""
        code_to_analyze = task.context.get('code', '')

        if not code_to_analyze:
            return self._create_error_result(task, "No code provided for analysis")

        # Generate analysis prompt
        analysis_prompt = self._build_analysis_prompt(task, code_to_analyze, analysis)

        # Get analysis from LLM
        self.report_progress(0.5, "Analyzing code")
        analysis_result = self._generate_analysis_with_llm(analysis_prompt, analysis)

        if analysis_result:
            # Create analysis report artifact
            report_artifact = self.create_artifact(
                f"{task.task_id}_analysis_report",
                "analysis_report",
                analysis_result
            )

            return AgentResult(
                task_id=task.task_id,
                agent_id=self.agent_id,
                agent_type=self.get_agent_type(),
                success=True,
                artifacts=[report_artifact],
                output_data={'analysis_report': analysis_result},
                logs=["Generated code analysis report"]
            )
        else:
            return self._create_error_result(task, "Failed to generate code analysis")

    def _build_code_generation_prompt(self, task: Task, analysis: Dict[str, Any]) -> str:
        """Build a prompt for code generation."""
        language = analysis['language']
        code_type = analysis['code_type']
        frameworks = ', '.join(analysis['frameworks']) if analysis['frameworks'] else 'standard library'

        prompt = f"""
You are an expert {language} developer. Generate high-quality, production-ready code based on the following requirements.

TASK DESCRIPTION:
{task.description}

REQUIREMENTS:
- Programming Language: {language}
- Code Type: {code_type}
- Frameworks/Libraries: {frameworks}
- Style Guide: {self.language_configs.get(language, {}).get('style_guide', 'standard')}

CONTEXT:
{json.dumps(task.context, indent=2)}

INPUT REQUIREMENTS:
{chr(10).join(f"- {req}" for req in task.input_requirements)}

EXPECTED OUTPUTS:
{chr(10).join(f"- {output}" for output in task.output_artifacts)}

CODING GUIDELINES:
1. Write clean, readable, and maintainable code
2. Follow {language} best practices and conventions
3. Include appropriate error handling
4. Add meaningful comments and docstrings
5. Use descriptive variable and function names
6. Consider performance and security implications
7. Make code modular and reusable

OUTPUT FORMAT:
Please provide the complete, working code. Start your response with the code block and then explain your implementation approach.

```{language}
[Your code here]
```

IMPLEMENTATION NOTES:
[Explain your approach, key decisions, and any important considerations]
"""

        return prompt

    def _build_debugging_prompt(self, task: Task, problem_code: str,
                              error_message: str, analysis: Dict[str, Any]) -> str:
        """Build a prompt for debugging."""
        language = analysis['language']

        prompt = f"""
You are an expert {language} developer and debugger. Analyze the following problematic code and provide a fixed version.

PROBLEM DESCRIPTION:
{task.description}

PROBLEMATIC CODE:
```{language}
{problem_code}
```

ERROR MESSAGE:
{error_message}

CONTEXT:
{json.dumps(task.context, indent=2)}

DEBUGGING TASK:
1. Identify the root cause of the problem
2. Provide a corrected version of the code
3. Explain what was wrong and why your fix works
4. Suggest improvements or best practices to prevent similar issues

OUTPUT FORMAT:
```{language}
[Fixed code here]
```

EXPLANATION:
[Detailed explanation of the problem and solution]
"""

        return prompt

    def _build_analysis_prompt(self, task: Task, code: str, analysis: Dict[str, Any]) -> str:
        """Build a prompt for code analysis."""
        language = analysis['language']

        prompt = f"""
You are an expert {language} code reviewer and analyst. Analyze the following code and provide a comprehensive report.

ANALYSIS REQUEST:
{task.description}

CODE TO ANALYZE:
```{language}
{code}
```

CONTEXT:
{json.dumps(task.context, indent=2)}

ANALYSIS AREAS:
1. Code Quality & Style
2. Performance Considerations
3. Security Issues
4. Maintainability
5. Best Practices Compliance
6. Potential Bugs or Issues
7. Suggestions for Improvement

OUTPUT FORMAT (JSON):
{{
  "overall_score": 1-10,
  "code_quality": {{
    "score": 1-10,
    "issues": ["list of issues"],
    "suggestions": ["list of suggestions"]
  }},
  "performance": {{
    "score": 1-10,
    "issues": ["list of issues"],
    "suggestions": ["list of suggestions"]
  }},
  "security": {{
    "score": 1-10,
    "issues": ["list of issues"],
    "suggestions": ["list of suggestions"]
  }},
  "maintainability": {{
    "score": 1-10,
    "issues": ["list of issues"],
    "suggestions": ["list of suggestions"]
  }},
  "summary": "Overall summary of the analysis",
  "recommended_actions": ["prioritized list of recommended actions"]
}}
"""

        return prompt

    def _generate_code_with_llm(self, prompt: str, analysis: Dict[str, Any]) -> Optional[str]:
        """Generate code using LLM."""
        if not self.llm_client:
            # Fallback: return template code
            return self._generate_template_code(analysis)

        try:
            response = self.llm_client.generate(
                prompt=prompt,
                max_tokens=4000,
                temperature=0.1
            )

            # Extract code from response
            code = self._extract_code_from_response(response, analysis['language'])
            return code

        except Exception as e:
            self.logger.error(f"LLM code generation failed: {e}")
            return self._generate_template_code(analysis)

    def _generate_analysis_with_llm(self, prompt: str, analysis: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate code analysis using LLM."""
        if not self.llm_client:
            return self._generate_basic_analysis()

        try:
            response = self.llm_client.generate(
                prompt=prompt,
                max_tokens=3000,
                temperature=0.1
            )

            # Try to parse JSON response
            analysis_result = self._parse_analysis_response(response)
            return analysis_result

        except Exception as e:
            self.logger.error(f"LLM analysis generation failed: {e}")
            return self._generate_basic_analysis()

    def _extract_code_from_response(self, response: str, language: str) -> Optional[str]:
        """Extract code from LLM response."""
        # Look for code blocks
        patterns = [
            rf'```{language}\n(.*?)\n```',
            r'```\n(.*?)\n```',
            rf'```{language}(.*?)```',
            r'```(.*?)```'
        ]

        for pattern in patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                return match.group(1).strip()

        # If no code block found, try to extract based on common patterns
        lines = response.split('\n')
        code_lines = []
        in_code = False

        for line in lines:
            if any(keyword in line.lower() for keyword in ['def ', 'class ', 'function ', 'import ', 'from ']):
                in_code = True

            if in_code:
                code_lines.append(line)

        if code_lines:
            return '\n'.join(code_lines)

        return None

    def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
        """Parse analysis response from LLM."""
        try:
            # Try to find JSON in response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass

        # Fallback: create basic analysis from text
        return {
            "overall_score": 7,
            "summary": response[:500] + "..." if len(response) > 500 else response,
            "analysis_text": response
        }

    def _generate_template_code(self, analysis: Dict[str, Any]) -> str:
        """Generate template code as fallback."""
        language = analysis['language']
        code_type = analysis['code_type']

        templates = {
            'python': {
                'function': '''def main():
    """Main function implementation."""
    # TODO: Implement functionality
    pass

if __name__ == "__main__":
    main()''',
                'class': '''class MyClass:
    """A sample class implementation."""

    def __init__(self):
        """Initialize the class."""
        pass

    def method(self):
        """A sample method."""
        # TODO: Implement method
        pass''',
                'module': '''"""
Module description.
"""

# TODO: Add imports
# TODO: Implement module functionality'''
            }
        }

        return templates.get(language, {}).get(code_type, f"# TODO: Implement {code_type} in {language}")

    def _generate_basic_analysis(self) -> Dict[str, Any]:
        """Generate basic analysis as fallback."""
        return {
            "overall_score": 5,
            "code_quality": {"score": 5, "issues": [], "suggestions": []},
            "performance": {"score": 5, "issues": [], "suggestions": []},
            "security": {"score": 5, "issues": [], "suggestions": []},
            "maintainability": {"score": 5, "issues": [], "suggestions": []},
            "summary": "Basic analysis completed (LLM not available)",
            "recommended_actions": ["Review code manually", "Add tests", "Add documentation"]
        }

    def _generate_test_code(self, task: Task, main_code: str, analysis: Dict[str, Any]) -> Optional[str]:
        """Generate test code for the main code."""
        language = analysis['language']
        test_framework = self.language_configs.get(language, {}).get('test_framework', 'unittest')

        test_prompt = f"""
Generate comprehensive unit tests for the following {language} code using {test_framework}.

CODE TO TEST:
```{language}
{main_code}
```

REQUIREMENTS:
1. Test all public functions/methods
2. Include edge cases and error conditions
3. Use appropriate assertions
4. Follow {test_framework} best practices
5. Include setup and teardown if needed

OUTPUT:
Provide complete test code that can be run independently.
"""

        if self.llm_client:
            try:
                response = self.llm_client.generate(
                    prompt=test_prompt,
                    max_tokens=3000,
                    temperature=0.1
                )
                return self._extract_code_from_response(response, language)
            except Exception as e:
                self.logger.error(f"Test generation failed: {e}")

        # Fallback: basic test template
        return self._generate_test_template(language, test_framework)

    def _generate_test_template(self, language: str, test_framework: str) -> str:
        """Generate basic test template."""
        if language == 'python' and test_framework == 'pytest':
            return '''import pytest

def test_example():
    """Test example function."""
    # TODO: Implement test
    assert True

def test_edge_case():
    """Test edge case."""
    # TODO: Implement edge case test
    assert True'''

        return f"# TODO: Implement {test_framework} tests for {language}"

    def _generate_documentation(self, task: Task, code: str, analysis: Dict[str, Any]) -> Optional[str]:
        """Generate documentation for the code."""
        doc_prompt = f"""
Generate comprehensive documentation for the following code.

CODE:
```{analysis['language']}
{code}
```

REQUIREMENTS:
1. API documentation for public functions/classes
2. Usage examples
3. Installation/setup instructions if applicable
4. Clear explanations of functionality

OUTPUT FORMAT: Markdown
"""

        if self.llm_client:
            try:
                response = self.llm_client.generate(
                    prompt=doc_prompt,
                    max_tokens=2000,
                    temperature=0.2
                )
                return response
            except Exception as e:
                self.logger.error(f"Documentation generation failed: {e}")

        # Fallback: basic documentation
        return f"""# {task.task_id} Documentation

## Description
{task.description}

## Code
```{analysis['language']}
{code}
```

## Usage
TODO: Add usage examples

## Notes
Generated by CodeWriterAgent
"""

    def _create_code_artifact(self, task: Task, code: str, language: str,
                            name_suffix: str = "") -> TaskArtifact:
        """Create a code artifact."""
        extension = self.language_configs.get(language, {}).get('extension', '.txt')
        name = f"{task.task_id}_code{name_suffix}{extension}"

        return self.create_artifact(
            name=name,
            artifact_type="code",
            content=code,
            metadata={
                'language': language,
                'task_id': task.task_id,
                'agent_id': self.agent_id,
                'file_extension': extension
            }
        )

    def _create_test_artifact(self, task: Task, test_code: str, language: str) -> TaskArtifact:
        """Create a test artifact."""
        extension = self.language_configs.get(language, {}).get('extension', '.txt')
        name = f"{task.task_id}_test{extension}"

        return self.create_artifact(
            name=name,
            artifact_type="test",
            content=test_code,
            metadata={
                'language': language,
                'task_id': task.task_id,
                'agent_id': self.agent_id,
                'artifact_type': 'test_code'
            }
        )

    def _create_documentation_artifact(self, task: Task, documentation: str) -> TaskArtifact:
        """Create a documentation artifact."""
        name = f"{task.task_id}_documentation.md"

        return self.create_artifact(
            name=name,
            artifact_type="documentation",
            content=documentation,
            metadata={
                'task_id': task.task_id,
                'agent_id': self.agent_id,
                'format': 'markdown'
            }
        )

    def _detect_language(self, task: Task) -> str:
        """Detect programming language from task."""
        description = task.description.lower()
        context = str(task.context).lower()

        language_keywords = {
            'python': ['python', 'django', 'flask', 'pandas', 'numpy', '.py'],
            'javascript': ['javascript', 'js', 'node', 'react', 'vue', 'angular', '.js'],
            'typescript': ['typescript', 'ts', '.ts'],
            'java': ['java', 'spring', 'maven', 'gradle', '.java'],
            'go': ['golang', 'go', '.go'],
            'rust': ['rust', '.rs'],
            'cpp': ['c++', 'cpp', '.cpp'],
            'csharp': ['c#', 'csharp', 'dotnet', '.cs']
        }

        text = f"{description} {context}"
        for language, keywords in language_keywords.items():
            if any(keyword in text for keyword in keywords):
                return language

        # Check explicit language specification
        if 'language' in task.context:
            return task.context['language']

        return self.default_language

    def _detect_code_type(self, task: Task) -> str:
        """Detect what type of code needs to be generated."""
        description = task.description.lower()

        if any(keyword in description for keyword in ['class', 'object', 'inheritance']):
            return 'class'
        elif any(keyword in description for keyword in ['function', 'method', 'procedure']):
            return 'function'
        elif any(keyword in description for keyword in ['module', 'package', 'library']):
            return 'module'
        elif any(keyword in description for keyword in ['script', 'tool', 'utility']):
            return 'script'
        elif any(keyword in description for keyword in ['api', 'service', 'endpoint']):
            return 'api'
        elif any(keyword in description for keyword in ['test', 'unittest', 'testing']):
            return 'test'
        else:
            return 'general'

    def _detect_frameworks(self, task: Task) -> List[str]:
        """Detect frameworks mentioned in the task."""
        text = f"{task.description} {str(task.context)}".lower()

        frameworks = {
            'react', 'vue', 'angular', 'express', 'django', 'flask', 'fastapi',
            'spring', 'hibernate', 'junit', 'pytest', 'jest', 'mocha'
        }

        detected = [fw for fw in frameworks if fw in text]
        return detected

    def _requires_tests(self, task: Task) -> bool:
        """Check if task requires test generation."""
        description = task.description.lower()
        return ('test' in description or
                'testing' in description or
                'unit test' in description or
                self.include_tests)

    def _requires_docs(self, task: Task) -> bool:
        """Check if task requires documentation."""
        description = task.description.lower()
        return ('document' in description or
                'documentation' in description or
                'doc' in description or
                self.include_docs)