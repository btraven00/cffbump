import yaml
import os
import re
import subprocess
import json
from urllib.request import urlopen
from urllib.error import URLError
from typing import List, Dict, Any, Optional

CFF_PATH = "CITATION.cff"
AUTHORS_PATH = "AUTHORS.md"
CONFIG_PATH = "cffbump.config.yaml"

# Configuration defaults
DEFAULT_GIT_MIN_COMMITS = 2
DEFAULT_INCLUDE_SOURCES = ["md", "git", "crossref"]


def get_last_tag_info():
    """Return (version, commit, date) from the last known git tag, or ('0.0.0', None, None)."""
    tag_result = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0"],
        capture_output=True,
        text=True,
    )
    if tag_result.returncode != 0 or not tag_result.stdout.strip():
        return "0.0.0", None, None
    tag = tag_result.stdout.strip()
    commit_result = subprocess.run(
        ["git", "rev-list", "-n", "1", tag],
        capture_output=True,
        text=True,
    )
    commit = commit_result.stdout.strip() if commit_result.returncode == 0 else None
    date_result = subprocess.run(
        ["git", "log", "-1", "--format=%as", tag],
        capture_output=True,
        text=True,
    )
    date = date_result.stdout.strip() if date_result.returncode == 0 and date_result.stdout.strip() else None
    return tag.lstrip("v"), commit, date


def load_config():
    """Load configuration with priority: env vars > config file > defaults"""
    config = {
        "git_min_commits": DEFAULT_GIT_MIN_COMMITS,
        "include_sources": DEFAULT_INCLUDE_SOURCES,
        "doi": None,
        "date_filter": None,
    }

    # Load from config file (overrides defaults)
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            user_config = yaml.safe_load(f) or {}
            config.update(user_config)

    # Environment variables (highest priority, overrides config file)
    if "INPUT_GIT_MIN_COMMITS" in os.environ:
        config["git_min_commits"] = int(os.environ["INPUT_GIT_MIN_COMMITS"])

    if "INPUT_INCLUDE_SOURCES" in os.environ:
        # Parse comma-separated string into list
        sources_str = os.environ["INPUT_INCLUDE_SOURCES"]
        config["include_sources"] = [s.strip() for s in sources_str.split(",")]

    if "INPUT_DOI" in os.environ and os.environ["INPUT_DOI"]:
        config["doi"] = os.environ["INPUT_DOI"]

    if "INPUT_DATE_FILTER" in os.environ and os.environ["INPUT_DATE_FILTER"]:
        config["date_filter"] = os.environ["INPUT_DATE_FILTER"]

    return config


def get_authors_from_md():
    """Parses AUTHORS.md for 'Given Family' strings, handles various formats"""
    new_authors = []
    if os.path.exists(AUTHORS_PATH):
        with open(AUTHORS_PATH, "r") as f:
            for line in f:
                if line.startswith("- "):
                    name_part = line.replace("- ", "").strip()
                    # Remove email if present: "Name (email@example.com)" -> "Name"
                    name_part = re.sub(r"\s*\([^)]*\)\s*$", "", name_part)

                    if not name_part:
                        continue

                    # Split by whitespace and handle name prefixes
                    parts = name_part.split()
                    if len(parts) == 1:
                        # Single name - assume it's family name
                        new_authors.append({"family-names": parts[0]})
                    else:
                        # Multiple parts - last is family name, rest is given names
                        new_authors.append(
                            {
                                "given-names": " ".join(parts[:-1]),
                                "family-names": parts[-1],
                            }
                        )
    return new_authors


