"""
IPL Historical Data Processor
================================
Drop this file into your /backend folder.

STEP 1: Download the dataset from Kaggle:
  https://www.kaggle.com/datasets/patrickb1912/ipl-complete-dataset-20082020
  OR the updated one:
  https://www.kaggle.com/datasets/vora1011/ipl-2008-to-2021-all-match-dataset

  You need: matches.csv  (one row per match)

STEP 2: Put matches.csv inside your /backend folder.

STEP 3: Run this script once:
  python ipl_data_processor.py

STEP 4: It will generate historical_data.json in /backend.
  The predictor will automatically load this and use real stats
  instead of hardcoded values.
"""

import pandas as pd
import json
import os
from collections import defaultdict

# ── Team name normalisations ────────────────────────────────────────────────
# The Kaggle CSV uses old/inconsistent names. Map them to current 2026 names.
TEAM_MAP = {
    "Mumbai Indians": "Mumbai Indians",
    "Chennai Super Kings": "Chennai Super Kings",
    "Royal Challengers Bangalore": "Royal Challengers Bengaluru",
    "Royal Challengers Bengaluru": "Royal Challengers Bengaluru",
    "Kolkata Knight Riders": "Kolkata Knight Riders",
    "Delhi Capitals": "Delhi Capitals",
    "Delhi Daredevils": "Delhi Capitals",
    "Sunrisers Hyderabad": "Sunrisers Hyderabad",
    "Rajasthan Royals": "Rajasthan Royals",
    "Punjab Kings": "Punjab Kings",
    "Kings XI Punjab": "Punjab Kings",
    "Lucknow Super Giants": "Lucknow Super Giants",
    "Gujarat Titans": "Gujarat Titans",
    "Deccan Chargers": None,          # defunct – kept for history, excluded from H2H
    "Pune Warriors": None,
    "Rising Pune Supergiant": None,
    "Rising Pune Supergiants": None,
    "Kochi Tuskers Kerala": None,
    "Gujarat Lions": None,
}

ACTIVE_TEAMS = {v for v in TEAM_MAP.values() if v is not None}

# ── Venue normalisations ────────────────────────────────────────────────────
VENUE_MAP = {
    "Eden Gardens": "Eden Gardens, Kolkata",
    "Wankhede Stadium": "Wankhede Stadium, Mumbai",
    "M Chinnaswamy Stadium": "M. Chinnaswamy Stadium, Bengaluru",
    "M. Chinnaswamy Stadium": "M. Chinnaswamy Stadium, Bengaluru",
    "Rajiv Gandhi International Stadium, Uppal": "Rajiv Gandhi International Stadium, Hyderabad",
    "Rajiv Gandhi International Stadium": "Rajiv Gandhi International Stadium, Hyderabad",
    "MA Chidambaram Stadium, Chepauk": "MA Chidambaram Stadium, Chennai",
    "MA Chidambaram Stadium": "MA Chidambaram Stadium, Chennai",
    "Sawai Mansingh Stadium": "Sawai Mansingh Stadium, Jaipur",
    "Punjab Cricket Association IS Bindra Stadium, Mohali": "Punjab Cricket Association Stadium, Mohali",
    "Punjab Cricket Association Stadium, Mohali": "Punjab Cricket Association Stadium, Mohali",
    "Narendra Modi Stadium, Ahmedabad": "Narendra Modi Stadium, Ahmedabad",
    "Sardar Patel Stadium, Motera": "Narendra Modi Stadium, Ahmedabad",
    "Arun Jaitley Stadium": "Arun Jaitley Stadium, Delhi",
    "Arun Jaitley Stadium, Delhi": "Arun Jaitley Stadium, Delhi",
    "Feroz Shah Kotla": "Arun Jaitley Stadium, Delhi",
    "BRSABV Ekana Cricket Stadium, Lucknow": "BRSABV Ekana Cricket Stadium, Lucknow",
    "Dr DY Patil Sports Academy": "Dr DY Patil Sports Academy, Mumbai",
    "Bharat Ratna Shri Atal Bihari Vajpayee Ekana Cricket Stadium": "BRSABV Ekana Cricket Stadium, Lucknow",
}

def normalise_team(name):
    return TEAM_MAP.get(name, name)

def normalise_venue(name):
    for k, v in VENUE_MAP.items():
        if k.lower() in str(name).lower():
            return v
    return name


