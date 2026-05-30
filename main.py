"""
main.py — Flask Server Entry Point for Google Cloud Run
Exposes a secured /run-job endpoint for Cloud Scheduler triggers.
"""

import os

from flask import Flask, request, jsonify

from src.bot_logic import run_daily_automation
from src.config import CRON_SECRET_KEY

app = Flask(__name__)


@app.route("/run-job", methods=["POST"])
def trigger_bot():
    """
    Secured endpoint that triggers the daily LinkedIn automation.
    Cloud Scheduler sends a POST request with a Bearer token for authentication.
    """
    # --- Security: Validate the Bearer token ---
    auth_header = request.headers.get("Authorization")
    expected_header = f"Bearer {CRON_SECRET_KEY}"

    if auth_header != expected_header:
        return jsonify({"error": "Unauthorized"}), 401

    # --- Run the automation pipeline ---
    result = run_daily_automation()

    if result["status"] == "success":
        return jsonify(result), 200
    else:
        return jsonify(result), 500


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for Cloud Run readiness probes."""
    return jsonify({"status": "healthy", "service": "linkedin-ai-bot"}), 200


if __name__ == "__main__":
    # Cloud Run assigns the PORT environment variable
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
