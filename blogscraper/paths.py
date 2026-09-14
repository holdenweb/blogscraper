"""Target-path helpers: where each source's entries live in the fragment tree.

Each source computes its own path at transform time and stores it on the post,
so the production line (export) is source-blind — it just uses ``post.path``
(ADR-0011). Blogger mirrors its dated URL; Artima, which has no dated permalink,
builds a path from the post's date and a slug of its title.
"""
from __future__ import annotations

import datetime
import re

_BLOGGER_PATH = re.compile(r"/(\d{4})/(\d{2})/([^/]*)\.html?$")


def slugify(text: str) -> str:
    """A lower-case, dash-separated slug; never empty."""
    slug = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return slug or "post"


def blogger_path(original_url: str) -> str:
    """``posts/YYYY/MM/slug.html`` mirrored from a dated Blogger URL.

    Raises ValueError for anything that is not a dated post URL, rather than
    inventing a path for it.
    """
    m = _BLOGGER_PATH.search(original_url or "")
    if not m:
        raise ValueError(f"not a dated Blogger post URL: {original_url!r}")
    year, month, slug = m.groups()
    return f"posts/{year}/{month}/{slug}.html"


def artima_path(published: datetime.datetime, title: str) -> str:
    """``posts/YYYY/MM/slug.html`` from an Artima entry's date and title."""
    return f"posts/{published:%Y/%m}/{slugify(title)}.html"
