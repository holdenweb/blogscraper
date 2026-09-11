"""Build the tag collection: an inverted index from category term to post ids.

Each Post lists its Blogger categories in ``categories``; this inverts that into
one document per term, holding the post_ids that carry it. Like the other
derived collections it is rebuilt from Post at will — dropped and remade, never
appended (ADR-0004) — so a post that loses a tag drops out of that tag's entries.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Iterable


def tag_index(posts: Iterable[Any]) -> dict[str, list[str]]:
    """Map each category term to the sorted, unique post ids carrying it.

    Tags and their entries are both sorted, so the collection is deterministic
    and diffs cleanly across rebuilds. ``posts`` need only expose ``post_id``
    and ``categories``.
    """
    index: dict[str, set[str]] = defaultdict(set)
    for post in posts:
        for term in set(post.categories or []):
            index[term].add(post.post_id)
    return {term: sorted(index[term]) for term in sorted(index)}


def build_tags() -> dict[str, int]:
    """Drop and rebuild the `tag` collection from the current posts."""
    from blogscraper.models import Post, Tag

    index = tag_index(Post.objects)
    Tag.drop_collection()
    for term, entries in index.items():
        Tag(tag=term, entries=entries).save()
    return {"tags": len(index), "taggings": sum(len(e) for e in index.values())}
