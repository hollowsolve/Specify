#!/usr/bin/env python3
"""
Python client example for the Specify API.

This script demonstrates how to use the Specify API from Python
using the httpx library for HTTP requests and websockets for real-time communication.
"""

import asyncio
import json
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

import httpx
import websockets


class SpecifyAPIClient:
    """Async Python client for the Specify API."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.api_base = f"{self.base_url}/api"
        self.session_id = str(uuid.uuid4())
        self.client = httpx.AsyncClient(timeout=30.0)
        self.websocket = None

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def close(self):
        """Close the HTTP client and WebSocket connection."""
        if self.websocket:
            await self.websocket.close()
        await self.client.aclose()

    # Health and version endpoints
    async def health_check(self) -> Dict[str, Any]:
        """Check API health."""
        response = await self.client.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()

    async def get_version(self) -> Dict[str, Any]:
        """Get API version information."""
        response = await self.client.get(f"{self.base_url}/version")
        response.raise_for_status()
        return response.json()

    # Phase 1: Analysis
    async def analyze_prompt(
        self,
        prompt: str,
        user_context: Optional[str] = None,
        analysis_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze a prompt using Phase 1."""
        data = {
            "prompt": prompt,
            "session_id": self.session_id
        }
        if user_context:
            data["user_context"] = user_context
        if analysis_options:
            data["analysis_options"] = analysis_options

        response = await self.client.post(f"{self.api_base}/analyze", json=data)
        response.raise_for_status()
        return response.json()

    async def get_analysis_result(self, analysis_id: str) -> Dict[str, Any]:
        """Get analysis result by ID."""
        response = await self.client.get(f"{self.api_base}/analyze/{analysis_id}")
        response.raise_for_status()
        return response.json()

    async def get_analysis_status(self, analysis_id: str) -> Dict[str, Any]:
        """Get analysis status."""
        response = await self.client.get(f"{self.api_base}/analyze/{analysis_id}/status")
        response.raise_for_status()
        return response.json()

    # Phase 2: Specification
    async def create_specification(
        self,
        analysis_result_id: str,
        mode: str = "balanced",
        custom_rules: Optional[list] = None,
        focus_areas: Optional[list] = None
    ) -> Dict[str, Any]:
        """Create a specification using Phase 2."""
        data = {
            "analysis_result_id": analysis_result_id,
            "mode": mode,
            "session_id": self.session_id
        }
        if custom_rules:
            data["custom_rules"] = custom_rules
        if focus_areas:
            data["focus_areas"] = focus_areas

        response = await self.client.post(f"{self.api_base}/specify", json=data)
        response.raise_for_status()
        return response.json()

    async def get_specification(self, specification_id: str) -> Dict[str, Any]:
        """Get specification by ID."""
        response = await self.client.get(f"{self.api_base}/specify/{specification_id}")
        response.raise_for_status()
        return response.json()

    async def get_edge_cases(self, specification_id: str) -> list:
        """Get edge cases for a specification."""
        response = await self.client.get(f"{self.api_base}/specify/{specification_id}/edge-cases")
        response.raise_for_status()
        return response.json()

    async def get_contradictions(self, specification_id: str) -> list:
        """Get contradictions for a specification."""
        response = await self.client.get(f"{self.api_base}/specify/{specification_id}/contradictions")
        response.raise_for_status()
        return response.json()

    # Phase 3: Refinement
    async def start_refinement(
        self,
        specification_id: str,
        interaction_mode: str = "interactive",
        auto_approve_threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """Start a refinement session using Phase 3."""
        data = {
            "specification_id": specification_id,
            "session_id": self.session_id,
            "interaction_mode": interaction_mode
        }
        if auto_approve_threshold is not None:
            data["auto_approve_threshold"] = auto_approve_threshold

        response = await self.client.post(f"{self.api_base}/refinement/start", json=data)
        response.raise_for_status()
        return response.json()

    async def get_refinement_session(self, refinement_session_id: str) -> Dict[str, Any]:
        """Get refinement session by ID."""
        response = await self.client.get(f"{self.api_base}/refinement/{refinement_session_id}")
        response.raise_for_status()
        return response.json()

    async def approve_suggestion(
        self,
        refinement_session_id: str,
        suggestion_id: str,
        feedback: Optional[str] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Approve a refinement suggestion."""
        data = {
            "suggestion_id": suggestion_id,
            "session_id": self.session_id
        }
        if feedback:
            data["feedback"] = feedback
        if reason:
            data["reason"] = reason

        response = await self.client.post(
            f"{self.api_base}/refinement/{refinement_session_id}/approve",
            json=data
        )
        response.raise_for_status()
        return response.json()

    async def reject_suggestion(
        self,
        refinement_session_id: str,
        suggestion_id: str,
        feedback: Optional[str] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Reject a refinement suggestion."""
        data = {
            "suggestion_id": suggestion_id,
            "session_id": self.session_id
        }
        if feedback:
            data["feedback"] = feedback
        if reason:
            data["reason"] = reason

        response = await self.client.post(
            f"{self.api_base}/refinement/{refinement_session_id}/reject",
            json=data
        )
        response.raise_for_status()
        return response.json()

    async def finalize_refinement(
        self,
        refinement_session_id: str,
        include_rejected: bool = False,
        final_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Finalize a refinement session."""
        data = {
            "session_id": self.session_id,
            "include_rejected": include_rejected
        }
        if final_notes:
            data["final_notes"] = final_notes

        response = await self.client.post(
            f"{self.api_base}/refinement/{refinement_session_id}/finalize",
            json=data
        )
        response.raise_for_status()
        return response.json()

    # Phase 4: Dispatch
    async def start_execution(
        self,
        specification_id: str,
        execution_mode: str = "adaptive",
        target_platform: Optional[str] = None,
        output_format: str = "files",
        agent_constraints: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Start agent execution using Phase 4."""
        data = {
            "specification_id": specification_id,
            "execution_mode": execution_mode,
            "output_format": output_format,
            "session_id": self.session_id
        }
        if target_platform:
            data["target_platform"] = target_platform
        if agent_constraints:
            data["agent_constraints"] = agent_constraints

        response = await self.client.post(f"{self.api_base}/dispatch/execute", json=data)
        response.raise_for_status()
        return response.json()

    async def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """Get execution status."""
        response = await self.client.get(f"{self.api_base}/dispatch/{execution_id}/status")
        response.raise_for_status()
        return response.json()

    async def get_execution_results(self, execution_id: str) -> Dict[str, Any]:
        """Get execution results."""
        response = await self.client.get(f"{self.api_base}/dispatch/{execution_id}/results")
        response.raise_for_status()
        return response.json()

    async def cancel_execution(self, execution_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """Cancel an execution."""
        data = {"session_id": self.session_id}
        if reason:
            data["reason"] = reason

        response = await self.client.post(
            f"{self.api_base}/dispatch/{execution_id}/cancel",
            json=data
        )
        response.raise_for_status()
        return response.json()

    # WebSocket functionality
    async def connect_websocket(self):
        """Connect to WebSocket for real-time updates."""
        ws_url = f"ws://localhost:8000/api/ws/{self.session_id}"
        self.websocket = await websockets.connect(ws_url)

        # Subscribe to all event types
        subscribe_message = {
            "type": "subscribe",
            "session_id": self.session_id,
            "data": {
                "event_types": [
                    "analysis_progress",
                    "specification_update",
                    "refinement_suggestion",
                    "agent_started",
                    "agent_progress",
                    "agent_completed",
                    "execution_complete",
                    "error"
                ]
            }
        }
        await self.websocket.send(json.dumps(subscribe_message))

    async def listen_for_events(self):
        """Listen for WebSocket events."""
        if not self.websocket:
            await self.connect_websocket()

        async for message in self.websocket:
            try:
                event = json.loads(message)
                print(f"[{datetime.now()}] WebSocket Event: {event['type']}")
                print(f"  Data: {event.get('data', {})}")
            except json.JSONDecodeError:
                print(f"Received non-JSON message: {message}")

    # High-level workflow methods
    async def complete_workflow(self, prompt: str, user_context: Optional[str] = None) -> Dict[str, Any]:
        """Complete the entire Specify workflow."""
        print(f"Starting complete workflow for session: {self.session_id}")

        # Phase 1: Analysis
        print("Phase 1: Analyzing prompt...")
        analysis_response = await self.analyze_prompt(prompt, user_context)
        analysis_id = analysis_response["analysis_id"]
        print(f"Analysis ID: {analysis_id}")

        # Wait for analysis to complete
        analysis_result = await self.get_analysis_result(analysis_id)
        print(f"Analysis completed: {analysis_result['intent']}")

        # Phase 2: Specification
        print("Phase 2: Creating specification...")
        spec_response = await self.create_specification(analysis_id)
        spec_id = spec_response["specification_id"]
        print(f"Specification ID: {spec_id}")

        specification = await self.get_specification(spec_id)
        print(f"Specification created with {len(specification['edge_cases'])} edge cases")

        # Phase 3: Refinement (simplified - auto-approve all)
        print("Phase 3: Starting refinement...")
        refinement_response = await self.start_refinement(spec_id, auto_approve_threshold=0.5)
        refinement_id = refinement_response["session_id"]
        print(f"Refinement Session ID: {refinement_id}")

        # Finalize immediately for demo
        finalize_response = await self.finalize_refinement(refinement_id)
        print("Refinement finalized")

        # Phase 4: Execution
        print("Phase 4: Starting execution...")
        execution_response = await self.start_execution(spec_id)
        execution_id = execution_response["execution_id"]
        print(f"Execution ID: {execution_id}")

        # Check status
        execution_status = await self.get_execution_status(execution_id)
        print(f"Execution status: {execution_status['status']}")

        return {
            "session_id": self.session_id,
            "analysis_id": analysis_id,
            "specification_id": spec_id,
            "refinement_id": refinement_id,
            "execution_id": execution_id,
            "final_status": execution_status
        }


async def main():
    """Example usage of the Specify API client."""
    async with SpecifyAPIClient() as client:
        print("=== Specify API Python Client Example ===")
        print(f"Session ID: {client.session_id}")

        # Health check
        health = await client.health_check()
        print(f"API Health: {health['status']}")

        # Version info
        version = await client.get_version()
        print(f"API Version: {version['api_version']}")

        # Example prompt
        prompt = """
        Create a web application for a book club that allows members to:
        1. Browse and search a catalog of books
        2. Create reading lists and track progress
        3. Schedule and manage book club meetings
        4. Discuss books in forums with spoiler protection
        5. Rate and review books
        6. Get personalized book recommendations

        The application should support multiple book clubs and have
        both web and mobile interfaces.
        """

        user_context = "This is for a non-profit organization that manages multiple book clubs."

        # Run complete workflow
        try:
            # Start WebSocket listener in background
            async def listen_task():
                try:
                    await client.listen_for_events()
                except Exception as e:
                    print(f"WebSocket error: {e}")

            # Start listening for events
            listener_task = asyncio.create_task(listen_task())

            # Run the workflow
            result = await client.complete_workflow(prompt, user_context)
            print("\n=== Workflow Complete ===")
            print(json.dumps(result, indent=2, default=str))

            # Cancel the listener
            listener_task.cancel()

        except Exception as e:
            print(f"Workflow error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())