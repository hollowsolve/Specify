# Specify FastAPI Backend

A production-ready FastAPI backend that exposes the entire Specify system (Phases 1-4) via REST and WebSocket APIs.

## Overview

This FastAPI backend provides a comprehensive web API for the Specify system, enabling web applications to access all four phases of the prompt specification and execution pipeline:

1. **Phase 1 (Analysis)**: Prompt analysis and intent extraction
2. **Phase 2 (Specification)**: Requirement refinement and edge case detection
3. **Phase 3 (Refinement)**: Interactive human-in-the-loop refinement
4. **Phase 4 (Dispatch)**: Multi-agent execution and code generation

## Architecture

```
api/
├── main.py                 # FastAPI application entry point
├── config.py              # Configuration management
├── routers/               # API route handlers
│   ├── analyzer.py        # Phase 1 endpoints
│   ├── specification.py   # Phase 2 endpoints
│   ├── refinement.py      # Phase 3 endpoints
│   ├── dispatch.py        # Phase 4 endpoints
│   └── websocket.py       # Real-time WebSocket endpoints
├── schemas/               # Pydantic request/response models
│   ├── request_schemas.py # Input validation models
│   └── response_schemas.py# Output data models
├── services/              # Business logic layer
│   ├── analyzer_service.py    # Phase 1 service wrapper
│   ├── specification_service.py # Phase 2 service wrapper
│   ├── refinement_service.py   # Phase 3 service wrapper
│   ├── dispatch_service.py     # Phase 4 service wrapper
│   └── session_manager.py      # Session management
├── middleware/            # Cross-cutting concerns
│   ├── logging_middleware.py   # Request/response logging
│   └── error_handler.py       # Global exception handling
└── examples/              # Usage examples and documentation
    ├── curl_examples.sh   # cURL command examples
    ├── python_client.py   # Python client library
    └── README.md          # Usage documentation
```

## Key Features

### RESTful API Design
- Clean, predictable endpoints following REST conventions
- Comprehensive request/response validation with Pydantic
- Auto-generated OpenAPI/Swagger documentation
- Structured error responses with proper HTTP status codes

### Real-time Communication
- WebSocket support for live updates during all phases
- Event-driven architecture for progress notifications
- Bidirectional communication for interactive refinement
- Subscription-based event filtering

### Production-Ready
- CORS configuration for Next.js frontend integration
- Comprehensive error handling and logging
- Session management with Redis support
- Request/response middleware for monitoring
- Rate limiting and security headers

### Type Safety
- Full Pydantic validation for all inputs/outputs
- Type hints throughout the codebase
- Schema-driven API development
- Automatic API documentation generation

## API Endpoints

### Core Endpoints
- `GET /health` - Health check
- `GET /version` - Version information
- `GET /api/docs` - Interactive API documentation

### Phase 1: Analysis
- `POST /api/analyze` - Analyze prompt
- `GET /api/analyze/{analysis_id}` - Get analysis result
- `GET /api/analyze/{analysis_id}/status` - Get analysis status
- `POST /api/analyze/{analysis_id}/cancel` - Cancel analysis

### Phase 2: Specification
- `POST /api/specify` - Create specification
- `GET /api/specify/{spec_id}` - Get specification
- `GET /api/specify/{spec_id}/edge-cases` - Get edge cases
- `GET /api/specify/{spec_id}/contradictions` - Get contradictions

### Phase 3: Refinement
- `POST /api/refinement/start` - Start refinement session
- `GET /api/refinement/{session_id}` - Get session state
- `POST /api/refinement/{session_id}/approve` - Approve suggestion
- `POST /api/refinement/{session_id}/reject` - Reject suggestion
- `POST /api/refinement/{session_id}/modify` - Modify suggestion
- `POST /api/refinement/{session_id}/finalize` - Finalize specification

### Phase 4: Dispatch
- `POST /api/dispatch/execute` - Start execution
- `GET /api/dispatch/{execution_id}/status` - Get execution status
- `GET /api/dispatch/{execution_id}/graph` - Get execution DAG
- `GET /api/dispatch/{execution_id}/results` - Get results
- `POST /api/dispatch/{execution_id}/cancel` - Cancel execution

