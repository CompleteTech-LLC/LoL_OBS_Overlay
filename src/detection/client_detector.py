"""League of Legends Client Detection Service.

This module provides functionality to detect the currently active League of Legends
account by connecting to the Live Client Data API and League Client Update (LCU) API.
"""

import json
import requests
import urllib3
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

# Disable SSL warnings for local API calls
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class LeagueClientDetector:
    """Detects active League of Legends account from game client APIs."""
    
    def __init__(self):
        """Initialize the client detector."""
        from ..api.config import Config
        
        self.config = Config()
        self.logger = logging.getLogger(__name__)
        self.live_client_base_url = self.config.live_client_base_url
        self.session_accounts = []  # Track accounts used this session
        
    def get_active_player(self) -> Optional[Dict[str, Any]]:
        """Get active player information from Live Client Data API.
        
        Returns:
            Dict containing player info if successful, None if failed
        """
        try:
            response = requests.get(
                f"{self.live_client_base_url}/activeplayer",
                verify=False,
                timeout=3  # Reduced timeout for faster detection
            )
            
            if response.status_code == 200:
                data = response.json()
                return data
            else:
                # Silently fail for non-200 status codes (common when not in game)
                return None
                
        except requests.exceptions.ConnectionError:
            # Connection refused is normal when League isn't running
            return None
        except requests.exceptions.Timeout:
            # Timeout is normal, don't log
            return None
        except Exception:
            # Silently handle other exceptions
            return None
    
    def extract_riot_id_from_active_player(self, player_data: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """Extract Riot ID components from active player data.
        
        Args:
            player_data: Raw player data from Live Client API
            
        Returns:
            Dict with 'game_name', 'tag_line', and 'riot_id' if successful
        """
        try:
            # Check if riotId is available (newer format)
            if 'riotId' in player_data:
                riot_id = player_data['riotId']
                if '#' in riot_id:
                    game_name, tag_line = riot_id.split('#', 1)
                    return {
                        'game_name': game_name,
                        'tag_line': tag_line,
                        'riot_id': riot_id
                    }
            
            # Fallback to summonerName if available
            if 'summonerName' in player_data:
                summoner_name = player_data['summonerName']
                self.logger.warning(f"Only summoner name available: {summoner_name}")
                return {
                    'game_name': summoner_name,
                    'tag_line': None,
                    'riot_id': summoner_name
                }
                
            self.logger.error("No usable player identifier found in active player data")
            return None
            
        except Exception as e:
            self.logger.error(f"Error extracting Riot ID: {e}")
            return None
    
    def detect_current_account(self) -> Optional[Dict[str, str]]:
        """Detect the currently active League account.
        
        Returns:
            Dict with account info if successful, None if failed
        """
        # Try Live Client Data API first (works during actual games)
        player_data = self.get_active_player()
        if player_data:
            account_info = self.extract_riot_id_from_active_player(player_data)
            if account_info:
                self._add_to_session_accounts(account_info)
                return account_info
        
        # Try alternative endpoints for training tool/practice modes
        game_stats = self._get_game_stats()
        if game_stats:
            # If we can get game stats, try to get player list
            player_list = self._get_player_list()
            if player_list:
                # Look for the local player in the list
                for player in player_list:
                    if player.get('summonerName'):  # Local player usually has summoner name
                        account_info = {
                            'game_name': player['summonerName'],
                            'tag_line': None,  # Training tool might not have tag line
                            'riot_id': player['summonerName']
                        }
                        self._add_to_session_accounts(account_info)
                        return account_info
        
        return None
    
    def _get_game_stats(self) -> Optional[Dict[str, Any]]:
        """Get game statistics from Live Client API."""
        try:
            response = requests.get(
                f"{self.live_client_base_url}/gamestats",
                verify=False,
                timeout=2
            )
            return response.json() if response.status_code == 200 else None
        except Exception:
            return None
    
    def _get_player_list(self) -> Optional[List[Dict[str, Any]]]:
        """Get player list from Live Client API."""
        try:
            response = requests.get(
                f"{self.live_client_base_url}/playerlist",
                verify=False,
                timeout=2
            )
            return response.json() if response.status_code == 200 else None
        except Exception:
            return None
    
    def _add_to_session_accounts(self, account_info: Dict[str, str]) -> None:
        """Add account to session tracking list.
        
        Args:
            account_info: Account information dictionary
        """
        # Check if account already exists in session
        for existing in self.session_accounts:
            if existing['riot_id'] == account_info['riot_id']:
                existing['last_seen'] = datetime.now().isoformat()
                return
        
        # Add new account to session
        account_with_timestamp = {
            **account_info,
            'first_seen': datetime.now().isoformat(),
            'last_seen': datetime.now().isoformat()
        }
        self.session_accounts.append(account_with_timestamp)
        self.logger.info(f"Added new account to session: {account_info['riot_id']}")
    
    def get_session_accounts(self) -> List[Dict[str, Any]]:
        """Get all accounts detected during this session.
        
        Returns:
            List of account dictionaries with timestamps
        """
        return self.session_accounts.copy()
    
    def test_live_client_connection(self) -> Dict[str, Any]:
        """Test connection to Live Client Data API and return diagnostic info.
        
        Returns:
            Dict with connection status and available data
        """
        result = {
            'live_client_available': False,
            'active_player_data': None,
            'all_players_available': False,
            'game_stats_available': False,
            'error': None
        }
        
        try:
            # Test active player endpoint
            response = requests.get(
                f"{self.live_client_base_url}/activeplayer",
                verify=False,
                timeout=5
            )
            
            if response.status_code == 200:
                result['live_client_available'] = True
                result['active_player_data'] = response.json()
                
                # Test other endpoints
                try:
                    all_players_response = requests.get(
                        f"{self.live_client_base_url}/playerlist",
                        verify=False,
                        timeout=3
                    )
                    result['all_players_available'] = all_players_response.status_code == 200
                except:
                    pass
                
                try:
                    game_stats_response = requests.get(
                        f"{self.live_client_base_url}/gamestats",
                        verify=False,
                        timeout=3
                    )
                    result['game_stats_available'] = game_stats_response.status_code == 200
                except:
                    pass
                    
            else:
                result['error'] = f"HTTP {response.status_code}: {response.text}"
                
        except requests.exceptions.ConnectionError:
            result['error'] = "Connection refused - Live Client API not available"
        except requests.exceptions.Timeout:
            result['error'] = "Connection timeout"
        except Exception as e:
            result['error'] = f"Unexpected error: {str(e)}"
        
        return result


def main():
    """Test the client detector."""
    logging.basicConfig(level=logging.INFO)
    
    detector = LeagueClientDetector()
    
    print("🔍 Testing League Client Detection...")
    print("=" * 50)
    
    # Test connection
    connection_test = detector.test_live_client_connection()
    print(f"Live Client Available: {connection_test['live_client_available']}")
    
    if connection_test['error']:
        print(f"❌ Error: {connection_test['error']}")
        return
    
    if connection_test['active_player_data']:
        print("✅ Active player data found!")
        player_data = connection_test['active_player_data']
        
        # Print relevant data
        print(f"Summoner Name: {player_data.get('summonerName', 'N/A')}")
        if 'riotId' in player_data:
            print(f"Riot ID: {player_data['riotId']}")
        
        print(f"Level: {player_data.get('level', 'N/A')}")
        print(f"Current Gold: {player_data.get('currentGold', 'N/A')}")
        
        # Test account detection
        print("\n🎯 Testing account detection...")
        account_info = detector.detect_current_account()
        if account_info:
            print(f"✅ Detected account: {account_info['riot_id']}")
            if account_info['tag_line']:
                print(f"   Game Name: {account_info['game_name']}")
                print(f"   Tag Line: {account_info['tag_line']}")
        else:
            print("❌ Could not detect account")
    
    else:
        print("❌ No active player data available")


if __name__ == "__main__":
    main()