def get_authors_from_git(
    min_commits: int = DEFAULT_GIT_MIN_COMMITS, date_filter: Optional[str] = None
) -> List[Dict[str, str]]:
    """Extract authors from git history based on commit count threshold"""
    authors_dict = {}

    try:
        # Get git log with author name and email
        cmd = ["git", "log", "--format=%aN|%aE"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        # Count commits per author
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            name, email = line.split("|")
            key = (name, email)
            authors_dict[key] = authors_dict.get(key, 0) + 1

        # Filter by minimum commits
        new_authors = []
        seen = set()

        for (name, email), count in authors_dict.items():
            if count >= min_commits:
                # Parse name into given and family names
                parts = name.strip().split()
                if len(parts) == 1:
                    author_entry = {"family-names": parts[0]}
                else:
                    author_entry = {
                        "given-names": " ".join(parts[:-1]),
                        "family-names": parts[-1],
                    }

                # Add email if it's not a GitHub no-reply address
                if email and "@noreply.github.com" not in email:
                    author_entry["email"] = email

                # Avoid duplicates (same family-names + given-names)
                author_key = (
                    author_entry.get("family-names", ""),
                    author_entry.get("given-names", ""),
                )
                if author_key not in seen:
                    new_authors.append(author_entry)
                    seen.add(author_key)

        return new_authors
    except subprocess.CalledProcessError as e:
        print(f"Warning: Failed to extract authors from git history: {e}")
        return []
    except Exception as e:
        print(f"Warning: Error processing git log: {e}")
        return []


def get_authors_from_crossref(doi: Optional[str] = None) -> List[Dict[str, str]]:
    """Extract authors from a published paper via Crossref API"""
    if not doi:
        return []

    # Normalize DOI format
    if doi.startswith("http"):
        doi = doi.split("/")[-1] if "/" in doi else doi

    try:
        # Query Crossref API (free, no authentication needed)
        url = f"https://api.crossref.org/works/{doi}"
        with urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))

        if data.get("status") != "ok":
            print(
                f"Warning: Crossref returned status {data.get('status')} for DOI {doi}"
            )
            return []

        authors = []
        message = data.get("message", {})
        author_list = message.get("author", [])

        for author_dict in author_list:
            author_entry = {}
            if "given" in author_dict:
                author_entry["given-names"] = author_dict["given"]
            if "family" in author_dict:
                author_entry["family-names"] = author_dict["family"]
            if "ORCID" in author_dict:
                author_entry["orcid"] = author_dict["ORCID"]

            if author_entry:
                authors.append(author_entry)

        return authors
    except URLError as e:
        print(f"Warning: Failed to fetch from Crossref for DOI {doi}: {e}")
        return []
    except json.JSONDecodeError:
        print(f"Warning: Invalid JSON response from Crossref for DOI {doi}")
        return []
    except Exception as e:
        print(f"Warning: Error querying Crossref: {e}")
        return []


def match_author(author1: Dict[str, str], author2: Dict[str, str]) -> bool:
    """Check if two authors are the same person using exact matching and initial heuristics"""
    # Family name must match exactly
    family1 = author1.get("family-names", "").lower()
    family2 = author2.get("family-names", "").lower()

    if not family1 or not family2:
        return False

    # Exact family name match required
    if family1 != family2:
        return False

    # Check given names if both exist
    given1 = author1.get("given-names", "").lower().strip()
    given2 = author2.get("given-names", "").lower().strip()

    if not given1 or not given2:
        # If one has no given name, consider it a match based on family name
        return True

    # Exact match on given names
    if given1 == given2:
        return True

    # Heuristic: Check if one is an initial form of the other
    # e.g., "A. Johnson" matches "Alice Johnson"
    # Split into parts to handle multiple initials like "A. B." or "Alice Bob"
    parts1 = given1.replace(".", "").split()
    parts2 = given2.replace(".", "").split()

    # If both have same number of name parts, check if they match as initials
    if len(parts1) == len(parts2):
        # Check if all parts match either exactly or as initials
        for p1, p2 in zip(parts1, parts2):
            # Skip empty parts
            if not p1 or not p2:
                continue
            # Check if one is an initial of the other
            if len(p1) == 1 and p2.startswith(p1):
                continue
            elif len(p2) == 1 and p1.startswith(p2):
                continue
            elif p1 == p2:
                continue
            else:
                # No match for this part
                return False
        # All parts matched
        return True

    return False


