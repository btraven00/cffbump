# CFFBump: Multi-Source Author Extraction for CITATION.cff

Automated GitHub Action to keep your `CITATION.cff` file up-to-date by extracting authors from multiple sources.

**Available on GitHub Marketplace:** [CFFBump](https://github.com/marketplace/actions/cffbump)

## Features

- Extract authors from AUTHORS.md, git history, and Crossref (DOI lookups)
- Automatic semantic version bumping (patch)
- Preserves existing metadata (ORCID, email, affiliation)
- Configurable via YAML or workflow inputs

## Quick Start

### 1. Create AUTHORS.md

```markdown
# Authors

- Alice Johnson
- Bob Smith (bob@example.com)
```

### 2. Configure (Optional)

Create `cffbump.config.yaml`:

```yaml
include_sources: [md, git, crossref]
git_min_commits: 2
doi: "10.1371/journal.pone.0021373"
```

Or configure via workflow inputs:

```yaml
- uses: btraven00/cffbump@v1
  with:
    git-min-commits: '2'
    include-sources: 'md,git,crossref'
    doi: '10.1371/journal.pone.0021373'
```

### 3. Set Trigger

Edit `.github/workflows/cffbump.yaml`:

```yaml
# On releases
on:
  release:
    types: [published]

# On version tags
on:
  push:
    tags: ['v*']
```

## How It Works

1. Extract authors from enabled sources
2. Deduplicate by exact family name + given names
3. Merge with existing CITATION.cff (preserving hand-edited data)
4. Bump patch version
5. Commit and push

## Configuration

| Option | Default | Description |
|--------|---------|-------------|
| `include_sources` | `[md, git, crossref]` | Sources to extract from |
| `git_min_commits` | `2` | Min commits to include git author |
| `doi` | - | DOI for Crossref API |
| `date_filter` | - | Filter git history by date |

## Author Matching

Authors match if they have the same family name AND:
- Same given names (exact), OR
- One is missing given names, OR
- One has initials matching the other's full name

Examples:
- ✅ `Alice Johnson` = `Alice Johnson`
- ✅ `Alice Johnson` = `A. Johnson`
- ✅ `Alice Bob Smith` = `A. B. Smith`
- ✅ `Alice Johnson` = `Johnson`
- ❌ `Alice Johnson` ≠ `Bob Johnson`
- ❌ `A. Johnson` ≠ `B. Johnson`

## Testing Locally

```bash
python3 test_cffbump.py
python3 .github/scripts/cffbump.py
```

## License

Public domain under the Unlicense. See [LICENSE](LICENSE).
