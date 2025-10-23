# Prompt Analyzer

A Python-based prompt analyzer with multi-pass LLM parsing using Anthropic Claude API.

## Project Structure

```
/
├── src/analyzer/          # Main analyzer package
│   ├── __init__.py       # Package initialization
│   ├── models.py         # Data models for analysis results
│   └── parser.py         # Main PromptAnalyzer class
├── requirements.txt      # Project dependencies
├── .env.example         # Environment variables template
├── example.py           # Usage example
└── README.md            # This file
```

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure API key:
```bash
cp .env.example .env
# Edit .env and add your Anthropic API key
```

## Usage

```python
from src.analyzer import PromptAnalyzer

# Initialize analyzer
analyzer = PromptAnalyzer()

# Analyze a prompt
result = analyzer.analyze("Your prompt here...")

# Access results
print(f"Intent: {result.intent}")
print(f"Requirements: {result.explicit_requirements}")
print(f"Assumptions: {result.implicit_assumptions}")
print(f"Ambiguities: {result.ambiguities}")
```

## Analysis Passes

1. **Pass 1**: Extract primary intent
2. **Pass 2**: Extract explicit requirements
3. **Pass 3**: Extract implicit assumptions
4. **Pass 4**: Identify ambiguities/unclear points

## Example

Run the example script:
```bash
python example.py
```