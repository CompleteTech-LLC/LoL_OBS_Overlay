"""Riot API client for League of Legends data retrieval.

This module provides a secure, rate-limited client for interacting with the
Riot Games API with comprehensive error handling and logging.
"""

import requests
import time
import logging
from typing import Optional, Dict, List, Any, Union
from .config import Config, BASE_URLS, REGIONAL_ROUTING, RATE_LIMIT_DELAY


class RiotAPIError(Exception):
    """Custom exception for Riot API errors.
    
    Attributes:
        message (str): Error message
        status_code (Optional[int]): HTTP status code if available
        response_text (Optional[str]): Raw response text if available
    """
    
    def __init__(self, message: str, status_code: Optional[int] = None, 
                 response_text: Optional[str] = None) -> None:
        """Initialize RiotAPIError.
        
        Args:
            message: Error description
            status_code: HTTP status code from failed request
            response_text: Raw response text from failed request
        """
        self.status_code = status_code
        self.response_text = response_text
        super().__init__(message)


class RiotAPIClient:
    """Secure client for interacting with Riot Games API.
    
    This client provides rate limiting, error handling, retry logic,
    and secure request management for all Riot API endpoints.
    
    Attributes:
        config (Config): Configuration instance
        logger (logging.Logger): Logger for this client
        session (requests.Session): HTTP session for requests
    """
    
    def __init__(self, config: Optional[Config] = None) -> None:
        """Initialize the Riot API client.
        
        Args:
            config: Configuration instance (creates default if None)
            
        Raises:
            ValueError: If configuration is invalid
        """
        self.config = config or Config()
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update(self.config.headers)
        
        # Configure session timeout and retries
        self.session.timeout = self.config.session_timeout
        self.logger.info("Riot API client initialized successfully")
    
    def _sanitize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize request parameters for security.
        
        Args:
            params: Dictionary of request parameters
            
        Returns:
            Sanitized parameters dictionary
        """
        sanitized = {}
        for key, value in params.items():
            if isinstance(value, (str, int, float)):
                # Convert to string and limit length for security
                sanitized[key] = str(value)[:100]
            elif isinstance(value, (list, tuple)):
                # Handle list parameters, limit size
                sanitized[key] = [str(v)[:100] for v in value[:10]]
        return sanitized
    
    def _make_request(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make a request to the Riot API with error handling and rate limiting.
        
        Args:
            url: The API endpoint URL
            params: Query parameters for the request
            
        Returns:
            JSON response data
            
        Raises:
            RiotAPIError: If the request fails
        """
        try:
            response = self.session.get(url, params=params)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                # Rate limited - wait and retry once
                retry_after = int(response.headers.get('Retry-After', 1))
                self.logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                time.sleep(retry_after)
                response = self.session.get(url, params=params)
                if response.status_code == 200:
                    return response.json()
            
            # Handle other error cases
            error_msg = f"API request failed: {response.status_code}"
            if response.status_code == 403:
                error_msg += " - Access forbidden (check API key permissions)"
            elif response.status_code == 404:
                error_msg += " - Resource not found"
            
            raise RiotAPIError(
                error_msg,
                status_code=response.status_code,
                response_text=response.text
            )
            
        except requests.RequestException as e:
            raise RiotAPIError(f"Network error: {str(e)}")
    
    def get_account_by_riot_id(self, game_name: str, tag_line: str) -> Optional[Dict[str, Any]]:
        """
        Get account information using Riot ID (game name + tag line).
        
        Args:
            game_name: The player's game name
            tag_line: The player's tag line
            
        Returns:
            Account data dictionary or None if not found
        """
        url = f"{BASE_URLS['account']}/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        
        try:
            data = self._make_request(url)
            self.logger.info(f"Successfully retrieved account for {game_name}#{tag_line}")
            return data
        except RiotAPIError as e:
            if e.status_code == 404:
                self.logger.warning(f"Account not found: {game_name}#{tag_line}")
                return None
            self.logger.error(f"Failed to get account {game_name}#{tag_line}: {e}")
            raise
    
    def get_summoner_by_puuid(self, puuid: str, region: str = "euw1") -> Optional[Dict[str, Any]]:
        """
        Get summoner information using PUUID.
        
        Args:
            puuid: The player's PUUID
            region: The region for the request
            
        Returns:
            Summoner data dictionary or None if not found
        """
        url = f"https://{region}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
        
        try:
            data = self._make_request(url)
            self.logger.info(f"Successfully retrieved summoner data for PUUID: {puuid[:20]}...")
            return data
        except RiotAPIError as e:
            if e.status_code == 404:
                self.logger.warning(f"Summoner not found for PUUID: {puuid[:20]}...")
                return None
            self.logger.error(f"Failed to get summoner for PUUID {puuid[:20]}...: {e}")
            raise
    
    def get_match_ids_by_puuid(self, puuid: str, region: str = "euw1", 
                              start_time: int = None, count: int = 20) -> List[str]:
        """
        Get match IDs for a player by PUUID.
        
        Args:
            puuid: The player's PUUID
            region: The region for the request
            start_time: Start time for match filtering (epoch seconds)
            count: Number of matches to retrieve
            
        Returns:
            List of match IDs
        """
        # Get the routing region for match API
        routing_region = REGIONAL_ROUTING.get(region, "europe")
        url = f"https://{routing_region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
        
        params = {"count": count}
        if start_time:
            params["startTime"] = start_time
        
        try:
            data = self._make_request(url, params)
            self.logger.info(f"Retrieved {len(data)} match IDs for PUUID: {puuid[:20]}...")
            return data
        except RiotAPIError as e:
            self.logger.error(f"Failed to get match IDs for PUUID {puuid[:20]}...: {e}")
            return []
    
    def get_match_data(self, match_id: str, region: str = "euw1") -> Optional[Dict[str, Any]]:
        """
        Get detailed match data by match ID.
        
        Args:
            match_id: The match ID
            region: The region for the request
            
        Returns:
            Match data dictionary or None if not found
        """
        routing_region = REGIONAL_ROUTING.get(region, "europe")
        url = f"https://{routing_region}.api.riotgames.com/lol/match/v5/matches/{match_id}"
        
        try:
            data = self._make_request(url)
            time.sleep(RATE_LIMIT_DELAY)  # Respect rate limits
            return data
        except RiotAPIError as e:
            if e.status_code == 404:
                self.logger.warning(f"Match not found: {match_id}")
                return None
            self.logger.error(f"Failed to get match data for {match_id}: {e}")
            return None
    
    def get_ranked_entries_by_puuid(self, puuid: str, region: str = "euw1") -> Optional[List[Dict[str, Any]]]:
        """
        Get ranked entries using PUUID (newer endpoint).
        
        Args:
            puuid: The player's PUUID
            region: The region for the request
            
        Returns:
            List of ranked entries or None if not available
        """
        url = f"https://{region}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}"
        
        try:
            data = self._make_request(url)
            self.logger.info(f"Successfully retrieved ranked data via PUUID for: {puuid[:20]}...")
            return data
        except RiotAPIError as e:
            if e.status_code == 403:
                self.logger.info("PUUID ranked endpoint access denied (insufficient permissions)")
                return None
            self.logger.error(f"Failed to get ranked data via PUUID {puuid[:20]}...: {e}")
            return None
    
    def get_ranked_entries_by_summoner_id(self, summoner_id: str, region: str = "euw1") -> Optional[List[Dict[str, Any]]]:
        """
        Get ranked entries using summoner ID.
        
        Args:
            summoner_id: The summoner's ID
            region: The region for the request
            
        Returns:
            List of ranked entries or None if not found
        """
        url = f"https://{region}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}"
        
        try:
            data = self._make_request(url)
            self.logger.info(f"Successfully retrieved ranked data via summoner ID")
            return data
        except RiotAPIError as e:
            if e.status_code == 404:
                self.logger.warning(f"No ranked data found for summoner ID: {summoner_id[:20]}...")
                return None
            self.logger.error(f"Failed to get ranked data via summoner ID {summoner_id[:20]}...: {e}")
            return None
    
    def get_high_tier_league(self, tier: str, queue: str, region: str = "euw1") -> Optional[Dict[str, Any]]:
        """
        Get high tier league data (Challenger/Grandmaster/Master).
        
        Args:
            tier: The tier ("challengerleagues", "grandmasterleagues", "masterleagues")
            queue: The queue type ("RANKED_SOLO_5x5", "RANKED_FLEX_SR")
            region: The region for the request
            
        Returns:
            League data dictionary or None if not found
        """
        url = f"https://{region}.api.riotgames.com/lol/league/v4/{tier}/by-queue/{queue}"
        
        try:
            data = self._make_request(url)
            return data
        except RiotAPIError as e:
            if e.status_code == 403:
                self.logger.debug(f"Access denied for {tier} {queue}")
                return None
            self.logger.error(f"Failed to get {tier} data for {queue}: {e}")
            return None