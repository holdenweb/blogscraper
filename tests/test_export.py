"""Fragment-tree export: path mirroring, rewrites, and the publish round-trip.

The delimiter contract is ADR-0009: the only substitutable token is
``${{{ROOT}}}``; every other flavour of ``${...}``, ``{{...}}``, ``{%...%}``
and ``{#...#}`` in a post body must survive publish untouched.
"""
import json
import re


def test_redirect_entry_maps_old_url_to_placeholdered_path():
    # The cutover 301: old Blogger path -> new path, with ROOT left as a
    # placeholder so the consumer substitutes its own mount (e.g. /blog).
    from blogscraper.export import redirect_entry

    entry = redirect_entry(
        "https://holdenweb.blogspot.com/2026/02/im-depressed.html",
        "posts/2026/02/im-depressed.html",
    )
    assert entry == {
        "from": "/2026/02/im-depressed.html",
        "to": "${{{ROOT}}}/posts/2026/02/im-depressed.html",
        "status": 301,
    }


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


def test_rewrite_repairs_mathjax_cdn_and_upgrades_http_subresources():
    from blogscraper.export import rewrite_content

    html = (
        '<script src="http://cdn.mathjax.org/mathjax/latest/MathJax.js'
        '?config=TeX-AMS-MML_HTMLorMML"></script>'
        '<img src="http://g-images.amazon.com/x.jpg"/>'
        '<script src="http://code.jquery.com/jquery.js"></script>'
        '<embed src="http://example.com/e.swf"/>'
        '<a href="http://en.wikipedia.org/wiki/X">link</a>'
    )
    out = rewrite_content(html, image_map={}, known_paths=set())
    # Dead MathJax CDN -> current HTTPS CDN, config query preserved.
    assert ("https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.9/MathJax.js"
            "?config=TeX-AMS-MML_HTMLorMML") in out
    assert "cdn.mathjax.org" not in out
    # Other http:// subresources upgraded to https.
    assert 'src="https://g-images.amazon.com/x.jpg"' in out
    assert 'src="https://code.jquery.com/jquery.js"' in out
    assert 'src="https://example.com/e.swf"' in out
    # Hyperlinks are navigation, not mixed content — left as authored.
    assert 'href="http://en.wikipedia.org/wiki/X"' in out


def test_harvested_image_wins_over_http_upgrade():
    from blogscraper.export import rewrite_content

    src = "http://blogger.googleusercontent.com/img/h.png"
    out = rewrite_content(f'<img src="{src}"/>', image_map={src: "h.png"}, known_paths=set())
    assert "${{{IMAGE_ROOT}}}/images/h.png" in out
    assert "http://blogger" not in out


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


def test_comments_for_maps_both_sources_to_one_shape(test_db):
    import datetime

    from blogscraper.export import comments_for
    from blogscraper.models import ArtimaComment, ArtimaEntry, Comment, Post

    # Blogger: Comment keyed by the post's Atom id; html body kept, text escaped.
    Post(post_id="tag:p1", source="blogger", path="posts/2020/01/a.html",
         title="A", content_html="<p>x</p>").save()
    Comment(comment_id="c1", post_id="tag:p1", title="Re: A", body="<p>hi</p>",
            body_type="html", author_name="Ann",
            published=datetime.datetime(2020, 1, 3)).save()
    Comment(comment_id="c2", post_id="tag:p1", body="plain <text>", body_type="text",
            author_name="Bob", published=datetime.datetime(2020, 1, 2)).save()
    got = comments_for(Post.objects.get(post_id="tag:p1"))
    assert [c["author"] for c in got] == ["Bob", "Ann"]  # chronological
    assert got[1]["body_html"] == "<p>hi</p>"
    assert got[0]["body_html"] == "plain &lt;text&gt;"  # text escaped

    # Artima: embedded comments located by the thread id inside post_id.
    entry = ArtimaEntry(thread_id=42, title="T", permalink="http://x", comment_count=1)
    entry.comments = [ArtimaComment(author_name="Cat", subject="Re: T",
                                    body_html="<p>yo</p>",
                                    posted=datetime.datetime(2007, 8, 7))]
    entry.save()
    Post(post_id="artima:thread-42", source="artima", path="posts/2007/08/t.html",
         title="T", content_html="<p>b</p>").save()
    ag = comments_for(Post.objects.get(post_id="artima:thread-42"))
    assert ag[0]["author"] == "Cat"
    assert ag[0]["heading"] == "Re: T"
    assert ag[0]["body_html"] == "<p>yo</p>"


