"""
Venue statistics and pitch profiles for IPL venues.

Provides historical venue data, pitch characteristics, and toss analysis
based on IPL historical data from 2008-2025.
"""

from typing import Dict, Any

# ── Pitch Type and Characteristics Mapping ────────────────────────────────────
# Based on IPL historical data and expert analysis

PITCH_PROFILES: Dict[str, Dict[str, Any]] = {
    "Wankhede Stadium": {
        "type": "batting",
        "pace_friendly": True,
        "spin_friendly": False,
        "dew_impact": "HIGH",
        "avg_first_innings": 185,
        "avg_second_innings": 178,
        "toss_bat_win_pct": 42.3,
        "chasing_success_pct": 57.7,
        "boundary_size": "small",
        "altitude_m": 14,
        "notes": "High-scoring venue with short boundaries. Dew plays a major role in evening matches."
    },
    "MA Chidambaram Stadium": {
        "type": "spin",
        "pace_friendly": False,
        "spin_friendly": True,
        "dew_impact": "HIGH",
        "avg_first_innings": 165,
        "avg_second_innings": 158,
        "toss_bat_win_pct": 48.5,
        "chasing_success_pct": 51.5,
        "boundary_size": "medium",
        "altitude_m": 7,
        "notes": "Slow, turning pitch that favors spinners. Coastal humidity causes heavy dew."
    },
    "M. Chinnaswamy Stadium": {
        "type": "batting",
        "pace_friendly": True,
        "spin_friendly": False,
        "dew_impact": "LOW",
        "avg_first_innings": 190,
        "avg_second_innings": 182,
        "toss_bat_win_pct": 45.2,
        "chasing_success_pct": 54.8,
        "boundary_size": "small",
        "altitude_m": 920,
        "notes": "Highest scoring venue in IPL. Thin air at altitude helps the ball travel. Fast outfield."
    },
    "Eden Gardens": {
        "type": "balanced",
        "pace_friendly": True,
        "spin_friendly": True,
        "dew_impact": "MODERATE",
        "avg_first_innings": 172,
        "avg_second_innings": 168,
        "toss_bat_win_pct": 46.8,
        "chasing_success_pct": 53.2,
        "boundary_size": "large",
        "altitude_m": 9,
        "notes": "Large ground with long boundaries. Assists both pace and spin. Evening dew factor."
    },
    "Narendra Modi Stadium": {
        "type": "balanced",
        "pace_friendly": True,
        "spin_friendly": True,
        "dew_impact": "LOW",
        "avg_first_innings": 175,
        "avg_second_innings": 171,
        "toss_bat_win_pct": 47.5,
        "chasing_success_pct": 52.5,
        "boundary_size": "large",
        "altitude_m": 53,
        "notes": "World's largest cricket stadium. Balanced conditions with long straight boundaries."
    },
    "Rajiv Gandhi Intl. Cricket Stadium": {
        "type": "batting",
        "pace_friendly": True,
        "spin_friendly": False,
        "dew_impact": "HIGH",
        "avg_first_innings": 180,
        "avg_second_innings": 175,
        "toss_bat_win_pct": 43.1,
        "chasing_success_pct": 56.9,
        "boundary_size": "medium",
        "altitude_m": 542,
        "notes": "Fast, true pitch ideal for stroke play. Heavy dew in evening matches."
    },
    "Sawai Mansingh Stadium": {
        "type": "spin",
        "pace_friendly": False,
        "spin_friendly": True,
        "dew_impact": "MODERATE",
        "avg_first_innings": 168,
        "avg_second_innings": 162,
        "toss_bat_win_pct": 49.2,
        "chasing_success_pct": 50.8,
        "boundary_size": "medium",
        "altitude_m": 430,
        "notes": "Slow pitch with variable bounce. Spinners dominate in middle overs."
    },
    "Punjab Cricket Association Stadium": {
        "type": "batting",
        "pace_friendly": True,
        "spin_friendly": False,
        "dew_impact": "LOW",
        "avg_first_innings": 182,
        "avg_second_innings": 176,
        "toss_bat_win_pct": 44.7,
        "chasing_success_pct": 55.3,
        "boundary_size": "small",
        "altitude_m": 310,
        "notes": "Fast outfield with short square boundaries. Pace bowlers get early movement."
    },
    "Dr. DY Patil Sports Academy": {
        "type": "balanced",
        "pace_friendly": True,
        "spin_friendly": False,
        "dew_impact": "HIGH",
        "avg_first_innings": 178,
        "avg_second_innings": 173,
        "toss_bat_win_pct": 45.9,
        "chasing_success_pct": 54.1,
        "boundary_size": "medium",
        "altitude_m": 22,
        "notes": "Coastal venue with heavy dew. Good batting conditions with occasional seam movement."
    },
    "Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium": {
        "type": "balanced",
        "pace_friendly": True,
        "spin_friendly": True,
        "dew_impact": "MODERATE",
        "avg_first_innings": 170,
        "avg_second_innings": 166,
        "toss_bat_win_pct": 48.0,
        "chasing_success_pct": 52.0,
        "boundary_size": "medium",
        "altitude_m": 123,
        "notes": "Modern stadium with consistent pitch. Assists both departments equally."
    },
    "Arun Jaitley Stadium": {
        "type": "batting",
        "pace_friendly": True,
        "spin_friendly": False,
        "dew_impact": "MODERATE",
        "avg_first_innings": 176,
        "avg_second_innings": 171,
        "toss_bat_win_pct": 46.3,
        "chasing_success_pct": 53.7,
        "boundary_size": "medium",
        "altitude_m": 216,
        "notes": "Good batting track with even bounce. Slight advantage for pacers with new ball."
    }
}


