"""
Blog Subscriber Backend.
Subscribers stored in MongoDB Atlas.
"""

from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import requests as http_requests

app = Flask(__name__)
CORS(app)

# MongoDB Atlas
MONGO_URI = "mongodb+srv://enriquecool8_db_user:superconcorde@upsc.pfexmr5.mongodb.net/blog?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client["blog"]
subscribers = db["subscribers"]

# EmailJS config
EMAILJS_SERVICE_ID = "service_pqbgayk"
EMAILJS_TEMPLATE_ID = "template_9errptn"
EMAILJS_PUBLIC_KEY = "azdoAUitATQqW6aeO"
EMAILJS_PRIVATE_KEY = "hw1FGHdZIdByi6gExYk7D"


@app.route("/subscribe", methods=["POST"])
def subscribe():
    data = request.get_json()
    email = (data or {}).get("email", "").strip().lower()
    if not email or "@" not in email:
        return jsonify({"error": "Invalid email"}), 400

    if subscribers.find_one({"email": email}):
        return jsonify({"message": "Already subscribed"}), 200

    subscribers.insert_one({
        "email": email,
        "subscribedAt": datetime.utcnow().isoformat(),
        "active": True,
    })
    return jsonify({"message": "Subscribed!", "total": subscribers.count_documents({})}), 201


@app.route("/subscribers", methods=["GET"])
def list_subs():
    all_subs = list(subscribers.find({}, {"_id": 0}))
    active = [s for s in all_subs if s.get("active", True)]
    return jsonify({"total": len(all_subs), "active": len(active), "subscribers": all_subs})


@app.route("/subscribers", methods=["DELETE"])
def remove_sub():
    data = request.get_json()
    email = (data or {}).get("email", "").strip().lower()
    subscribers.delete_one({"email": email})
    return jsonify({"message": f"Removed {email}", "total": subscribers.count_documents({})})


@app.route("/notify", methods=["POST"])
def notify():
    data = request.get_json()
    subject = (data or {}).get("subject", "")
    message = (data or {}).get("message", "")
    if not subject or not message:
        return jsonify({"error": "Subject and message required"}), 400

    active = list(subscribers.find({"active": True}, {"_id": 0}))
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
            if resp.status_code == 200:
                sent += 1
            else:
                failed += 1
        except:
            failed += 1

    return jsonify({"sent": sent, "failed": failed, "total": len(active)})


@app.route("/health", methods=["GET"])
def health():
    try:
        client.admin.command("ping")
        return jsonify({"status": "ok", "db": "connected"})
    except:
        return jsonify({"status": "ok", "db": "disconnected"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