### WebSocket
- `WS /api/ws/{session_id}` - Real-time updates connection

## Integration with Existing System

The API seamlessly integrates with the existing Specify codebase:

```python
# Service layer wraps existing Phase 1-4 systems
from src.analyzer import PromptAnalyzer, AnalysisResult
from src.engine import SpecificationEngine, RefinedSpecification
from src.refinement import RefinementLoop, RefinementSession
from src.dispatcher import AgentDispatcher, ExecutionResult
```

### Service Layer Pattern
Each phase is wrapped in a service class that:
- Provides async interfaces for FastAPI
- Handles session management and tracking
- Converts between core and API data formats
- Adds proper error handling and logging

### Session Management
- In-memory session storage (with Redis option)
- Multi-user support with session isolation
- Automatic cleanup of expired sessions
- Operation tracking within sessions

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start Development Server
```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Access Documentation
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

### 4. Test with Examples
```bash
# Run cURL examples
./api/examples/curl_examples.sh

# Run Python client
python api/examples/python_client.py
```

## Configuration

Configure via environment variables:

```bash
# Basic settings
export SPECIFY_DEBUG=true
export SPECIFY_HOST=0.0.0.0
export SPECIFY_PORT=8000

# CORS settings for frontend
export SPECIFY_CORS_ORIGINS="http://localhost:3000,https://yourdomain.com"

# Session management
export SPECIFY_SESSION_TIMEOUT_MINUTES=30
export SPECIFY_REDIS_URL="redis://localhost:6379"  # Optional

# LLM configuration
export SPECIFY_ANTHROPIC_API_KEY="your-key"
export SPECIFY_OPENAI_API_KEY="your-key"
```

## Error Handling

Comprehensive error handling with structured responses:

```json
{
  "success": false,
  "error_type": "validation_error",
  "error_code": "VALIDATION_FAILED",
  "message": "Request validation failed",
  "details": {
    "validation_errors": [...],
    "request_id": "abc123",
    "timestamp": "2024-01-01T00:00:00Z"
  }
}
```

## WebSocket Events

Real-time events for all phases:

- `analysis_progress` - Analysis progress updates
- `specification_update` - Specification changes
- `refinement_suggestion` - New suggestions available
- `agent_started` - Agent execution started
- `agent_progress` - Agent progress updates
- `agent_completed` - Agent finished
- `execution_complete` - Full execution finished
- `error` - Error notifications

## Production Deployment

### Using Gunicorn
```bash
gunicorn api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Docker Deployment
```dockerfile
FROM python:3.11-slim
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "api.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
```

### Environment Configuration
- Development: Auto-reload, debug logging, permissive CORS
- Production: Performance optimization, restricted CORS, security headers

## Monitoring

Built-in monitoring capabilities:
- Request/response logging with timing
- Structured logging for analytics
- Performance metrics collection
- Health check endpoints
- Error tracking and reporting

## Security Features

- CORS configuration for cross-origin requests
- Request validation and sanitization
- Rate limiting (configurable)
- Security headers middleware
- Input validation for all endpoints
- Proper HTTP status codes

## Next Steps

1. **Frontend Integration**: Connect with Next.js frontend
2. **Authentication**: Add user authentication and authorization
3. **Database**: Add persistent storage for sessions and results
4. **Caching**: Implement Redis caching for performance
5. **Monitoring**: Set up production monitoring and alerting
6. **Testing**: Add comprehensive test suite
7. **CI/CD**: Set up automated deployment pipeline

## API Design Summary

The Specify FastAPI backend provides:

✅ **Complete REST API** covering all four phases
✅ **Real-time WebSocket** communication for live updates
✅ **Production-ready** architecture with proper error handling
✅ **Type-safe** with full Pydantic validation
✅ **Well-documented** with auto-generated OpenAPI specs
✅ **Session management** for multi-user support
✅ **Middleware** for logging, CORS, and error handling
✅ **Examples** with cURL and Python client
✅ **Configuration** via environment variables
✅ **Integration** with existing Phase 1-4 systems

The API is ready for frontend integration and provides a solid foundation for building web applications on top of the Specify system.