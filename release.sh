#!/bin/bash
set -euo pipefail

ensure_clean_tree() {
    if ! git diff --quiet || ! git diff --cached --quiet; then
        echo "Working tree has uncommitted changes. Commit or stash them before releasing."
        exit 1
    fi
}

ensure_clean_tree

UPSTREAM_REF=$(git rev-parse --abbrev-ref --symbolic-full-name "@{u}" 2>/dev/null || true)
if [[ -z "$UPSTREAM_REF" ]]; then
    echo "Current branch has no upstream tracking reference. Set it with:"
    echo "  git branch --set-upstream-to origin/<branch>"
    exit 1
fi

UPSTREAM=${UPSTREAM_REF#refs/remotes/}
REMOTE_NAME=${UPSTREAM%%/*}
git fetch --quiet "$REMOTE_NAME"

LOCAL_HEAD=$(git rev-parse HEAD)
REMOTE_HEAD=$(git rev-parse "@{u}")
if [[ "$LOCAL_HEAD" != "$REMOTE_HEAD" ]]; then
    echo "Local HEAD ($LOCAL_HEAD) is not in sync with $UPSTREAM ($REMOTE_HEAD). Push/pull before releasing."
    exit 1
fi

LATEST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "0.0.0")
IFS='.' read -ra VERSION <<< "$LATEST_TAG"
MAJOR=${VERSION[0]:-0}
MINOR=${VERSION[1]:-0}
PATCH=${VERSION[2]:-0}

echo "Current: $LATEST_TAG"
echo "1) Patch: $MAJOR.$MINOR.$((PATCH+1))"
echo "2) Minor: $MAJOR.$((MINOR+1)).0"
echo "3) Major: $((MAJOR+1)).0.0"
read -r -p "Choice: " choice

case $choice in
    1) NEW_VERSION="$MAJOR.$MINOR.$((PATCH+1))";;
    2) NEW_VERSION="$MAJOR.$((MINOR+1)).0";;
    3) NEW_VERSION="$((MAJOR+1)).0.0";;
    *) echo "Invalid"; exit 1;;
esac

# create a new tag
git tag -a "$NEW_VERSION" -m "$NEW_VERSION"
git push
git push --tags

gh release create "$NEW_VERSION" --generate-notes --title "Release $NEW_VERSION"
