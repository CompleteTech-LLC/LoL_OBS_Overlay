#!/usr/bin/env python3
"""League of Legends Account Lookup Tool.

A comprehensive tool for looking up League of Legends player accounts,
ranked information, and daily match history using the Riot Games API.
"""

import sys
import logging
from typing import Optional

from ..api.config import Config, setup_logging
from ..api.riot_api import RiotAPIClient, RiotAPIError
from .ranked_info import RankedInfoRetriever
from .match_history import MatchHistoryRetriever
from ..utils.formatters import OutputFormatter


class LeagueAccountLookup:
    """Main class for League of Legends account lookup functionality."""
    
    def __init__(self, region: str = "euw1"):
        """Initialize the lookup service.
        
        Args:
            region: The region to use for API requests (default: euw1)
        """
        self.region = region
        self.logger = logging.getLogger(__name__)
        
        try:
            self.config = Config()
            self.api_client = RiotAPIClient(self.config)
            self.ranked_retriever = RankedInfoRetriever(self.api_client)
            self.match_retriever = MatchHistoryRetriever(self.api_client)
            self.formatter = OutputFormatter()
            
            self.logger.info(f"League Account Lookup initialized for region: {region}")
            
        except ValueError as e:
            self.logger.error(f"Configuration error: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Initialization error: {e}")
            raise
    
    def lookup_account(self, game_name: str, tag_line: str) -> Optional[dict]:
        """Perform complete account lookup.
        
        Args:
            game_name: Player's game name
            tag_line: Player's tag line
            
        Returns:
            Dictionary containing all lookup results, or None if account not found
        """
        if not game_name or not tag_line:
            error_msg = "Game name and tag line are required"
            print(self.formatter.format_error_message(
                error_msg, 
                "Please provide both game name and tag line (e.g., 'PlayerName', 'TAG')"
            ))
            return None
        
        self.logger.info(f"Starting lookup for: {game_name}#{tag_line}")
        
        try:
            # Step 1: Get account information
            account = self.api_client.get_account_by_riot_id(game_name, tag_line)
            if not account:
                error_msg = f"Account not found: {game_name}#{tag_line}"
                print(self.formatter.format_error_message(
                    error_msg,
                    "Please check the spelling and ensure the account exists"
                ))
                return None
            
            # Step 2: Get summoner information
            summoner = self.api_client.get_summoner_by_puuid(account['puuid'], self.region)
            
            # Step 3: Get ranked information
            ranked_data = self.ranked_retriever.get_ranked_info_by_puuid(account['puuid'], self.region)
            formatted_ranked = None
            if ranked_data:
                formatted_ranked = RankedInfoRetriever.format_ranked_data(ranked_data)
            
            # Step 4: Get daily matches
            daily_matches = self.match_retriever.get_daily_matches(account['puuid'], self.region)
            formatted_matches = []
            for match_data in daily_matches:
                formatted_match = MatchHistoryRetriever.format_match_data(match_data, account['puuid'])
                if formatted_match:
                    formatted_matches.append(formatted_match)
            
            daily_stats = MatchHistoryRetriever.calculate_daily_stats(formatted_matches)
            
            # Display results
            print(self.formatter.format_account_info(account, summoner))
            print(self.formatter.format_ranked_info(formatted_ranked or []))
            print(self.formatter.format_daily_matches(formatted_matches, daily_stats))
            print(self.formatter.format_lookup_summary(account, summoner, formatted_ranked or [], daily_stats))
            
            return {
                'account': account,
                'summoner': summoner,
                'ranked': formatted_ranked,
                'daily_matches': formatted_matches,
                'daily_stats': daily_stats
            }
            
        except RiotAPIError as e:
            error_msg = f"API error during lookup: {e}"
            if e.status_code == 403:
                suggestion = "API key may have insufficient permissions or be invalid"
            elif e.status_code == 429:
                suggestion = "Rate limit exceeded. Please wait before trying again"
            else:
                suggestion = "Please check your internet connection and try again"
            
            print(self.formatter.format_error_message(error_msg, suggestion))
            self.logger.error(error_msg)
            return None
            
        except Exception as e:
            error_msg = f"Unexpected error during lookup: {e}"
            print(self.formatter.format_error_message(
                error_msg,
                "Please check your configuration and try again"
            ))
            self.logger.error(error_msg, exc_info=True)
            return None


def validate_input(game_name: str, tag_line: str) -> bool:
    """Validate user input for game name and tag line.
    
    Args:
        game_name: The game name to validate
        tag_line: The tag line to validate
        
    Returns:
        True if input is valid, False otherwise
    """
    if not game_name or len(game_name.strip()) == 0:
        print("❌ Error: Game name cannot be empty")
        return False
    
    if not tag_line or len(tag_line.strip()) == 0:
        print("❌ Error: Tag line cannot be empty")
        return False
    
    from ..api.config import Config
    config = Config()
    
    # Use configurable length validation
    if len(game_name) > config.max_game_name_length:
        print(f"❌ Error: Game name is too long (max {config.max_game_name_length} characters)")
        return False
    
    if len(tag_line) > config.max_tag_line_length:
        print(f"❌ Error: Tag line is too long (max {config.max_tag_line_length} characters)")
        return False
    
    return True


def main():
    """Main function for command-line usage."""
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Get command line arguments
        if len(sys.argv) >= 3:
            game_name = sys.argv[1]
            tag_line = sys.argv[2]
            region = sys.argv[3] if len(sys.argv) > 3 else "euw1"
        else:
            print("❌ Error: game_name and tag_line are required")
            print("Usage: python -m src.data.lookup_account <game_name> <tag_line> [region]")
            sys.exit(1)
        
        # Validate input
        if not validate_input(game_name, tag_line):
            sys.exit(1)
        
        # Perform lookup
        lookup_service = LeagueAccountLookup(region)
        result = lookup_service.lookup_account(game_name, tag_line)
        
        if result:
            logger.info(f"Lookup completed successfully for {game_name}#{tag_line}")
        else:
            logger.warning(f"Lookup failed for {game_name}#{tag_line}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Lookup cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()