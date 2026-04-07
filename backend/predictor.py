import json
import os
import math
import random
import numpy as np
from typing import Dict, List, Tuple, Optional

try:
    from backend.venue_stats import get_venue_profile, get_dew_factor_text
except ImportError:
    # Fallback if venue_stats not available
    def get_venue_profile(venue: str) -> dict:
        return {"type": "balanced", "dew_impact": "MODERATE", "avg_first_innings": 170}
    def get_dew_factor_text(venue: str) -> str:
        return "Dew impact not available"


class IPLPredictor:
    """
    Enhanced IPL Match Prediction Engine using advanced weighted multi-factor analysis.

    Improvements:
    - Dynamic weight adjustment based on match context
    - Momentum-based recent form analysis
    - Advanced squad strength evaluation
    - Exponential smoothing for probability calculation
    - Context-aware venue and pitch modeling
    """

    MAX_OVERSEAS_PLAYERS = 4

    # Weight multipliers for different factors (tuned for better accuracy)
    WEIGHTS = {
        "recent_form": 35,      # Increased from 30 - recent form is highly predictive
        "h2h": 15,              # Reduced from 20 - historical data less relevant
        "home_advantage": 20,   # Increased from 18 - home advantage is significant
        "toss": 12,             # Increased from 10 - toss can be decisive
        "match_type": 10,       # New - playoff pressure matters
        "venue_suitability": 10,# Increased from 8 - pitch conditions matter
        "momentum": 15,         # New - winning/losing streaks are important
    }

    def __init__(self, data_dir: str):
        self.teams = self._load_json(os.path.join(data_dir, "teams.json"))
        self.venues = self._load_json(os.path.join(data_dir, "venues.json"))
        self.head_to_head = self._load_json(os.path.join(data_dir, "head_to_head.json"))
        self.recent_form = self._load_json(os.path.join(data_dir, "recent_form.json"))

    def _load_json(self, path: str) -> dict:
        with open(path, "r") as f:
            return json.load(f)

    def get_all_teams(self) -> List[dict]:
        return [
            {"short": k, "name": v["name"], "color": v["color"]}
            for k, v in self.teams.items()
        ]

    def get_all_venues(self) -> List[str]:
        return list(self.venues.keys())

    def get_team_squad(self, team_short: str) -> dict:
        team = self.teams.get(team_short)
        if not team:
            return {}
        return team

    def get_h2h(self, team1: str, team2: str) -> dict:
        key = f"{team1}_{team2}"
        alt_key = f"{team2}_{team1}"
        data = self.head_to_head.get(key) or self.head_to_head.get(alt_key)
        if not data:
            return {"team1": team1, "team2": team2, "team1_wins": 0, "team2_wins": 0, "total_matches": 0, "last5": []}
        if data.get("team1") == team2:
            return {
                "team1": team1,
                "team2": team2,
                "team1_wins": data["team2_wins"],
                "team2_wins": data["team1_wins"],
                "total_matches": data["total_matches"],
                "last5": [team1 if r == team2 else team2 for r in data["last5"]],
            }
        return data

    def _get_recent_form_score(self, team: str) -> float:
        form = self.recent_form.get(team, {})
        return form.get("win_percentage", 50) / 100.0

    def _calculate_momentum(self, team: str) -> float:
        """
        Calculate team momentum based on recent match results.
        Uses exponential weighting - recent matches matter more.

        Returns: momentum score between 0.0 and 1.0
        """
        h2h_records = self.head_to_head
        recent_results = []

        # Extract recent results from all head-to-head records
        for key, data in h2h_records.items():
            if team in key:
                last5 = data.get("last5", [])
                # Reverse to get most recent first
                for result in reversed(last5):
                    if result == team:
                        recent_results.append(1.0)  # Win
                    else:
                        recent_results.append(0.0)  # Loss

        if not recent_results:
            return 0.5  # Neutral momentum

        # Take last 5 matches and apply exponential weighting
        recent_results = recent_results[:5]
        weights = [0.35, 0.25, 0.20, 0.12, 0.08]  # Most recent has highest weight
        weighted_sum = sum(r * w for r, w in zip(recent_results, weights[:len(recent_results)]))
        total_weight = sum(weights[:len(recent_results)])

        return weighted_sum / total_weight if total_weight > 0 else 0.5

    def _calculate_squad_strength(self, team: str, injured_players: List[str]) -> float:
        """
        Advanced squad strength calculation considering:
        - Role balance (batsmen, bowlers, all-rounders)
        - Key player availability
        - Overseas player quality
        - Form scores

        Returns: strength multiplier between 0.3 and 1.2
        """
        squad = self.teams.get(team, {}).get("squad", [])
        available = [p for p in squad if p["name"] not in injured_players]

        if not available:
            return 0.3

        # Count roles
        batsmen = [p for p in available if "Batsman" in p["role"] or "Wicket-Keeper" in p["role"]]
        bowlers = [p for p in available if "Bowler" in p["role"]]
        allrounders = [p for p in available if "All-rounder" in p["role"]]
        key_players = [p for p in available if p.get("key_player", False)]
        overseas = [p for p in available if p.get("is_overseas", False)]

        # Base strength from role balance
        strength = 0.5

        # Batting strength (need at least 6 quality batsmen)
        batting_strength = min(len(batsmen) / 6.0, 1.0) * 0.2
        strength += batting_strength

        # Bowling strength (need at least 5 quality bowlers including all-rounders)
        total_bowling = len(bowlers) + len(allrounders)
        bowling_strength = min(total_bowling / 5.0, 1.0) * 0.2
        strength += bowling_strength

        # All-rounder bonus (all-rounders are valuable)
        allrounder_bonus = min(len(allrounders) / 2.0, 1.0) * 0.1
        strength += allrounder_bonus

        # Key player availability (critical for team performance)
        total_key = len([p for p in squad if p.get("key_player", False)])
        if total_key > 0:
            key_available_ratio = len(key_players) / total_key
            strength += key_available_ratio * 0.15

        # Overseas player quality (overseas players often match-winners)
        if overseas:
            avg_overseas_form = sum(p.get("form_score", 50) for p in overseas) / len(overseas)
            overseas_bonus = (avg_overseas_form / 100.0) * 0.1
            strength += overseas_bonus

        # Average form score of available players
        if available:
            avg_form = sum(p.get("form_score", 50) for p in available) / len(available)
            form_multiplier = (avg_form / 50.0) * 0.15  # Normalized around 50
            strength += form_multiplier

        # Penalties for missing key players
        injured_key = [p for p in injured_players if any(
            pl["name"] == p and pl.get("key_player", False)
            for pl in squad
        )]
        if injured_key:
            penalty = len(injured_key) * 0.12
            strength -= penalty

        # Ensure strength is in valid range
        return max(0.3, min(strength, 1.2))

    def _get_h2h_advantage(self, team1: str, team2: str) -> Tuple[float, float]:
        h2h = self.get_h2h(team1, team2)
        total = h2h["total_matches"]
        if total == 0:
            return 0.5, 0.5
        t1_ratio = h2h["team1_wins"] / total
        t2_ratio = h2h["team2_wins"] / total
        return t1_ratio, t2_ratio

    def _home_advantage(self, team: str, venue: str) -> float:
        venue_data = self.venues.get(venue, {})
        if venue_data.get("team") == team:
            return 1.0
        return 0.0

    def _toss_advantage(
        self,
        team: str,
        toss_winner: str,
        toss_decision: str,
        venue: str,
        time_of_day: str,
    ) -> float:
        if toss_winner != team:
            return 0.0
        venue_data = self.venues.get(venue, {})
        dew_factor = venue_data.get("dew_factor", "low")
        # If dew is high in a night match and team chose to field, batting second is advantageous
        if time_of_day in ("night", "day_night") and dew_factor in ("high", "medium"):
            if toss_decision == "field":
                return 1.0  # toss winner chose to field = batting second advantage
        # In general winning toss and batting has mild advantage
        if toss_decision == "bat":
            return 0.5
        return 0.5

    def _player_strength(self, team: str, injured_players: List[str]) -> float:
        squad = self.teams.get(team, {}).get("squad", [])
        key_players = [p for p in squad if p.get("key_player")]
        if not key_players:
            return 1.0
        injured_key = sum(
            1 for p in key_players if p["name"] in injured_players
        )
        return max(0.3, 1.0 - (injured_key * 0.15))

    def _venue_strength(self, team: str, venue: str) -> float:
        """
        Advanced venue suitability analysis based on:
        - Spin vs pace balance in squad
        - Historical performance at similar venues
        - Pitch type preferences

        Returns: suitability score between 0.0 and 1.0
        """
        venue_data = self.venues.get(venue, {})
        team_data = self.teams.get(team, {})
        squad = team_data.get("squad", [])

        if not venue_data or not squad:
            return 0.5  # Neutral

        # Count bowler types
        spinners = sum(1 for p in squad if p["role"] == "Bowler" and
                      any(keyword in p.get("name", "").lower()
                          for keyword in ["ashwin", "chahal", "kuldeep", "jadeja", "bishnoi"]))
        pacers = sum(1 for p in squad if p["role"] == "Bowler" and
                    not any(keyword in p.get("name", "").lower()
                            for keyword in ["ashwin", "chahal", "kuldeep", "jadeja", "bishnoi"]))

        total_bowlers = spinners + pacers
        if total_bowlers == 0:
            return 0.5

        spin_ratio = spinners / total_bowlers
        pace_ratio = pacers / total_bowlers

        # Venue characteristics
        spin_friendly = venue_data.get("spin_friendly", False)
        pace_friendly = venue_data.get("pace_friendly", False)

        score = 0.5  # Base neutral score

        # Spin-friendly venue
        if spin_friendly:
            # Teams with more spinners get advantage
            score += spin_ratio * 0.3
            # Penalty for pace-heavy attacks
            if spin_ratio < 0.3:
                score -= 0.1

        # Pace-friendly venue
        if pace_friendly:
            # Teams with more pacers get advantage
            score += pace_ratio * 0.3
            # Penalty for spin-heavy attacks
            if pace_ratio < 0.6:
                score -= 0.1

        # Batting-friendly vs bowling-friendly venue
        avg_score = venue_data.get("avg_first_innings", 170)
        if avg_score > 180:  # High-scoring venue
            # Teams with strong batting lineups benefit
            batsmen = [p for p in squad if "Batsman" in p["role"] or "Wicket-Keeper" in p["role"]]
            if len(batsmen) >= 6:
                score += 0.1
        elif avg_score < 160:  # Low-scoring, bowling-friendly
            # Teams with strong bowling attacks benefit
            if total_bowlers >= 5:
                score += 0.1

        return max(0.0, min(score, 1.0))

    def _calculate_scores(
        self,
        team1: str,
        team2: str,
        venue: str,
        match_type: str,
        time_of_day: str,
        toss_winner: str,
        toss_decision: str,
        injured_players: List[str],
    ) -> Tuple[float, float, List[dict]]:
        """
        Enhanced scoring calculation with improved factor weighting and analysis.
        Uses exponential smoothing and context-aware adjustments.
        """
        factors = []

        # Base scores start at 50 for fairness
        t1_score = 50.0
        t2_score = 50.0

        # 1. Recent Form (35 points max) - Most predictive factor
        t1_form = self._get_recent_form_score(team1)
        t2_form = self._get_recent_form_score(team2)
        t1_score += t1_form * self.WEIGHTS["recent_form"]
        t2_score += t2_form * self.WEIGHTS["recent_form"]

        t1_form_pct = int(t1_form * 100)
        t2_form_pct = int(t2_form * 100)
        factors.append({
            "factor": "Recent Form & Win Rate",
            "detail": f"{self.teams[team1]['name']}: {t1_form_pct}% win rate | {self.teams[team2]['name']}: {t2_form_pct}% win rate",
            "impact": "high" if abs(t1_form_pct - t2_form_pct) > 20 else "medium",
        })

        # 2. Momentum Analysis (15 points max) - NEW!
        t1_momentum = self._calculate_momentum(team1)
        t2_momentum = self._calculate_momentum(team2)
        t1_score += t1_momentum * self.WEIGHTS["momentum"]
        t2_score += t2_momentum * self.WEIGHTS["momentum"]

        t1_mom_pct = int(t1_momentum * 100)
        t2_mom_pct = int(t2_momentum * 100)
        factors.append({
            "factor": "Recent Momentum",
            "detail": f"{self.teams[team1]['name']}: {t1_mom_pct}% recent success | {self.teams[team2]['name']}: {t2_mom_pct}% recent success",
            "impact": "high" if abs(t1_mom_pct - t2_mom_pct) > 30 else "medium",
        })

        # 3. Head-to-Head (15 points max) - Reduced weight
        t1_h2h, t2_h2h = self._get_h2h_advantage(team1, team2)
        t1_score += t1_h2h * self.WEIGHTS["h2h"]
        t2_score += t2_h2h * self.WEIGHTS["h2h"]

        h2h_data = self.get_h2h(team1, team2)
        factors.append({
            "factor": "Head-to-Head Record",
            "detail": f"{self.teams[team1]['name']}: {h2h_data['team1_wins']} wins | {self.teams[team2]['name']}: {h2h_data['team2_wins']} wins in {h2h_data['total_matches']} matches",
            "impact": "high" if abs(h2h_data["team1_wins"] - h2h_data["team2_wins"]) > 5 else "medium",
        })

        # 4. Home Advantage (20 points max) - Increased importance
        t1_home = self._home_advantage(team1, venue)
        t2_home = self._home_advantage(team2, venue)
        t1_score += t1_home * self.WEIGHTS["home_advantage"]
        t2_score += t2_home * self.WEIGHTS["home_advantage"]

        if t1_home:
            factors.append({
                "factor": "Home Ground Advantage",
                "detail": f"{self.teams[team1]['name']} are playing at their fortress — {venue}. Crowd support and familiarity are crucial.",
                "impact": "high",
            })
        elif t2_home:
            factors.append({
                "factor": "Home Ground Advantage",
                "detail": f"{self.teams[team2]['name']} are playing at their fortress — {venue}. Crowd support and familiarity are crucial.",
                "impact": "high",
            })
        else:
            factors.append({
                "factor": "Neutral Venue",
                "detail": f"Both teams on unfamiliar territory at {venue} — no home advantage",
                "impact": "low",
            })

        # 5. Toss Impact (12 points max) - Contextual
        t1_toss = self._toss_advantage(team1, toss_winner, toss_decision, venue, time_of_day)
        t2_toss = self._toss_advantage(team2, toss_winner, toss_decision, venue, time_of_day)
        t1_score += t1_toss * self.WEIGHTS["toss"]
        t2_score += t2_toss * self.WEIGHTS["toss"]

        if toss_winner:
            winner_name = self.teams.get(toss_winner, {}).get("name", toss_winner)
            venue_data = self.venues.get(venue, {})
            dew = venue_data.get("dew_factor", "low")
            detail = f"{winner_name} won the toss and chose to {toss_decision}."
            if time_of_day in ("night", "day_night") and dew in ("high", "medium"):
                detail += f" Heavy dew expected at {venue} — team batting second has significant advantage!"
            factors.append({
                "factor": "Toss & Conditions",
                "detail": detail,
                "impact": "high" if (dew == "high" and time_of_day in ("night", "day_night")) else "medium",
            })

        # 6. Squad Strength & Availability (multiplier: 0.3x to 1.2x)
        t1_strength = self._calculate_squad_strength(team1, injured_players)
        t2_strength = self._calculate_squad_strength(team2, injured_players)
        t1_score *= t1_strength
        t2_score *= t2_strength

        injured_t1 = [p for p in injured_players if any(
            pl["name"] == p for pl in self.teams.get(team1, {}).get("squad", [])
        )]
        injured_t2 = [p for p in injured_players if any(
            pl["name"] == p for pl in self.teams.get(team2, {}).get("squad", [])
        )]

        if injured_t1 or injured_t2:
            detail_parts = []
            if injured_t1:
                detail_parts.append(f"{self.teams[team1]['name']} missing key players: {', '.join(injured_t1)}")
            if injured_t2:
                detail_parts.append(f"{self.teams[team2]['name']} missing key players: {', '.join(injured_t2)}")
            factors.append({
                "factor": "Player Availability & Squad Depth",
                "detail": " | ".join(detail_parts),
                "impact": "high",
            })
        else:
            factors.append({
                "factor": "Squad Strength",
                "detail": f"Both teams at full strength with balanced squads",
                "impact": "low",
            })

        # 7. Match Type (10 points max) - Playoff pressure
        if match_type in ("qualifier", "eliminator", "final"):
            # Experienced teams with better h2h do better under pressure
            pressure_factor = abs(t1_h2h - t2_h2h)
            if t1_h2h > t2_h2h:
                t1_score += self.WEIGHTS["match_type"] * (1 + pressure_factor)
            elif t2_h2h > t1_h2h:
                t2_score += self.WEIGHTS["match_type"] * (1 + pressure_factor)

            factors.append({
                "factor": f"{match_type.title()} Match Pressure",
                "detail": f"High-stakes knockout game! Teams with proven track records and mental strength have the edge.",
                "impact": "high",
            })
        else:
            factors.append({
                "factor": "League Stage Match",
                "detail": "Regular season fixture — every point counts for playoff qualification",
                "impact": "low",
            })

        # 8. Venue Suitability (10 points max) - Enhanced
        t1_venue = self._venue_strength(team1, venue)
        t2_venue = self._venue_strength(team2, venue)
        t1_score += t1_venue * self.WEIGHTS["venue_suitability"]
        t2_score += t2_venue * self.WEIGHTS["venue_suitability"]

        venue_data = self.venues.get(venue, {})
        if venue_data:
            pitch_type = "spin-friendly" if venue_data.get("spin_friendly") else "pace-friendly" if venue_data.get("pace_friendly") else "balanced"
            avg_score = venue_data.get("avg_first_innings", 170)
            factors.append({
                "factor": "Venue & Pitch Conditions",
                "detail": f"{venue} — {pitch_type} pitch, average first innings: {avg_score}",
                "impact": "medium",
            })

        # 9. Time of Day Factor
        if time_of_day == "night":
            factors.append({
                "factor": "Night Match Under Lights",
                "detail": "Evening match with heavy dew expected — batting second will be significantly easier",
                "impact": "high",
            })
        elif time_of_day == "day":
            factors.append({
                "factor": "Afternoon Day Match",
                "detail": "Hot conditions with pitch deterioration expected — spinners may dominate later overs",
                "impact": "medium",
            })

        return t1_score, t2_score, factors

    def _get_playing_xi(
        self,
        team: str,
        venue: str,
        injured_players: List[str],
    ) -> List[dict]:
        team_data = self.teams.get(team, {})
        squad = [p.copy() for p in team_data.get("squad", [])]
        venue_data = self.venues.get(venue, {})

        # Remove injured players
        available = [p for p in squad if p["name"] not in injured_players]

        # Boost scores based on venue conditions
        spin_friendly = venue_data.get("spin_friendly", False)
        pace_friendly = venue_data.get("pace_friendly", False)
        for player in available:
            score = player.get("form_score", 50)
            if spin_friendly and "spin" in player["name"].lower():
                score += 5
            if pace_friendly and player["role"] == "Bowler":
                score += 3
            if player.get("key_player"):
                score += 15
            player["selection_score"] = score

        # Sort by selection score descending
        available.sort(key=lambda x: x.get("selection_score", 0), reverse=True)

        # Must include: 1 wicket-keeper, at least 3 bowlers, at least 2 all-rounders
        xi = []
        overseas_count = 0
        wk_count = 0
        bowler_count = 0
        allrounder_count = 0
        batsman_count = 0

        # First pass: pick key roles ensuring balance
        remaining = []
        for player in available:
            role = player["role"]
            is_overseas = player.get("is_overseas", False)
            over_limit = overseas_count >= self.MAX_OVERSEAS_PLAYERS and is_overseas

            if over_limit:
                remaining.append(player)
                continue

            # Ensure WK
            if "Wicket-Keeper" in role and wk_count == 0 and len(xi) < 11:
                xi.append(player)
                if is_overseas:
                    overseas_count += 1
                wk_count += 1
                continue

            remaining.append(player)

        # Second pass: fill by score, respecting overseas limit
        for player in remaining:
            if len(xi) >= 11:
                break
            is_overseas = player.get("is_overseas", False)
            if is_overseas and overseas_count >= self.MAX_OVERSEAS_PLAYERS:
                continue
            role = player["role"]
            if "Wicket-Keeper" in role and wk_count >= 2:
                continue
            xi.append(player)
            if is_overseas:
                overseas_count += 1
            if "Wicket-Keeper" in role:
                wk_count += 1
            elif role == "Bowler":
                bowler_count += 1
            elif "All-rounder" in role:
                allrounder_count += 1
            else:
                batsman_count += 1

        # Ensure 11 players
        if len(xi) < 11:
            for player in available:
                if player not in xi and len(xi) < 11:
                    xi.append(player)

        return xi[:11]

    def _apply_weather_adjustments(
        self,
        t1_score: float,
        t2_score: float,
        weather_data: dict,
        toss_decision: str,
        time_of_day: str
    ) -> Tuple[float, float, Optional[dict]]:
        """
        Apply weather-based adjustments to team scores.

        Real-time weather data significantly impacts match outcomes:
        - High dew favors chasing teams
        - High humidity affects ball swing
        - Rain probability impacts team selection
        - Wind speed affects boundary scoring

        Returns:
            Tuple of (adjusted_t1_score, adjusted_t2_score, weather_factor_insight)
        """
        dew_risk = weather_data.get("dew_risk", "MODERATE")
        humidity = weather_data.get("humidity_pct", 60)
        temp = weather_data.get("temp_c", 30)
        rain_prob = weather_data.get("rain_prob_pct", 0)
        wind_speed = weather_data.get("wind_kmh", 10)

        adjustment_t1 = 0
        adjustment_t2 = 0
        impact_level = "low"
        details = []

        # 1. Dew Factor Impact (most significant in evening matches)
        if time_of_day in ("night", "day_night"):
            if dew_risk == "HIGH":
                # Significant advantage for chasing team
                if toss_decision == "field":  # Team 2 batting second
                    adjustment_t2 += 8
                    impact_level = "high"
                    details.append(f"Heavy dew ({weather_data.get('dewpoint_c', 18)}°C dew point) - batting second much easier")
                else:  # Team 1 batting second
                    adjustment_t1 += 8
                    impact_level = "high"
                    details.append(f"Heavy dew ({weather_data.get('dewpoint_c', 18)}°C dew point) - batting second much easier")
            elif dew_risk == "MODERATE":
                # Moderate advantage for chasing team
                if toss_decision == "field":
                    adjustment_t2 += 4
                    impact_level = "medium"
                    details.append("Moderate dew expected - slight advantage batting second")
                else:
                    adjustment_t1 += 4
                    impact_level = "medium"
                    details.append("Moderate dew expected - slight advantage batting second")

        # 2. Humidity Impact on swing bowling
        if humidity > 75:
            # High humidity helps swing bowlers early on
            details.append(f"High humidity ({humidity}%) - swing bowlers will be effective early")
            # Minimal score adjustment as it affects both teams
        elif humidity < 40:
            # Dry conditions - less swing, better for batting
            adjustment_t1 += 1
            adjustment_t2 += 1
            details.append(f"Low humidity ({humidity}%) - less swing, better batting conditions")

        # 3. Rain Probability Impact
        if rain_prob > 50:
            # High rain risk - DLS scenarios favor chasing
            if toss_decision == "field":
                adjustment_t2 += 3
            else:
                adjustment_t1 += 3
            if impact_level == "low":
                impact_level = "medium"
            details.append(f"High rain probability ({rain_prob}%) - DLS may favor chasing team")
        elif rain_prob > 30:
            details.append(f"Moderate rain risk ({rain_prob}%) - match may be affected")

        # 4. Temperature Impact
        if temp > 35:
            # Very hot conditions - fatigue factor for fielding team
            details.append(f"Hot conditions ({temp}°C) - fielding fatigue may be a factor")
        elif temp < 20:
            # Cooler conditions - ball may swing more
            details.append(f"Cool conditions ({temp}°C) - ball may swing more with new ball")

        # 5. Wind Speed Impact
        if wind_speed > 25:
            # Strong winds affect boundary hitting and fielding
            details.append(f"Strong winds ({wind_speed} km/h) - may affect boundaries and catches")
            adjustment_t1 += 2  # Both teams benefit from wind-assisted boundaries
            adjustment_t2 += 2

        # Apply adjustments
        t1_score += adjustment_t1
        t2_score += adjustment_t2

        # Create weather factor insight
        if details:
            weather_factor = {
                "factor": "Real-Time Weather Conditions",
                "detail": " | ".join(details),
                "impact": impact_level
            }
        else:
            weather_factor = None

        return t1_score, t2_score, weather_factor

    def _apply_monte_carlo_variation(
        self,
        base_value: float,
        variation_pct: float = 10.0,
        min_val: float = 0.0,
        max_val: float = 1.0
    ) -> float:
        """
        Apply random variation to a base value for Monte Carlo simulation.

        Args:
            base_value: The base value to vary
            variation_pct: Percentage variation to apply (e.g., 10 = ±10%)
            min_val: Minimum allowed value
            max_val: Maximum allowed value

        Returns:
            Varied value within bounds
        """
        # Generate random variation using normal distribution
        variation = random.gauss(0, variation_pct / 100.0)
        varied_value = base_value * (1 + variation)

        # Ensure bounds
        return max(min_val, min(max_val, varied_value))

    def _run_single_simulation(
        self,
        team1: str,
        team2: str,
        venue: str,
        match_type: str,
        time_of_day: str,
        toss_winner: str,
        toss_decision: str,
        injured_players: List[str],
        weather_data: Optional[dict],
        apply_variation: bool = True
    ) -> Tuple[float, float]:
        """
        Run a single Monte Carlo simulation with random variations.

        Returns:
            Tuple of (team1_probability, team2_probability)
        """
        # Calculate base scores
        t1_score, t2_score, _ = self._calculate_scores(
            team1, team2, venue, match_type, time_of_day,
            toss_winner, toss_decision, injured_players,
        )

        # Apply weather adjustments if available
        if weather_data and not weather_data.get("error"):
            t1_score, t2_score, _ = self._apply_weather_adjustments(
                t1_score, t2_score, weather_data, toss_decision, time_of_day
            )

        if apply_variation:
            # Apply random variations to simulate uncertainty
            # Form variation: ±15% (form can be volatile)
            t1_form_var = self._apply_monte_carlo_variation(
                self._get_recent_form_score(team1),
                variation_pct=15.0
            )
            t2_form_var = self._apply_monte_carlo_variation(
                self._get_recent_form_score(team2),
                variation_pct=15.0
            )

            # Momentum variation: ±20% (momentum is highly variable)
            t1_mom_var = self._apply_monte_carlo_variation(
                self._calculate_momentum(team1),
                variation_pct=20.0
            )
            t2_mom_var = self._apply_monte_carlo_variation(
                self._calculate_momentum(team2),
                variation_pct=20.0
            )

            # Squad strength variation: ±10% (injuries, form on the day)
            t1_squad_var = self._apply_monte_carlo_variation(
                self._calculate_squad_strength(team1, injured_players),
                variation_pct=10.0,
                min_val=0.3,
                max_val=1.2
            )
            t2_squad_var = self._apply_monte_carlo_variation(
                self._calculate_squad_strength(team2, injured_players),
                variation_pct=10.0,
                min_val=0.3,
                max_val=1.2
            )

            # Apply variations to scores
            # Recalculate with varied form
            form_adjustment_t1 = (t1_form_var - self._get_recent_form_score(team1)) * self.WEIGHTS["recent_form"]
            form_adjustment_t2 = (t2_form_var - self._get_recent_form_score(team2)) * self.WEIGHTS["recent_form"]
            t1_score += form_adjustment_t1
            t2_score += form_adjustment_t2

            # Recalculate with varied momentum
            mom_adjustment_t1 = (t1_mom_var - self._calculate_momentum(team1)) * self.WEIGHTS["momentum"]
            mom_adjustment_t2 = (t2_mom_var - self._calculate_momentum(team2)) * self.WEIGHTS["momentum"]
            t1_score += mom_adjustment_t1
            t2_score += mom_adjustment_t2

            # Apply squad strength multiplier variation
            base_squad_t1 = self._calculate_squad_strength(team1, injured_players)
            base_squad_t2 = self._calculate_squad_strength(team2, injured_players)
            if base_squad_t1 > 0:
                t1_score = t1_score / base_squad_t1 * t1_squad_var
            if base_squad_t2 > 0:
                t2_score = t2_score / base_squad_t2 * t2_squad_var

            # Add random match-day performance variation (±5%)
            t1_score *= (1 + random.gauss(0, 0.05))
            t2_score *= (1 + random.gauss(0, 0.05))

        # Calculate probabilities using sigmoid
        score_diff = t1_score - t2_score
        exponent = score_diff / 30.0
        sigmoid = 1 / (1 + math.exp(-exponent))

        t1_prob = sigmoid * 100
        t2_prob = (1 - sigmoid) * 100

        return t1_prob, t2_prob

    def _monte_carlo_predict(
        self,
        team1: str,
        team2: str,
        venue: str,
        match_type: str,
        time_of_day: str,
        toss_winner: str,
        toss_decision: str,
        injured_players: List[str],
        weather_data: Optional[dict],
        num_simulations: int = 1000
    ) -> Tuple[float, float, float]:
        """
        Run Monte Carlo simulation to predict match outcome with uncertainty quantification.

        Args:
            num_simulations: Number of Monte Carlo simulations to run (default: 1000)

        Returns:
            Tuple of (team1_probability, team2_probability, confidence_score)
        """
        t1_probs = []
        t2_probs = []

        # Run multiple simulations
        for _ in range(num_simulations):
            t1_prob, t2_prob = self._run_single_simulation(
                team1, team2, venue, match_type, time_of_day,
                toss_winner, toss_decision, injured_players, weather_data,
                apply_variation=True
            )
            t1_probs.append(t1_prob)
            t2_probs.append(t2_prob)

        # Calculate statistics
        t1_mean = np.mean(t1_probs)
        t2_mean = np.mean(t2_probs)
        t1_std = np.std(t1_probs)
        t2_std = np.std(t2_probs)

        # Confidence is inversely related to standard deviation
        # Lower std = higher confidence
        avg_std = (t1_std + t2_std) / 2

        # Calculate confidence score (0-1 scale)
        # Lower std (< 5%) = very high confidence
        # Higher std (> 15%) = low confidence
        if avg_std < 5:
            confidence_score = 0.95
        elif avg_std < 8:
            confidence_score = 0.85
        elif avg_std < 12:
            confidence_score = 0.70
        elif avg_std < 18:
            confidence_score = 0.55
        else:
            confidence_score = 0.40

        return round(t1_mean, 1), round(t2_mean, 1), confidence_score

    def predict(self, match_params: dict) -> dict:
        """
        Generate match prediction with enhanced accuracy using:
        - Monte Carlo simulation with 1000+ iterations
        - Logistic transformation for realistic probabilities
        - Comprehensive factor analysis
        - Context-aware confidence scoring
        - Real-time weather and dew factor integration
        """
        team1 = match_params["team1"]
        team2 = match_params["team2"]
        venue = match_params["venue"]
        match_type = match_params.get("match_type", "league")
        time_of_day = match_params.get("time_of_day", "day_night")
        toss_winner = match_params.get("toss_winner", "")
        toss_decision = match_params.get("toss_decision", "bat")
        injured_players = match_params.get("injured_players", [])
        weather_data = match_params.get("weather_data")  # Optional weather data
        num_simulations = match_params.get("num_simulations", 1000)  # Default: 1000 simulations
        use_monte_carlo = match_params.get("use_monte_carlo", True)  # Enable by default

        if team1 not in self.teams:
            return {"error": f"Unknown team: {team1}"}
        if team2 not in self.teams:
            return {"error": f"Unknown team: {team2}"}

        # Use Monte Carlo simulation for improved accuracy
        if use_monte_carlo:
            t1_prob, t2_prob, mc_confidence = self._monte_carlo_predict(
                team1, team2, venue, match_type, time_of_day,
                toss_winner, toss_decision, injured_players, weather_data,
                num_simulations
            )
        else:
            # Fallback to original deterministic method
            t1_score, t2_score, factors = self._calculate_scores(
                team1, team2, venue, match_type, time_of_day,
                toss_winner, toss_decision, injured_players,
            )

            # Apply weather-based adjustments if weather data is provided
            if weather_data and not weather_data.get("error"):
                t1_score, t2_score, weather_factor = self._apply_weather_adjustments(
                    t1_score, t2_score, weather_data, toss_decision, time_of_day
                )

            # Calculate probabilities using sigmoid
            score_diff = t1_score - t2_score
            exponent = score_diff / 30.0
            sigmoid = 1 / (1 + math.exp(-exponent))

            t1_prob = round(sigmoid * 100, 1)
            t2_prob = round((1 - sigmoid) * 100, 1)
            mc_confidence = None

        # Get detailed factors for analysis (using deterministic calculation)
        t1_score, t2_score, factors = self._calculate_scores(
            team1, team2, venue, match_type, time_of_day,
            toss_winner, toss_decision, injured_players,
        )

        # Apply weather-based adjustments to factors if weather data is provided
        if weather_data and not weather_data.get("error"):
            t1_score, t2_score, weather_factor = self._apply_weather_adjustments(
                t1_score, t2_score, weather_data, toss_decision, time_of_day
            )
            if weather_factor:
                factors.append(weather_factor)

        # Ensure probabilities sum to 100% (handle rounding)
        if t1_prob + t2_prob != 100.0:
            t2_prob = round(100.0 - t1_prob, 1)

        winner = team1 if t1_prob >= t2_prob else team2
        margin = abs(t1_prob - t2_prob)

        # More nuanced confidence levels
        # If Monte Carlo is used, incorporate MC confidence
        if mc_confidence is not None:
            # Combine margin and MC confidence
            if margin > 25 and mc_confidence > 0.80:
                confidence = "Very High"
            elif margin > 15 and mc_confidence > 0.70:
                confidence = "High"
            elif margin > 8 or mc_confidence > 0.60:
                confidence = "Medium"
            elif margin > 3 or mc_confidence > 0.50:
                confidence = "Low"
            else:
                confidence = "Very Low"
        else:
            # Original confidence calculation
            if margin > 25:
                confidence = "Very High"
            elif margin > 15:
                confidence = "High"
            elif margin > 8:
                confidence = "Medium"
            elif margin > 3:
                confidence = "Low"
            else:
                confidence = "Very Low"

        t1_xi = self._get_playing_xi(team1, venue, injured_players)
        t2_xi = self._get_playing_xi(team2, venue, injured_players)

        venue_info = self.venues.get(venue, {})

        # Enhance venue info with venue_stats module data
        venue_profile = get_venue_profile(venue)
        venue_info["pitch_profile"] = venue_profile.get("type", "balanced")
        venue_info["historical_avg_score"] = venue_profile.get("avg_first_innings", 170)
        venue_info["chasing_success_rate"] = venue_profile.get("chasing_success_pct", 50)

        form_data = {
            team1: self.recent_form.get(team1, {}),
            team2: self.recent_form.get(team2, {}),
        }
        h2h_data = self.get_h2h(team1, team2)

        result = {
            "predicted_winner": winner,
            "predicted_winner_name": self.teams[winner]["name"],
            "team1": team1,
            "team1_name": self.teams[team1]["name"],
            "team1_color": self.teams[team1]["color"],
            "team2": team2,
            "team2_name": self.teams[team2]["name"],
            "team2_color": self.teams[team2]["color"],
            "team1_probability": t1_prob,
            "team2_probability": t2_prob,
            "confidence": confidence,
            "team1_playing_xi": t1_xi,
            "team2_playing_xi": t2_xi,
            "key_insights": factors,
            "venue_info": venue_info,
            "venue": venue,
            "h2h": h2h_data,
            "recent_form": form_data,
            "match_type": match_type,
            "time_of_day": time_of_day,
            "model_version": "2.2-monte-carlo",  # Track model version
        }

        # Add Monte Carlo metadata if used
        if use_monte_carlo and mc_confidence is not None:
            result["monte_carlo"] = {
                "enabled": True,
                "simulations": num_simulations,
                "confidence_score": round(mc_confidence, 3)
            }

        # Add weather data if available
        if weather_data and not weather_data.get("error"):
            result["weather"] = weather_data

        return result
