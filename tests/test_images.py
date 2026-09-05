"""Image harvest into the `photo` collection (supersedes adhoc15.py).

Blogger-hosted images vanish when the blog is decommissioned, so they are
copied locally, keyed by the exact src the post uses (so export can rewrite
`<img src>` deterministically). External images are left where they are.
"""


def test_image_refs_extracts_src_and_metadata():
    from blogscraper.images import image_refs

    html = (
        '<div>'
        '<a href="big.png"><img src="https://blogger.googleusercontent.com/img/x.png"'
        ' alt="A cat" width="320" height="240"/></a>'
        '<img src="https://example.com/badge.gif"/>'
        '<img/>'  # no src: skipped
        '</div>'
    )
    refs = image_refs(html)
    assert [r["src"] for r in refs] == [
        "https://blogger.googleusercontent.com/img/x.png",
        "https://example.com/badge.gif",
    ]
    assert refs[0]["alt"] == "A cat"
    assert refs[0]["width"] == 320
    assert refs[0]["height"] == 240
    assert refs[1]["alt"] is None


def test_is_blogger_hosted_recognises_the_endangered_hosts():
    from blogscraper.images import is_blogger_hosted

    assert is_blogger_hosted("https://blogger.googleusercontent.com/img/x.png")
    assert is_blogger_hosted("http://photos1.blogger.com/x.jpg")
    assert is_blogger_hosted("https://lh3.googleusercontent.com/x")
    assert is_blogger_hosted("https://holdenweb.blogspot.com/img.png")
    assert not is_blogger_hosted("https://g-images.amazon.com/badge.gif")
    assert not is_blogger_hosted("https://www.paypal.com/x.gif")
    assert not is_blogger_hosted("relative.png")


def test_harvest_stores_blogger_images_and_skips_external(test_db):
    from blogscraper.images import harvest
    from blogscraper.models import PhotoImage, Post

    blog = "https://blogger.googleusercontent.com/img/x.png"
    ext = "https://g-images.amazon.com/badge.gif"
    Post(
        post_id="p1",
        original_url="https://holdenweb.blogspot.com/2020/01/a.html",
        content_html=f'<img src="{blog}" alt="cat" width="320"/><img src="{ext}"/>',
    ).save()

    fetched = {blog: (b"PNGDATA", "image/png")}
    result = harvest(lambda url: fetched[url])

    assert result["stored"] == 1
    assert result["external"] == 1
    pi = PhotoImage.objects.get(src=blog)
    assert pi.content_type == "image/png"
    assert pi.image.read() == b"PNGDATA"
    assert pi.alt == "cat" and pi.width == 320
    assert PhotoImage.objects(src=ext).count() == 0  # external not copied


def test_harvest_is_idempotent(test_db):
    from blogscraper.images import harvest
    from blogscraper.models import PhotoImage, Post

    blog = "https://blogger.googleusercontent.com/img/x.png"
    Post(post_id="p1", original_url="u", content_html=f'<img src="{blog}"/>').save()

    calls = []

    def fetch(url):
        calls.append(url)
        return (b"D", "image/png")

    assert harvest(fetch)["stored"] == 1
    second = harvest(fetch)
    assert second["stored"] == 0
    assert second["existing"] == 1
    assert calls == [blog]  # the stored image is not refetched
    assert PhotoImage.objects.count() == 1


def test_harvest_records_failures_without_aborting(test_db):
    from blogscraper.images import harvest
    from blogscraper.models import PhotoImage, Post

    good = "https://blogger.googleusercontent.com/img/good.png"
    bad = "https://blogger.googleusercontent.com/img/bad.png"
    Post(post_id="p1", original_url="u", content_html=f'<img src="{good}"/><img src="{bad}"/>').save()

    def fetch(url):
        if url == bad:
            raise RuntimeError("404 Not Found")
        return (b"OK", "image/png")

    result = harvest(fetch)
    assert result["stored"] == 1  # a failure does not abort the rest
    assert result["failed"] == 1
    assert any("bad.png" in e for e in result["errors"])
    assert PhotoImage.objects.get().src == good
