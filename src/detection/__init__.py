"""Detection module for League of Legends client integration.

This module provides functionality to detect active League accounts
and manage streaming session data.
"""

from .client_detector import LeagueClientDetector
from .streaming_session_manager import StreamingSessionManager

__all__ = ['LeagueClientDetector', 'StreamingSessionManager']