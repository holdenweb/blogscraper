"""Fragment-tree export (Phase 4).

Emits one content-only HTML fragment per post under ``posts/YYYY/MM/slug.html``,
mirroring each post's original Blogger path (ADR-0007) so old-URL -> new-URL
redirects reduce to a domain swap plus a root prefix. Harvested images are
written under ``images/`` and a ``manifest.json`` carries per-fragment metadata
for whatever decorates the content at serve time.

The site root is unknown until the tree is mounted, so every generated URL is
written with the placeholder ``${{{ROOT}}}`` and substituted at publish time by
Jinja. All of Jinja's delimiters are moved to distinctive sentinels so that
shell, template and code samples in post bodies pass through untouched, and the
generator scans for those sentinels rather than escaping content (ADR-0009).
"""
from __future__ import annotations

import datetime
import hashlib
import importlib
import json
import mimetypes
import re
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

from bs4 import BeautifulSoup

# The publish-time contract — the delimiter constants and the render helpers —
# lives in its own dependency-free module so a consumer can copy it (ADR-0009).
# The generator imports the pieces it needs to emit matching placeholders.
from blogscraper.publish import (
    IMAGE_ROOT_PLACEHOLDER,
    ROOT_PLACEHOLDER,
    SENTINELS,
)

_POST_PATH = re.compile(r"/(\d{4})/(\d{2})/([^/]*)\.html?$")


def fragment_path(original_url: str) -> str:
    """``posts/YYYY/MM/slug.html`` mirrored from a Blogger post URL.

    Raises ValueError for anything that is not a dated post URL, rather than
    inventing a path for it.
    """
    m = _POST_PATH.search(original_url or "")
    if not m:
        raise ValueError(f"not a dated Blogger post URL: {original_url!r}")
    year, month, slug = m.groups()
    return f"posts/{year}/{month}/{slug}.html"


def find_collisions(html: str) -> list[str]:
    """Which placeholder sentinels, if any, occur literally in ``html``."""
    return [s for s in SENTINELS if s in html]


def _internal_ref(href: str, known_paths: set[str]) -> str | None:
    """A ``${{{ROOT}}}/...`` reference for a link to a captured post, else None.

    Links to blogspot posts we did not capture stay absolute — better a live
    external link than a dead one into our own tree.
    """
    parsed = urlparse(href)
    if not parsed.netloc.endswith("blogspot.com"):
        return None
    try:
        path = fragment_path(parsed.path)
    except ValueError:
        return None
    return f"{ROOT_PLACEHOLDER}/{path}" if path in known_paths else None


def rewrite_content(
    html: str, *, image_map: dict[str, str], known_paths: set[str]
) -> str:
    """Rewrite harvested ``<img src>`` and internal ``<a href>`` to placeholders.

    Only these attributes are touched; the rest of the body is left as authored
    (BeautifulSoup edits attributes in place rather than re-escaping text).
    """
    soup = BeautifulSoup(html, "html.parser")
    for img in soup.find_all("img"):
        name = image_map.get(img.get("src"))
        if name:
            img["src"] = f"{IMAGE_ROOT_PLACEHOLDER}/images/{name}"
    for a in soup.find_all("a", href=True):
        # A link straight to a harvested image (Blogger's "full size" link)
        # goes to the image root; otherwise a link to one of our own posts.
        name = image_map.get(a["href"])
        if name:
            a["href"] = f"{IMAGE_ROOT_PLACEHOLDER}/images/{name}"
            continue
        ref = _internal_ref(a["href"], known_paths)
        if ref:
            a["href"] = ref
    return str(soup)


def identity(html: str, meta: dict) -> str:
    """Default decorator: return the fragment unchanged."""
    return html


def resolve_decorator(spec: str | None) -> Callable[[str, dict], str]:
    """Resolve ``pkg.module:callable`` to a decorator; default identity.

    Lets holdenweb.com supply serve-time decoration without this repository
    importing it (ADR-0007).
    """
    if not spec:
        return identity
    module_name, _, attr = spec.partition(":")
    return getattr(importlib.import_module(module_name), attr)


def _image_filename(src: str, content_type: str | None) -> str:
    """A stable, unique local name for an image, independent of its URL shape.

    Blogger image URLs are long and often extensionless, so the name is a hash
    of the src with an extension inferred from the stored content type.
    """
    stem = hashlib.sha1(src.encode()).hexdigest()[:16]
    ext = mimetypes.guess_extension(content_type or "") or ".bin"
    return f"{stem}{ext}"


def _iso(dt: datetime.datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _manifest_entry(post, path: str) -> dict:
    return {
        "post_id": post.post_id,
        "title": post.title,
        "path": path,
        "original_url": post.original_url,
        "published": _iso(post.published),
        "updated": _iso(post.updated),
        "categories": list(post.categories or []),
        "comment_count": post.comment_count,
        "thumbnail_url": post.thumbnail_url,
    }


def export_all(out_dir, *, decorator: str | Callable | None = None) -> dict:
    """Generate the whole fragment tree, images and manifest into ``out_dir``.

    Returns a summary; ``collisions`` lists posts whose URL could not be
    mirrored or whose body contains a placeholder sentinel — surfaced loudly,
    never silently skipped.
    """
    from blogscraper.models import PhotoImage, Post

    out = Path(out_dir)
    decorate = decorator if callable(decorator) else resolve_decorator(decorator)

    image_map: dict[str, str] = {}
    images_written = 0
    for pi in PhotoImage.objects:
        name = _image_filename(pi.src, pi.content_type)
        image_map[pi.src] = name
        dest = out / "images" / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(pi.image.read())
        images_written += 1

    posts = list(Post.objects)
    known_paths: set[str] = set()
    for p in posts:
        try:
            known_paths.add(fragment_path(p.original_url))
        except ValueError:
            pass

    collisions: list[str] = []
    manifest_posts: list[dict] = []
    for p in posts:
        try:
            path = fragment_path(p.original_url)
        except ValueError:
            collisions.append(f"{p.post_id}: unmirrorable original_url {p.original_url!r}")
            continue
        body = p.content_html or ""
        hit = find_collisions(body)
        if hit:
            collisions.append(f"{p.post_id}: body contains sentinel(s) {hit}")
        rewritten = rewrite_content(body, image_map=image_map, known_paths=known_paths)
        entry = _manifest_entry(p, path)
        fragment = decorate(rewritten, entry)
        dest = out / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(fragment)
        manifest_posts.append(entry)

    manifest = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "root_placeholder": ROOT_PLACEHOLDER,
        "posts": manifest_posts,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))

    return {
        "posts": len(manifest_posts),
        "images": images_written,
        "collisions": collisions,
    }
