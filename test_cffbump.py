"""
Unit tests for cffbump.py author extraction functions
"""

import os
import sys
import tempfile
import yaml
from pathlib import Path

# Add the scripts directory to the path
scripts_dir = os.path.join(os.path.dirname(__file__), ".github", "scripts")
sys.path.insert(0, scripts_dir)

import cffbump
from cffbump import (
    get_authors_from_md,
    get_authors_from_git,
    get_authors_from_crossref,
    match_author,
    merge_authors,
    load_config,
)


def test_get_authors_from_md():
    """Test parsing AUTHORS.md"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("""# Authors

- Alice Johnson
- Bob Smith (bob@example.com)
- Carol
""")
        f.flush()
        original_path = cffbump.AUTHORS_PATH
        cffbump.AUTHORS_PATH = f.name

        try:
            authors = get_authors_from_md()
            assert len(authors) == 3
            assert authors[0]["given-names"] == "Alice"
            assert authors[0]["family-names"] == "Johnson"
            assert authors[1]["given-names"] == "Bob"
            assert authors[1]["family-names"] == "Smith"
            assert authors[2]["family-names"] == "Carol"  # Single name
            assert "given-names" not in authors[2]
            print("PASS: test_get_authors_from_md passed")
        finally:
            cffbump.AUTHORS_PATH = original_path
            os.unlink(f.name)


def test_get_authors_from_git():
    """Test extracting authors from git history"""
    # This test runs in the actual repo - just verify it returns valid data
    authors = get_authors_from_git(min_commits=1)

    # Should return a list
    assert isinstance(authors, list)
    
    # If there are authors, they should have the required structure
    if authors:
        for author in authors:
            assert "family-names" in author
            # given-names is optional
            if "given-names" in author:
                assert isinstance(author["given-names"], str)
            assert isinstance(author["family-names"], str)
    
    family_names = {a["family-names"] for a in authors}
    print(f"  Found git authors: {family_names}")
    print("PASS: test_get_authors_from_git passed")


def test_match_author():
    """Test author exact matching"""
    author1 = {"given-names": "Alice", "family-names": "Johnson"}
    author2 = {"given-names": "Alice", "family-names": "Johnson"}
    author3 = {"given-names": "Alicia", "family-names": "Johnson"}
    author4 = {"given-names": "Alice", "family-names": "Smith"}
    author5 = {"family-names": "Johnson"}

    assert match_author(author1, author2) == True  # Exact match
    assert match_author(author1, author3) == False  # Different given names
    assert match_author(author1, author4) == False  # Different family name
    assert (
        match_author(author1, author5) == True
    )  # Same family name, one without given name
    print("PASS: test_match_author passed")


def test_match_author_initials():
    """Test author matching with initials"""
    # Single initial cases
    alice_full = {"given-names": "Alice", "family-names": "Johnson"}
    alice_initial = {"given-names": "A.", "family-names": "Johnson"}
    alice_initial_no_dot = {"given-names": "A", "family-names": "Johnson"}
    bob_initial = {"given-names": "B.", "family-names": "Johnson"}
    
    # Should match: full name with initial
    assert match_author(alice_full, alice_initial) == True
    assert match_author(alice_initial, alice_full) == True
    
    # Should match: initial with and without dot
    assert match_author(alice_initial, alice_initial_no_dot) == True
    
    # Should NOT match: different initials
    assert match_author(alice_initial, bob_initial) == False
    
    # Multiple names/initials
    alice_bob_full = {"given-names": "Alice Bob", "family-names": "Smith"}
    alice_bob_initials = {"given-names": "A. B.", "family-names": "Smith"}
    alice_bob_mixed = {"given-names": "Alice B.", "family-names": "Smith"}
    alice_carol_initials = {"given-names": "A. C.", "family-names": "Smith"}
    
    # Should match: multiple names with initials
    assert match_author(alice_bob_full, alice_bob_initials) == True
    assert match_author(alice_bob_full, alice_bob_mixed) == True
    assert match_author(alice_bob_initials, alice_bob_mixed) == True
    
    # Should NOT match: different middle name/initial
    assert match_author(alice_bob_initials, alice_carol_initials) == False
    
    print("PASS: test_match_author_initials passed")


def test_merge_authors():
    """Test author merging and deduplication"""
    source1 = [
        {"given-names": "Alice", "family-names": "Johnson"},
        {"given-names": "Bob", "family-names": "Smith"},
    ]
    source2 = [
        {"given-names": "Alice", "family-names": "Johnson"},  # Duplicate
        {"given-names": "Carol", "family-names": "Williams"},
    ]

    merged = merge_authors([source1, source2])

    # Should have 3 unique authors
    assert len(merged) == 3

    # Check that Alice from source2 didn't duplicate
    alices = [a for a in merged if a["family-names"] == "Johnson"]
    assert len(alices) == 1
    print("PASS: test_merge_authors passed")


def test_load_config():
    """Test loading configuration"""
    # Test default config
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        os.rename(f.name, f.name + "_bak")
        original_config = cffbump.CONFIG_PATH
        cffbump.CONFIG_PATH = f.name + "_nonexistent"

        try:
            config = load_config()
            assert config["git_min_commits"] == 2
            assert "md" in config["include_sources"]
            print("PASS: test_load_config passed")
        finally:
            cffbump.CONFIG_PATH = original_config


def test_preserve_author_metadata():
    """Test that existing author metadata (ORCID, email, affiliation) is preserved"""
    existing = [
        {
            "given-names": "Alice",
            "family-names": "Johnson",
            "email": "alice@example.com",
            "orcid": "https://orcid.org/0000-0001-2345-6789",
            "affiliation": "University of Example",
        },
        {"given-names": "Bob", "family-names": "Smith", "email": "bob@example.com"},
    ]

    # New source has Alice without metadata and a new person
    new_source = [
        {"given-names": "Alice", "family-names": "Johnson"},  # Same person, less info
        {"given-names": "Carol", "family-names": "Williams"},
    ]

    merged = merge_authors([existing, new_source])

    # Should have 3 people
    assert len(merged) == 3

    # Alice should keep all her metadata from existing
    alice = [a for a in merged if a["family-names"] == "Johnson"][0]
    assert alice["email"] == "alice@example.com"
    assert alice["orcid"] == "https://orcid.org/0000-0001-2345-6789"
    assert alice["affiliation"] == "University of Example"

    # Bob should still be there with email
    bob = [a for a in merged if a["family-names"] == "Smith"][0]
    assert bob["email"] == "bob@example.com"

    print("PASS: test_preserve_author_metadata passed")


def test_merge_additional_metadata():
    """Test that new metadata is added to existing authors"""
    existing = [
        {"given-names": "Alice", "family-names": "Johnson", "email": "alice@example.com"}
    ]

    # New source has ORCID for Alice
    new_source = [
        {
            "given-names": "Alice",
            "family-names": "Johnson",
            "orcid": "https://orcid.org/0000-0001-2345-6789",
        }
    ]

    merged = merge_authors([existing, new_source])

    # Should have 1 person with both email and ORCID
    assert len(merged) == 1
    alice = merged[0]
    assert alice["email"] == "alice@example.com"
    assert alice["orcid"] == "https://orcid.org/0000-0001-2345-6789"

    print("PASS: test_merge_additional_metadata passed")


if __name__ == "__main__":
    print("Running unit tests for cffbump...")
    test_get_authors_from_md()
    test_match_author()
    test_match_author_initials()
    test_merge_authors()
    test_preserve_author_metadata()
    test_merge_additional_metadata()
    test_load_config()
    test_get_authors_from_git()
    print("\nAll tests passed! ✓")
