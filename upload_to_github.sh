#!/bin/bash

# Script for safely uploading code to GitHub with merge conflict handling
# Updated for easy use with AI Chat Studio

# Initialize or re-initialize Git if needed
if [ ! -d .git ]; then
  echo "Initializing Git repository..."
  git init
fi

# Configure Git
echo "Configuring Git..."
read -p "Enter your Git user email: " GIT_EMAIL
read -p "Enter your Git user name: " GIT_NAME
git config --local user.email "$GIT_EMAIL"
git config --local user.name "$GIT_NAME"

# Check if GitHub token is available in environment or prompt for it
if [ -z "$GITHUB_TOKEN" ]; then
  echo "Please enter your GitHub Personal Access Token:"
  read -s GITHUB_TOKEN
fi

# Check and set the remote repository
echo "Setting up remote repository..."
if git remote | grep -q "origin"; then
  # Remote already exists, update it
  git remote set-url origin https://$GITHUB_TOKEN@github.com/daddyholnes/Gemini-PlayPod.git
else
  # Add new remote
  git remote add origin https://$GITHUB_TOKEN@github.com/daddyholnes/Gemini-PlayPod.git
fi

# Determine which strategy to use (check if repo exists and has content)
echo "Checking repository status..."
git fetch origin
REPO_EXISTS=$(git ls-remote --heads origin main || git ls-remote --heads origin master)

if [ -n "$REPO_EXISTS" ]; then
  echo "Remote repository exists and has content."
  echo "How would you like to proceed?"
  echo "1) Pull changes from remote and merge with local changes"
  echo "2) Force push local changes (overwrites remote repository!)"
  echo "3) Create a new branch with local changes"
  read -p "Select option (1-3, default: 1): " PUSH_OPTION
  PUSH_OPTION=${PUSH_OPTION:-1}
else
  # New repository, just do a normal push
  PUSH_OPTION=4
fi

# Add files to Git
echo "Adding files to Git..."
git add -A

# Create commit if there are changes
git diff-index --quiet HEAD || {
  echo "Creating commit..."
  read -p "Enter commit message (default: 'Update AI Chat Studio'): " COMMIT_MSG
  COMMIT_MSG=${COMMIT_MSG:-"Update AI Chat Studio"}
  git commit -m "$COMMIT_MSG"
}

# Push based on selected option
case $PUSH_OPTION in
  1)
    echo "Pulling changes from remote and merging..."
    # Try to find the default branch
    DEFAULT_BRANCH=$(git ls-remote --symref origin HEAD | grep -o 'refs/heads/[^"]*' | sed 's/refs\/heads\///')
    if [ -z "$DEFAULT_BRANCH" ]; then
      # If we can't determine the default branch, try main then master
      if git ls-remote --heads origin main | grep -q main; then
        DEFAULT_BRANCH="main"
      else
        DEFAULT_BRANCH="master"
      fi
    fi
    echo "Default branch is: $DEFAULT_BRANCH"
    
    # Pull and merge
    git pull origin $DEFAULT_BRANCH --allow-unrelated-histories
    
    # Push changes
    echo "Pushing merged changes..."
    git push origin $DEFAULT_BRANCH
    ;;
  2)
    echo "Force pushing local changes (this will overwrite remote repository)..."
    # Determine if main or master is the default branch
    if git ls-remote --heads origin main | grep -q main; then
      git push -f origin main
    else
      git push -f origin master
    fi
    ;;
  3)
    echo "Creating a new branch with local changes..."
    read -p "Enter branch name (default: 'update-ai-chat-studio'): " BRANCH_NAME
    BRANCH_NAME=${BRANCH_NAME:-"update-ai-chat-studio"}
    git checkout -b $BRANCH_NAME
    git push -u origin $BRANCH_NAME
    echo "Branch '$BRANCH_NAME' has been created and pushed to GitHub."
    echo "You can now create a pull request to merge these changes into the main branch."
    ;;
  4)
    echo "Pushing to new repository..."
    git push -u origin master || git push -u origin main
    ;;
esac

echo "Done! Your code has been pushed to GitHub."
echo "Repository URL: https://github.com/daddyholnes/Gemini-PlayPod"