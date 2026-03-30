"""
historical_loader.py
====================
Drop this into your /backend folder alongside app.py.

In your app.py (or predictor.py), add at the top:

    from historical_loader import get_h2h, get_team_win_rate, get_venue_profile, get_titles

Then replace hardcoded values with these function calls.
Examples shown at the bottom of this file.
"""

import json
import os

_DATA = None
_DATA_FILE = os.path.join(os.path.dirname(__file__), "historical_data.json")


def _load():
    global _DATA
    if _DATA is None:
        if os.path.exists(_DATA_FILE):
            with open(_DATA_FILE) as f:
                _DATA = json.load(f)
            print(f"[HistoricalLoader] ✅ Loaded {_DATA['meta']['total_matches_processed']} matches "
                  f"({_DATA['meta']['seasons'][0]}–{_DATA['meta']['seasons'][-1]})")
        else:
            print("[HistoricalLoader] ⚠️  historical_data.json not found — using fallback defaults.")
            _DATA = {}
    return _DATA


# ── Public API ──────────────────────────────────────────────────────────────

def get_h2h(team1: str, team2: str) -> dict:
    """
    Returns head-to-head win counts between two teams.
    Example return: {"Mumbai Indians": 14, "Chennai Super Kings": 10, "no_result": 1}
    """
    data = _load()
    key = "_vs_".join(sorted([team1, team2]))
    return data.get("head_to_head", {}).get(key, {})


def get_h2h_win_rate(team: str, opponent: str) -> float:
    """
    Returns the win rate (0.0–1.0) of `team` against `opponent`.
    Falls back to 0.5 if no data.
    """
    h2h = get_h2h(team, opponent)
    team_wins = h2h.get(team, 0)
    opp_wins  = h2h.get(opponent, 0)
    total = team_wins + opp_wins
    return round(team_wins / total, 3) if total else 0.5


def get_team_win_rate(team: str, venue: str = None) -> float:
    """
    Returns overall win rate for `team`.
    If `venue` is provided, returns venue-specific win rate.
    Falls back to 0.5 if no data.
    """
    data = _load()
    stats = data.get("team_stats", {}).get(team, {})
    if not stats:
        return 0.5
    if venue:
        venue_stats = stats.get("venue_stats", {}).get(venue, {})
        return venue_stats.get("win_rate", stats.get("overall_win_rate", 0.5))
    return stats.get("overall_win_rate", 0.5)


def get_recent_form(team: str) -> float:
    """
    Returns win rate from the team's last 20 matches.
    Falls back to overall win rate, then 0.5.
    """
    data = _load()
    stats = data.get("team_stats", {}).get(team, {})
    return stats.get("recent_form_win_rate", stats.get("overall_win_rate", 0.5))


def get_venue_profile(venue: str) -> dict:
    """
    Returns venue stats dict:
    {
        "total_matches": int,
        "toss_winner_win_rate": float,
        "chasing_success_rate": float,
        "teams_prefer_field": float,
    }
    Returns safe defaults if venue not found.
    """
    data = _load()
    default = {
        "total_matches": 0,
        "toss_winner_win_rate": 0.5,
        "chasing_success_rate": 0.5,
        "teams_prefer_field": 0.5,
    }
    # fuzzy match: check if venue string is a substring
    profiles = data.get("venue_profiles", {})
    for k, v in profiles.items():
        if venue.lower() in k.lower() or k.lower() in venue.lower():
            return v
    return default


def get_titles(team: str) -> int:
    """Returns number of IPL titles won by a team."""
    data = _load()
    return data.get("titles_won", {}).get(team, 0)


def get_meta() -> dict:
    """Returns metadata about the loaded dataset."""
    return _load().get("meta", {})


# ── Integration example ─────────────────────────────────────────────────────
"""
HOW TO USE IN YOUR EXISTING predictor.py / app.py:

BEFORE (hardcoded):
    h2h_score = 15 if team1_wins_historically else 0

AFTER (data-driven):
    from historical_loader import get_h2h_win_rate, get_team_win_rate, get_venue_profile

    h2h_rate = get_h2h_win_rate(team1, team2)   # e.g. 0.58
    h2h_score = h2h_rate * 15                    # scales to max 15 pts

    # Win rate at this specific venue
    venue_wr = get_team_win_rate(team1, venue)   # e.g. 0.70
    venue_score = venue_wr * 10                  # scales to max 10 pts

    # Recent form
    form = get_recent_form(team1)                # last 20 matches win rate
    form_score = form * 35                       # scales to max 35 pts

    # Venue chasing stat for toss decision analysis
    vp = get_venue_profile(venue)
    chasing_advantage = vp["chasing_success_rate"]  # e.g. 0.62 → chasing team favoured
"""
