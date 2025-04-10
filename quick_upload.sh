#!/bin/bash

# Simplified script for quick GitHub upload without interactive prompts
# For AI Chat Studio

# Initialize or re-initialize Git if needed
if [ ! -d .git ]; then
  echo "Initializing Git repository..."
  git init
fi

# Configure Git with default values
echo "Configuring Git..."
git config --local user.email "replit@example.com"
git config --local user.name "Replit User"

# Check if GitHub token is available in environment
if [ -z "$GITHUB_TOKEN" ]; then
  echo "ERROR: GitHub token not found in environment. Please set the GITHUB_TOKEN secret in Replit."
  exit 1
fi

# Set up the remote repository
echo "Setting up remote repository..."
REPO_NAME="Gems-Podplai-Studio"
if git remote | grep -q "origin"; then
  # Remote already exists, update it
  git remote set-url origin "https://${GITHUB_TOKEN}@github.com/daddyholnes/${REPO_NAME}.git"
else
  # Add new remote
  git remote add origin "https://${GITHUB_TOKEN}@github.com/daddyholnes/${REPO_NAME}.git"
fi

# Add files to Git
echo "Adding files to Git..."
git add .

# Create commit
echo "Creating commit..."
git commit -m "Update AI Chat Studio for GitHub installation"

# Push to GitHub
echo "Pushing to GitHub..."
git push -f origin main || git push -f origin master

echo "Done! Your code has been pushed to GitHub."
echo "Repository URL: https://github.com/daddyholnes/Gems-Podplai-Studio"