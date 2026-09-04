# justfile

export BLOG_ID := "496482"

# --- Current pipeline (blogscraper package) ---

# Run the test suite.
test:
    uv run pytest

# Fetch posts and their comments from the live blog into the raw collections.
scrape:
    uv run python -m blogscraper scrape

# Fetch only the replies feeds for posts that claim comments.
comments:
    uv run python -m blogscraper comments

# Report raw documents that violate the transform's assumptions.
validate:
    uv run python -m blogscraper validate

# Rebuild the typed post/comment collections from the raw collections.
transform:
    uv run python -m blogscraper transform

# Full refresh from the live blog: scrape, then rebuild derived collections.
refresh: scrape transform

# Generate the fragment tree, images and manifest into build/ (gitignored).
export:
    uv run python -m blogscraper export --out build

# Back up the whole database (no longer part of the pipeline - just a backup).
backup:
    mongodump -d blogscraper

# --- Legacy adhoc pipeline (superseded; kept until the scripts are retired) ---

legacy-scrape:
    uv run drop.py
    uv run scraper.py
    mongodump -d blogscraper

legacy-refresh:
    uv run drop.py
    mongorestore --nsInclude=blogscraper.blog_post

legacy-create: legacy-refresh
    uv run adhoc1.py
    uv run adhoc2.py
    uv run adhoc3.py
    uv run adhoc6.py
    uv run adhoc7.py
    uv run adhoc8.py
    uv run adhoc9.py
    uv run adhoc10.py
    uv run adhoc11.py
    uv run adhoc12.py
    uv run adhoc13.py
