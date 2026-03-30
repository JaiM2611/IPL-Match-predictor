# IPL Match Predictor 2026 🏏

Advanced IPL match prediction engine powered by enhanced machine learning algorithms and real-time data aggregation. Predicts match outcomes by analyzing team form, player availability, venue conditions, and multiple other strategic factors.

## ✨ Latest Updates (2026)

### 🎯 Enhanced Prediction Model v2.0
- **Momentum Analysis**: Exponentially weighted recent match performance
- **Advanced Squad Strength**: Role-based composition analysis (batsmen, bowlers, all-rounders, key players, overseas)
- **Logistic Transformation**: Sigmoid function for realistic probability distribution
- **Dynamic Weighting**: Optimized factor weights based on predictive power
- **Context-Aware Analysis**: Match type, venue conditions, and time-of-day adjustments

### 🔄 Real-Time Data Integration (NEW)
- **Live Scores** — Current match scorecard updated every 60 seconds via CricAPI / Cricbuzz
- **Points Table** — Auto-refreshed standings with NRR and form guide (every 5 min)
- **Orange Cap** — Live IPL 2026 top run-scorer leaderboard (every 10 min)
- **Purple Cap** — Live IPL 2026 top wicket-taker leaderboard (every 10 min)
- **Injury Updates** — Latest player availability news from News API / GNews
- **Multi-source fallback**: CricAPI → RapidAPI/Cricbuzz → News API/GNews → static JSON
- **In-memory caching** with per-source TTLs to avoid excessive API calls

### 🎨 Modern UI Redesign
- Sleek dark theme with vibrant gradients (orange, teal, purple)
- Animated backgrounds and smooth transitions
- Enhanced card designs with hover effects and glowing borders
- Responsive layout for all devices
- Custom scrollbar and improved typography

## 🛠️ Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Playwright WebKit browser (required for python-espncricinfo live data)
playwright install webkit
```

## 🔑 Real-Time API Configuration

Set the following environment variables to enable live data. The app gracefully falls back to curated static data when keys are absent.

| Variable | Source | Used For |
|---|---|---|
| `CRIC_API_KEY` | [cricapi.com](https://cricapi.com/) | Standings, stats, live scores |
| `RAPIDAPI_KEY` | [rapidapi.com — Cricbuzz](https://rapidapi.com/cricbuzz/api/cricbuzz-cricket) | Standings, cap stats, live scores |
| `NEWS_API_KEY` | [newsapi.org](https://newsapi.org/) | Injury / team news |
| `GNEWS_API_KEY` | [gnews.io](https://gnews.io/) | Injury / team news (fallback) |
| `IPL_2026_SERIES_ID_CRICAPI` | — | Override CricAPI series ID |
| `IPL_2026_SERIES_ID_CRICBUZZ` | — | Override Cricbuzz series ID |

```bash
export CRIC_API_KEY="your-cricapi-key"
export RAPIDAPI_KEY="your-rapidapi-key"
export NEWS_API_KEY="your-newsapi-key"
export GNEWS_API_KEY="your-gnews-key"
```

## 🌐 API Endpoints

### Core Prediction

| Endpoint | Method | Description |
|---|---|---|
| `GET /api/teams` | GET | All IPL 2026 teams |
| `GET /api/venues` | GET | All IPL venues |
| `GET /api/squad/<team>` | GET | Team squad & player details |
| `GET /api/h2h/<team1>/<team2>` | GET | Head-to-head record |
| `POST /api/predict` | POST | Generate match prediction |

### Real-Time Data

| Endpoint | Method | Description | Refresh |
|---|---|---|---|
| `GET /api/v2/standings` | GET | IPL 2026 points table | 5 min |
| `GET /api/v2/injuries` | GET | Player injury updates | 5 min |
| `GET /api/orange-cap` | GET | Top run-scorers leaderboard | 10 min |
| `GET /api/purple-cap` | GET | Top wicket-takers leaderboard | 10 min |
| `GET /api/live-matches` | GET | Live / recent match scores | 1 min |

### ESPNcricinfo (python-espncricinfo library — Playwright/WebKit)

| Endpoint | Description |
|---|---|
| `GET /api/v2/espncricinfo/live[?date=YYYY-MM-DD]` | Live / recent match references for a given day |
| `GET /api/v2/espncricinfo/match/<series_id>/<match_id>` | Full match details (teams, players, innings, toss, result) |
| `GET /api/v2/espncricinfo/player/<player_id>` | Player profile (name, age, role, batting/bowling style) |

## 🚀 Features

- **Match Prediction**: AI-powered predictions with confidence levels (Very High/High/Medium/Low/Very Low)
- **Playing XI Selection**: Automatically selects optimal 11 players based on form, venue, and injuries
- **Live Scores**: Real-time match scorecard with per-over updates
- **Orange & Purple Cap**: Live leaderboards for top run-scorers and wicket-takers
- **Real-time Points Table**: Auto-refreshing standings with NRR and form
- **Injury Tracker**: Latest player availability news from multiple news sources
- **Multi-Factor Analysis**: Considers 9+ factors including:
  - Recent form & win rate (35 points)
  - Momentum analysis (15 points)
  - Head-to-head record (15 points)
  - Home advantage (20 points)
  - Toss impact & dew factor (12 points)
  - Match type pressure (10 points)
  - Venue suitability (10 points)
  - Squad strength & availability (multiplier)
  - Time of day conditions

## Frontend Screenshots

### Predict Tab
![Predict Tab](screenshots/predictor-tab.png)

### Points Table Tab
![Points Table Tab](screenshots/points-table-tab.png)

### Injury Updates Tab
![Injury Updates Tab](screenshots/injuries-tab.png)
