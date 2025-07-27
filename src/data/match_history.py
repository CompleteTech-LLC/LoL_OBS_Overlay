"""Module for handling match history retrieval and processing."""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from ..api.riot_api import RiotAPIClient
from ..api.config import QUEUE_TYPES


class MatchHistoryRetriever:
    """Handles match history retrieval and processing."""
    
    def __init__(self, api_client: RiotAPIClient):
        self.api_client = api_client
        self.logger = logging.getLogger(__name__)
    
    def get_daily_matches(self, puuid: str, region: str = None) -> List[Dict[str, Any]]:
        """
        Get matches from today.
        
        Args:
            puuid: The player's PUUID
            region: The region for the request
            
        Returns:
            List of match data dictionaries
        """
        # Calculate start of today in epoch seconds
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        start_time = int(today.timestamp())
        
        from ..api.config import Config
        config = Config()
        
        # Get match IDs from today
        match_ids = self.api_client.get_match_ids_by_puuid(
            puuid, region, start_time=start_time, count=config.default_match_count
        )
        
        if not match_ids:
            self.logger.info("No matches found for today")
            return []
        
        # Get detailed match data
        matches_data = []
        for match_id in match_ids:
            match_data = self.api_client.get_match_data(match_id, region)
            if match_data:
                matches_data.append(match_data)
        
        self.logger.info(f"Retrieved {len(matches_data)} matches for today")
        return matches_data
    
    @staticmethod
    def format_match_data(match_data: Dict[str, Any], target_puuid: str) -> Optional[Dict[str, Any]]:
        """
        Format match data for display.
        
        Args:
            match_data: Raw match data from API
            target_puuid: PUUID of the target player
            
        Returns:
            Formatted match data dictionary or None if player not found
        """
        info = match_data['info']
        
        # Find target player in the match
        player_data = None
        for participant in info['participants']:
            if participant.get('puuid') == target_puuid:
                player_data = participant
                break
        
        if not player_data:
            return None
        
        # Extract match information
        game_duration = info['gameDuration']
        queue_id = info['queueId']
        game_start = datetime.fromtimestamp(info['gameStartTimestamp'] / 1000, timezone.utc)
        
        # Extract player performance data
        champion = player_data['championName']
        kills = player_data['kills']
        deaths = player_data['deaths']
        assists = player_data['assists']
        win = player_data['win']
        
        # Extract role information
        individual_position = player_data.get('individualPosition', 'UNKNOWN')
        team_position = player_data.get('teamPosition', 'UNKNOWN')
        lane = player_data.get('lane', 'UNKNOWN')
        role = player_data.get('role', 'UNKNOWN')
        
        # Calculate derived statistics
        kda_ratio = (kills + assists) / max(deaths, 1)
        cs = player_data['totalMinionsKilled'] + player_data.get('neutralMinionsKilled', 0)
        gold = player_data['goldEarned']
        
        # Format duration
        minutes = game_duration // 60
        seconds = game_duration % 60
        duration_str = f"{minutes}:{seconds:02d}"
        
        # Get queue name
        queue_name = QUEUE_TYPES.get(queue_id, f"Queue {queue_id}")
        
        # Format role for display
        role_display = individual_position.title() if individual_position != 'UNKNOWN' else 'Unknown'
        if role_display == 'Utility':
            role_display = 'Support'
        elif role_display == 'Bottom':
            role_display = 'ADC'
        
        return {
            'result': "Victory" if win else "Defeat",
            'champion': champion,
            'role': role_display,
            'position': individual_position,
            'lane': lane,
            'kda': f"{kills}/{deaths}/{assists}",
            'kda_ratio': round(kda_ratio, 2),
            'duration': duration_str,
            'cs': cs,
            'gold': gold,
            'queue': queue_name,
            'time': game_start.strftime('%H:%M UTC'),
            'win': win,
            'game_start': game_start
        }
    
    @staticmethod
    def calculate_daily_stats(formatted_matches: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate daily statistics from formatted matches.
        
        Args:
            formatted_matches: List of formatted match data
            
        Returns:
            Dictionary containing daily statistics
        """
        if not formatted_matches:
            return {
                'total_games': 0,
                'wins': 0,
                'losses': 0,
                'winrate': 0.0,
                'roles_played': {},
                'champions_played': {}
            }
        
        wins = sum(1 for match in formatted_matches if match['win'])
        losses = len(formatted_matches) - wins
        winrate = round((wins / len(formatted_matches)) * 100, 1) if formatted_matches else 0
        
        # Calculate role statistics
        roles_played = {}
        champions_played = {}
        
        for match in formatted_matches:
            role = match.get('role', 'Unknown')
            champion = match.get('champion', 'Unknown')
            
            # Count roles
            if role not in roles_played:
                roles_played[role] = {'games': 0, 'wins': 0}
            roles_played[role]['games'] += 1
            if match['win']:
                roles_played[role]['wins'] += 1
            
            # Count champions
            if champion not in champions_played:
                champions_played[champion] = {'games': 0, 'wins': 0}
            champions_played[champion]['games'] += 1
            if match['win']:
                champions_played[champion]['wins'] += 1
        
        # Calculate win rates for roles
        for role_data in roles_played.values():
            role_data['winrate'] = round((role_data['wins'] / role_data['games']) * 100, 1)
        
        # Calculate win rates for champions
        for champ_data in champions_played.values():
            champ_data['winrate'] = round((champ_data['wins'] / champ_data['games']) * 100, 1)
        
        return {
            'total_games': len(formatted_matches),
            'wins': wins,
            'losses': losses,
            'winrate': winrate,
            'roles_played': roles_played,
            'champions_played': champions_played
        }