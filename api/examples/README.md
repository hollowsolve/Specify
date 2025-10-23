# Specify API Examples

This directory contains examples and documentation for using the Specify API.

## Files

- `curl_examples.sh` - Complete cURL examples for all API endpoints
- `python_client.py` - Python client library and usage examples
- `README.md` - This documentation file

## Quick Start

### 1. Start the API Server

```bash
# Install dependencies
pip install -r requirements.txt

# Start the development server
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000` with documentation at:
- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`

### 2. Run cURL Examples

```bash
# Make the script executable
chmod +x api/examples/curl_examples.sh

# Run all examples
./api/examples/curl_examples.sh
```

### 3. Run Python Client

```bash
# Install additional dependencies for the client
pip install httpx websockets

# Run the Python client example
python api/examples/python_client.py
```

## API Workflow

The Specify API follows a 4-phase workflow:

### Phase 1: Analysis
Analyze prompts to extract intent, requirements, assumptions, and ambiguities.

```bash
curl -X POST "http://localhost:8000/api/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Build a todo app with real-time collaboration",
    "session_id": "your-session-id"
  }'
```

### Phase 2: Specification
Refine analysis results into comprehensive specifications with edge cases and contradiction detection.

```bash
curl -X POST "http://localhost:8000/api/specify" \
  -H "Content-Type: application/json" \
  -d '{
    "analysis_result_id": "analysis-id-from-phase-1",
    "mode": "balanced",
    "session_id": "your-session-id"
  }'
```

### Phase 3: Refinement
Interactive refinement with human feedback and iterative improvement.

```bash
curl -X POST "http://localhost:8000/api/refinement/start" \
  -H "Content-Type: application/json" \
  -d '{
    "specification_id": "spec-id-from-phase-2",
    "session_id": "your-session-id"
  }'
```

### Phase 4: Dispatch
Multi-agent execution to implement the finalized specification.

```bash
curl -X POST "http://localhost:8000/api/dispatch/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "specification_id": "finalized-spec-id",
    "execution_mode": "adaptive",
    "session_id": "your-session-id"
  }'
```

## WebSocket Real-time Updates

Connect to WebSocket for live updates:

```bash
# Using wscat (install with: npm install -g wscat)
wscat -c "ws://localhost:8000/api/ws/your-session-id"
```

### Subscribe to Events

```json
{
  "type": "subscribe",
  "session_id": "your-session-id",
  "data": {
    "event_types": [
      "analysis_progress",
      "specification_update",
      "refinement_suggestion",
      "agent_started",
      "agent_progress",
      "agent_completed",
      "execution_complete"
    ]
  }
}
```

## Session Management

Sessions help track related operations across the workflow:

```bash
# Operations with the same session_id are grouped together
SESSION_ID="my-project-session-$(date +%s)"

# Use the session ID in all requests
curl -X POST "http://localhost:8000/api/analyze" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "...", "session_id": "'$SESSION_ID'"}'
```

## Error Handling

The API returns structured error responses:

```json
{
  "success": false,
  "error_type": "validation_error",
  "error_code": "VALIDATION_FAILED",
  "message": "Request validation failed",
  "details": {
    "validation_errors": [
      {
        "field": "prompt",
        "message": "field required",
        "type": "value_error.missing"
      }
    ]
  },
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

## Authentication (Future)

The API is currently designed to support authentication in the future:

```bash
# Future authentication header
curl -X POST "http://localhost:8000/api/analyze" \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "..."}'
```

## Rate Limiting

The API includes rate limiting (configurable):

- Default: 100 requests per minute per IP
- Rate limit headers are included in responses:
  - `X-RateLimit-Limit`
  - `X-RateLimit-Remaining`
  - `X-RateLimit-Reset`

## Configuration

Key configuration options via environment variables:

```bash
# Basic settings
export SPECIFY_DEBUG=true
export SPECIFY_HOST=0.0.0.0
export SPECIFY_PORT=8000

# CORS settings
export SPECIFY_CORS_ORIGINS="http://localhost:3000,https://yourdomain.com"

# Session settings
export SPECIFY_SESSION_TIMEOUT_MINUTES=30
export SPECIFY_MAX_SESSIONS_PER_USER=10

# Redis (optional)
export SPECIFY_REDIS_ENABLED=true
export SPECIFY_REDIS_URL="redis://localhost:6379"

# LLM settings
export SPECIFY_ANTHROPIC_API_KEY="your-anthropic-key"
export SPECIFY_OPENAI_API_KEY="your-openai-key"
```

## Production Deployment

For production deployment:

```bash
# Install production dependencies
pip install gunicorn

# Run with gunicorn
gunicorn api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Or use the provided configuration
gunicorn api.main:app --config gunicorn.conf.py
```

## Monitoring

The API includes built-in monitoring endpoints:

- Health: `/health`
- Version: `/version`
- Metrics: `/metrics` (Prometheus format)

## Support

For issues and questions:

1. Check the API documentation at `/api/docs`
2. Review the examples in this directory
3. Check the logs for detailed error information
4. Ensure all dependencies are properly installed

## Next Steps

1. Integrate with your frontend application
2. Set up proper authentication
3. Configure production deployment
4. Set up monitoring and logging
5. Customize the configuration for your use case