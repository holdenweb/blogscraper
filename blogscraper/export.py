"""Fragment-tree export (Phase 4).

Emits one content-only HTML fragment per post at the ``path`` its source set at
transform time (``posts/YYYY/MM/slug.html``), so the exporter is source-blind —
Blogger and Artima posts flow through the same line (ADR-0011). Harvested images
are written under ``images/`` and a ``manifest.json`` carries per-fragment
metadata for whatever decorates the content at serve time.

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
from html import escape
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from blogscraper.paths import blogger_path

# The publish-time contract — the delimiter constants and the render helpers —
# lives in its own dependency-free module so a consumer can copy it (ADR-0009).
# The generator imports the pieces it needs to emit matching placeholders.
from blogscraper.publish import (
    IMAGE_ROOT_PLACEHOLDER,
    ROOT_PLACEHOLDER,
    SENTINELS,
)


def redirect_entry(original_url: str, path: str) -> dict:
    """A cutover 301 from a post's old Blogger URL to its new path.

    ``from`` is the literal old path; ``to`` keeps ROOT as a placeholder so the
    consumer substitutes its own mount exactly as it does for links inside
    fragments — with ROOT=/blog, ``/YYYY/MM/slug.html`` -> ``/blog/posts/...``.
    """
    return {
        "from": urlparse(original_url).path,
        "to": f"{ROOT_PLACEHOLDER}/{path}",
        "status": 301,
    }


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
        path = blogger_path(parsed.path)
    except ValueError:
        return None
    return f"{ROOT_PLACEHOLDER}/{path}" if path in known_paths else None


_MATHJAX_DEAD = "cdn.mathjax.org/mathjax/latest/MathJax.js"
_MATHJAX_LIVE = "https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.9/MathJax.js"


def _fix_resource_url(url: str) -> str:
    """Repair a stale subresource URL (ADR-0013): the dead MathJax CDN becomes a
    current HTTPS one (a scheme bump alone can't revive a decommissioned host),
    and any remaining http:// becomes https:// — mixed content is blocked on the
    HTTPS site. Hyperlinks are navigation, handled elsewhere and left as authored.
    """
    if not url:
        return url
    if _MATHJAX_DEAD in url:
        query = url.partition("?")[2]
        return _MATHJAX_LIVE + (f"?{query}" if query else "")
    if url.startswith("http://"):
        return "https://" + url[len("http://"):]
    return url


def rewrite_content(
    html: str, *, image_map: dict[str, str], known_paths: set[str]
) -> str:
    """Rewrite harvested ``<img src>`` and internal ``<a href>`` to placeholders,
    repair stale subresource URLs, and leave the rest of the body as authored.

    Only attributes are touched (BeautifulSoup edits them in place rather than
    re-escaping text).
    """
    soup = BeautifulSoup(html, "html.parser")
    for img in soup.find_all("img"):
        name = image_map.get(img.get("src"))
        if name:
            img["src"] = f"{IMAGE_ROOT_PLACEHOLDER}/images/{name}"
    # Repair any remaining http:// subresource (incl. the dead MathJax CDN);
    # harvested images are already placeholders and pass through untouched.
    for el in soup.find_all(src=True):
        el["src"] = _fix_resource_url(el["src"])
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


def _manifest_entry(post, path: str, comment_pages=()) -> dict:
    return {
        "post_id": post.post_id,
        "source": post.source,
        "title": post.title,
        "path": path,
        "original_url": post.original_url,
        "published": _iso(post.published),
        "updated": _iso(post.updated),
        "categories": list(post.categories or []),
        "comment_count": post.comment_count,
        "thumbnail_url": post.thumbnail_url,
        "comment_pages": list(comment_pages),
    }


def comments_for(post) -> list[dict]:
    """A post's comments as one uniform list, regardless of source (ADR-0012).

    Render-time convergence of the two source-native shapes: Blogger `Comment`
    docs keyed by the Atom post_id, and Artima `ArtimaComment`s embedded in the
    entry located by the thread id inside the post_id.
    """
    from blogscraper.models import ArtimaEntry, Comment

    if post.source == "artima":
        thread_id = int(post.post_id.rsplit("-", 1)[1])
        entry = ArtimaEntry.objects(thread_id=thread_id).first()
        ordered = sorted(
            entry.comments if entry else [],
            key=lambda c: c.posted or datetime.datetime.min,
        )
        return [
            {"author": c.author_name, "when": c.posted, "heading": c.subject,
             "body_html": c.body_html or ""}
            for c in ordered
        ]
    out = []
    for c in Comment.objects(post_id=post.post_id).order_by("published"):
        body = c.body or ""
        body_html = body if c.body_type == "html" else escape(body)
        out.append({"author": c.author_name, "when": c.published,
                    "heading": c.title, "body_html": body_html})
    return out


def _furniture(post, n_comments: int, first_comment_page: str | None) -> tuple[str, str]:
    """(top, bottom) HTML wrapping a post fragment: a provenance subheading above,
    a bold tag list and a comments link below (ADR-0012)."""
    top = ""
    if post.original_url:
        top = (
            f'<p class="provenance">Originally published at '
            f'<a href="{escape(post.original_url, quote=True)}">'
            f'{escape(post.original_url)}</a></p>'
        )
    parts = []
    cats = list(post.categories or [])
    if cats:
        parts.append('<p class="tags">' + " ".join(f"<b>{escape(t)}</b>" for t in cats) + "</p>")
    if n_comments and first_comment_page:
        label = f"{n_comments} comment" + ("" if n_comments == 1 else "s")
        parts.append(
            f'<p class="comments">'
            f'<a href="{ROOT_PLACEHOLDER}/{first_comment_page}">{label}</a></p>'
        )
    return top, "".join(parts)


def _comment_base(post_path: str) -> str:
    return post_path[:-5] if post_path.endswith(".html") else post_path


def render_comment_pages(post_path: str, comments: list[dict], per_page: int = 10):
    """Paginated comment-page fragments as a list of (path, html), 10 per page,
    under the post's own path (`<slug>.comments/<n>.html`)."""
    base = _comment_base(post_path)
    total = (len(comments) + per_page - 1) // per_page
    pages = []
    for i in range(total):
        page_no = i + 1
        chunk = comments[i * per_page:(i + 1) * per_page]
        path = f"{base}.comments/{page_no}.html"
        pages.append((path, _render_comment_page(chunk, page_no, total, base, post_path)))
    return pages


def _render_comment_page(chunk, page_no, total, base, post_path) -> str:
    items = []
    for c in chunk:
        head = f'<h3>{escape(c["heading"])}</h3>' if c.get("heading") else ""
        meta = escape(c.get("author") or "Anonymous")
        if c.get("when") is not None:
            meta += f" · {c['when'].isoformat()}"
        items.append(
            f'<div class="comment">{head}'
            f'<p class="comment-meta">{meta}</p>{c["body_html"]}</div>'
        )
    nav = []
    if page_no > 1:
        nav.append(f'<a href="{ROOT_PLACEHOLDER}/{base}.comments/{page_no - 1}.html">Older comments</a>')
    nav.append(f"Page {page_no} of {total}")
    if page_no < total:
        nav.append(f'<a href="{ROOT_PLACEHOLDER}/{base}.comments/{page_no + 1}.html">Newer comments</a>')
    return (
        f'<div class="comments-page">{"".join(items)}'
        f'<p class="comment-nav">{" · ".join(nav)}</p>'
        f'<p class="comment-back"><a href="{ROOT_PLACEHOLDER}/{post_path}">Back to post</a></p>'
        f"</div>"
    )


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
    known_paths: set[str] = {p.path for p in posts if p.path}

    collisions: list[str] = []
    manifest_posts: list[dict] = []
    for p in posts:
        if not p.path:
            collisions.append(f"{p.post_id}: no target path (source={p.source})")
            continue
        body = p.content_html or ""
        hit = find_collisions(body)
        if hit:
            collisions.append(f"{p.post_id}: body contains sentinel(s) {hit}")
        rewritten = rewrite_content(body, image_map=image_map, known_paths=known_paths)

        comments = comments_for(p)
        comment_pages = render_comment_pages(p.path, comments) if comments else []
        page_paths = [path for path, _ in comment_pages]

        entry = _manifest_entry(p, p.path, page_paths)
        top, bottom = _furniture(p, len(comments), page_paths[0] if page_paths else None)
        fragment = decorate(top + rewritten + bottom, entry)

        dest = out / p.path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(fragment)
        for cpath, chtml in comment_pages:
            cdest = out / cpath
            cdest.parent.mkdir(parents=True, exist_ok=True)
            cdest.write_text(chtml)
        manifest_posts.append(entry)

    manifest = {
        "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "root_placeholder": ROOT_PLACEHOLDER,
        "posts": manifest_posts,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))

    # The cutover redirect map is a Blogger-migration concern — the old Artima
    # URLs are on artima.com, which we do not control — so it lists only the
    # Blogger posts (ADR-0011).
    redirects = sorted(
        (
            redirect_entry(e["original_url"], e["path"])
            for e in manifest_posts
            if e["source"] == "blogger"
        ),
        key=lambda r: r["from"],
    )
    (out / "redirects.json").write_text(
        json.dumps(
            {"root_placeholder": ROOT_PLACEHOLDER, "redirects": redirects}, indent=2
        )
    )

    return {
        "posts": len(manifest_posts),
        "images": images_written,
        "redirects": len(redirects),
        "collisions": collisions,
    }
