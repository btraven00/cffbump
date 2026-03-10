#!/bin/bash
# Setup test fixtures from git bundles
# Usage: ./setup.sh <fixture_name>

set -e

FIXTURE_NAME=$1
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUNDLE_FILE="$SCRIPT_DIR/${FIXTURE_NAME}.bundle"
FIXTURE_DIR="$SCRIPT_DIR/${FIXTURE_NAME}"

if [ -z "$FIXTURE_NAME" ]; then
    echo "Usage: $0 <fixture_name>"
    echo "Example: $0 basic-repo"
    exit 1
fi

if [ ! -f "$BUNDLE_FILE" ]; then
    echo "Error: Bundle file not found: $BUNDLE_FILE"
    exit 1
fi

# Remove existing fixture directory
if [ -d "$FIXTURE_DIR" ]; then
    rm -rf "$FIXTURE_DIR"
fi

# Create new repository from bundle
mkdir -p "$FIXTURE_DIR"
cd "$FIXTURE_DIR"
git clone "$BUNDLE_FILE" .

# Success message
echo "✓ Initialized $FIXTURE_NAME from bundle"
