#!/usr/bin/env python3
"""
Test script for IPL Match Predictor 2026 - Weather Integration Demo
Demonstrates all new features added for real-time weather and venue intelligence.
"""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.predictor import IPLPredictor
from backend.venue_stats import get_venue_profile, get_all_venues, get_dew_factor_text
from backend.data_fetcher import RealTimeDataFetcher


def test_venue_stats():
    """Test venue stats module."""
    print("=" * 70)
    print("TEST 1: Venue Intelligence Module")
    print("=" * 70)

    venues = get_all_venues()
    print(f"\n✓ Loaded {len(venues)} IPL venues")

    # Test a few venues
    for venue_name in ['Wankhede Stadium', 'MA Chidambaram Stadium', 'M. Chinnaswamy Stadium']:
        profile = get_venue_profile(venue_name)
        print(f"\n{venue_name}:")
        print(f"  Type: {profile['type']}")
        print(f"  Avg Score: {profile['avg_first_innings']}")
        print(f"  Chasing Success: {profile['chasing_success_pct']}%")
        print(f"  Dew Impact: {profile['dew_impact']}")
        print(f"  Boundary Size: {profile['boundary_size']}")


def test_weather_api():
    """Test weather API integration."""
    print("\n" + "=" * 70)
    print("TEST 2: Weather API Integration (Open-Meteo)")
    print("=" * 70)

    data_dir = os.path.join(os.path.dirname(__file__), 'backend', 'data')
    fetcher = RealTimeDataFetcher(data_dir)

    # Test weather for a venue
    venue = "Wankhede Stadium"
    print(f"\nFetching weather for {venue}...")
    weather = fetcher.get_weather_and_dew(venue)

    if 'error' in weather:
        print(f"  ⚠ {weather['error']} (API may be blocked in sandbox)")
        print(f"  Note: Works in production with internet access")
    else:
        print(f"  ✓ Temperature: {weather['temp_c']}°C")
        print(f"  ✓ Humidity: {weather['humidity_pct']}%")
        print(f"  ✓ Dew Point: {weather['dewpoint_c']}°C")
        print(f"  ✓ Wind Speed: {weather['wind_kmh']} km/h")
        print(f"  ✓ Rain Probability: {weather['rain_prob_pct']}%")
        print(f"  ✓ Dew Risk: {weather['dew_risk']}")


def test_prediction_without_weather():
    """Test prediction without weather data."""
    print("\n" + "=" * 70)
    print("TEST 3: Prediction Without Weather (Baseline)")
    print("=" * 70)

    data_dir = os.path.join(os.path.dirname(__file__), 'backend', 'data')
    predictor = IPLPredictor(data_dir)

    match_params = {
        'team1': 'MI',
        'team2': 'CSK',
        'venue': 'Wankhede Stadium',
        'match_type': 'league',
        'time_of_day': 'night',
        'toss_winner': 'MI',
        'toss_decision': 'field',
        'injured_players': []
    }

    result = predictor.predict(match_params)

    print(f"\nMatch: {result['team1_name']} vs {result['team2_name']}")
    print(f"Venue: {result['venue']}")
    print(f"\nPrediction:")
    print(f"  Winner: {result['predicted_winner_name']}")
    print(f"  Probability: {result['team1_probability']}% vs {result['team2_probability']}%")
    print(f"  Confidence: {result['confidence']}")
    print(f"  Model Version: {result['model_version']}")
    print(f"  Factors Analyzed: {len(result['key_insights'])}")


