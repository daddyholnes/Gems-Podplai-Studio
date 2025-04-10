#!/bin/bash

# This script creates a fresh repository with only the current files
# This is a simpler alternative to cleaning the Git history

echo "Creating a backup (just in case)..."
cp -r . ../ai-chat-studio-backup

echo "Removing .git directory to start fresh..."
rm -rf .git

echo "Initializing a new repository..."
git init

echo "Configuring Git..."
read -p "Enter your Git user email: " GIT_EMAIL
read -p "Enter your Git user name: " GIT_NAME
git config --local user.email "$GIT_EMAIL"
git config --local user.name "$GIT_NAME"

echo "Adding current files (without sensitive data)..."
git add .

echo "Creating initial commit..."
git commit -m "Initial commit of AI Chat Studio"

echo "Setting up GitHub remote..."
read -p "Enter your GitHub token: " GITHUB_TOKEN
git remote add origin https://$GITHUB_TOKEN@github.com/daddyholnes/Gemini-PlayPod.git

echo "Fresh repository is ready. Now you can push with:"
echo "git push -f origin main"