def process(csv_path="matches.csv", out_path="historical_data.json"):
    print(f"📂 Loading {csv_path} ...")
    df = pd.read_csv(csv_path)

    # ── normalise columns ───────────────────────────────────────────────────
    df["team1"]   = df["team1"].map(normalise_team)
    df["team2"]   = df["team2"].map(normalise_team)
    df["winner"]  = df["winner"].map(normalise_team)
    df["venue"]   = df["venue"].apply(normalise_venue)
    df["toss_winner"] = df["toss_winner"].map(normalise_team)

    # drop rows with unknown teams (defunct franchises)
    df = df[df["team1"].isin(ACTIVE_TEAMS) & df["team2"].isin(ACTIVE_TEAMS)]
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.sort_values("date")

    print(f"✅ {len(df)} matches loaded after filtering.\n")

    # ────────────────────────────────────────────────────────────────────────
    # 1. HEAD-TO-HEAD  { "MI_vs_CSK": { "MI": 14, "CSK": 10, "no_result": 1 } }
    # ────────────────────────────────────────────────────────────────────────
    h2h = {}
    for _, row in df.iterrows():
        t1, t2, winner = row["team1"], row["team2"], row["winner"]
        key = "_vs_".join(sorted([t1, t2]))
        if key not in h2h:
            h2h[key] = defaultdict(int)
        if pd.isna(winner):
            h2h[key]["no_result"] += 1
        else:
            h2h[key][winner] += 1

    # convert defaultdict → plain dict
    h2h = {k: dict(v) for k, v in h2h.items()}

    # ────────────────────────────────────────────────────────────────────────
    # 2. TEAM WIN RATES  (overall + per-venue + recent form last 20 matches)
    # ────────────────────────────────────────────────────────────────────────
    team_stats = {}
    for team in ACTIVE_TEAMS:
        played = df[(df["team1"] == team) | (df["team2"] == team)]
        wins   = played[played["winner"] == team]

        # recent form: last 20 matches
        recent = played.tail(20)
        recent_wins = recent[recent["winner"] == team]

        # per-venue win rate
        venue_stats = {}
        for venue, vdf in played.groupby("venue"):
            v_wins = vdf[vdf["winner"] == team]
            venue_stats[venue] = {
                "played": len(vdf),
                "won": len(v_wins),
                "win_rate": round(len(v_wins) / len(vdf), 3) if len(vdf) else 0.0
            }

        team_stats[team] = {
            "total_played": len(played),
            "total_won": len(wins),
            "overall_win_rate": round(len(wins) / len(played), 3) if len(played) else 0.0,
            "recent_form_win_rate": round(len(recent_wins) / len(recent), 3) if len(recent) else 0.0,
            "venue_stats": venue_stats
        }

    # ────────────────────────────────────────────────────────────────────────
    # 3. VENUE PROFILES  (chasing success, toss advantage, avg scores)
    # ────────────────────────────────────────────────────────────────────────
    venue_profiles = {}
    for venue, vdf in df.groupby("venue"):
        total = len(vdf)
        if total < 5:
            continue  # skip venues with too few matches

        toss_winner_won = vdf[vdf["toss_winner"] == vdf["winner"]]
        toss_win_rate   = round(len(toss_winner_won) / total, 3)

        # toss decision breakdown
        field_first = vdf[vdf["toss_decision"] == "field"]
        bat_first   = vdf[vdf["toss_decision"] == "bat"]

        # teams that chose to field and won
        field_won = field_first[field_first["toss_winner"] == field_first["winner"]]
        bat_won   = bat_first[bat_first["toss_winner"] == bat_first["winner"]]

        chasing_success = round(len(field_won) / len(field_first), 3) if len(field_first) else 0.5

        venue_profiles[venue] = {
            "total_matches": total,
            "toss_winner_win_rate": toss_win_rate,
            "chasing_success_rate": chasing_success,
            "teams_prefer_field": round(len(field_first) / total, 3),
        }

    # ────────────────────────────────────────────────────────────────────────
    # 4. SEASON-BY-SEASON CHAMPION
    # ────────────────────────────────────────────────────────────────────────
    champions = {}
    if "season" in df.columns:
        for season, sdf in df.groupby("season"):
            finals = sdf[sdf.get("match_type", sdf.get("result", "")) == "Final"] \
                     if "match_type" in sdf.columns else sdf.tail(1)
            if not finals.empty:
                champ = finals.iloc[-1]["winner"]
                if pd.notna(champ):
                    champions[str(season)] = champ

    # ────────────────────────────────────────────────────────────────────────
    # 5. TITLES WON per team
    # ────────────────────────────────────────────────────────────────────────
    titles = defaultdict(int)
    for champ in champions.values():
        titles[champ] += 1

    # ────────────────────────────────────────────────────────────────────────
    # OUTPUT
    # ────────────────────────────────────────────────────────────────────────
    output = {
        "meta": {
            "generated_at": pd.Timestamp.now().isoformat(),
            "total_matches_processed": len(df),
            "seasons": sorted(df["season"].unique().tolist()) if "season" in df.columns else [],
        },
        "head_to_head": h2h,
        "team_stats": team_stats,
        "venue_profiles": venue_profiles,
        "champions": champions,
        "titles_won": dict(titles),
    }

    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"✅ Saved → {out_path}")
    print(f"\n📊 Summary:")
    print(f"   H2H matchups computed  : {len(h2h)}")
    print(f"   Active teams tracked   : {len(team_stats)}")
    print(f"   Venue profiles built   : {len(venue_profiles)}")
    print(f"   Seasons covered        : {output['meta']['seasons']}")


if __name__ == "__main__":
    if not os.path.exists("matches.csv"):
        print("❌ matches.csv not found in current directory.")
        print("   Download it from:")
        print("   https://www.kaggle.com/datasets/patrickb1912/ipl-complete-dataset-20082020")
    else:
        process()
