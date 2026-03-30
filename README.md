# IPL Match Predictor 2026 🏏

Advanced IPL match prediction engine powered by enhanced machine learning algorithms and real-time data aggregation. Predicts match outcomes by analyzing team form, player availability, venue conditions, and multiple other strategic factors.

## ✨ Latest Updates (2026)

### 🎯 Enhanced Prediction Model v2.0
- **Momentum Analysis**: Exponentially weighted recent match performance
- **Advanced Squad Strength**: Role-based composition analysis (batsmen, bowlers, all-rounders, key players, overseas)
- **Logistic Transformation**: Sigmoid function for realistic probability distribution
- **Dynamic Weighting**: Optimized factor weights based on predictive power
- **Context-Aware Analysis**: Match type, venue conditions, and time-of-day adjustments

### 🎨 Modern UI Redesign
- Sleek dark theme with vibrant gradients (orange, teal, purple)
- Animated backgrounds and smooth transitions
- Enhanced card designs with hover effects and glowing borders
- Responsive layout for all devices
- Custom scrollbar and improved typography

### 🔄 Updated API Integration
- Configurable IPL 2026 series ID with multiple fallback options
- Multi-source data aggregation (Cric API, FreeWebAPI, News API, GNews, TheSportsDB, ESPNcricinfo)
- Automatic fallback mechanism for reliable data fetching
- **python-espncricinfo library** integration ([outside-edge/python-espncricinfo](https://github.com/outside-edge/python-espncricinfo)) for live match data via Playwright/WebKit

## 🛠️ Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Playwright WebKit browser (required for python-espncricinfo live data)
playwright install webkit
```

## 🌐 API Endpoints

### ESPNcricinfo (python-espncricinfo library — Playwright/WebKit)

| Endpoint | Description |
|---|---|
| `GET /api/v2/espncricinfo/live[?date=YYYY-MM-DD]` | Live / recent match references for a given day |
| `GET /api/v2/espncricinfo/match/<series_id>/<match_id>` | Full match details (teams, players, innings, toss, result) |
| `GET /api/v2/espncricinfo/player/<player_id>` | Player profile (name, age, role, batting/bowling style) |

## 🚀 Features

- **Match Prediction**: AI-powered predictions with confidence levels (Very High/High/Medium/Low/Very Low)
- **Playing XI Selection**: Automatically selects optimal 11 players based on form, venue, and injuries
- **Real-time Data**: Live points table, injury updates, and team news
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