def merge_authors(authors_list: List[List[Dict[str, str]]]) -> List[Dict[str, str]]:
    """Merge authors from multiple sources with deduplication"""
    merged = []
    seen = []

    # Process all authors from all sources
    for source_authors in authors_list:
        for author in source_authors:
            # Check if author already exists
            is_duplicate = False
            for existing in seen:
                if match_author(author, existing):
                    is_duplicate = True
                    # Merge additional fields (e.g., ORCID)
                    for key in ["orcid", "email"]:
                        if key in author and key not in existing:
                            existing[key] = author[key]
                    break

            if not is_duplicate:
                merged.append(author)
                seen.append(author)

    return merged


def main():
    # Load configuration
    config = load_config()
    include_sources = config.get("include_sources", DEFAULT_INCLUDE_SOURCES)

    # 1. Load existing CFF data
    if os.path.exists(CFF_PATH):
        with open(CFF_PATH, "r") as f:
            cff_data = yaml.safe_load(f) or {}
    else:
        cff_data = {
            "cff-version": "1.2.0",
            "message": "Cite me!",
            "authors": [],
            "version": "0.0.0",
        }

    # 2. Determine routing: if preferred-citation is an article, crossref authors
    #    go there; git/md authors go to the top-level software authors block.
    preferred = cff_data.get("preferred-citation", {})
    has_article_preferred = preferred.get("type") == "article"

    software_new_authors = []  # for top-level authors
    article_new_authors = []   # for preferred-citation.authors

    if "md" in include_sources:
        md_authors = get_authors_from_md()
        software_new_authors.append(md_authors)
        print(f"Extracted {len(md_authors)} authors from AUTHORS.md")

    if "git" in include_sources:
        git_min_commits = config.get("git_min_commits", DEFAULT_GIT_MIN_COMMITS)
        git_authors = get_authors_from_git(min_commits=git_min_commits)
        software_new_authors.append(git_authors)
        print(
            f"Extracted {len(git_authors)} authors from git history (min {git_min_commits} commits)"
        )

    if "crossref" in include_sources:
        # Try to get DOI from preferred-citation, then config, then identifiers
        doi = preferred.get("doi") or config.get("doi")
        if not doi and cff_data.get("identifiers"):
            doi = cff_data.get("identifiers", [{}])[0].get("value")
        if doi:
            crossref_authors = get_authors_from_crossref(doi)
            if has_article_preferred:
                article_new_authors.append(crossref_authors)
            else:
                software_new_authors.append(crossref_authors)
            print(
                f"Extracted {len(crossref_authors)} authors from Crossref (DOI: {doi})"
            )
        else:
            print("Warning: No DOI found for Crossref lookup")

    # 3. Update top-level authors (software contributors)
    existing_authors = cff_data.get("authors", [])
    final_authors = merge_authors([existing_authors, merge_authors(software_new_authors)])
    cff_data["authors"] = final_authors
    print(f"Total authors in CITATION.cff: {len(final_authors)}")

    # 4. Update preferred-citation authors if it's an article
    if has_article_preferred and article_new_authors:
        existing_article_authors = preferred.get("authors", [])
        final_article_authors = merge_authors([existing_article_authors, merge_authors(article_new_authors)])
        cff_data["preferred-citation"]["authors"] = final_article_authors
        print(f"Total authors in preferred-citation: {len(final_article_authors)}")

    # 5. Set version, commit, and date-released from last published tag
    current_version, tag_commit, tag_date = get_last_tag_info()
    cff_data["version"] = current_version
    print(f"Set version to {cff_data['version']}")
    if tag_commit:
        cff_data["commit"] = tag_commit
        print(f"Set commit to {tag_commit}")
    if tag_date:
        cff_data["date-released"] = tag_date
        print(f"Set date-released to {tag_date}")

    # 6. Save (preserving YAML structure)
    with open(CFF_PATH, "w") as f:
        yaml.dump(cff_data, f, sort_keys=False, default_flow_style=False)

    print(f"Updated {CFF_PATH}")


if __name__ == "__main__":
    main()
