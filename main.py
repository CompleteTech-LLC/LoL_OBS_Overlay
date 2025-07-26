#!/usr/bin/env python3
"""League of Legends API Client - Main Entry Point.

This is the main entry point for the League of Legends API client.
It provides a unified interface for all major functionality including:
- Account lookups
- Ranked information retrieval  
- Match history analysis
- OBS overlay generation
- Live client detection
- Streaming session management

Usage:
    python main.py lookup <game_name> <tag_line> [region]
    python main.py overlay <game_name> <tag_line> [region]
    python main.py monitor
    python main.py detect
"""

import sys
import logging
from pathlib import Path

# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.api.config import setup_logging
from src.data.lookup_account import LeagueAccountLookup
from src.overlay.obs_overlay import OBSOverlayExporter
from src.detection.client_detector import LeagueClientDetector
from src.detection.streaming_session_manager import StreamingSessionManager


def detect_account_region(game_name: str, tag_line: str) -> str:
    """Detect the correct region for an account by trying different regions."""
    from src.api.riot_api import RiotAPIClient
    from src.api.config import Config, DEFAULT_REGIONS_TO_TRY
    
    # Use configurable regions list
    regions_to_try = DEFAULT_REGIONS_TO_TRY
    
    config = Config()
    api_client = RiotAPIClient(config)
    
    for region in regions_to_try:
        try:
            # Try to get account info from this region
            account = api_client.get_account_by_riot_id(game_name, tag_line)
            if account:
                print(f"🌍 Found account in region: {region.upper()}")
                return region
        except Exception:
            continue
    
    # Default to NA1 if not found
    print("⚠️ Could not detect region, defaulting to NA1")
    return "na1"


def show_help():
    """Display help information."""
    print("""
League of Legends API Client v1.0.0

USAGE:
    python main.py <command> [arguments]

COMMANDS:
    lookup <game_name> <tag_line> [region]
        Look up a player's account, ranked info, and today's matches
        Example: python main.py lookup CoachRogue2 Fill euw1
    
    overlay <game_name> <tag_line> [region]  
        Generate OBS overlay files for a player
        Example: python main.py overlay CoachRogue2 Fill euw1
    
    monitor
        Start real-time account monitoring for streaming
        Automatically detects account switches and updates overlays
    
    detect
        Test League client detection and show current active account
    
    help
        Show this help message

SETUP:
    1. Create a .env file in the project root
    2. Add your Riot API key: RIOT_API_KEY=your_key_here
    3. Run any command to get started!

EXAMPLES:
    # Look up a specific player
    python main.py lookup "Faker" "T1" kr
    
    # Generate overlay for current detected account
    python main.py overlay auto
    
    # Start monitoring mode for streaming
    python main.py monitor
""")


def cmd_lookup(args):
    """Handle lookup command."""
    if len(args) < 2:
        print("❌ Error: lookup requires game_name and tag_line")
        print("Usage: python main.py lookup <game_name> <tag_line> [region]")
        return False
    
    game_name = args[0]
    tag_line = args[1]  
    region = args[2] if len(args) > 2 else detect_account_region(game_name, tag_line)
    
    print(f"🔍 Looking up player: {game_name}#{tag_line} in {region.upper()}")
    
    try:
        lookup_service = LeagueAccountLookup(region)
        result = lookup_service.lookup_account(game_name, tag_line)
        return result is not None
    except Exception as e:
        print(f"❌ Lookup failed: {e}")
        return False


def cmd_overlay(args):
    """Handle overlay command."""
    if len(args) >= 1 and args[0].lower() == "auto":
        # Auto-detect current account
        print("🔍 Auto-detecting current League account...")
        detector = LeagueClientDetector()
        account_info = detector.detect_current_account()
        
        if account_info and account_info.get('tag_line'):
            game_name = account_info['game_name']
            tag_line = account_info['tag_line']
            # Auto-detect region for this account
            region = detect_account_region(game_name, tag_line)
            print(f"✅ Detected account: {account_info['riot_id']} in {region.upper()}")
        else:
            print("❌ Could not detect account - please start a League game first")
            return False
    else:
        if len(args) < 2:
            print("❌ Error: overlay requires game_name and tag_line (or 'auto')")
            print("Usage: python main.py overlay <game_name> <tag_line> [region]")
            print("       python main.py overlay auto")
            return False
        
        game_name = args[0]
        tag_line = args[1]
        region = args[2] if len(args) > 2 else detect_account_region(game_name, tag_line)
    
    print(f"🎥 Generating OBS overlay for: {game_name}#{tag_line} in {region.upper()}")
    
    try:
        exporter = OBSOverlayExporter()
        data = exporter.export_player_data(game_name, tag_line, region)
        
        if "error" in data:
            print(f"❌ Overlay generation failed: {data['error']}")
            return False
        
        abs_path = Path(exporter.output_dir).resolve()
        print(f"✅ OBS overlay files generated successfully!")
        print(f"📁 Files saved to: {abs_path}")
        print(f"\n🎥 To use in OBS Studio:")
        print(f"   1. Add Browser Source")
        print(f"   2. Set URL to: file://{abs_path}/04_combined_overlay.html")
        print(f"   3. Set Width: 800, Height: 200")
        print(f"   4. Enable 'Shutdown source when not visible'")
        print(f"   5. Enable 'Refresh browser when scene becomes active'")
        return True
    except Exception as e:
        print(f"❌ Overlay generation failed: {e}")
        return False


def cmd_monitor(args):
    """Handle monitor command."""
    try:
        # Import and call the main monitoring function
        from src.detection.streaming_session_manager import main as monitor_main
        monitor_main()
        return True
    except KeyboardInterrupt:
        print("\n👋 Monitor stopped by user")
        return True
    except Exception as e:
        print(f"❌ Monitor failed: {e}")
        return False


def cmd_detect(args):
    """Handle detect command."""
    print("🔍 Testing League client detection...")
    
    try:
        detector = LeagueClientDetector()
        
        # Test connection
        connection_test = detector.test_live_client_connection()
        
        if connection_test['error']:
            print(f"❌ Connection failed: {connection_test['error']}")
            print("💡 Make sure League of Legends is running and you're in a game")
            return False
        
        if connection_test['live_client_available']:
            print("✅ Live Client API is available!")
            
            account_info = detector.detect_current_account()
            if account_info:
                print(f"🎯 Current account: {account_info['riot_id']}")
                if account_info.get('tag_line'):
                    print(f"   Game Name: {account_info['game_name']}")
                    print(f"   Tag Line: {account_info['tag_line']}")
            else:
                print("⚠️ Could not extract account information")
        else:
            print("❌ Live Client API not available")
            print("💡 Start a League of Legends game to enable detection")
            
        return True
    except Exception as e:
        print(f"❌ Detection failed: {e}")
        return False


def main():
    """Main entry point."""
    # Setup logging
    setup_logging(level='WARNING')  # Reduce noise for CLI usage
    
    # Parse command line arguments
    if len(sys.argv) < 2:
        show_help()
        sys.exit(0)
    
    command = sys.argv[1].lower()
    args = sys.argv[2:]
    
    # Route to appropriate command
    success = False
    
    if command in ['help', '-h', '--help']:
        show_help()
        success = True
    elif command == 'lookup':
        success = cmd_lookup(args)
    elif command == 'overlay':
        success = cmd_overlay(args)
    elif command == 'monitor':
        success = cmd_monitor(args)
    elif command == 'detect':
        success = cmd_detect(args)
    else:
        print(f"❌ Unknown command: {command}")
        print("Use 'python main.py help' for usage information")
        success = False
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()