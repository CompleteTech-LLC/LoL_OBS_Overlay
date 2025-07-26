"""Module for handling ranked information retrieval and processing."""

import logging
from typing import Optional, List, Dict, Any
from ..api.riot_api import RiotAPIClient
from ..api.config import HIGH_TIER_LEAGUES, RANKED_QUEUES


class RankedInfoRetriever:
    """Handles ranked information retrieval using multiple methods."""
    
    def __init__(self, api_client: RiotAPIClient):
        self.api_client = api_client
        self.logger = logging.getLogger(__name__)
    
    def get_ranked_info_by_puuid(self, puuid: str, region: str = "euw1") -> Optional[List[Dict[str, Any]]]:
        """
        Get ranked information using PUUID with fallback methods.
        
        Args:
            puuid: The player's PUUID
            region: The region for the request
            
        Returns:
            List of ranked entries or None if not found
        """
        self.logger.info("Searching for ranked data...")
        
        # Method 1: Direct PUUID-based ranked lookup
        self.logger.info("Attempting PUUID-based ranked lookup...")
        ranked_data = self.api_client.get_ranked_entries_by_puuid(puuid, region)
        
        if ranked_data:
            self.logger.info("✅ Successfully retrieved ranked data via PUUID!")
            return ranked_data
        
        # Method 2: Check high tier leagues (Challenger/GM/Master)
        self.logger.info("Checking high tier leagues...")
        high_tier_data = self._check_high_tier_leagues(puuid, region)
        
        if high_tier_data:
            return high_tier_data
        
        # Method 3: Try to get summoner ID from match data and attempt ranked lookup
        self.logger.info("Attempting ranked lookup via match API...")
        summoner_id = self._get_summoner_id_from_match(puuid, region)
        
        if summoner_id:
            self.logger.info(f"Found summoner ID from match: {summoner_id[:20]}...")
            ranked_data = self.api_client.get_ranked_entries_by_summoner_id(summoner_id, region)
            
            if ranked_data:
                self.logger.info("Successfully retrieved ranked data via summoner ID!")
                return ranked_data
        
        self.logger.warning("Unable to retrieve ranked data through available methods")
        return None
    
    def _check_high_tier_leagues(self, puuid: str, region: str) -> Optional[List[Dict[str, Any]]]:
        """
        Check high tier leagues for the player.
        
        Args:
            puuid: The player's PUUID
            region: The region for the request
            
        Returns:
            List of ranked entries if found in high tier leagues
        """
        for queue in RANKED_QUEUES:
            for tier in HIGH_TIER_LEAGUES:
                league_data = self.api_client.get_high_tier_league(tier, queue, region)
                
                if league_data and 'entries' in league_data:
                    for entry in league_data['entries']:
                        if entry.get('puuid') == puuid:
                            self.logger.info(f"Found player in {tier.replace('leagues', '').upper()} {queue}")
                            # Add queue type for consistency
                            entry['queueType'] = queue
                            return [entry]
        
        return None
    
    def _get_summoner_id_from_match(self, puuid: str, region: str) -> Optional[str]:
        """
        Get summoner ID from recent match data.
        
        Args:
            puuid: The player's PUUID
            region: The region for the request
            
        Returns:
            Summoner ID if found, None otherwise
        """
        # Get recent matches
        match_ids = self.api_client.get_match_ids_by_puuid(puuid, region, count=1)
        
        if not match_ids:
            return None
        
        # Get detailed match data
        match_data = self.api_client.get_match_data(match_ids[0], region)
        
        if not match_data:
            return None
        
        # Find our player in the match
        for participant in match_data['info']['participants']:
            if participant.get('puuid') == puuid:
                return participant.get('summonerId')
        
        return None
    
    @staticmethod
    def format_ranked_data(ranked_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Format ranked data for display.
        
        Args:
            ranked_data: Raw ranked data from API
            
        Returns:
            Formatted ranked data
        """
        formatted_data = []
        
        for queue in ranked_data:
            # Handle different formats (high tier vs standard)
            if 'rank' in queue and 'tier' not in queue:
                # High tier format (Challenger/GM/Master)
                tier = "CHALLENGER"
                rank = queue['rank']
                tier_rank = f"CHALLENGER {queue['rank']}"
                queue_name = queue.get('queueType', 'RANKED_SOLO_5x5').replace('_', ' ').title()
            else:
                # Standard format
                queue_name = queue.get('queueType', 'Unknown').replace('_', ' ').title()
                tier = queue.get('tier', 'Unknown')
                rank = queue.get('rank', 'Unknown')
                tier_rank = f"{tier} {rank}"
            
            wins = queue.get('wins', 0)
            losses = queue.get('losses', 0)
            lp = queue.get('leaguePoints', 0)
            total_games = wins + losses
            winrate = round((wins / total_games) * 100, 1) if total_games > 0 else 0
            
            formatted_entry = {
                'queue_name': queue_name,
                'tier_rank': tier_rank,
                'tier': tier,
                'rank': rank,
                'lp': lp,
                'wins': wins,
                'losses': losses,
                'winrate': winrate,
                'total_games': total_games
            }
            
            formatted_data.append(formatted_entry)
        
        return formatted_data