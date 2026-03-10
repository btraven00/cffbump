#!/usr/bin/env python3
"""
Verification script for CFFBump test fixtures.
Validates that CITATION.cff was properly updated with authors and version.

Usage:
    python verify.py <fixture_name>
    python verify.py basic-repo
"""

import sys
import os
import yaml
from pathlib import Path


def verify_fixture(fixture_name):
    """
    Verify a test fixture was properly updated by cffbump.

    Args:
        fixture_name: Name of fixture directory (e.g., 'basic-repo')

    Returns:
        (success: bool, message: str)
    """
    fixture_dir = Path(__file__).parent / fixture_name
    cff_file = fixture_dir / "CITATION.cff"
    config_file = fixture_dir / "cffbump.config.yaml"

    # Check CITATION.cff exists
    if not cff_file.exists():
        return False, f"CITATION.cff not found in {fixture_dir}"

    # Load and validate CFF file
    try:
        with open(cff_file, "r") as f:
            cff_data = yaml.safe_load(f)
    except Exception as e:
        return False, f"Failed to parse CITATION.cff: {e}"

    # Validate CFF structure
    if not isinstance(cff_data, dict):
        return False, "CITATION.cff is not valid YAML"

    if "authors" not in cff_data:
        return False, "No authors found in CITATION.cff"

    if not isinstance(cff_data["authors"], list):
        return False, "Authors must be a list"

    if len(cff_data["authors"]) == 0:
        return False, "Authors list is empty"

    # Validate each author
    for i, author in enumerate(cff_data["authors"]):
        if not isinstance(author, dict):
            return False, f"Author {i} is not a dictionary"

        if "family-names" not in author:
            return False, f"Author {i} missing family-names"

    # Check version
    if "version" not in cff_data:
        return False, "No version found in CITATION.cff"

    version = cff_data["version"]
    if not isinstance(version, str):
        return False, f"Version must be string, got {type(version)}"

    # Validate version format
    try:
        parts = version.split(".")
        if len(parts) < 1:
            return False, f"Invalid version format: {version}"
        for part in parts:
            int(part)  # Ensure each part is numeric
    except ValueError:
        return False, f"Invalid version format: {version}"

    # Fixture-specific checks
    if fixture_name == "basic-repo":
        return verify_basic_repo(cff_data, cff_file)
    elif fixture_name == "crossref-repo":
        return verify_crossref_repo(cff_data, cff_file)
    elif fixture_name == "minimal-repo":
        return verify_minimal_repo(cff_data, cff_file)
    else:
        return False, f"Unknown fixture: {fixture_name}"


def verify_basic_repo(cff_data, cff_file):
    """Verify basic-repo fixture has Alice and Bob."""
    authors = cff_data["authors"]
    family_names = {author.get("family-names", "").lower() for author in authors}

    expected = {"smith", "jones"}
    if not expected.issubset(family_names):
        missing = expected - family_names
        return (
            False,
            f"basic-repo missing authors: {missing}. Found: {family_names}",
        )

    return True, f"✓ basic-repo: {len(authors)} authors merged correctly"


def verify_crossref_repo(cff_data, cff_file):
    """Verify crossref-repo fixture fetched authors from Crossref API."""
    authors = cff_data["authors"]

    # With Crossref enabled, should have more than just Charlie Brown
    if len(authors) < 2:
        return (
            False,
            f"crossref-repo should have authors from Crossref. Found: {len(authors)}",
        )

    family_names = [author.get("family-names", "") for author in authors]
    if "Brown" not in family_names:
        return False, "crossref-repo missing Charlie Brown"

    return True, f"✓ crossref-repo: {len(authors)} authors (including Crossref API)"


def verify_minimal_repo(cff_data, cff_file):
    """Verify minimal-repo has David Lee."""
    authors = cff_data["authors"]
    family_names = {author.get("family-names", "").lower() for author in authors}

    if "lee" not in family_names:
        return (
            False,
            f"minimal-repo missing David Lee. Found: {family_names}",
        )

    return True, f"✓ minimal-repo: {len(authors)} author(s)"


def main():
    if len(sys.argv) != 2:
        print("Usage: python verify.py <fixture_name>")
        print("Example: python verify.py basic-repo")
        sys.exit(1)

    fixture_name = sys.argv[1]
    success, message = verify_fixture(fixture_name)

    print(message)

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
