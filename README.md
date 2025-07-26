# League of Legends API Client

A real-time League of Legends account monitoring tool that automatically generates OBS overlays for streamers. Detects account switches, tracks ranked data, and provides live-updating overlays perfect for streaming.

## ✨ Key Features

- **🎮 Real-Time Monitoring**: Automatically detects your current League account during games
- **🎥 Live OBS Overlays**: Auto-updating overlays with rank, stats, and match history
- **🔄 Account Switching**: Seamlessly handles multiple accounts during streaming
- **📊 Live Stats**: Rank, daily performance, recent matches, and session tracking
- **⚡ Instant Updates**: Overlays refresh every 5 seconds with aggressive auto-refresh
- **🛡️ Robust & Secure**: Rate limiting, error handling, and secure API management

## 📁 Project Structure

```
league_of_legends_api/
├── main.py              # Main CLI entry point
├── src/                 # Source code package
│   ├── api/            # Riot Games API integration
│   │   ├── config.py   # Configuration and constants
│   │   └── riot_api.py # API client with error handling
│   ├── data/           # Data processing and retrieval
│   │   ├── lookup_account.py    # Account lookup service
│   │   ├── match_history.py     # Match history processing
│   │   └── ranked_info.py       # Ranked information retrieval
│   ├── detection/      # Live client integration
│   │   ├── client_detector.py          # League client detection
│   │   └── streaming_session_manager.py # Session management
│   ├── overlay/        # OBS Studio integration
│   │   ├── obs_overlay.py      # Overlay generation
│   │   └── generate_overlay.py # Overlay CLI tool
│   └── utils/          # Utility functions
│       └── formatters.py       # Output formatting
├── obs_data/           # Generated overlay files (auto-created)
├── requirements.txt    # Python dependencies
├── .env               # Environment variables (create this)
└── README.md          # This file
```

## ⚡ Quick Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Get Your API Key
1. Visit [Riot Developer Portal](https://developer.riotgames.com/)
2. Create account and generate API key
3. Copy `.env.example` to `.env` and add your key:
```bash
cp .env.example .env
# Edit .env: RIOT_API_KEY=your_actual_api_key_here
```

### 3. Start Monitoring
```bash
python main.py monitor
```

**That's it!** Start a League game and the tool will automatically:
- ✅ Detect your account
- ✅ Generate OBS overlays 
- ✅ Update every 5 seconds
- ✅ Handle account switches

## 🎥 OBS Setup

1. **Start monitoring**: `python main.py monitor`
2. **Add Browser Source** in OBS
3. **Set URL**: `file:///YOUR_PATH/obs_data/04_combined_overlay.html`
4. **Dimensions**: Width 800, Height 200
5. **Enable**: "Refresh browser when scene becomes active"

## 🔧 Configuration

You can customize monitoring behavior by editing your `.env` file:

```bash
# Monitoring Intervals
GAME_CHECK_INTERVAL=1          # How often to check for active games (seconds)
ACCOUNT_REFRESH_INTERVAL=60    # How often to refresh data when idle (seconds)  
OVERLAY_UPDATE_INTERVAL=5      # How often to update overlays during games (seconds)

# API Settings
RIOT_API_KEY=your_key_here
RATE_LIMIT_DELAY=0.1          # Delay between API requests

# Other Settings
SESSION_TIMEOUT=30            # HTTP request timeout
CURRENT_SEASON=2025          # Display season year
```

## 🌍 Supported Regions

- **NA1**: North America
- **EUW1**: Europe West  
- **EUN1**: Europe Nordic & East
- **KR**: Korea
- **JP1**: Japan
- **BR1**: Brazil
- **LAN/LAS**: Latin America
- **OC1**: Oceania
- **RU**: Russia
- **TR1**: Turkey

## 📋 How It Works

1. **Start monitoring**: `python main.py monitor`
2. **Launch League**: The tool detects when you start a game
3. **Auto-detection**: Identifies your current account from the live client
4. **Overlay generation**: Creates/updates HTML overlays with your stats
5. **Live updates**: Refreshes data every 5 seconds during games
6. **Account switching**: Seamlessly handles multiple accounts

## 🎮 Overlay Features

The generated overlays include:
- **🏆 Current rank and LP**
- **📊 Today's game statistics** 
- **🎯 Recent match history**
- **👥 Session account tracking**
- **⚡ Live updates every 5 seconds**
- **🎨 Professional League-themed design**

## 📄 License

This project is for educational and personal use. Please respect Riot Games' API Terms of Service and rate limits.

---

**⚠️ Disclaimer**: This tool is not affiliated with Riot Games. League of Legends is a trademark of Riot Games, Inc.
