"""OBS overlay integration module for League of Legends data.

This module provides secure HTML overlay generation for OBS Studio integration,
with proper data sanitization and template management.
"""

import html
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import logging
from ..data.lookup_account import LeagueAccountLookup
from ..detection.client_detector import LeagueClientDetector


class OBSOverlayExporter:
    """Exports League data in OBS-friendly formats with secure transparent overlays.
    
    This class handles the generation of HTML overlays for OBS Studio with proper
    data sanitization, error handling, and template management.
    
    Attributes:
        output_dir (Path): Directory for output files
        logger (logging.Logger): Logger instance for this class
    """
    
    def __init__(self, output_dir: str = "obs_data") -> None:
        """Initialize the OBS overlay exporter.
        
        Args:
            output_dir: Directory to save overlay files (default: "obs_data")
        """
        self.output_dir = Path(output_dir)
        self.logger = logging.getLogger(__name__)
        self.ensure_output_directory()
    
    def ensure_output_directory(self) -> None:
        """Create output directory if it doesn't exist."""
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Output directory ensured: {self.output_dir}")
        except OSError as e:
            self.logger.error(f"Failed to create output directory {self.output_dir}: {e}")
            raise
    
    def export_player_data(self, game_name: str, tag_line: str, region: str = None) -> Dict[str, Any]:
        """Export complete player data for OBS overlay.
        
        Args:
            game_name: Player's game name (will be sanitized)
            tag_line: Player's tag line (will be sanitized)
            region: Region for lookup (auto-detects if None)
            
        Returns:
            Dictionary containing all player data, or error dict if failed
            
        Raises:
            ValueError: If input parameters are invalid
        """
        # Input validation and sanitization
        if not self._validate_input(game_name, tag_line, region):
            return {"error": "Invalid input parameters"}
        
        game_name = self._sanitize_input(game_name)
        tag_line = self._sanitize_input(tag_line)
        
        # Auto-detect region if not provided
        if region is None:
            from ..api.riot_api import RiotAPIClient
            from ..api.config import Config
            api_client = RiotAPIClient(Config())
            region = api_client.detect_account_region(game_name, tag_line)
            self.logger.info(f"Auto-detected region: {region}")
        
        # Perform lookup with error handling
        try:
            lookup_service = LeagueAccountLookup(region)
            result = lookup_service.lookup_account(game_name, tag_line)
            
            if not result or not isinstance(result, dict):
                self.logger.warning(f"Player not found: {game_name}#{tag_line}")
                return {"error": "Player not found"}
        except Exception as e:
            self.logger.error(f"Lookup failed for {game_name}#{tag_line}: {e}")
            return {"error": f"Lookup failed: {str(e)}"}
        
        # Safely extract summoner data
        summoner_data = result.get('summoner') if result else None
        
        # Format data for OBS with sanitized content
        obs_data = {
            "timestamp": datetime.now().isoformat(),
            "player": {
                "riot_id": f"{game_name}#{tag_line}",
                "summoner_name": self._sanitize_output(summoner_data.get('name', game_name) if summoner_data else game_name),
                "level": max(0, int(summoner_data.get('summonerLevel', 0)) if summoner_data else 0),
                "region": region.upper()
            },
            "ranked": self._format_ranked_for_obs(result.get('ranked', [])),
            "daily_stats": self._format_daily_stats_for_obs(result.get('daily_stats', {})),
            "recent_matches": self._format_matches_for_obs(result.get('daily_matches', []))
        }
        
        # Export to files
        self._save_json_data(obs_data)
        self._generate_overlay_files(obs_data)
        
        return obs_data
    
    def _validate_input(self, game_name: str, tag_line: str, region: str) -> bool:
        """Validate input parameters for security and correctness."""
        if not all([game_name, tag_line, region]):
            return False
            
        from ..api.config import Config
        config = Config()
        
        # Use configurable length validation
        if len(game_name) > config.max_game_name_length or len(tag_line) > config.max_tag_line_length:
            return False
            
        # Check for potential malicious content
        dangerous_chars = ['<', '>', '"', "'", '&', '\x00']
        if any(char in game_name + tag_line + region for char in dangerous_chars):
            return False
            
        return True
    
    def _sanitize_input(self, text: str) -> str:
        """Sanitize input text for safe processing."""
        if not isinstance(text, str):
            return str(text)
        return text.strip()[:50]  # Limit length and strip whitespace
    
    def _sanitize_output(self, text: Union[str, int, float]) -> str:
        """Sanitize output text for safe HTML inclusion."""
        if text is None:
            return ""
        return html.escape(str(text))
    
    def _format_ranked_for_obs(self, ranked_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Format ranked data for OBS display."""
        if not ranked_data:
            return {
                "has_rank": False,
                "rank": "Unranked",
                "tier": "UNRANKED",
                "division": "",
                "lp": 0,
                "wins": 0,
                "losses": 0,
                "winrate": 0
            }
        
        # Use first (highest/most relevant) ranked entry
        primary_rank = ranked_data[0]
        
        return {
            "has_rank": True,
            "rank": primary_rank['tier_rank'],
            "tier": primary_rank['tier'],
            "division": primary_rank['rank'],
            "lp": primary_rank['lp'],
            "wins": primary_rank['wins'],
            "losses": primary_rank['losses'],
            "winrate": primary_rank['winrate'],
            "total_games": primary_rank['total_games']
        }
    
    def _format_daily_stats_for_obs(self, daily_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Format daily statistics for OBS display."""
        return {
            "games_today": daily_stats.get('total_games', 0),
            "wins_today": daily_stats.get('wins', 0),
            "losses_today": daily_stats.get('losses', 0),
            "winrate_today": daily_stats.get('winrate', 0),
            "roles_played": daily_stats.get('roles_played', {}),
            "champions_played": daily_stats.get('champions_played', {}),
            "most_played_role": self._get_most_played_role(daily_stats.get('roles_played', {})),
            "best_champion": self._get_best_champion(daily_stats.get('champions_played', {}))
        }
    
    def _format_matches_for_obs(self, formatted_matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format recent matches for OBS display."""
        obs_matches = []
        for match in formatted_matches[:5]:  # Last 5 games for overlay
            obs_matches.append({
                "champion": match.get('champion', 'Unknown'),
                "role": match.get('role', 'Unknown'),
                "result": match.get('result', 'Unknown'),
                "win": match.get('win', False),
                "kda": match.get('kda', '0/0/0'),
                "kda_ratio": match.get('kda_ratio', 0),
                "duration": match.get('duration', '0:00'),
                "cs": match.get('cs', 0),
                "queue": match.get('queue', 'Unknown'),
                "time": match.get('time', '00:00 UTC')
            })
        
        return obs_matches
    
    def _get_most_played_role(self, roles: Dict[str, Any]) -> str:
        """Get the most played role today."""
        if not roles:
            return "None"
        return max(roles.keys(), key=lambda role: roles[role]['games'])
    
    def _get_best_champion(self, champions: Dict[str, Any]) -> str:
        """Get the best performing champion today."""
        if not champions:
            return "None"
        
        # Sort by winrate, then by games played
        best_champ = max(
            champions.keys(),
            key=lambda champ: (champions[champ]['winrate'], champions[champ]['games'])
        )
        return best_champ
    
    def _save_json_data(self, data: Dict[str, Any]) -> None:
        """Save data as JSON files for OBS with error handling."""
        json_files = {
            "player_data.json": data,
            "ranked_info.json": data.get("ranked", {}),
            "daily_stats.json": data.get("daily_stats", {}),
            "recent_matches.json": data.get("recent_matches", [])
        }
        
        for filename, file_data in json_files.items():
            try:
                file_path = self.output_dir / filename
                with file_path.open('w', encoding='utf-8') as f:
                    json.dump(file_data, f, indent=2, ensure_ascii=False)
                self.logger.debug(f"Saved JSON file: {filename}")
            except (OSError, json.JSONEncodeError) as e:
                self.logger.error(f"Failed to save {filename}: {e}")
                raise
    
    def _generate_overlay_files(self, data: Dict[str, Any]) -> None:
        """Generate HTML overlay files with transparent backgrounds."""
        try:
            # Generate individual overlays with numbered filenames
            self._create_rank_overlay(data["ranked"], data["player"])
            self._create_daily_stats_overlay(data["daily_stats"], data["player"])
            self._create_recent_matches_overlay(data["recent_matches"], data["player"])
            self._create_combined_overlay(data)
            self._create_accounts_overlay()
            
            self.logger.info("All overlay files generated successfully")
        except Exception as e:
            self.logger.error(f"Failed to generate overlay files: {e}")
            raise
    
    def _create_html_template(self, title: str, content: str, 
                            styles: str = "", scripts: str = "", 
                            container_class: str = "overlay-container") -> str:
        """Create a secure HTML template with sanitized content."""
        safe_title = self._sanitize_output(title)
        base_styles = """
            body {
                margin: 0;
                padding: 20px;
                font-family: 'Arial', sans-serif;
                background: transparent;
                color: white;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.8);
            }
            .overlay-container {
                background: rgba(0, 20, 40, 0.85);
                border: 2px solid #c89b3c;
                border-radius: 10px;
                padding: 15px;
                display: inline-block;
                backdrop-filter: blur(5px);
            }
        """
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{safe_title}</title>
    <style>
        {base_styles}
        {styles}
    </style>
</head>
<body>
    <div class="{container_class}">
        {content}
    </div>
    <script>
        // Auto-refresh functionality
        setTimeout(() => location.reload(), 30000);
        {scripts}
    </script>
</body>
</html>"""
    
    def _create_rank_overlay(self, ranked: Dict[str, Any], player: Dict[str, Any]) -> None:
        """Create rank-only overlay HTML."""
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            margin: 0;
            padding: 20px;
            font-family: 'Arial', sans-serif;
            background: transparent;
            color: white;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.8);
        }}
        .rank-container {{
            background: rgba(0, 20, 40, 0.85);
            border: 2px solid #c89b3c;
            border-radius: 10px;
            padding: 15px;
            display: inline-block;
            backdrop-filter: blur(5px);
        }}
        .player-name {{
            font-size: 18px;
            color: #c89b3c;
            margin-bottom: 10px;
            font-weight: bold;
        }}
        .rank-info {{
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .rank-details {{
            font-size: 14px;
            color: #cdbe91;
        }}
        .winrate {{
            color: {"#00ff00" if ranked.get("winrate", 0) >= 60 else "#ffff00" if ranked.get("winrate", 0) >= 50 else "#ff6666"};
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="rank-container">
        <div class="player-name">{player["riot_id"]}</div>
        <div class="rank-info">{ranked["rank"]}</div>
        <div class="rank-details">
            {ranked["lp"]} LP | Level {player["level"]}<br>
            <span class="winrate">{ranked["wins"]}W-{ranked["losses"]}L ({ranked["winrate"]}%)</span>
        </div>
    </div>
    
    <script>
        // Auto-refresh every 30 seconds
        setTimeout(() => location.reload(), 30000);
    </script>
</body>
</html>"""
        
        with open(os.path.join(self.output_dir, "01_rank_overlay.html"), "w", encoding="utf-8") as f:
            f.write(html_content)
    
    def _create_daily_stats_overlay(self, daily: Dict[str, Any], player: Dict[str, Any]):
        """Create daily stats overlay HTML."""
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            margin: 0;
            padding: 15px;
            font-family: 'Arial', sans-serif;
            background: transparent;
            color: white;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.8);
        }}
        .stats-container {{
            background: rgba(20, 40, 60, 0.85);
            border: 2px solid #0596aa;
            border-radius: 10px;
            padding: 15px;
            display: inline-block;
            backdrop-filter: blur(5px);
        }}
        .stats-title {{
            font-size: 16px;
            color: #0596aa;
            margin-bottom: 10px;
            font-weight: bold;
        }}
        .stats-line {{
            font-size: 14px;
            margin-bottom: 5px;
        }}
        .highlight {{
            color: #00ff88;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="stats-container">
        <div class="stats-title">Today's Performance</div>
        <div class="stats-line">Games: <span class="highlight">{daily["games_today"]}</span></div>
        <div class="stats-line">Record: <span class="highlight">{daily["wins_today"]}W-{daily["losses_today"]}L ({daily["winrate_today"]}%)</span></div>
        <div class="stats-line">Best Role: <span class="highlight">{daily["most_played_role"]}</span></div>
        <div class="stats-line">Best Champion: <span class="highlight">{daily["best_champion"]}</span></div>
    </div>
    
    <script>
        setTimeout(() => location.reload(), 30000);
    </script>
</body>
</html>"""
        
        with open(os.path.join(self.output_dir, "02_daily_stats_overlay.html"), "w", encoding="utf-8") as f:
            f.write(html_content)
    
    def _create_recent_matches_overlay(self, matches: List[Dict[str, Any]], player: Dict[str, Any]):
        """Create recent matches overlay HTML."""
        matches_html = ""
        for i, match in enumerate(matches[:3]):  # Show last 3 games
            result_color = "#00ff88" if match["win"] else "#ff6666"
            matches_html += f"""
            <div class="match" style="border-left: 4px solid {result_color};">
                <div class="match-info">
                    <span class="champion">{match["champion"]}</span> 
                    <span class="role">({match["role"]})</span>
                </div>
                <div class="match-stats">KDA: {match["kda"]} | {match["duration"]}</div>
            </div>"""
        
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            margin: 0;
            padding: 15px;
            font-family: 'Arial', sans-serif;
            background: transparent;
            color: white;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.8);
        }}
        .matches-container {{
            background: rgba(40, 20, 60, 0.85);
            border: 2px solid #8a2be2;
            border-radius: 10px;
            padding: 15px;
            display: inline-block;
            backdrop-filter: blur(5px);
            min-width: 250px;
        }}
        .matches-title {{
            font-size: 16px;
            color: #8a2be2;
            margin-bottom: 10px;
            font-weight: bold;
        }}
        .match {{
            margin-bottom: 8px;
            padding: 5px;
            background: rgba(0,0,0,0.3);
            border-radius: 5px;
            padding-left: 10px;
        }}
        .match-info {{
            font-size: 14px;
            font-weight: bold;
        }}
        .match-stats {{
            font-size: 12px;
            color: #cccccc;
        }}
        .champion {{
            color: #ffff88;
        }}
        .role {{
            color: #88ffff;
        }}
    </style>
</head>
<body>
    <div class="matches-container">
        <div class="matches-title">Recent Games</div>
        {matches_html}
    </div>
    
    <script>
        setTimeout(() => location.reload(), 30000);
    </script>
</body>
</html>"""
        
        with open(os.path.join(self.output_dir, "03_recent_matches_overlay.html"), "w", encoding="utf-8") as f:
            f.write(html_content)
    
    def _create_combined_overlay(self, data: Dict[str, Any]):
        """Create a combined overlay with all information including accounts."""
        from ..detection.client_detector import LeagueClientDetector
        
        # Get today's accounts for display using session manager
        from ..detection.streaming_session_manager import StreamingSessionManager
        session_manager = StreamingSessionManager()
        todays_accounts = session_manager.get_todays_accounts()
        
        detector = LeagueClientDetector()
        
        # Get current account for highlighting
        current_account = detector.detect_current_account()
        current_riot_id = current_account.get('riot_id') if current_account else None
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: 'Arial', sans-serif;
            background: transparent;
            color: white;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.8);
        }}
        .overlay-container {{
            display: flex;
            gap: 15px;
            padding: 20px;
            flex-wrap: wrap;
        }}
        .panel {{
            background: rgba(0, 20, 40, 0.95);
            border: 3px solid #c89b3c;
            border-radius: 10px;
            padding: 15px;
            backdrop-filter: blur(5px);
            min-width: 120px;
        }}
        .rank-panel {{ border-color: #c89b3c; }}
        .stats-panel {{ border-color: #0596aa; }}
        .matches-panel {{ border-color: #8a2be2; }}
        .accounts-panel {{ border-color: #ff6b35; }}
        .panel-title {{
            font-size: 16px;
            font-weight: bold;
            margin-bottom: 10px;
            color: #c89b3c;
        }}
        .rank-display {{
            font-size: 20px;
            font-weight: bold;
            margin-bottom: 5px;
            color: {("#888888" if data["ranked"]["rank"] == "Unranked" else "#ffffff")};
        }}
        .detail-line {{
            font-size: 12px;
            margin-bottom: 3px;
            color: #cdbe91;
        }}
        .stat-item {{
            font-size: 12px;
            margin-bottom: 3px;
        }}
        .match-item {{
            font-size: 11px;
            margin-bottom: 5px;
            padding: 3px;
            background: rgba(0,0,0,0.3);
            border-radius: 3px;
        }}
        .win {{ color: #00ff88; }}
        .loss {{ color: #ff6666; }}
        .highlight {{ color: #ffff88; font-weight: bold; }}
        .account-item {{
            font-size: 10px;
            margin-bottom: 2px;
            padding: 2px;
            background: rgba(0,0,0,0.2);
            border-radius: 2px;
        }}
        .current-account-item {{
            color: #00ff88;
            font-weight: bold;
        }}
        .account-name {{ color: #ff6b35; }}
        .account-region {{ color: #aaa; }}
    </style>
</head>
<body>
    <div class="overlay-container">
        <!-- Rank Panel -->
        <div class="panel rank-panel">
            <div class="panel-title">{data["player"]["riot_id"]}</div>
            <div class="rank-display">{data["ranked"]["rank"]}</div>
            <div class="detail-line">{data["ranked"]["lp"]} LP | Level {data["player"]["level"]}</div>
            <div class="detail-line">{data["ranked"]["wins"]}W-{data["ranked"]["losses"]}L ({data["ranked"]["winrate"]}%)</div>
            <div style="font-size: 10px; color: #666;">Updated: {data["timestamp"][:19]}</div>
        </div>
        
        <!-- Daily Stats Panel -->
        <div class="panel stats-panel">
            <div class="panel-title" style="color: #0596aa;">Today</div>
            <div class="stat-item">Games: <span class="highlight">{data["daily_stats"]["games_today"]}</span></div>
            <div class="stat-item">Record: <span class="highlight">{data["daily_stats"]["wins_today"]}W-{data["daily_stats"]["losses_today"]}L</span></div>
            <div class="stat-item">WR: <span class="highlight">{data["daily_stats"]["winrate_today"]}%</span></div>
            <div class="stat-item">Role: <span class="highlight">{data["daily_stats"]["most_played_role"]}</span></div>
        </div>
        
        <!-- Recent Matches Panel -->
        <div class="panel matches-panel">
            <div class="panel-title" style="color: #8a2be2;">Recent</div>
            {"".join([f'<div class="match-item"><span class="{"win" if match["win"] else "loss"}">{match["champion"]}</span> ({match["role"]}) {match["kda"]}</div>' for match in data["recent_matches"][:3]])}
        </div>
        
        <!-- Accounts Panel -->
        <div class="panel accounts-panel">
            <div class="panel-title" style="color: #ff6b35;">Today's Accounts</div>
            {self._generate_accounts_html_for_combined(todays_accounts, current_riot_id)}
        </div>
    </div>
    
    <script>
        // Multiple refresh mechanisms for reliable OBS updates
        
        // 1. Regular auto-refresh every 5 seconds
        setInterval(() => location.reload(), 5000);
        
        // 2. Check file modification time and refresh if changed
        let lastModified = null;
        
        async function checkForUpdates() {{
            try {{
                const response = await fetch(location.href, {{ method: 'HEAD' }});
                const modified = response.headers.get('Last-Modified');
                
                if (lastModified && modified && modified !== lastModified) {{
                    location.reload();
                }}
                lastModified = modified;
            }} catch (e) {{
                // Silently handle errors
            }}
        }}
        
        // Check for updates every 2 seconds
        setInterval(checkForUpdates, 2000);
        
        // 3. Refresh when window gains focus (OBS scene switch)
        window.addEventListener('focus', () => {{
            setTimeout(() => location.reload(), 100);
        }});
        
        // 4. Refresh on visibility change
        document.addEventListener('visibilitychange', () => {{
            if (!document.hidden) {{
                setTimeout(() => location.reload(), 100);
            }}
        }});
    </script>
</body>
</html>"""
        
        with open(os.path.join(self.output_dir, "04_combined_overlay.html"), "w", encoding="utf-8") as f:
            f.write(html_content)
    
    def _generate_accounts_html_for_combined(self, todays_accounts: list, current_riot_id: str) -> str:
        """Generate compact accounts HTML for combined overlay."""
        if not todays_accounts:
            return '<div class="account-item">No accounts today</div>'
        
        accounts_html = ""
        for account in todays_accounts[:4]:  # Show max 4 accounts to save space
            riot_id = account.get("riot_id", "Unknown")
            region = account.get("region", "unknown")
            
            is_current = (riot_id == current_riot_id)
            current_class = "current-account-item" if is_current else ""
            current_indicator = "👉 " if is_current else ""
            
            accounts_html += f'''<div class="account-item {current_class}">
                {current_indicator}<span class="account-name">{self._sanitize_output(riot_id)}</span> 
                <span class="account-region">({region.upper()})</span>
            </div>'''
        
        return accounts_html
    
    def _create_accounts_overlay(self) -> None:
        """Create accounts overlay showing all accounts used today."""
        # Get today's accounts using session manager
        from ..detection.streaming_session_manager import StreamingSessionManager
        from ..detection.client_detector import LeagueClientDetector
        
        session_manager = StreamingSessionManager()
        todays_accounts = session_manager.get_todays_accounts()
        
        # Get current account for highlighting
        detector = LeagueClientDetector()
        current_account = detector.detect_current_account()
        current_riot_id = current_account.get('riot_id') if current_account else None
        
        # Generate accounts HTML
        if todays_accounts:
            accounts_html = ""
            for i, account in enumerate(todays_accounts, 1):
                riot_id = account.get("riot_id", "Unknown")
                region = account.get("region", "unknown").upper()
                times_used = account.get("times_used", 0)
                last_seen_time = account.get('last_seen', '').split('T')[1][:8] if 'T' in account.get('last_seen', '') else "Unknown"
                
                # Highlight current account
                highlight_class = "current-account" if riot_id == current_riot_id else ""
                
                accounts_html += f"""
                <div class="account-item {highlight_class}">
                    <div class="account-name">{riot_id}</div>
                    <div class="account-details">{region} • Used {times_used}x • Last: {last_seen_time}</div>
                </div>"""
        else:
            accounts_html = '<div class="no-accounts">No accounts detected today</div>'
        
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            margin: 0;
            padding: 15px;
            font-family: 'Arial', sans-serif;
            background: transparent;
            color: white;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.8);
        }}
        .accounts-container {{
            background: rgba(0, 20, 40, 0.85);
            border: 2px solid #c89b3c;
            border-radius: 10px;
            padding: 15px;
            display: inline-block;
            backdrop-filter: blur(5px);
            min-width: 300px;
            max-width: 500px;
        }}
        .accounts-title {{
            font-size: 18px;
            color: #c89b3c;
            margin-bottom: 15px;
            font-weight: bold;
            text-align: center;
        }}
        .account-item {{
            padding: 8px 12px;
            margin: 5px 0;
            border-radius: 5px;
            background: rgba(255, 255, 255, 0.1);
            border-left: 3px solid #555;
        }}
        .account-item.current-account {{
            background: rgba(200, 155, 60, 0.2);
            border-left-color: #c89b3c;
        }}
        .account-name {{
            font-weight: bold;
            font-size: 14px;
            margin-bottom: 3px;
        }}
        .account-details {{
            font-size: 11px;
            color: #ccc;
        }}
        .no-accounts {{
            text-align: center;
            color: #888;
            font-style: italic;
            padding: 20px;
        }}
    </style>