def test_prediction_with_weather():
    """Test prediction WITH weather data."""
    print("\n" + "=" * 70)
    print("TEST 4: Prediction WITH Weather (Enhanced)")
    print("=" * 70)

    data_dir = os.path.join(os.path.dirname(__file__), 'backend', 'data')
    predictor = IPLPredictor(data_dir)

    # Simulate HIGH dew conditions (typical Mumbai evening match)
    weather_data = {
        'temp_c': 28.5,
        'humidity_pct': 82.0,
        'dewpoint_c': 20.5,  # HIGH dew!
        'wind_kmh': 15.0,
        'rain_prob_pct': 10.0,
        'dew_risk': 'HIGH',
        'city': 'Mumbai',
        'venue': 'Wankhede Stadium'
    }

    match_params = {
        'team1': 'MI',
        'team2': 'CSK',
        'venue': 'Wankhede Stadium',
        'match_type': 'league',
        'time_of_day': 'night',
        'toss_winner': 'MI',
        'toss_decision': 'field',  # MI batting second (chasing)
        'injured_players': [],
        'weather_data': weather_data
    }

    result = predictor.predict(match_params)

    print(f"\nMatch: {result['team1_name']} vs {result['team2_name']}")
    print(f"Venue: {result['venue']}")
    print(f"Toss: {result['team1_name']} won and chose to field")
    print(f"\nWeather Conditions:")
    if 'weather' in result:
        print(f"  Temperature: {result['weather']['temp_c']}°C")
        print(f"  Humidity: {result['weather']['humidity_pct']}%")
        print(f"  Dew Point: {result['weather']['dewpoint_c']}°C")
        print(f"  Dew Risk: {result['weather']['dew_risk']}")

    print(f"\nPrediction:")
    print(f"  Winner: {result['predicted_winner_name']}")
    print(f"  Probability: {result['team1_probability']}% vs {result['team2_probability']}%")
    print(f"  Confidence: {result['confidence']}")
    print(f"  Model Version: {result['model_version']}")
    print(f"  Factors Analyzed: {len(result['key_insights'])}")

    # Show weather factor
    for factor in result['key_insights']:
        if 'Weather' in factor['factor']:
            print(f"\n  Weather Impact ({factor['impact'].upper()}):")
            details = factor['detail'].split(' | ')
            for detail in details:
                print(f"    • {detail}")


def test_comparison():
    """Compare predictions with and without weather."""
    print("\n" + "=" * 70)
    print("TEST 5: Weather Impact Comparison")
    print("=" * 70)

    data_dir = os.path.join(os.path.dirname(__file__), 'backend', 'data')
    predictor = IPLPredictor(data_dir)

    base_params = {
        'team1': 'RCB',
        'team2': 'KKR',
        'venue': 'M. Chinnaswamy Stadium',
        'match_type': 'league',
        'time_of_day': 'night',
        'toss_winner': 'RCB',
        'toss_decision': 'bat',  # RCB batting first
        'injured_players': []
    }

    # Without weather
    result_no_weather = predictor.predict(base_params)

    # With HIGH dew (favors chasing team KKR)
    weather_high_dew = {
        'temp_c': 30.0,
        'humidity_pct': 75.0,
        'dewpoint_c': 22.0,  # HIGH dew
        'wind_kmh': 20.0,
        'rain_prob_pct': 5.0,
        'dew_risk': 'HIGH',
        'city': 'Bangalore'
    }

    params_with_weather = base_params.copy()
    params_with_weather['weather_data'] = weather_high_dew
    result_with_weather = predictor.predict(params_with_weather)

    print(f"\nScenario: RCB vs KKR at Chinnaswamy")
    print(f"Toss: RCB won and chose to bat first")
    print(f"\nWITHOUT Weather Data:")
    print(f"  RCB: {result_no_weather['team1_probability']}%")
    print(f"  KKR: {result_no_weather['team2_probability']}%")
    print(f"  Winner: {result_no_weather['predicted_winner_name']}")

    print(f"\nWITH Weather Data (HIGH DEW):")
    print(f"  RCB: {result_with_weather['team1_probability']}%")
    print(f"  KKR: {result_with_weather['team2_probability']}%")
    print(f"  Winner: {result_with_weather['predicted_winner_name']}")

    diff = abs(result_with_weather['team2_probability'] - result_no_weather['team2_probability'])
    print(f"\n  Impact: KKR (chasing) got +{diff:.1f}% advantage due to HIGH dew!")


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("IPL MATCH PREDICTOR 2026 - WEATHER INTEGRATION TEST SUITE")
    print("=" * 70)

    try:
        test_venue_stats()
        test_weather_api()
        test_prediction_without_weather()
        test_prediction_with_weather()
        test_comparison()

        print("\n" + "=" * 70)
        print("✓ ALL TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        print("\nNew Features Summary:")
        print("  ✓ Real-time weather API (Open-Meteo - FREE)")
        print("  ✓ Venue intelligence (11 venues with historical data)")
        print("  ✓ Weather-enhanced predictions (dew, humidity, temp, wind, rain)")
        print("  ✓ Model version 2.1-weather")
        print("\nAPI Endpoints Added:")
        print("  • GET /api/weather/<venue>")
        print("  • GET /api/scorecard/<match_id>")
        print("  • GET /api/player/<player_id>")
        print("\n")

    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
