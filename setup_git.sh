#!/bin/bash
# Configure git for auto-committing subscribers.json on Render
# The GITHUB_TOKEN env var must be set in Render's dashboard

git config user.email "vaibhavsinghfcos@gmail.com"
git config user.name "Blog Backend"

if [ -n "$GITHUB_TOKEN" ]; then
    git remote set-url origin "https://${GITHUB_TOKEN}@github.com/vaibhav016/blog-backend.git"
    echo "Git remote configured with token"
else
    echo "WARNING: GITHUB_TOKEN not set. Subscriber persistence will not work."
fi
