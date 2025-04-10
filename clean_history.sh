#!/bin/bash

# This script uses git-filter-repo to completely remove sensitive files from Git history
# More info: https://github.com/newren/git-filter-repo

echo "Installing git-filter-repo..."
pip install git-filter-repo

echo "Creating a backup (just in case)..."
cp -r . ../ai-chat-studio-backup

echo "Removing sensitive files from Git history..."
git filter-repo --force --invert-paths --path attached_assets/Pasted--type-service-account-project-id-camera-calibration-beta-private-key-id-51a46-1744225793713.txt --path service-account-key.json --path attached_assets/Pasted--workspace-Step-1-Create-a-temporary-directory-for-the-clean-repository-mkdir-p-clean-repo--1744233321916.txt

echo "Adding files back that are still needed..."
git add .

echo "Creating commit without sensitive files..."
git commit -m "Clean repository of sensitive information"

echo "Cleaning is complete. Now you can force push with:"
echo "./upload_to_github.sh"
echo "and select option 2 to force push."