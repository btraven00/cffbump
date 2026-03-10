#!/bin/bash
# Integration test for cffbump
# This script demonstrates the full workflow

set -e

echo "=========================================="
echo "CFFBump Integration Test"
echo "=========================================="
echo

# Ensure we're in the right directory
cd "$(dirname "$0")"

echo "1. Running unit tests..."
python3 test_cffbump.py
echo

echo "2. Current state:"
echo "   - CITATION.cff version: $(grep '^version:' CITATION.cff | cut -d' ' -f2)"
echo "   - Total authors before: $(grep -c 'family-names:' CITATION.cff || echo 0)"
echo

echo "3. Running cffbump script..."
python3 .github/scripts/cffbump.py
echo

echo "4. Updated state:"
echo "   - CITATION.cff version: $(grep '^version:' CITATION.cff | cut -d' ' -f2)"
echo "   - Total authors after: $(grep -c 'family-names:' CITATION.cff || echo 0)"
echo

echo "5. CITATION.cff preview:"
head -20 CITATION.cff
echo "   ..."
echo

echo "=========================================="
echo "✓ Integration test completed successfully!"
echo "=========================================="
