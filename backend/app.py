import os
import logging
from flask import Flask, jsonify, request
from flask_cors import CORS

from backend.predictor import IPLPredictor
from backend.data_fetcher import RealTimeDataFetcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder="../frontend", static_url_path="")
CORS(app)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
predictor = IPLPredictor(DATA_DIR)
fetcher = RealTimeDataFetcher(DATA_DIR)


# ── Serve frontend ──────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return app.send_static_file("index.html")


# ── Teams & venues ───────────────────────────────────────────────────────────────

@app.route("/api/teams", methods=["GET"])
def get_teams():
    return jsonify(predictor.get_all_teams())


@app.route("/api/venues", methods=["GET"])
def get_venues():
    return jsonify(predictor.get_all_venues())


@app.route("/api/squad/<team_short>", methods=["GET"])
def get_squad(team_short: str):
    squad = predictor.get_team_squad(team_short.upper())
    if not squad:
        return jsonify({"error": "Team not found"}), 404
    return jsonify(squad)


@app.route("/api/h2h/<team1>/<team2>", methods=["GET"])
def get_h2h(team1: str, team2: str):
    data = predictor.get_h2h(team1.upper(), team2.upper())
    return jsonify(data)


# ── Prediction ───────────────────────────────────────────────────────────────────

@app.route("/api/predict", methods=["POST"])
def predict():
    body = request.get_json(force=True)
    if not body:
        return jsonify({"error": "No JSON body provided"}), 400

    required = ["team1", "team2", "venue"]
    for field in required:
        if field not in body:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    # Normalise
    body["team1"] = body["team1"].upper()
    body["team2"] = body["team2"].upper()

    if body["team1"] == body["team2"]:
        return jsonify({"error": "team1 and team2 must be different"}), 400

    result = predictor.predict(body)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


# ── Health check ─────────────────────────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "teams_loaded": len(predictor.teams)})


# ── Real-time data (v2) ───────────────────────────────────────────────────────────

@app.route("/api/v2/standings", methods=["GET"])
def standings():
    return jsonify(fetcher.get_standings())


@app.route("/api/v2/injuries", methods=["GET"])
def injuries():
    return jsonify(fetcher.get_injuries())


@app.route("/api/orange-cap", methods=["GET"])
def orange_cap():
    return jsonify(fetcher.get_orange_cap())


@app.route("/api/purple-cap", methods=["GET"])
def purple_cap():
    return jsonify(fetcher.get_purple_cap())


@app.route("/api/live-matches", methods=["GET"])
def live_matches():
    return jsonify(fetcher.get_live_matches())


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
