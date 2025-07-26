"""Formatting utilities for displaying League of Legends data."""

from datetime import datetime, timezone
from typing import List, Dict, Any


class OutputFormatter:
    """Handles formatting of various data types for console output."""
    
    @staticmethod
    def format_account_info(account: Dict[str, Any], summoner: Dict[str, Any] = None) -> str:
        """
        Format account information for display.
        
        Args:
            account: Account data from Riot API
            summoner: Summoner data from Riot API
            
        Returns:
            Formatted account information string
        """
        lines = [
            "=" * 50,
            "ACCOUNT INFORMATION",
            "=" * 50,
            f"Riot ID: {account['gameName']}#{account['tagLine']}",
            f"PUUID: {account['puuid']}"
        ]
        
        if summoner:
            lines.extend([
                f"Summoner Name: {summoner.get('name', 'N/A')}",
                f"Summoner Level: {summoner.get('summonerLevel', 'N/A')}",
                f"Profile Icon ID: {summoner.get('profileIconId', 'N/A')}"
            ])
        
        return "\n".join(lines)
    
    @staticmethod
    def format_ranked_info(ranked_data: List[Dict[str, Any]]) -> str:
        """
        Format ranked information for display.
        
        Args:
            ranked_data: Formatted ranked data
            
        Returns:
            Formatted ranked information string
        """
        if not ranked_data:
            return "\nRANKED INFORMATION\n" + "=" * 50 + "\nNo ranked data found - account may be unranked or have no recent ranked games."
        
        from ..api.config import Config
        config = Config()
        
        lines = [
            f"\nRANKED INFORMATION (Season {config.current_season})",
            "=" * 50
        ]
        
        for queue_info in ranked_data:
            lines.extend([
                f"\n{queue_info['queue_name']}:",
                f"  Rank: {queue_info['tier_rank']}",
                f"  LP: {queue_info['lp']}",
                f"  Wins: {queue_info['wins']}",
                f"  Losses: {queue_info['losses']}",
                f"  Win Rate: {queue_info['winrate']}%",
                f"  Total Games: {queue_info['total_games']}"
            ])
        
        return "\n".join(lines)
    
    @staticmethod
    def format_daily_matches(formatted_matches: List[Dict[str, Any]], daily_stats: Dict[str, Any]) -> str:
        """
        Format daily match history for display.
        
        Args:
            formatted_matches: List of formatted match data
            daily_stats: Daily statistics
            
        Returns:
            Formatted daily matches string
        """
        today_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        
        if not formatted_matches:
            return f"\nTODAY'S GAMES\n" + "=" * 50 + f"\nNo games played today ({today_date})"
        
        lines = [
            f"\nTODAY'S GAMES",
            "=" * 50,
            f"Found {len(formatted_matches)} games played today:",
            "=" * 60
        ]
        
        for i, match in enumerate(formatted_matches, 1):
            status_emoji = "🟢" if match['win'] else "🔴"
            lines.extend([
                f"\n{i}. {status_emoji} {match['result']} - {match['champion']} ({match.get('role', 'Unknown')}) ({match['time']})",
                f"   Queue: {match['queue']}",
                f"   KDA: {match['kda']} (Ratio: {match['kda_ratio']})",
                f"   Duration: {match['duration']} | CS: {match['cs']} | Gold: {match['gold']:,}"
            ])
        
        # Add daily statistics
        if daily_stats['total_games'] > 0:
            lines.extend([
                "",
                f"📊 Today's Record: {daily_stats['wins']}W-{daily_stats['losses']}L ({daily_stats['winrate']}% win rate)"
            ])
            
            # Add role breakdown if multiple roles played
            if len(daily_stats.get('roles_played', {})) > 1:
                lines.append("\n📍 Roles Played Today:")
                for role, stats in daily_stats['roles_played'].items():
                    lines.append(f"   {role}: {stats['wins']}W-{stats['games']-stats['wins']}L ({stats['winrate']}%)")
            
            # Add champion breakdown if multiple champions played
            if len(daily_stats.get('champions_played', {})) > 1:
                lines.append("\n🏆 Champions Played Today:")
                for champion, stats in daily_stats['champions_played'].items():
                    lines.append(f"   {champion}: {stats['wins']}W-{stats['games']-stats['wins']}L ({stats['winrate']}%)")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_error_message(error: str, suggestion: str = None) -> str:
        """
        Format error messages for display.
        
        Args:
            error: Error message
            suggestion: Optional suggestion for resolving the error
            
        Returns:
            Formatted error message
        """
        lines = [
            "❌ ERROR",
            "=" * 30,
            error
        ]
        
        if suggestion:
            lines.extend([
                "",
                "💡 Suggestion:",
                suggestion
            ])
        
        return "\n".join(lines)
    
    @staticmethod
    def format_lookup_summary(account: Dict[str, Any], summoner: Dict[str, Any], 
                            ranked_data: List[Dict[str, Any]], daily_stats: Dict[str, Any]) -> str:
        """
        Format a complete lookup summary.
        
        Args:
            account: Account data
            summoner: Summoner data
            ranked_data: Ranked data
            daily_stats: Daily statistics
            
        Returns:
            Complete formatted summary
        """
        summary_lines = [
            "\n" + "=" * 60,
            "LOOKUP SUMMARY",
            "=" * 60,
            f"Player: {account['gameName']}#{account['tagLine']}",
            f"Level: {summoner.get('summonerLevel', 'N/A') if summoner else 'N/A'}"
        ]
        
        # Add ranked summary
        if ranked_data:
            highest_rank = ranked_data[0]  # Assume first entry is highest/most relevant
            summary_lines.append(f"Highest Rank: {highest_rank['tier_rank']} ({highest_rank['lp']} LP)")
        else:
            summary_lines.append("Rank: Unranked")
        
        # Add daily performance
        if daily_stats['total_games'] > 0:
            summary_lines.append(f"Today's Performance: {daily_stats['wins']}W-{daily_stats['losses']}L ({daily_stats['winrate']}%)")
        else:
            summary_lines.append("Today's Performance: No games played")
        
        summary_lines.append("=" * 60)
        
        return "\n".join(summary_lines)