"""
Blog Subscriber Backend — lightweight Flask API.

Endpoints:
  POST /subscribe        — add a subscriber
  GET  /subscribers      — list all subscribers (admin)
  DELETE /subscribers     — remove a subscriber (admin)
  POST /notify           — send email to all active subscribers (admin)

Stores subscribers in subscribers.json, auto-committed to the Git repo
so data persists across Render redeploys.

Run: python3 app.py
"""

import json
import os
import subprocess
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests as http_requests

app = Flask(__name__)
CORS(app)

REPO_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(REPO_DIR, "subscribers.json")

# EmailJS config
EMAILJS_SERVICE_ID = "service_pqbgayk"
EMAILJS_TEMPLATE_ID = "template_9errptn"
EMAILJS_PUBLIC_KEY = "azdoAUitATQqW6aeO"
EMAILJS_PRIVATE_KEY = "hw1FGHdZIdByi6gExYk7D"

# Git config for auto-commit
GIT_REMOTE = os.environ.get("GIT_REMOTE", "origin")
GIT_BRANCH = os.environ.get("GIT_BRANCH", "master")


def git_setup():
    """Configure git credentials using GITHUB_TOKEN env var."""
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        subprocess.run(["git", "config", "user.email", "vaibhavsinghfcos@gmail.com"], cwd=REPO_DIR, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Blog Backend"], cwd=REPO_DIR, capture_output=True)
        repo_url = f"https://{token}@github.com/vaibhav016/blog-backend.git"
        # Check if remote exists
        r = subprocess.run(["git", "remote"], cwd=REPO_DIR, capture_output=True)
        if GIT_REMOTE in r.stdout.decode():
            subprocess.run(["git", "remote", "set-url", GIT_REMOTE, repo_url], cwd=REPO_DIR, capture_output=True)
        else:
            subprocess.run(["git", "remote", "add", GIT_REMOTE, repo_url], cwd=REPO_DIR, capture_output=True)
        print("Git configured with GITHUB_TOKEN")
    else:
        print("WARNING: GITHUB_TOKEN not set. Persistence disabled.")


def git_pull():
    """Pull latest subscribers.json from repo on startup."""
    try:
        subprocess.run(
            ["git", "pull", GIT_REMOTE, GIT_BRANCH],
            cwd=REPO_DIR, capture_output=True, timeout=30,
        )
    except Exception as e:
        print(f"Git pull failed: {e}")


def git_push_subscribers():
    """Commit and push subscribers.json to repo."""
    try:
        subprocess.run(
            ["git", "add", "subscribers.json"],
            cwd=REPO_DIR, capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", f"Update subscribers {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"],
            cwd=REPO_DIR, capture_output=True,
        )
        result = subprocess.run(
            ["git", "push", GIT_REMOTE, GIT_BRANCH],
            cwd=REPO_DIR, capture_output=True, timeout=30,
        )
        if result.returncode == 0:
            print("Subscribers pushed to repo")
        else:
            print(f"Git push failed: {result.stderr.decode()}")
    except Exception as e:
        print(f"Git push error: {e}")


def load_subscribers():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_subscribers(subs):
    with open(DATA_FILE, "w") as f:
        json.dump(subs, f, indent=2)
    git_push_subscribers()


@app.route("/subscribe", methods=["POST"])
def subscribe():
    data = request.get_json()
    email = (data or {}).get("email", "").strip().lower()

    if not email or "@" not in email:
        return jsonify({"error": "Invalid email"}), 400

    subs = load_subscribers()

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
            resp = http_requests.post(
                "https://api.emailjs.com/api/v1.0/email/send",
                json={
                    "service_id": EMAILJS_SERVICE_ID,
                    "template_id": EMAILJS_TEMPLATE_ID,
                    "user_id": EMAILJS_PUBLIC_KEY,
                    "accessToken": EMAILJS_PRIVATE_KEY,
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
                print(f"EmailJS error for {sub['email']}: {resp.status_code} {resp.text}")
                failed += 1
        except Exception as e:
            print(f"Exception for {sub['email']}: {e}")
            failed += 1

    return jsonify({"sent": sent, "failed": failed, "total": len(active)})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/debug-git", methods=["GET"])
def debug_git():
    """Check git status and config for debugging."""
    results = {}
    for cmd_name, cmd in [
        ("token_set", ["bash", "-c", "echo ${GITHUB_TOKEN:+yes}"]),
        ("remote", ["git", "remote", "-v"]),
        ("status", ["git", "status", "--short"]),
        ("log", ["git", "log", "--oneline", "-3"]),
    ]:
        try:
            r = subprocess.run(cmd, cwd=REPO_DIR, capture_output=True, timeout=10)
            results[cmd_name] = r.stdout.decode().strip()
            if r.stderr.decode().strip():
                results[cmd_name + "_err"] = r.stderr.decode().strip()
        except Exception as e:
            results[cmd_name] = str(e)
    return jsonify(results)


import threading

def init_git():
    """Run git setup and pull in a background thread so it doesn't block server startup."""
    git_setup()
    git_pull()

threading.Thread(target=init_git, daemon=True).start()

if __name__ == "__main__":
    print("Blog Subscriber Backend running on http://localhost:5050")
    print(f"Subscribers stored in: {DATA_FILE}")
    app.run(host="0.0.0.0", port=5050, debug=True)
