#!/bin/bash

# cURL Examples for Specify API
# This script demonstrates how to use the Specify API endpoints

API_BASE_URL="http://localhost:8000/api"
SESSION_ID="example-session-123"

echo "=== Specify API cURL Examples ==="
echo "Base URL: $API_BASE_URL"
echo "Session ID: $SESSION_ID"
echo ""

# Health check
echo "1. Health Check"
curl -X GET "$API_BASE_URL/../health" \
  -H "Content-Type: application/json" | jq '.'
echo ""

# Version info
echo "2. Version Information"
curl -X GET "$API_BASE_URL/../version" \
  -H "Content-Type: application/json" | jq '.'
echo ""

# Phase 1: Analyze a prompt
echo "3. Phase 1 - Analyze Prompt"
ANALYSIS_RESPONSE=$(curl -s -X POST "$API_BASE_URL/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Build a web application that allows users to create and manage todo lists with real-time collaboration features",
    "session_id": "'$SESSION_ID'",
    "user_context": "This is for a team productivity tool",
    "analysis_options": {
      "detailed_analysis": true,
      "include_edge_cases": true
    }
  }')

echo "$ANALYSIS_RESPONSE" | jq '.'
ANALYSIS_ID=$(echo "$ANALYSIS_RESPONSE" | jq -r '.analysis_id')
echo "Analysis ID: $ANALYSIS_ID"
echo ""

# Get analysis result
echo "4. Get Analysis Result"
curl -X GET "$API_BASE_URL/analyze/$ANALYSIS_ID" \
  -H "Content-Type: application/json" | jq '.'
echo ""

# Phase 2: Create specification
echo "5. Phase 2 - Create Specification"
SPEC_RESPONSE=$(curl -s -X POST "$API_BASE_URL/specify" \
  -H "Content-Type: application/json" \
  -d '{
    "analysis_result_id": "'$ANALYSIS_ID'",
    "mode": "balanced",
    "session_id": "'$SESSION_ID'",
    "custom_rules": ["security_focused", "performance_optimized"],
    "focus_areas": ["authentication", "real_time_sync", "data_persistence"]
  }')

echo "$SPEC_RESPONSE" | jq '.'
SPEC_ID=$(echo "$SPEC_RESPONSE" | jq -r '.specification_id')
echo "Specification ID: $SPEC_ID"
echo ""

# Get specification
echo "6. Get Specification"
curl -X GET "$API_BASE_URL/specify/$SPEC_ID" \
  -H "Content-Type: application/json" | jq '.'
echo ""

# Get edge cases
echo "7. Get Edge Cases"
curl -X GET "$API_BASE_URL/specify/$SPEC_ID/edge-cases" \
  -H "Content-Type: application/json" | jq '.'
echo ""

# Phase 3: Start refinement
echo "8. Phase 3 - Start Refinement"
REFINEMENT_RESPONSE=$(curl -s -X POST "$API_BASE_URL/refinement/start" \
  -H "Content-Type: application/json" \
  -d '{
    "specification_id": "'$SPEC_ID'",
    "session_id": "'$SESSION_ID'",
    "interaction_mode": "interactive",
    "auto_approve_threshold": 0.8
  }')

echo "$REFINEMENT_RESPONSE" | jq '.'
REFINEMENT_ID=$(echo "$REFINEMENT_RESPONSE" | jq -r '.session_id // .refinement_session_id')
echo "Refinement Session ID: $REFINEMENT_ID"
echo ""

# Get refinement session
echo "9. Get Refinement Session"
curl -X GET "$API_BASE_URL/refinement/$REFINEMENT_ID" \
  -H "Content-Type: application/json" | jq '.'
echo ""

# Approve a suggestion (example)
echo "10. Approve Suggestion (Example)"
curl -X POST "$API_BASE_URL/refinement/$REFINEMENT_ID/approve" \
  -H "Content-Type: application/json" \
  -d '{
    "suggestion_id": "suggestion-123",
    "session_id": "'$SESSION_ID'",
    "feedback": "This suggestion looks good and addresses the security concerns",
    "reason": "Improves overall system security"
  }' | jq '.'
echo ""

# Finalize refinement
echo "11. Finalize Refinement"
FINALIZED_RESPONSE=$(curl -s -X POST "$API_BASE_URL/refinement/$REFINEMENT_ID/finalize" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "'$SESSION_ID'",
    "include_rejected": false,
    "final_notes": "Specification has been thoroughly reviewed and approved"
  }')

echo "$FINALIZED_RESPONSE" | jq '.'
echo ""

# Phase 4: Start execution
echo "12. Phase 4 - Start Execution"
EXECUTION_RESPONSE=$(curl -s -X POST "$API_BASE_URL/dispatch/execute" \
  -H "Content-Type: application/json" \
  -d '{
    "specification_id": "'$SPEC_ID'",
    "execution_mode": "adaptive",
    "session_id": "'$SESSION_ID'",
    "target_platform": "web",
    "output_format": "files",
    "agent_constraints": {
      "max_agents": 4,
      "timeout_minutes": 30
    }
  }')

echo "$EXECUTION_RESPONSE" | jq '.'
EXECUTION_ID=$(echo "$EXECUTION_RESPONSE" | jq -r '.execution_id')
echo "Execution ID: $EXECUTION_ID"
echo ""

# Get execution status
echo "13. Get Execution Status"
curl -X GET "$API_BASE_URL/dispatch/$EXECUTION_ID/status" \
  -H "Content-Type: application/json" | jq '.'
echo ""

# Get execution graph
echo "14. Get Execution Graph"
curl -X GET "$API_BASE_URL/dispatch/$EXECUTION_ID/graph" \
  -H "Content-Type: application/json" | jq '.'
echo ""

# Get execution progress
echo "15. Get Execution Progress"
curl -X GET "$API_BASE_URL/dispatch/$EXECUTION_ID/progress" \
  -H "Content-Type: application/json" | jq '.'
echo ""

# List session analyses
echo "16. List Session Analyses"
curl -X GET "$API_BASE_URL/analyze/session/$SESSION_ID/analyses" \
  -H "Content-Type: application/json" | jq '.'
echo ""

# List session specifications
echo "17. List Session Specifications"
curl -X GET "$API_BASE_URL/specify/session/$SESSION_ID/specifications" \
  -H "Content-Type: application/json" | jq '.'
echo ""

# List session executions
echo "18. List Session Executions"
curl -X GET "$API_BASE_URL/dispatch/session/$SESSION_ID/executions" \
  -H "Content-Type: application/json" | jq '.'
echo ""

echo "=== Examples Complete ==="
echo ""
echo "Note: Some requests may fail if the previous operations didn't complete successfully."
echo "In a real scenario, you would check the status of each operation before proceeding."
echo ""
echo "To test WebSocket connections, use a WebSocket client like wscat:"
echo "  npm install -g wscat"
echo "  wscat -c \"ws://localhost:8000/api/ws/$SESSION_ID\""