"""Fragment-tree export: path mirroring, rewrites, and the publish round-trip.

The delimiter contract is ADR-0009: the only substitutable token is
``${{{ROOT}}}``; every other flavour of ``${...}``, ``{{...}}``, ``{%...%}``
and ``{#...#}`` in a post body must survive publish untouched.
"""
import json
import re


def test_fragment_path_mirrors_blogger_path():
    from blogscraper.export import fragment_path

    url = "https://holdenweb.blogspot.com/2026/02/im-depressed.html"
    assert fragment_path(url) == "posts/2026/02/im-depressed.html"
    # An untitled post has no title but still has a dated URL, so its slug
    # comes from the URL, not the (absent) title.
    untitled = "https://holdenweb.blogspot.com/2007/09/.html"
    assert fragment_path(untitled) == "posts/2007/09/.html"


def test_fragment_path_rejects_unmirrorable_url():
    from blogscraper.export import fragment_path

    # A URL that is not a dated post path is a real surprise: fail loudly
    # rather than invent a path (ADR-0005's spirit, applied to export).
    try:
        fragment_path("https://holdenweb.blogspot.com/p/about.html")
    except ValueError:
        return
    raise AssertionError("expected ValueError for a non-dated URL")


def test_collision_scan_flags_only_the_sentinels():
    from blogscraper.export import find_collisions

    assert find_collisions("plain ${HOME} and {{ x }} and {% if a %}") == []
    assert find_collisions("oops ${{{ROOT}}} typed by hand")  # variable sentinel
    assert find_collisions("a ${{% weird %}}} block")  # block sentinel
    assert find_collisions("a ${{# weird #}}} comment")  # comment sentinel


def test_rewrite_internal_post_links_only_when_known():
    from blogscraper.export import ROOT_PLACEHOLDER, rewrite_content

    html = (
        '<a href="https://holdenweb.blogspot.com/2020/01/known.html">mine</a>'
        '<a href="https://holdenweb.blogspot.com/2020/01/gone.html">deleted</a>'
        '<a href="https://python.org/">external</a>'
    )
    out = rewrite_content(
        html, image_map={}, known_paths={"posts/2020/01/known.html"}
    )
    assert f'href="{ROOT_PLACEHOLDER}/posts/2020/01/known.html"' in out
    # A blogspot link we did not capture stays absolute, not a dead ROOT link.
    assert "https://holdenweb.blogspot.com/2020/01/gone.html" in out
    assert "https://python.org/" in out


def test_rewrite_image_src_only_when_harvested():
    from blogscraper.export import IMAGE_ROOT_PLACEHOLDER, rewrite_content

    harvested = "https://blogger.googleusercontent.com/img/a.png"
    other = "https://blogger.googleusercontent.com/img/b.png"
    html = f'<img src="{harvested}"/><img src="{other}"/>'
    out = rewrite_content(
        html, image_map={harvested: "a.png"}, known_paths=set()
    )
    assert f'src="{IMAGE_ROOT_PLACEHOLDER}/images/a.png"' in out
    assert other in out  # not harvested, so left alone


def test_rewrite_full_size_image_links():
    # Blogger's "click for full size" <a href> to a harvested image is
    # rewritten to the image root, just like the <img src> it wraps, while an
    # internal post link still resolves to the content root.
    from blogscraper.export import (
        IMAGE_ROOT_PLACEHOLDER,
        ROOT_PLACEHOLDER,
        rewrite_content,
    )

    full = "https://blogger.googleusercontent.com/s1600/full.png"
    thumb = "https://blogger.googleusercontent.com/s400/thumb.png"
    html = (
        f'<a href="{full}"><img src="{thumb}"/></a>'
        '<a href="https://holdenweb.blogspot.com/2020/01/known.html">post</a>'
    )
    out = rewrite_content(
        html,
        image_map={full: "full.png", thumb: "thumb.png"},
        known_paths={"posts/2020/01/known.html"},
    )
    assert f'href="{IMAGE_ROOT_PLACEHOLDER}/images/full.png"' in out
    assert f'src="{IMAGE_ROOT_PLACEHOLDER}/images/thumb.png"' in out
    assert f'href="{ROOT_PLACEHOLDER}/posts/2020/01/known.html"' in out


def test_resolve_decorator_default_and_dotted_path():
    from blogscraper.export import identity, resolve_decorator

    assert resolve_decorator(None) is identity
    assert resolve_decorator("") is identity
    assert resolve_decorator("blogscraper.export:identity") is identity
    assert resolve_decorator(None)("<p>x</p>", {"title": "t"}) == "<p>x</p>"


def test_export_all_writes_fragments_manifest_and_images(tmp_path, test_db):
    from blogscraper.models import PhotoImage, Post
    from blogscraper.publish import render_fragment

    png = b"\x89PNG\r\n\x1a\nFAKEBYTES"
    src = "https://blogger.googleusercontent.com/img/pic.png"
    pi = PhotoImage(src=src, content_type="image/png")
    pi.image.put(png, content_type="image/png")
    pi.save()

    Post(
        post_id="tag:blogger.com,1999:post-1",
        title="First",
        original_url="https://holdenweb.blogspot.com/2020/01/first.html",
        published=__import__("datetime").datetime(2020, 1, 2),
        categories=["python"],
        comment_count=3,
        content_html=(
            f'<div>See <a href="https://holdenweb.blogspot.com/2019/12/second.html">'
            f'the other</a> <img src="{src}"/> code: <code>${{HOME}}</code></div>'
        ),
    ).save()
    Post(
        post_id="tag:blogger.com,1999:post-2",
        title="Second",
        original_url="https://holdenweb.blogspot.com/2019/12/second.html",
        published=__import__("datetime").datetime(2019, 12, 31),
        content_html="<div>Second body</div>",
    ).save()

    from blogscraper.export import export_all

    result = export_all(tmp_path)
    assert result["posts"] == 2
    assert result["collisions"] == []

    first = (tmp_path / "posts/2020/01/first.html").read_text()
    # Internal link and harvested image are rewritten to the placeholder;
    # the shell sample is left byte-for-byte intact.
    assert "${{{ROOT}}}/posts/2019/12/second.html" in first
    assert "${HOME}" in first

    # The image is rewritten to *some* placeholder path, and whatever name the
    # export chose, that exact file exists with the original bytes.
    img = re.search(r"\$\{\{\{IMAGE_ROOT\}\}\}/images/([^\"']+)", first)
    assert img, "image src was not rewritten"
    image_name = img.group(1)
    assert (tmp_path / "images" / image_name).read_bytes() == png

    manifest = json.loads((tmp_path / "manifest.json").read_text())
    entry = next(p for p in manifest["posts"] if p["title"] == "First")
    assert entry["path"] == "posts/2020/01/first.html"
    assert entry["categories"] == ["python"]
    assert entry["comment_count"] == 3
    assert entry["original_url"].endswith("/2020/01/first.html")

    # The published round-trip: mounting at /blog resolves every placeholder.
    published = render_fragment(first, "/blog")
    assert "/blog/posts/2019/12/second.html" in published
    assert f"/blog/images/{image_name}" in published
    assert "${HOME}" in published  # still literal after publish
