"""
Real-time data fetcher for IPL 2026 Match Predictor.

Supports multiple API sources with intelligent fallbacks and in-memory caching.
API keys are read exclusively from environment variables — never hardcoded.

Priority order for every data type:
  1. External live API (CricAPI → RapidAPI/Cricbuzz → News API / GNews)
  2. In-memory cache (if not yet expired)
  3. Static local JSON fallback
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    import requests as _requests
except ImportError:  # pragma: no cover
    _requests = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# ── Cache TTLs (seconds) ──────────────────────────────────────────────────────
CACHE_TTL: Dict[str, int] = {
    "standings": 5 * 60,       # 5 minutes
    "injuries": 5 * 60,        # 5 minutes
    "orange_cap": 10 * 60,     # 10 minutes
    "purple_cap": 10 * 60,     # 10 minutes
    "live_matches": 60,         # 1 minute — live scores refresh fast
}

# IPL 2026 series IDs (best-guess / update when official IDs are published)
IPL_2026_SERIES_ID_CRICAPI = os.environ.get(
    "IPL_2026_SERIES_ID_CRICAPI", "d5a498c8-7596-4b93-8ab0-e0efc3345312"
)
IPL_2026_SERIES_ID_CRICBUZZ = os.environ.get("IPL_2026_SERIES_ID_CRICBUZZ", "9237")


# ── Simple in-memory cache ────────────────────────────────────────────────────

class _DataCache:
    """Thread-safe-ish in-memory cache with per-entry TTL."""

    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if not entry:
            return None
        if time.time() - entry["ts"] > entry["ttl"]:
            del self._store[key]
            return None
        return entry["data"]

    def set(self, key: str, data: Any, ttl: int) -> None:
        self._store[key] = {"data": data, "ts": time.time(), "ttl": ttl}

    def age(self, key: str) -> Optional[float]:
        """Return seconds since last set, or None if not cached."""
        entry = self._store.get(key)
        return time.time() - entry["ts"] if entry else None


# ── Main fetcher class ────────────────────────────────────────────────────────

class RealTimeDataFetcher:
    """
    Multi-source real-time data fetcher.

    Configure external API access by setting environment variables:
        CRIC_API_KEY      — CricAPI.com key
        RAPIDAPI_KEY      — RapidAPI key (Cricbuzz endpoints)
        NEWS_API_KEY      — NewsAPI.org key
        GNEWS_API_KEY     — GNews.io key
    """

    def __init__(self, data_dir: str) -> None:
        self.data_dir = data_dir
        self.cache = _DataCache()

        # API keys from environment (never hardcoded)
        self.cric_api_key: str = os.environ.get("CRIC_API_KEY", "")
        self.rapidapi_key: str = os.environ.get("RAPIDAPI_KEY", "")
        self.news_api_key: str = os.environ.get("NEWS_API_KEY", "")
        self.gnews_api_key: str = os.environ.get("GNEWS_API_KEY", "")

        # Preload static fallback data
        self._static_form: dict = self._load_json("recent_form.json")
        self._static_cap: dict = self._load_json("orange_purple_cap.json")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _load_json(self, filename: str) -> dict:
        path = os.path.join(self.data_dir, filename)
        try:
            with open(path) as fh:
                return json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            logger.warning("Could not load %s: %s", filename, exc)
            return {}

    def _get(self, url: str, headers: Optional[dict] = None,
             params: Optional[dict] = None) -> Optional[dict]:
        """HTTP GET with timeout; returns parsed JSON or None."""
        if _requests is None:
            logger.warning("requests library is not installed; cannot fetch live data")
            return None
        try:
            resp = _requests.get(url, headers=headers or {}, params=params or {}, timeout=8)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.warning("HTTP request failed for %s: %s", url, exc)
            return None

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    # ── Points Table / Standings ──────────────────────────────────────────────

    def get_standings(self) -> dict:
        """Return current IPL 2026 standings from the best available source."""
        cached = self.cache.get("standings")
        if cached:
            return cached

        result = (
            (self.cric_api_key and self._standings_cricapi())
            or (self.rapidapi_key and self._standings_rapidapi())
            or self._standings_static()
        )

        self.cache.set("standings", result, CACHE_TTL["standings"])
        return result

    def _standings_cricapi(self) -> Optional[dict]:
        data = self._get(
            "https://api.cricapi.com/v1/series_points",
            params={"apikey": self.cric_api_key, "id": IPL_2026_SERIES_ID_CRICAPI},
        )
        if not data or data.get("status") != "success":
            return None
        rows = [
            {
                "team": e.get("teamInfo", {}).get("shortname", ""),
                "name": e.get("teamInfo", {}).get("name", ""),
                "matches": e.get("matchesPlayed", 0),
                "wins": e.get("wins", 0),
                "losses": e.get("loss", 0),
                "points": e.get("points", 0),
                "nrr": e.get("nrr", 0),
            }
            for e in data.get("data", [])
        ]
        return {"data": rows, "source": "cric_api", "timestamp": self._now_iso()} if rows else None

    def _standings_rapidapi(self) -> Optional[dict]:
        data = self._get(
            f"https://cricbuzz-cricket.p.rapidapi.com/series/v1/{IPL_2026_SERIES_ID_CRICBUZZ}/points-table",
            headers={
                "X-RapidAPI-Key": self.rapidapi_key,
                "X-RapidAPI-Host": "cricbuzz-cricket.p.rapidapi.com",
            },
        )
        if not data:
            return None
        rows = []
        for group in data.get("pointsTable", []):
            for e in group.get("pointsTableInfo", []):
                ti = e.get("teamInfo", {})
                rows.append({
                    "team": ti.get("teamSName", ""),
                    "name": ti.get("teamName", ""),
                    "matches": e.get("matchesPlayed", 0),
                    "wins": e.get("matchesWon", 0),
                    "losses": e.get("matchesLost", 0),
                    "points": e.get("points", 0),
                    "nrr": e.get("nrrValue", 0),
                })
        return (
            {"data": rows, "source": "cricbuzz", "timestamp": self._now_iso()}
            if rows else None
        )

    _TEAM_NAMES: Dict[str, str] = {
        "MI": "Mumbai Indians", "CSK": "Chennai Super Kings",
        "RCB": "Royal Challengers Bangalore", "KKR": "Kolkata Knight Riders",
        "SRH": "Sunrisers Hyderabad", "DC": "Delhi Capitals",
        "RR": "Rajasthan Royals", "PBKS": "Punjab Kings",
        "GT": "Gujarat Titans", "LSG": "Lucknow Super Giants",
    }

    def _standings_static(self) -> dict:
        rows: List[dict] = []
        for short, data in self._static_form.items():
            mp = data.get("matches_played", 0)
            wp = data.get("win_percentage", 50) / 100
            wins = round(wp * mp)
            rows.append({
                "team": short,
                "name": self._TEAM_NAMES.get(short, short),
                "matches": mp,
                "wins": wins,
                "losses": mp - wins,
                "points": data.get("points", 0),
                "nrr": data.get("nrr", 0),
                "form": data.get("last5", []),
            })
        rows.sort(key=lambda r: (-r["points"], -float(r.get("nrr") or 0)))
        return {"data": rows, "source": "static", "timestamp": self._now_iso()}

    # ── Injury Updates ────────────────────────────────────────────────────────

    def get_injuries(self) -> dict:
        """Return latest player injury / availability news."""
        cached = self.cache.get("injuries")
        if cached:
            return cached

        result = (
            (self.news_api_key and self._injuries_newsapi())
            or (self.gnews_api_key and self._injuries_gnews())
            or self._injuries_static()
        )

        self.cache.set("injuries", result, CACHE_TTL["injuries"])
        return result

    def _injuries_newsapi(self) -> Optional[dict]:
        data = self._get(
            "https://newsapi.org/v2/everything",
            params={
                "q": "IPL 2026 injury player unavailable",
                "apiKey": self.news_api_key,
                "pageSize": 15,
                "sortBy": "publishedAt",
                "language": "en",
            },
        )
        if not data or data.get("status") != "ok":
            return None
        items = [
            {"text": a.get("title", ""), "url": a.get("url", "")}
            for a in data.get("articles", [])[:10]
            if a.get("title")
        ]
        return (
            {"data": items, "source": "news_api", "timestamp": self._now_iso()}
            if items else None
        )

    def _injuries_gnews(self) -> Optional[dict]:
        data = self._get(
            "https://gnews.io/api/v4/search",
            params={
                "q": "IPL 2026 player injury",
                "token": self.gnews_api_key,
                "lang": "en",
                "max": 10,
            },
        )
        if not data:
            return None
        items = [
            {"text": a.get("title", ""), "url": a.get("url", "")}
            for a in data.get("articles", [])
            if a.get("title")
        ]
        return (
            {"data": items, "source": "gnews_api", "timestamp": self._now_iso()}
            if items else None
        )

    # Static injury seed data — curated for IPL 2026 pre-season
    _STATIC_INJURIES: List[dict] = [
        {"player": "Ishan Kishan",      "team": "MI",   "status": "Uncertain",
         "injury": "Personal reasons — availability TBC"},
        {"player": "KL Rahul",           "team": "LSG",  "status": "Fit",
         "injury": "Recovered from thigh injury"},
        {"player": "Jofra Archer",       "team": "MI",   "status": "Uncertain",
         "injury": "Elbow management — workload monitoring"},
        {"player": "Ravindra Jadeja",    "team": "CSK",  "status": "Fit",
         "injury": "Fully recovered from knee surgery"},
        {"player": "Shreyas Iyer",       "team": "PBKS", "status": "Fit",
         "injury": "Back issue resolved"},
        {"player": "T Natarajan",        "team": "SRH",  "status": "Uncertain",
         "injury": "Side strain — under observation"},
        {"player": "Prasidh Krishna",    "team": "RR",   "status": "Doubtful",
         "injury": "Stress fracture — return date unknown"},
        {"player": "Deepak Chahar",      "team": "CSK",  "status": "Fit",
         "injury": "Hamstring fully healed"},
        {"player": "Rinku Singh",        "team": "KKR",  "status": "Fit",
         "injury": "Minor shoulder strain — cleared"},
    ]

    def _injuries_static(self) -> dict:
        return {
            "data": self._STATIC_INJURIES,
            "source": "static",
            "timestamp": self._now_iso(),
        }

    # ── Orange Cap (top run-scorers) ──────────────────────────────────────────

    def get_orange_cap(self) -> dict:
        """Return IPL 2026 Orange Cap standings (top run-scorers)."""
        cached = self.cache.get("orange_cap")
        if cached:
            return cached

        result = (
            (self.cric_api_key and self._cap_cricapi("batting"))
            or (self.rapidapi_key and self._orange_cap_rapidapi())
            or self._cap_static("orange")
        )

        self.cache.set("orange_cap", result, CACHE_TTL["orange_cap"])
        return result

    # ── Purple Cap (top wicket-takers) ────────────────────────────────────────

    def get_purple_cap(self) -> dict:
        """Return IPL 2026 Purple Cap standings (top wicket-takers)."""
        cached = self.cache.get("purple_cap")
        if cached:
            return cached

        result = (
            (self.cric_api_key and self._cap_cricapi("bowling"))
            or (self.rapidapi_key and self._purple_cap_rapidapi())
            or self._cap_static("purple")
        )

        self.cache.set("purple_cap", result, CACHE_TTL["purple_cap"])
        return result

    def _cap_cricapi(self, stat_type: str) -> Optional[dict]:
        data = self._get(
            "https://api.cricapi.com/v1/series_stats",
            params={"apikey": self.cric_api_key, "id": IPL_2026_SERIES_ID_CRICAPI},
        )
        if not data or data.get("status") != "success":
            return None

        stats = data.get("data", {})
        if stat_type == "batting":
            entries = stats.get("batting", [])
            if not entries:
                return None
            players = [
                {
                    "rank": i + 1,
                    "player": p.get("name", ""),
                    "team": p.get("team", ""),
                    "runs": p.get("runs", 0),
                    "innings": p.get("innings", 0),
                    "average": p.get("average", 0),
                    "strike_rate": p.get("strikeRate", 0),
                    "highest": p.get("highest", 0),
                    "fifties": p.get("fifties", 0),
                    "hundreds": p.get("hundreds", 0),
                }
                for i, p in enumerate(entries[:10])
            ]
        else:  # bowling
            entries = stats.get("bowling", [])
            if not entries:
                return None
            players = [
                {
                    "rank": i + 1,
                    "player": p.get("name", ""),
                    "team": p.get("team", ""),
                    "wickets": p.get("wickets", 0),
                    "innings": p.get("innings", 0),
                    "economy": p.get("economy", 0),
                    "average": p.get("average", 0),
                    "best": p.get("bestBowling", "0/0"),
                }
                for i, p in enumerate(entries[:10])
            ]

        source_key = "cric_api_batting" if stat_type == "batting" else "cric_api_bowling"
        return {"data": players, "source": source_key, "timestamp": self._now_iso()}

    def _orange_cap_rapidapi(self) -> Optional[dict]:
        data = self._get(
            f"https://cricbuzz-cricket.p.rapidapi.com/series/v1/{IPL_2026_SERIES_ID_CRICBUZZ}/stats",
            headers={
                "X-RapidAPI-Key": self.rapidapi_key,
                "X-RapidAPI-Host": "cricbuzz-cricket.p.rapidapi.com",
            },
            params={"statsType": "mostRuns"},
        )
        if not data:
            return None
        players = []
        for i, entry in enumerate(data.get("values", [])[:10]):
            app_index = entry.get("appIndex", {})
            vals = entry.get("values", [])
            players.append({
                "rank": i + 1,
                "player": app_index.get("seoTitle", ""),
                "team": "",
                "runs": vals[0] if vals else 0,
                "innings": vals[1] if len(vals) > 1 else 0,
                "average": vals[3] if len(vals) > 3 else 0,
                "strike_rate": vals[4] if len(vals) > 4 else 0,
            })
        return (
            {"data": players, "source": "cricbuzz", "timestamp": self._now_iso()}
            if players else None
        )

    def _purple_cap_rapidapi(self) -> Optional[dict]:
        data = self._get(
            f"https://cricbuzz-cricket.p.rapidapi.com/series/v1/{IPL_2026_SERIES_ID_CRICBUZZ}/stats",
            headers={
                "X-RapidAPI-Key": self.rapidapi_key,
                "X-RapidAPI-Host": "cricbuzz-cricket.p.rapidapi.com",
            },
            params={"statsType": "mostWickets"},
        )
        if not data:
            return None
        players = []
        for i, entry in enumerate(data.get("values", [])[:10]):
            app_index = entry.get("appIndex", {})
            vals = entry.get("values", [])
            players.append({
                "rank": i + 1,
                "player": app_index.get("seoTitle", ""),
                "team": "",
                "wickets": vals[0] if vals else 0,
                "innings": vals[1] if len(vals) > 1 else 0,
                "economy": vals[3] if len(vals) > 3 else 0,
                "average": vals[4] if len(vals) > 4 else 0,
            })
        return (
            {"data": players, "source": "cricbuzz", "timestamp": self._now_iso()}
            if players else None
        )

    def _cap_static(self, cap_type: str) -> dict:
        key = "orange_cap" if cap_type == "orange" else "purple_cap"
        return {
            "data": self._static_cap.get(key, []),
            "source": "static",
            "timestamp": self._now_iso(),
        }

    # ── Live / Recent Match Scores ─────────────────────────────────────────────

    def get_live_matches(self) -> dict:
        """Return live or most recent IPL 2026 match scores."""
        cached = self.cache.get("live_matches")
        if cached:
            return cached

        result = (
            (self.cric_api_key and self._live_cricapi())
            or (self.rapidapi_key and self._live_rapidapi())
            or {"data": [], "source": "none",
                "message": "No live matches — configure CRIC_API_KEY or RAPIDAPI_KEY for live scores",
                "timestamp": self._now_iso()}
        )

        self.cache.set("live_matches", result, CACHE_TTL["live_matches"])
        return result

    def _live_cricapi(self) -> Optional[dict]:
        data = self._get(
            "https://api.cricapi.com/v1/currentMatches",
            params={"apikey": self.cric_api_key},
        )
        if not data or data.get("status") != "success":
            return None

        ipl = [
            m for m in data.get("data", [])
            if "IPL" in m.get("series", "") or "Indian Premier League" in m.get("name", "")
        ]
        matches = [
            {
                "id": m.get("id", ""),
                "name": m.get("name", ""),
                "status": m.get("status", ""),
                "venue": m.get("venue", ""),
                "date": m.get("date", ""),
                "teams": m.get("teams", []),
                "score": m.get("score", []),
            }
            for m in ipl
        ]
        return {"data": matches, "source": "cric_api", "timestamp": self._now_iso()}

    def _live_rapidapi(self) -> Optional[dict]:
        data = self._get(
            "https://cricbuzz-cricket.p.rapidapi.com/matches/v1/live",
            headers={
                "X-RapidAPI-Key": self.rapidapi_key,
                "X-RapidAPI-Host": "cricbuzz-cricket.p.rapidapi.com",
            },
        )
        if not data:
            return None

        matches: List[dict] = []
        for type_match in data.get("typeMatches", []):
            for series_match in type_match.get("seriesMatches", []):
                wrapper = series_match.get("seriesAdWrapper", {})
                if "IPL" not in wrapper.get("seriesName", ""):
                    continue
                for m in wrapper.get("matches", []):
                    info = m.get("matchInfo", {})
                    score = m.get("matchScore", {})
                    matches.append({
                        "id": info.get("matchId", ""),
                        "name": (
                            f"{info.get('team1', {}).get('teamSName', '')} vs "
                            f"{info.get('team2', {}).get('teamSName', '')}"
                        ),
                        "status": info.get("status", ""),
                        "venue": info.get("venueInfo", {}).get("ground", ""),
                        "teams": [
                            info.get("team1", {}).get("teamSName", ""),
                            info.get("team2", {}).get("teamSName", ""),
                        ],
                        "score": score,
                    })

        return {"data": matches, "source": "cricbuzz", "timestamp": self._now_iso()}