def test_furniture_renders_provenance_tags_and_comments_link():
    from blogscraper.export import ROOT_PLACEHOLDER, _furniture
    from blogscraper.models import Post

    p = Post(post_id="x", source="blogger", title="T",
             original_url="https://holdenweb.blogspot.com/2020/01/a.html",
             categories=["python", "web"])
    top, bottom = _furniture(p, 3, "posts/2020/01/a.comments/1.html")
    assert "Originally published at" in top
    assert 'href="https://holdenweb.blogspot.com/2020/01/a.html"' in top
    assert "<b>python</b>" in bottom and "<b>web</b>" in bottom
    assert f"{ROOT_PLACEHOLDER}/posts/2020/01/a.comments/1.html" in bottom
    assert "3 comments" in bottom


def test_furniture_omits_absent_pieces_and_singular_comment():
    from blogscraper.export import _furniture
    from blogscraper.models import Post

    p = Post(post_id="x", source="artima", title="T",
             original_url="http://www.artima.com/weblogs/viewpost.jsp?thread=1",
             categories=[])
    top, bottom = _furniture(p, 0, None)
    assert "Originally published at" in top   # provenance always (has a URL)
    assert "<b>" not in bottom                # no tags
    assert "comment" not in bottom            # no comments link when zero
    _, bottom1 = _furniture(p, 1, "posts/x.comments/1.html")
    assert "1 comment" in bottom1 and "1 comments" not in bottom1  # pluralised


def test_render_comment_pages_paginates_ten_per_page():
    import datetime

    from blogscraper.export import ROOT_PLACEHOLDER, render_comment_pages

    comments = [
        {"author": f"A{i}", "when": datetime.datetime(2020, 1, 1), "heading": None,
         "body_html": f"<p>c{i}.</p>"}
        for i in range(23)
    ]
    pages = dict(render_comment_pages("posts/2020/01/a.html", comments, per_page=10))
    assert list(pages) == [
        "posts/2020/01/a.comments/1.html",
        "posts/2020/01/a.comments/2.html",
        "posts/2020/01/a.comments/3.html",
    ]
    p1, p2, p3 = (pages[f"posts/2020/01/a.comments/{n}.html"] for n in (1, 2, 3))
    assert "c0." in p1 and "c9." in p1 and "c10." not in p1  # 10 to a page
    assert "c22." in p3
    assert f"{ROOT_PLACEHOLDER}/posts/2020/01/a.comments/2.html" in p1  # newer →
    assert f"{ROOT_PLACEHOLDER}/posts/2020/01/a.comments/1.html" in p2  # ← older
    assert "Page 2 of 3" in p2
    assert f"{ROOT_PLACEHOLDER}/posts/2020/01/a.html" in p1  # back to post


def test_export_all_generates_comment_pages(tmp_path, test_db):
    import datetime
    import json

    from blogscraper.export import export_all
    from blogscraper.models import Comment, Post

    Post(post_id="tag:p1", source="blogger", path="posts/2020/01/a.html", title="A",
         original_url="https://holdenweb.blogspot.com/2020/01/a.html",
         content_html="<p>body</p>", comment_count=12).save()
    for i in range(12):
        Comment(comment_id=f"c{i}", post_id="tag:p1", body=f"<p>comment {i}.</p>",
                body_type="html", author_name=f"A{i}",
                published=datetime.datetime(2020, 1, 1, 0, i)).save()

    export_all(tmp_path)
    frag = (tmp_path / "posts/2020/01/a.html").read_text()
    assert "12 comments" in frag
    assert "${{{ROOT}}}/posts/2020/01/a.comments/1.html" in frag
    assert (tmp_path / "posts/2020/01/a.comments/1.html").exists()
    assert (tmp_path / "posts/2020/01/a.comments/2.html").exists()  # 10 + 2
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    entry = next(p for p in manifest["posts"] if p["post_id"] == "tag:p1")
    assert entry["comment_pages"] == [
        "posts/2020/01/a.comments/1.html",
        "posts/2020/01/a.comments/2.html",
    ]


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
        source="blogger",
        path="posts/2020/01/first.html",
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
        source="blogger",
        path="posts/2019/12/second.html",
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
    # Furniture: provenance line and a bold tag; no comments link (no comments).
    assert "Originally published at" in first
    assert "<b>python</b>" in first
    assert 'class="comments"' not in first

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

    # The cutover redirect map: old Blogger path -> new placeholdered path.
    redirects = json.loads((tmp_path / "redirects.json").read_text())
    assert redirects["root_placeholder"] == "${{{ROOT}}}"
    by_from = {r["from"]: r for r in redirects["redirects"]}
    assert by_from["/2020/01/first.html"]["to"] == "${{{ROOT}}}/posts/2020/01/first.html"
    assert by_from["/2020/01/first.html"]["status"] == 301
    assert "/2019/12/second.html" in by_from

    # The published round-trip: mounting at /blog resolves every placeholder.
    published = render_fragment(first, "/blog")
    assert "/blog/posts/2019/12/second.html" in published
    assert f"/blog/images/{image_name}" in published
    assert "${HOME}" in published  # still literal after publish
