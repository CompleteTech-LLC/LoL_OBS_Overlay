"""API module for League of Legends Riot Games API integration.

This module provides secure and rate-limited access to the Riot Games API
with comprehensive error handling and configuration management.
"""

from .config import Config, setup_logging
from .riot_api import RiotAPIClient, RiotAPIError

__all__ = ['Config', 'setup_logging', 'RiotAPIClient', 'RiotAPIError']