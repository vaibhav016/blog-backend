"""
Blog Subscriber Backend.
Subscribers stored in JSONBin.io (free, persistent, no database needed).
"""

import os
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests as http_requests

app = Flask(__name__)
CORS(app)

# EmailJS config
EMAILJS_SERVICE_ID = "service_pqbgayk"
EMAILJS_TEMPLATE_ID = "template_9errptn"
EMAILJS_PUBLIC_KEY = "azdoAUitATQqW6aeO"
EMAILJS_PRIVATE_KEY = "hw1FGHdZIdByi6gExYk7D"

# JSONBin.io config (set these env vars in Render)
JSONBIN_BIN_ID = os.environ.get("JSONBIN_BIN_ID", "")
JSONBIN_API_KEY = os.environ.get("JSONBIN_API_KEY", "")
JSONBIN_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}"


def load_subscribers():
    try:
        r = http_requests.get(JSONBIN_URL, headers={"X-Master-Key": JSONBIN_API_KEY}, timeout=10)
        record = r.json().get("record", {})
        if isinstance(record, list):
            return record
        return record.get("users", [])
    except:
        return []


def save_subscribers(subs):
    try:
        http_requests.put(JSONBIN_URL, json={"users": subs},
                         headers={"Content-Type": "application/json", "X-Master-Key": JSONBIN_API_KEY}, timeout=10)
    except Exception as e:
        print(f"Save failed: {e}")


@app.route("/subscribe", methods=["POST"])
def subscribe():
    data = request.get_json()
    email = (data or {}).get("email", "").strip().lower()
    if not email or "@" not in email:
        return jsonify({"error": "Invalid email"}), 400

    subs = load_subscribers()
    if any(s["email"] == email for s in subs):
        return jsonify({"message": "Already subscribed"}), 200

    subs.append({"email": email, "subscribedAt": datetime.utcnow().isoformat(), "active": True})
    save_subscribers(subs)
    return jsonify({"message": "Subscribed!", "total": len(subs)}), 201


@app.route("/subscribers", methods=["GET"])
def list_subscribers():
    subs = load_subscribers()
    active = [s for s in subs if s.get("active", True)]
    return jsonify({"total": len(subs), "active": len(active), "subscribers": subs})


@app.route("/subscribers", methods=["DELETE"])
def remove_subscriber():
    data = request.get_json()
    email = (data or {}).get("email", "").strip().lower()
    subs = [s for s in load_subscribers() if s["email"] != email]
    save_subscribers(subs)
    return jsonify({"message": f"Removed {email}", "total": len(subs)})


@app.route("/notify", methods=["POST"])
def notify():
    data = request.get_json()
    subject = (data or {}).get("subject", "")
    message = (data or {}).get("message", "")
    if not subject or not message:
        return jsonify({"error": "Subject and message required"}), 400

    active = [s for s in load_subscribers() if s.get("active", True)]
    if not active:
        return jsonify({"error": "No active subscribers"}), 400

    sent = failed = 0
    for sub in active:
        try:
            resp = http_requests.post("https://api.emailjs.com/api/v1.0/email/send", json={
                "service_id": EMAILJS_SERVICE_ID, "template_id": EMAILJS_TEMPLATE_ID,
                "user_id": EMAILJS_PUBLIC_KEY, "accessToken": EMAILJS_PRIVATE_KEY,
                "template_params": {"to_email": sub["email"], "subject": subject, "message": message},
            })
            sent += 1 if resp.status_code == 200 else 0
            failed += 0 if resp.status_code == 200 else 1
        except:
            failed += 1

    return jsonify({"sent": sent, "failed": failed, "total": len(active)})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "storage": "jsonbin", "bin_configured": bool(JSONBIN_BIN_ID)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
