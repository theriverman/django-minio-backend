#!/bin/bash
set -e

# in case we forgot doing this manually before
(uv pip compile pyproject.toml -o requirements.txt > /dev/null 2>&1)
echo "requirements.txt regenerated"

# make sure we're in sync with remote
git fetch
git pull
git push
git push --tags

LATEST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "0.0.0")
IFS='.' read -ra VERSION <<< "$LATEST_TAG"
MAJOR=${VERSION[0]}
MINOR=${VERSION[1]}
PATCH=${VERSION[2]}

echo "Current: $LATEST_TAG"
echo "1) Patch: $MAJOR.$MINOR.$((PATCH+1))"
echo "2) Minor: $MAJOR.$((MINOR+1)).0"
echo "3) Major: $((MAJOR+1)).0.0"
read -p "Choice: " choice

case $choice in
    1) NEW_VERSION="$MAJOR.$MINOR.$((PATCH+1))";;
    2) NEW_VERSION="$MAJOR.$((MINOR+1)).0";;
    3) NEW_VERSION="$((MAJOR+1)).0.0";;
    *) echo "Invalid"; exit 1;;
esac

# create a new tag
git tag -a "$NEW_VERSION" -m "$NEW_VERSION"
git push --tags

(uv pip compile pyproject.toml -o requirements.txt > /dev/null 2>&1)
gh release create "$NEW_VERSION" --generate-notes --title "Release $NEW_VERSION"
