"""Fetch Blogger Atom feeds and store entries verbatim in raw collections.

Capture is recursive and lossless: the legacy scraper kept only each
entry's direct children as {tag, attrib, text}, which discarded element
children — author names among them (ADR-0004's context).
"""
from __future__ import annotations

import re
from typing import Any
from xml.etree import ElementTree as ET

# "{namespace-uri}tag" as produced by ElementTree.
NS_TAG_PAT = re.compile(r"\{(?P<ns>[^}]*)\}(?P<tag>.*)")

ATOM_NS = "http://www.w3.org/2005/Atom"


def split_tag(qualified: str) -> tuple[str, str]:
    if m := NS_TAG_PAT.match(qualified):
        return m["ns"], m["tag"]
    return "", qualified


def capture_element(element: ET.Element) -> dict[str, Any]:
    ns, tag = split_tag(element.tag)
    return {
        "ns": ns,
        "tag": tag,
        "attrib": dict(element.attrib),
        "text": element.text,
        "children": [capture_element(child) for child in element],
    }


def capture_entry(entry: ET.Element) -> dict[str, Any]:
    """One Atom <entry> as a raw document: its id, and its elements verbatim."""
    elements = [capture_element(child) for child in entry]
    atom_id = next(el["text"] for el in elements if el["tag"] == "id")
    return {"atom_id": atom_id, "elements": elements}


def find_element(raw: dict[str, Any], tag: str) -> dict[str, Any] | None:
    return next((el for el in raw["elements"] if el["tag"] == tag), None)


def _upsert(document_cls, key: dict[str, str], raw: dict[str, Any]) -> None:
    # Wholesale replacement, not a field merge: the raw document must be
    # exactly what the feed last said (ADR-0006). ensure_indexes() is an
    # idempotent createIndexes and keeps ingest safe regardless of call order.
    from datetime import datetime, timezone

    document_cls.ensure_indexes()
    document_cls._get_collection().replace_one(
        key,
        key | {"elements": raw["elements"], "fetched_at": datetime.now(timezone.utc)},
        upsert=True,
    )


def upsert_raw_post(raw: dict[str, Any]) -> None:
    from blogscraper.models import RawPost

    _upsert(RawPost, {"post_id": raw["atom_id"]}, raw)


def upsert_raw_comment(raw: dict[str, Any]) -> None:
    from blogscraper.models import RawComment

    in_reply_to = find_element(raw, "in-reply-to")
    _upsert(
        RawComment,
        {"comment_id": raw["atom_id"], "post_id": in_reply_to["attrib"]["ref"]},
        raw,
    )


def parse_feed(xml_text: str) -> tuple[list[dict[str, Any]], str | None]:
    root = ET.fromstring(xml_text)
    raws = [capture_entry(e) for e in root.findall(f"{{{ATOM_NS}}}entry")]
    next_url = next(
        (
            el.attrib["href"]
            for el in root.findall(f"{{{ATOM_NS}}}link")
            if el.attrib.get("rel") == "next"
        ),
        None,
    )
    return raws, next_url


def walk_feed(fetch, url: str, max_pages: int | None = None):
    """Yield raw entries from a paginated feed, following rel=next links.

    fetch is injected (url -> body text) so tests drive the walker from
    fixtures and production drives it from the network.
    """
    pages = 0
    while url:
        raws, url = parse_feed(fetch(url))
        yield from raws
        pages += 1
        if max_pages and pages >= max_pages:
            return


def posts_feed_url(blog_id: str, page_size: int = 25) -> str:
    return (
        f"https://www.blogger.com/feeds/{blog_id}/posts/default"
        f"?max-results={page_size}&start-index=1"
    )


def replies_feed_url(raw: dict[str, Any]) -> str | None:
    for el in raw["elements"]:
        attrib = el["attrib"]
        if (
            el["tag"] == "link"
            and attrib.get("rel") == "replies"
            and attrib.get("type") == "application/atom+xml"
        ):
            return attrib["href"]
    return None


def comment_total(raw: dict[str, Any]) -> int:
    el = find_element(raw, "total")
    return int(el["text"]) if el and el["text"] else 0


def scrape_posts(fetch, blog_id: str, max_pages: int | None = None) -> int:
    count = 0
    for raw in walk_feed(fetch, posts_feed_url(blog_id), max_pages):
        upsert_raw_post(raw)
        count += 1
    return count


def scrape_comments(fetch) -> int:
    """Fetch replies feeds for every raw post claiming comments (ADR-0008)."""
    from blogscraper.models import RawPost

    count = 0
    for doc in RawPost.objects:
        raw = {"atom_id": doc.post_id, "elements": doc.elements}
        if comment_total(raw) and (url := replies_feed_url(raw)):
            for comment_raw in walk_feed(fetch, url):
                upsert_raw_comment(comment_raw)
                count += 1
    return count


def make_fetcher(delay: float = 0.5):
    """A polite network fetch: identifying UA, fixed inter-request delay."""
    import time

    import requests

    session = requests.Session()
    session.headers["User-Agent"] = (
        "blogscraper/0.2 (+https://holdenweb.com; steve@holdenweb.com)"
    )

    def fetch(url: str) -> str:
        time.sleep(delay)
        response = session.get(url, timeout=30)
        response.raise_for_status()
        return response.text

    return fetch
