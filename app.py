"""
Blog Subscriber Backend — lightweight Flask API.

Endpoints:
  POST /subscribe        — add a subscriber
  GET  /subscribers      — list all subscribers (admin)
  DELETE /subscribers     — remove a subscriber (admin)
  POST /notify           — send email to all active subscribers (admin)

Stores subscribers in a local JSON file. Uses EmailJS for sending.
Run: python3 app.py
"""

import json
import os
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

DATA_FILE = os.path.join(os.path.dirname(__file__), "subscribers.json")

# EmailJS config
EMAILJS_SERVICE_ID = "service_pqbgayk"
EMAILJS_TEMPLATE_ID = "template_9errptn"
EMAILJS_PUBLIC_KEY = "azdoAUitATQqW6aeO"


def load_subscribers():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_subscribers(subs):
    with open(DATA_FILE, "w") as f:
        json.dump(subs, f, indent=2)


@app.route("/subscribe", methods=["POST"])
def subscribe():
    data = request.get_json()
    email = (data or {}).get("email", "").strip().lower()

    if not email or "@" not in email:
        return jsonify({"error": "Invalid email"}), 400

    subs = load_subscribers()

    # Check duplicate
    if any(s["email"] == email for s in subs):
        return jsonify({"message": "Already subscribed"}), 200

    subs.append({
        "email": email,
        "subscribedAt": datetime.utcnow().isoformat(),
        "active": True,
    })
    save_subscribers(subs)

    return jsonify({"message": "Subscribed!", "total": len(subs)}), 201


@app.route("/subscribers", methods=["GET"])
def list_subscribers():
    subs = load_subscribers()
    active = [s for s in subs if s.get("active", True)]
    return jsonify({
        "total": len(subs),
        "active": len(active),
        "subscribers": subs,
    })


@app.route("/subscribers", methods=["DELETE"])
def remove_subscriber():
    data = request.get_json()
    email = (data or {}).get("email", "").strip().lower()

    subs = load_subscribers()
    subs = [s for s in subs if s["email"] != email]
    save_subscribers(subs)

    return jsonify({"message": f"Removed {email}", "total": len(subs)})


@app.route("/notify", methods=["POST"])
def notify():
    data = request.get_json()
    subject = (data or {}).get("subject", "")
    message = (data or {}).get("message", "")

    if not subject or not message:
        return jsonify({"error": "Subject and message required"}), 400

    subs = load_subscribers()
    active = [s for s in subs if s.get("active", True)]

    if not active:
        return jsonify({"error": "No active subscribers"}), 400

    sent = 0
    failed = 0

    for sub in active:
        try:
            resp = requests.post(
                "https://api.emailjs.com/api/v1.0/email/send",
                json={
                    "service_id": EMAILJS_SERVICE_ID,
                    "template_id": EMAILJS_TEMPLATE_ID,
                    "user_id": EMAILJS_PUBLIC_KEY,
                    "template_params": {
                        "to_email": sub["email"],
                        "subject": subject,
                        "message": message,
                    },
                },
            )
            if resp.status_code == 200:
                sent += 1
            else:
                failed += 1
        except Exception:
            failed += 1

    return jsonify({"sent": sent, "failed": failed, "total": len(active)})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    print("Blog Subscriber Backend running on http://localhost:5050")
    print(f"Subscribers stored in: {DATA_FILE}")
    app.run(host="0.0.0.0", port=5050, debug=True)
