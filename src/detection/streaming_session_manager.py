"""Streaming Session Manager for League of Legends Overlay.

This module manages multiple accounts during streaming sessions, providing
account switching and session tracking functionality.
"""

import json
import os
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import logging
from .client_detector import LeagueClientDetector

# Fix Windows console encoding for Unicode characters
if sys.platform == "win32":
    import locale
    import codecs
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
# from ..overlay.obs_overlay import OBSOverlayExporter


class StreamingSessionManager:
    """Manages multiple League accounts during streaming sessions."""
    
    def __init__(self, session_file: str = "streaming_session.json"):
        """Initialize the streaming session manager.
        
        Args:
            session_file: Path to save session data
        """
        from ..api.config import Config
        
        self.config = Config()
        self.session_file = Path(session_file)
        self.logger = logging.getLogger(__name__)
        self.detector = LeagueClientDetector()
        # self.exporter = OBSOverlayExporter()
        self.session_data = self.load_session()
        
    def load_session(self) -> Dict[str, Any]:
        """Load existing session data or create new session."""
        if self.session_file.exists():
            try:
                with open(self.session_file, 'r') as f:
                    data = json.load(f)
                    self.logger.info(f"Loaded existing session with {len(data.get('accounts', []))} accounts")
                    return data
            except (json.JSONDecodeError, KeyError) as e:
                self.logger.warning(f"Could not load session file: {e}")
        
        # Create new session
        new_session = {
            "created": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "accounts": [],
            "current_account": None
        }
        self.save_session(new_session)
        self.logger.info("Created new streaming session")
        return new_session
    
    def save_session(self, data: Optional[Dict[str, Any]] = None) -> None:
        """Save session data to file."""
        if data is None:
            data = self.session_data
            
        data["last_updated"] = datetime.now().isoformat()
        
        try:
            with open(self.session_file, 'w') as f:
                json.dump(data, f, indent=2)
            self.logger.debug("Session data saved")
        except Exception as e:
            self.logger.error(f"Failed to save session: {e}")
    
    def detect_and_add_account(self) -> Optional[Dict[str, str]]:
        """Detect current account and add to session if new."""
        account_info = self.detector.detect_current_account()
        
        if account_info and account_info.get('tag_line'):
            self.add_account_to_session(account_info)
            return account_info
        
        return None
    
    def detect_account_region(self, game_name: str, tag_line: str) -> str:
        """Detect the correct region for an account by trying different regions.
        
        Args:
            game_name: Player's game name
            tag_line: Player's tag line
            
        Returns:
            The region where the account was found, defaults to "na1"
        """
        from ..api.config import DEFAULT_REGIONS_TO_TRY
        
        # Use configurable regions list
        regions_to_try = DEFAULT_REGIONS_TO_TRY
        
        for region in regions_to_try:
            try:
                from ..api.riot_api import RiotAPIClient
                from ..api.config import Config
                
                config = Config()
                api_client = RiotAPIClient(config)
                
                # Try to get account info from this region
                account = api_client.get_account_by_riot_id(game_name, tag_line)
                if account:
                    self.logger.info(f"Found account {game_name}#{tag_line} in region: {region}")
                    return region
                    
            except Exception:
                continue
        
        # Default to NA1 if not found
        self.logger.warning(f"Could not detect region for {game_name}#{tag_line}, defaulting to na1")
        return "na1"

    def add_account_to_session(self, account_info: Dict[str, str], region: str = None) -> None:
        """Add account to current session.
        
        Args:
            account_info: Account information from detector
            region: API region for the account (will auto-detect if None)
        """
        # Auto-detect region if not provided
        if region is None:
            region = self.detect_account_region(account_info["game_name"], account_info["tag_line"])
        
        account_entry = {
            "game_name": account_info["game_name"],
            "tag_line": account_info["tag_line"],
            "riot_id": account_info["riot_id"],
            "region": region,
            "first_seen": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
            "times_used": 1
        }
        
        # Check if account already exists
        for existing in self.session_data["accounts"]:
            if existing["riot_id"] == account_info["riot_id"]:
                existing["last_seen"] = datetime.now().isoformat()
                existing["times_used"] += 1
                self.logger.info(f"Updated existing account: {account_info['riot_id']}")
                self.save_session()
                return
        
        # Add new account
        self.session_data["accounts"].append(account_entry)
        self.session_data["current_account"] = account_entry
        self.logger.info(f"Added new account to session: {account_info['riot_id']}")
        self.save_session()
    
    def get_session_accounts(self) -> List[Dict[str, Any]]:
        """Get all accounts from current session."""
        return self.session_data.get("accounts", [])
    
    def get_todays_accounts(self) -> List[Dict[str, Any]]:
        """Get all accounts used today (across all sessions).
        
        Returns:
            List of accounts with activity today
        """
        from datetime import date
        today = date.today().isoformat()
        
        todays_accounts = []
        for account in self.session_data.get("accounts", []):
            # Check if account was seen today
            last_seen = account.get("last_seen", "")
            first_seen = account.get("first_seen", "")
            
            if (last_seen.startswith(today) or first_seen.startswith(today)):
                todays_accounts.append(account)
        
        # Sort by most recently used
        todays_accounts.sort(key=lambda x: x.get("last_seen", ""), reverse=True)
        return todays_accounts
    
    def set_current_account(self, riot_id: str) -> bool:
        """Set the current active account by Riot ID.
        
        Args:
            riot_id: The Riot ID (e.g., "Complete#Tech")
            
        Returns:
            True if account found and set, False otherwise
        """
        for account in self.session_data["accounts"]:
            if account["riot_id"] == riot_id:
                self.session_data["current_account"] = account
                account["last_seen"] = datetime.now().isoformat()
                self.save_session()
                self.logger.info(f"Switched to account: {riot_id}")
                return True
        
        self.logger.warning(f"Account not found in session: {riot_id}")
        return False
    
    def get_current_account(self) -> Optional[Dict[str, str]]:
        """Get the current active account from client detection only.
        
        Returns:
            Dictionary with game_name, tag_line, and region, or None if no account detected
        """
        # Try to detect current account first
        detected = self.detect_and_add_account()
        if detected:
            return {
                "game_name": detected["game_name"],
                "tag_line": detected["tag_line"],
                "region": self.session_data.get("current_account", {}).get("region", "euw1")
            }
        
        # Use manually set current account if available
        current = self.session_data.get("current_account")
        if current:
            return {
                "game_name": current["game_name"],
                "tag_line": current["tag_line"],
                "region": current.get("region", "euw1")
            }
        
        # No account available
        return None
    
    def generate_overlay_for_current_account(self) -> Dict[str, Any]:
        """Generate OBS overlay for the current account."""
        account = self.get_current_account()
        
        if not account:
            return {"error": "No account detected - start a League game to detect account"}
        
        # Import here to avoid circular imports
        from ..overlay.obs_overlay import OBSOverlayExporter
        import logging
        
        # Temporarily silence logging for overlay generation
        overlay_logger = logging.getLogger('src.overlay')
        original_level = overlay_logger.level
        overlay_logger.setLevel(logging.CRITICAL)
        
        # Also silence the lookup account output
        lookup_logger = logging.getLogger('src.data')
        lookup_original_level = lookup_logger.level
        lookup_logger.setLevel(logging.CRITICAL)
        
        # Temporarily suppress print statements during overlay generation
        import sys
        from io import StringIO
        
        original_stdout = sys.stdout
        sys.stdout = StringIO()
        
        try:
            exporter = OBSOverlayExporter()
            data = exporter.export_player_data(
                account["game_name"],
                account["tag_line"],
                account["region"]
            )
            return data
        finally:
            # Restore stdout and logging levels
            sys.stdout = original_stdout
            overlay_logger.setLevel(original_level)
            lookup_logger.setLevel(lookup_original_level)
    
    def print_session_status(self) -> None:
        """Print current session status."""
        print("\n" + "="*60)
        print("STREAMING SESSION STATUS")
        print("="*60)
        
        # Show today's accounts
        todays_accounts = self.get_todays_accounts()
        if todays_accounts:
            print(f"📅 Today's Accounts ({len(todays_accounts)}):")
            for i, account in enumerate(todays_accounts, 1):
                current_marker = "👉 " if account == self.session_data.get("current_account") else "   "
                last_seen_time = account['last_seen'].split('T')[1][:8] if 'T' in account['last_seen'] else "Unknown"
                print(f"{current_marker}{i}. {account['riot_id']} ({account['region']}) - Last used: {last_seen_time}")
        else:
            print("📅 No accounts used today")
        
        # Show current session accounts if different from today's
        session_accounts = self.get_session_accounts()
        if len(session_accounts) != len(todays_accounts):
            print(f"\n📋 This Session ({len(session_accounts)}):")
            for i, account in enumerate(session_accounts, 1):
                current_marker = "👉 " if account == self.session_data.get("current_account") else "   "
                print(f"{current_marker}{i}. {account['riot_id']} - Used {account['times_used']} times")
        
        current = self.get_current_account()
        if current:
            print(f"\n🎯 Current Account: {current['game_name']}#{current['tag_line']} ({current['region']})")
        else:
            print(f"\n🎯 Current Account: None detected - start a League game")
        
        # Test live detection
        detected = self.detector.detect_current_account()
        if detected:
            print(f"🟢 Live Detection: {detected['riot_id']} (Active)")
        else:
            print("🔴 Live Detection: No active game detected")
        
        print("="*60)


