"""Harvest post images into the `photo` collection (supersedes adhoc15.py).

Blogger serves post images from its own hosts, and those URLs die when the blog
is decommissioned — so the migration keeps a local copy. This walks each post's
content, fetches the Blogger-hosted `<img src>` images not already stored, and
saves the bytes (GridFS) keyed by the exact src the content uses, so export can
rewrite `<img src>` deterministically (ADR-0010).

External images are left alone: they are not Blogger's to lose, and copying
them onto the new site would be a separate decision. adhoc15.py fetched every
image with no dedup, no integrity, and swallowed errors silently; this upserts
on a unique src, skips what it already has, and reports what it could not fetch.
"""
from __future__ import annotations

from typing import Any, Callable
from urllib.parse import urlparse

from bs4 import BeautifulSoup

# The image handed back by a fetcher: raw bytes and a bare content type.
ImageFetch = Callable[[str], "tuple[bytes, str | None]"]

# Extensions that mark an <a href> as pointing straight at an image file — the
# "click for full size" links Blogger wraps around a displayed thumbnail.
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp")


def is_blogger_hosted(src: str) -> bool:
    """True for the Google/Blogger image hosts whose URLs die with the blog."""
    host = urlparse(src).netloc.lower()
    return bool(host) and (
        host.endswith("blogger.com")
        or host.endswith("blogspot.com")
        or host.endswith("googleusercontent.com")
    )


def _int_or_none(value: str | None) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def image_refs(html: str) -> list[dict[str, Any]]:
    """Every `<img>` with a src in ``html``, with its alt/width/height."""
    soup = BeautifulSoup(html or "", "html.parser")
    refs = []
    for img in soup.find_all("img"):
        src = img.get("src")
        if not src:
            continue
        refs.append(
            {
                "src": src,
                "alt": img.get("alt"),
                "width": _int_or_none(img.get("width")),
                "height": _int_or_none(img.get("height")),
            }
        )
    return refs


def image_link_hrefs(html: str) -> list[str]:
    """Every `<a href>` pointing straight at an image file in ``html``.

    These are the full-size images Blogger links behind the displayed
    thumbnail; harvesting them keeps "click for full size" working once the
    original host is gone.
    """
    soup = BeautifulSoup(html or "", "html.parser")
    hrefs = []
    for a in soup.find_all("a", href=True):
        if urlparse(a["href"]).path.lower().endswith(IMAGE_EXTS):
            hrefs.append(a["href"])
    return hrefs


def _post_image_refs(html: str) -> list[dict[str, Any]]:
    """Every image a post references: displayed `<img>` and full-size links."""
    return image_refs(html) + [
        {"src": href, "alt": None, "width": None, "height": None}
        for href in image_link_hrefs(html)
    ]


def harvest(
    fetch_image: ImageFetch, *, should_harvest: Callable[[str], bool] = is_blogger_hosted
) -> dict[str, Any]:
    """Fetch and store every not-yet-stored Blogger-hosted post image.

    Covers both displayed `<img src>` images and the full-size images linked
    behind them. Idempotent: an image already in the collection is not
    refetched. A fetch that fails is recorded and skipped, never aborting the
    run. ``fetch_image`` is injected (src -> (bytes, content_type)) so tests
    drive it without the network.
    """
    from blogscraper.models import PhotoImage, Post

    PhotoImage.ensure_indexes()
    stored = existing = external = failed = 0
    errors: list[str] = []
    known = set(PhotoImage.objects.distinct("src"))
    handled: set[str] = set()

    for post in Post.objects:
        for ref in _post_image_refs(post.content_html):
            src = ref["src"]
            if not should_harvest(src):
                external += 1
                continue
            if src in known:
                existing += 1
                continue
            if src in handled:  # same image used by more than one post
                continue
            handled.add(src)
            try:
                content, content_type = fetch_image(src)
            except Exception as exc:  # network/HTTP failure: report, don't abort
                failed += 1
                errors.append(f"{src}: {exc}")
                continue
            photo = PhotoImage(
                src=src,
                content_type=content_type,
                alt=ref["alt"],
                width=ref["width"],
                height=ref["height"],
            )
            photo.image.put(content, content_type=content_type)
            photo.save()
            known.add(src)
            stored += 1

    return {
        "stored": stored,
        "existing": existing,
        "external": external,
        "failed": failed,
        "errors": errors,
    }


def make_image_fetcher(delay: float = 0.5) -> ImageFetch:
    """A polite image fetch: identifying UA, fixed inter-request delay.

    Mirrors ingest.make_fetcher, but returns bytes and a bare content type
    rather than decoded text.
    """
    import time

    import requests

    session = requests.Session()
    session.headers["User-Agent"] = (
        "blogscraper/0.2 (+https://holdenweb.com; steve@holdenweb.com)"
    )

    def fetch_image(url: str) -> tuple[bytes, str | None]:
        time.sleep(delay)
        response = session.get(url, timeout=30)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "").split(";")[0].strip()
        return response.content, content_type or None

    return fetch_image
