#!/bin/bash
set -e

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

gh release create "$NEW_VERSION" --generate-notes --title "Release $NEW_VERSION"
