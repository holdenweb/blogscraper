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

# Harvest Blogger-hosted post images into the photo collection.
images:
    uv run python -m blogscraper images

# Rebuild the tag collection: each category term -> the post ids carrying it.
tags:
    uv run python -m blogscraper tags

# Scrape the old Artima weblog (entries + comments) into the artima collection.
artima:
    uv run python -m blogscraper artima

# Generate the fragment tree, images and manifest into build/ (gitignored).
export:
    uv run python -m blogscraper export --out build

# Back up the whole database (no longer part of the pipeline - just a backup).
backup:
    mongodump -d blogscraper

# The legacy adhoc pipeline (scraper.py, db.py, adhoc*.py) has been retired;
# it lives in the git history as the record of how the corpus was first built.
