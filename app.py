"""
Blog Subscriber Backend.
Subscribers in MongoDB Atlas. Emails via Gmail SMTP.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient

app = Flask(__name__)
CORS(app)

# MongoDB Atlas
MONGO_URI = "mongodb+srv://enriquecool8_db_user:superconcorde@upsc.pfexmr5.mongodb.net/blog?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client["blog"]
subscribers = db["subscribers"]

# Gmail SMTP
GMAIL_USER = "vaibhavsinghfcos@gmail.com"
GMAIL_APP_PASSWORD = "umqubaljxhgbcepb"
GMAIL_FROM_NAME = "Vaibhav Singh's Blog"


def send_email(to_email, subject, message):
    """Send email via Gmail SMTP."""
    msg = MIMEMultipart()
    msg["From"] = f"{GMAIL_FROM_NAME} <{GMAIL_USER}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(message, "plain"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.send_message(msg)


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
            send_email(sub["email"], subject, message)
            sent += 1
        except Exception as e:
            print(f"Failed to send to {sub['email']}: {e}")
            failed += 1

    return jsonify({"sent": sent, "failed": failed, "total": len(active)})


@app.route("/feedback", methods=["POST"])
def feedback():
    data = request.get_json()
    subject = (data or {}).get("subject", "Blog Feedback")
    message = (data or {}).get("message", "")
    if not message:
        return jsonify({"error": "Message required"}), 400

    try:
        send_email(GMAIL_USER, subject, message)
        return jsonify({"message": "Feedback sent!"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    try:
        client.admin.command("ping")
        return jsonify({"status": "ok", "db": "connected"})
    except:
        return jsonify({"status": "ok", "db": "disconnected"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