def get_venue_profile(venue_name: str) -> Dict[str, Any]:
    """
    Get detailed pitch profile and statistics for a venue.

    Args:
        venue_name: Name of the IPL venue

    Returns:
        Dictionary with venue characteristics, or default balanced profile if venue not found
    """
    # Try exact match first
    if venue_name in PITCH_PROFILES:
        return PITCH_PROFILES[venue_name]

    # Try partial match
    for known_venue, profile in PITCH_PROFILES.items():
        if venue_name.lower() in known_venue.lower() or known_venue.lower() in venue_name.lower():
            return profile

    # Return default balanced profile
    return {
        "type": "balanced",
        "pace_friendly": True,
        "spin_friendly": True,
        "dew_impact": "MODERATE",
        "avg_first_innings": 170,
        "avg_second_innings": 166,
        "toss_bat_win_pct": 47.0,
        "chasing_success_pct": 53.0,
        "boundary_size": "medium",
        "altitude_m": 100,
        "notes": "Unknown venue - using balanced conditions"
    }


def get_toss_advantage(venue_name: str, decision: str) -> float:
    """
    Calculate toss advantage based on venue-specific historical data.

    Args:
        venue_name: Name of the IPL venue
        decision: 'bat' or 'field'

    Returns:
        Advantage score (0.0 to 1.0)
    """
    profile = get_venue_profile(venue_name)

    if decision == "bat":
        # If toss_bat_win_pct > 50, batting first is advantageous
        win_pct = profile.get("toss_bat_win_pct", 47.0)
        return min(1.0, max(0.0, (win_pct - 40) / 20))  # Normalize to 0-1
    else:  # field
        # If chasing_success_pct > 50, fielding first (chasing) is advantageous
        chase_pct = profile.get("chasing_success_pct", 53.0)
        return min(1.0, max(0.0, (chase_pct - 40) / 20))  # Normalize to 0-1


def get_dew_factor_text(venue_name: str) -> str:
    """
    Get human-readable dew factor description for a venue.

    Args:
        venue_name: Name of the IPL venue

    Returns:
        Dew impact description
    """
    profile = get_venue_profile(venue_name)
    dew = profile.get("dew_impact", "MODERATE")

    descriptions = {
        "HIGH": "Heavy dew expected - significant advantage batting second",
        "MODERATE": "Moderate dew likely - slight advantage batting second",
        "LOW": "Minimal dew - no significant impact"
    }

    return descriptions.get(dew, descriptions["MODERATE"])


def get_all_venues() -> list:
    """Get list of all venues with their profiles."""
    return list(PITCH_PROFILES.keys())


def compare_venues(venue1: str, venue2: str) -> Dict[str, Any]:
    """
    Compare two venues across key metrics.

    Args:
        venue1: First venue name
        venue2: Second venue name

    Returns:
        Comparison dictionary with differences
    """
    p1 = get_venue_profile(venue1)
    p2 = get_venue_profile(venue2)

    return {
        "venue1": venue1,
        "venue2": venue2,
        "avg_score_diff": p1["avg_first_innings"] - p2["avg_first_innings"],
        "venue1_higher_scoring": p1["avg_first_innings"] > p2["avg_first_innings"],
        "venue1_more_spin_friendly": p1["spin_friendly"] and not p2["spin_friendly"],
        "venue2_more_spin_friendly": p2["spin_friendly"] and not p1["spin_friendly"],
        "dew_impact_comparison": {
            "venue1": p1["dew_impact"],
            "venue2": p2["dew_impact"]
        }
    }
