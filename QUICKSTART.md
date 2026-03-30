# Quick Start Guide - IPL Match Predictor

## Prerequisites
- Python 3.12+ installed
- pip package manager

## Installation

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

## Running the Application

### Development Server
```bash
# From the project root directory
python -m backend.app
```

The application will start on `http://localhost:5000`

### Production Server
```bash
# Using gunicorn (recommended for production)
gunicorn backend.app:app --bind 0.0.0.0:5000
```

## Testing

### Run Weather Integration Tests
```bash
python test_weather_integration.py
```

Expected output: All 5 tests should pass ✅

### Test API Endpoints
Start the server first, then test endpoints:

```bash
# Health check
curl http://localhost:5000/api/health

# Get all teams
curl http://localhost:5000/api/teams

# Get venues
curl http://localhost:5000/api/venues

# Make a prediction
curl -X POST http://localhost:5000/api/predict \
  -H "Content-Type: application/json" \
  -d '{
    "team1": "MI",
    "team2": "CSK",
    "venue": "Wankhede Stadium",
    "match_type": "league",
    "time_of_day": "night",
    "toss_winner": "MI",
    "toss_decision": "field"
  }'
```

## Environment Variables (Optional)

Create a `.env` file in the backend directory with API keys:

```bash
CRIC_API_KEY=your-cricapi-key
RAPIDAPI_KEY=your-rapidapi-key
NEWS_API_KEY=your-newsapi-key
GNEWS_API_KEY=your-gnews-key
```

**Note:** The application works without API keys and falls back to static data.

## Frontend

Access the web interface at: `http://localhost:5000/`

Features available:
- ⚡ Match Predictor
- 🔴 Live Scores
- 📊 Points Table
- 🟠 Orange Cap Leaders
- 🟣 Purple Cap Leaders
- 🏥 Injury Updates

## Troubleshooting

### Port 5000 already in use
```bash
# Kill existing process
pkill -f "python -m backend.app"

# Or use a different port
PORT=8080 python -m backend.app
```

### Module not found errors
```bash
# Make sure you're in the project root directory
cd /path/to/IPL-Match-predictor

# Reinstall dependencies
pip install -r requirements.txt
```

### Import errors
```bash
# Verify Python path
python -c "import sys; print(sys.path)"

# Run from project root
python -m backend.app
```

## Directory Structure

```
IPL-Match-predictor/
├── backend/
│   ├── app.py                 # Flask application
│   ├── predictor.py           # Prediction engine
│   ├── data_fetcher.py        # Real-time data
│   ├── venue_stats.py         # Venue intelligence
│   ├── player_stats.py        # Player statistics
│   └── data/                  # JSON data files
├── frontend/
│   ├── index.html             # Web UI
│   ├── styles.css             # Styling
│   ├── app.js                 # Frontend logic
│   └── chart.min.js           # Chart library
├── test_weather_integration.py # Test suite
├── requirements.txt           # Dependencies
└── README.md                  # Documentation
```

## Verification

Run this quick check to ensure everything works:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run tests
python test_weather_integration.py

# 3. Start server
python -m backend.app &

# 4. Test health endpoint
sleep 3 && curl http://localhost:5000/api/health

# 5. Stop server
pkill -f "python -m backend.app"
```

All steps should complete without errors ✅

## Support

For issues, check:
- [VALIDATION_REPORT.md](VALIDATION_REPORT.md) - Complete test results
- [README.md](README.md) - Full documentation
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - Feature details
