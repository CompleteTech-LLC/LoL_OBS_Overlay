"""Configuration module for League of Legends API client.

This module handles secure configuration loading, API key management,
and application constants with proper validation and security measures.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Secure configuration class for API settings and constants.
    
    This class handles API key validation, security checks, and provides
    a centralized configuration interface for the application.
    
    Attributes:
        api_key (str): Validated API key for Riot API access
        debug_mode (bool): Whether debug mode is enabled
        rate_limit_delay (float): Delay between API requests
    """
    
    def __init__(self) -> None:
        """Initialize configuration with security validation.
        
        Raises:
            ValueError: If no valid API key is found or validation fails
            SecurityError: If API key format appears invalid
        """
        self.riot_api_key = os.getenv('RIOT_API_KEY')
        self.league_api_key = os.getenv('LEAGUE_API_KEY')
        
        # Load all configuration first
        self.debug_mode = os.getenv('DEBUG', 'false').lower() == 'true'
        self.rate_limit_delay = float(os.getenv('RATE_LIMIT_DELAY', '0.1'))
        
        # Monitoring intervals
        self.game_check_interval = float(os.getenv('GAME_CHECK_INTERVAL', '1'))
        self.account_refresh_interval = float(os.getenv('ACCOUNT_REFRESH_INTERVAL', '60'))
        self.overlay_update_interval = float(os.getenv('OVERLAY_UPDATE_INTERVAL', '5'))
        
        # Session and validation settings
        self.session_timeout = int(os.getenv('SESSION_TIMEOUT', '30'))
        self.max_game_name_length = int(os.getenv('MAX_GAME_NAME_LENGTH', '16'))
        self.max_tag_line_length = int(os.getenv('MAX_TAG_LINE_LENGTH', '5'))
        self.min_api_key_length = int(os.getenv('MIN_API_KEY_LENGTH', '20'))
        
        # Live client configuration
        self.live_client_base_url = os.getenv('LIVE_CLIENT_BASE_URL', 'https://127.0.0.1:2999/liveclientdata')
        
        # Match history settings
        self.default_match_count = int(os.getenv('DEFAULT_MATCH_COUNT', '20'))
        
        # Display settings
        self.current_season = os.getenv('CURRENT_SEASON', '2025')
        
        # Now handle API key validation
        # Use League API key for all operations to maintain consistent encryption
        self.api_key = self.league_api_key if self.league_api_key else self.riot_api_key
        
        if not self.api_key:
            raise ValueError(
                "No valid API key found. Please set RIOT_API_KEY or LEAGUE_API_KEY in your .env file"
            )
        
        # Validate API key format for security (now that min_api_key_length is set)
        self._validate_api_key()
        
        # Don't log the actual API key for security
        logging.getLogger(__name__).info("Configuration loaded successfully")
    
    def _validate_api_key(self) -> None:
        """Validate API key format for basic security.
        
        Raises:
            ValueError: If API key format is invalid
        """
        if not isinstance(self.api_key, str):
            raise ValueError("API key must be a string")
        
        # Basic format validation (Riot API keys are typically 70+ characters)
        if len(self.api_key) < self.min_api_key_length:
            raise ValueError(f"API key appears too short to be valid (minimum {self.min_api_key_length} characters)")
        
        # Check for obvious fake keys
        if self.api_key.lower() in ['your_api_key_here', 'fake_key', 'test_key']:
            raise ValueError("Please set a real API key")
    
    @property
    def headers(self) -> Dict[str, str]:
        """Return secure headers for API requests.
        
        Returns:
            Dictionary containing request headers with API key
        """
        return {
            "X-Riot-Token": self.api_key,
            "User-Agent": "LeagueAPI-Client/1.0",
            "Accept": "application/json"
        }


# Default regions to try when detecting accounts
DEFAULT_REGIONS_TO_TRY = ["na1", "euw1", "eun1", "kr", "br1", "jp1", "oc1", "ru", "tr1", "la1", "la2"]

# API Base URLs
BASE_URLS = {
    'account': 'https://europe.api.riotgames.com',
    'europe': 'https://europe.api.riotgames.com',
    'euw1': 'https://euw1.api.riotgames.com',
    'eun1': 'https://eun1.api.riotgames.com'
}

# Regional routing mappings
REGIONAL_ROUTING = {
    'euw1': 'europe',
    'eun1': 'europe',
    'na1': 'americas',
    'br1': 'americas',
    'lan': 'americas',
    'las': 'americas',
    'kr': 'asia',
    'jp1': 'asia'
}

# Queue type mappings
QUEUE_TYPES = {
    420: "Ranked Solo/Duo",
    440: "Ranked Flex",
    450: "ARAM",
    400: "Normal Draft",
    430: "Normal Blind",
    490: "Normal Blind Pick",
    700: "Clash"
}

# Tier configurations for high-tier league lookups
HIGH_TIER_LEAGUES = ["challengerleagues", "grandmasterleagues", "masterleagues"]
RANKED_QUEUES = ["RANKED_SOLO_5x5", "RANKED_FLEX_SR"]

# Rate limiting settings
RATE_LIMIT_DELAY = 0.1  # seconds between requests

# Logging configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

def setup_logging(level: str = LOG_LEVEL) -> logging.Logger:
    """Setup secure logging configuration.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        
    Returns:
        Configured logger instance
        
    Raises:
        ValueError: If log level is invalid
    """
    # Validate log level
    valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    if level.upper() not in valid_levels:
        level = 'INFO'
    
    # Create secure log file path
    log_file = Path('lol_api.log')
    
    # Configure logging with security considerations
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=LOG_FORMAT,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file, mode='a', encoding='utf-8')
        ]
    )
    
    # Create filter to prevent sensitive data logging
    class SensitiveDataFilter(logging.Filter):
        """Filter to remove sensitive data from logs."""
        
        def filter(self, record: logging.LogRecord) -> bool:
            # Remove or mask API keys and other sensitive data
            if hasattr(record, 'msg') and isinstance(record.msg, str):
                # Don't log anything that looks like an API key
                if 'RGAPI-' in record.msg or len(record.msg.replace('-', '')) > 50:
                    record.msg = '[SENSITIVE DATA FILTERED]'
            return True
    
    # Apply filter to all handlers
    logger = logging.getLogger()
    for handler in logger.handlers:
        handler.addFilter(SensitiveDataFilter())
    
    return logging.getLogger(__name__)