</head>
<body>
    <div class="accounts-container">
        <div class="accounts-title">Today's Accounts ({len(todays_accounts)})</div>
        {accounts_html}
    </div>
    
    <script>
        setTimeout(() => location.reload(), 5000);
    </script>
</body>
</html>"""
        
        with open(os.path.join(self.output_dir, "05_accounts_overlay.html"), "w", encoding="utf-8") as f:
            f.write(html_content)


def detect_account_region(game_name: str, tag_line: str) -> str:
    """Detect the correct region for an account by trying different regions."""
    from ..api.riot_api import RiotAPIClient
    from ..api.config import Config, DEFAULT_REGIONS_TO_TRY
    
    config = Config()
    api_client = RiotAPIClient(config)
    
    # Check if user has configured a specific region first
    if config.region:
        try:
            print(f"🌍 Trying configured region: {config.region.upper()}")
            account = api_client.get_account_by_riot_id(game_name, tag_line)
            if account:
                print(f"🌍 Found account in configured region: {config.region.upper()}")
                return config.region
        except Exception:
            print(f"⚠️ Account not found in configured region {config.region.upper()}, trying other regions")
    
    # Use configurable regions list
    regions_to_try = DEFAULT_REGIONS_TO_TRY
    
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
    print("⚠️  Could not detect region, defaulting to NA1")
    return "na1"

def main():
    """Main function for dynamic OBS overlay export with account detection."""
    logging.basicConfig(level=logging.INFO)
    
    exporter = OBSOverlayExporter()
    detector = LeagueClientDetector()
    
    print("🔍 Detecting current League account...")
    
    # Try to detect current account from client
    account_info = detector.detect_current_account()
    
    if account_info and account_info.get('tag_line'):
        # Use detected account
        game_name = account_info['game_name']
        tag_line = account_info['tag_line']
        print(f"✅ Detected account: {account_info['riot_id']}")
        
        # Auto-detect region for this account
        region = detect_account_region(game_name, tag_line)
    else:
        # No fallback account - require client detection
        print("❌ Could not detect account - please start a League game first")
        return
    
    # Export data for detected account
    data = exporter.export_player_data(game_name, tag_line, region)
    
    print("✅ OBS overlay files generated!")
    print(f"📁 Files saved to: {exporter.output_dir}/")
    print("\n📋 Generated files:")
    print("- player_data.json (complete data)")
    print("- ranked_info.json (rank data only)")
    print("- daily_stats.json (daily stats only)")
    print("- recent_matches.json (recent matches only)")
    print("- 01_rank_overlay.html (rank display)")
    print("- 02_daily_stats_overlay.html (daily stats display)")
    print("- 03_recent_matches_overlay.html (recent matches display)")
    print("- 04_combined_overlay.html (all-in-one display)")
    print("- 05_accounts_overlay.html (today's accounts display)")
    
    print(f"\n🎥 To use in OBS:")
    print(f"1. Add Browser Source")
    print(f"2. Set URL to: file://{os.path.abspath(exporter.output_dir)}/04_combined_overlay.html")
    print(f"3. Set Width: 800, Height: 200")
    print(f"4. Enable 'Shutdown source when not visible'")
    print(f"5. Enable 'Refresh browser when scene becomes active'")


if __name__ == "__main__":
    main()