def main():
    """Automatic session management with real-time monitoring."""
    import time
    import logging
    
    # Configure logging to suppress all messages
    logging.basicConfig(level=logging.CRITICAL)
    
    # Specifically silence the noisy loggers
    logging.getLogger('src.detection.client_detector').setLevel(logging.CRITICAL)
    logging.getLogger('src.api.riot_api').setLevel(logging.CRITICAL)
    logging.getLogger('src.data').setLevel(logging.CRITICAL)
    logging.getLogger('src.overlay').setLevel(logging.CRITICAL)
    
    manager = StreamingSessionManager()
    last_detected_account = None
    last_account_refresh = 0
    last_overlay_update = 0
    game_was_active = False
    
    # Use configurable intervals
    game_check_interval = manager.config.game_check_interval
    account_refresh_interval = manager.config.account_refresh_interval
    overlay_update_interval = manager.config.overlay_update_interval
    
    print("🎮 League Account Monitor Started")
    print(f"📡 Checking for League games every {game_check_interval}s")
    print(f"🔄 Refreshing account data every {account_refresh_interval}s when idle")
    print(f"📺 Updating overlay every {overlay_update_interval}s during games")
    print("⏹️  Press Ctrl+C to stop")
    print("⭕ Waiting for League game to start...")
    
    try:
        while True:
            # Check for active account
            detected = manager.detect_and_add_account()
            current_time = time.time()
            
            if detected:
                # Game is active
                if not game_was_active:
                    print(f"🟢 Game detected: {detected['riot_id']}")
                    game_was_active = True
                
                # Update current account if it changed
                if last_detected_account != detected['riot_id']:
                    print(f"🔄 Account switched: {detected['riot_id']}")
                    last_detected_account = detected['riot_id']
                    # Immediately update overlay on account switch
                    manager.generate_overlay_for_current_account()
                    last_overlay_update = current_time
                
                # Update overlay at regular intervals during game
                elif current_time - last_overlay_update >= overlay_update_interval:
                    manager.generate_overlay_for_current_account()
                    last_overlay_update = current_time
                    
            else:
                # No game detected
                if game_was_active:
                    # Game just ended - immediately refresh account data
                    print("🔴 Game ended - refreshing data...", end=" ")
                    data = manager.generate_overlay_for_current_account()
                    if "error" not in data:
                        print("✅")
                    else:
                        print(f"❌ {data['error']}")
                    
                    last_account_refresh = current_time
                    game_was_active = False
                    
                elif current_time - last_account_refresh > account_refresh_interval:
                    # Refresh account data at configured interval when not in game
                    print("🔄 Refreshing account data...", end=" ")
                    data = manager.generate_overlay_for_current_account()
                    if "error" not in data:
                        print("✅")
                    else:
                        print(f"❌ {data['error']}")
                    last_account_refresh = current_time
                
                # Only show status periodically, not every second
                if not game_was_active and int(current_time) % 30 == 0:  # Every 30 seconds
                    print("⭕ Waiting for League game to start...", end="\r")
            
            time.sleep(game_check_interval)  # Use configurable check interval
            
    except KeyboardInterrupt:
        print("\n\n👋 Monitor stopped")
        # Generate final account refresh
        print("🔄 Final account data refresh...")
        data = manager.generate_overlay_for_current_account()
        if "error" not in data:
            print("✅ Final refresh complete!")
        else:
            print(f"❌ Final refresh failed: {data['error']}")


if __name__ == "__main__":
    main()