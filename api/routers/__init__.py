"""
API routers for the Specify system.

This module contains all the FastAPI routers that handle different
phases of the Specify system through REST and WebSocket endpoints.
"""

from . import analyzer
from . import specification
from . import refinement
from . import dispatch
from . import websocket

__all__ = [
    "analyzer",
    "specification",
    "refinement",
    "dispatch",
    "websocket",
]