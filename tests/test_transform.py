"""The table-driven transform: raw entries to typed post/comment fields."""
import datetime
from xml.etree import ElementTree as ET

ATOM = "{http://www.w3.org/2005/Atom}"


def raw_entries(xml_text):
    from blogscraper.ingest import capture_entry

    return [
        capture_entry(e)
        for e in ET.fromstring(xml_text).findall(f"{ATOM}entry")
    ]


def test_each_post_keeps_its_own_thumbnail(fixture_text):
    # Regression for the adhoc12 stale-variable bug, which gave all 538
    # migrated posts the last-validated post's thumbnail.
    from blogscraper.transform import post_fields

    a, b = (post_fields(r) for r in raw_entries(fixture_text("posts_page1.xml")))
    assert a["thumbnail_url"] != b["thumbnail_url"]
    assert a["thumbnail_url"].startswith("https://")


def test_scalar_fields(fixture_text):
    from blogscraper.transform import post_fields

    fields = post_fields(raw_entries(fixture_text("posts_page1.xml"))[0])
    assert fields["title"] == "I'm Depressed"
    assert fields["author_name"] == "holdenweb"
    assert fields["comment_count"] == 0
    assert fields["content_html"].startswith("<div>")
    assert fields["post_id"].startswith("tag:blogger.com,")


def test_dates_become_datetimes(fixture_text):
    from blogscraper.transform import post_fields

    fields = post_fields(raw_entries(fixture_text("posts_page1.xml"))[0])
    assert isinstance(fields["published"], datetime.datetime)
    assert fields["published"].year == 2026
    assert fields["updated"] >= fields["published"]


def test_categories_collected_in_feed_order(fixture_text):
    from blogscraper.transform import post_fields

    uncategorised, categorised = (
        post_fields(r) for r in raw_entries(fixture_text("posts_page1.xml"))
    )
    assert uncategorised["categories"] == []
    assert categorised["categories"] == [
        "danger", "exploit", "online", "privacy", "safety", "scam", "security",
    ]


def test_urls_derived_from_links(fixture_text):
    from blogscraper.transform import post_fields

    fields = post_fields(raw_entries(fixture_text("posts_page1.xml"))[0])
    assert fields["original_url"] == "https://holdenweb.blogspot.com/2026/02/im-depressed.html"
    assert fields["replies_feed_url"].endswith("/comments/default")


def test_comment_fields(fixture_text):
    from blogscraper.transform import comment_fields

    fields = comment_fields(raw_entries(fixture_text("replies_page.xml"))[0])
    assert fields["author_name"] == "Nils"
    assert fields["post_id"] == "tag:blogger.com,1999:blog-496482.post-3698534751810022852"
    assert fields["body"].startswith("I like it.")
    assert fields["body_type"] == "html"
    assert isinstance(fields["published"], datetime.datetime)


def test_validator_reports_surprises(fixture_text):
    # An element the spec doesn't know, and an attribute set it doesn't
    # expect, must both surface as violations rather than pass silently -
    # the adhoc scripts' verify-then-bail idea, made durable (ADR-0005).
    from blogscraper.transform import POST_SPECS, validate_raw

    raw = raw_entries(fixture_text("posts_page1.xml"))[0]
    assert validate_raw(raw, POST_SPECS) == []

    unknown = {
        **raw,
        "elements": raw["elements"]
        + [{"ns": "", "tag": "surprise", "attrib": {}, "text": "?", "children": []}],
    }
    assert any("surprise" in v for v in validate_raw(unknown, POST_SPECS))

    odd_title = {
        **raw,
        "elements": [
            {**el, "attrib": {**el["attrib"], "lang": "en"}} if el["tag"] == "title" else el
            for el in raw["elements"]
        ],
    }
    assert any("title" in v for v in validate_raw(odd_title, POST_SPECS))


def test_rebuild_derives_typed_collections(fixture_text, test_db):
    from blogscraper.ingest import capture_entry, upsert_raw_comment, upsert_raw_post
    from blogscraper.models import Comment, Post
    from blogscraper.transform import rebuild

    for raw in raw_entries(fixture_text("posts_page1.xml")):
        upsert_raw_post(raw)
    upsert_raw_comment(raw_entries(fixture_text("replies_page.xml"))[0])

    result = rebuild()
    assert result["violations"] == []
    assert result["posts"] == Post.objects.count() == 2
    assert result["comments"] == Comment.objects.count() == 1
    assert len({p.thumbnail_url for p in Post.objects}) == 2
    assert Comment.objects.get().author_name == "Nils"

    # Rebuild is idempotent: derived collections are dropped and remade.
    assert rebuild()["posts"] == Post.objects.count() == 2


def test_rebuild_converges_blogger_and_artima(fixture_text, test_db):
    # Both source streams land in the one `post` collection, each tagged with
    # its source and carrying its own target path (ADR-0011).
    from blogscraper.ingest import upsert_raw_post
    from blogscraper.models import ArtimaEntry, Post
    from blogscraper.transform import rebuild

    for raw in raw_entries(fixture_text("posts_page1.xml")):
        upsert_raw_post(raw)
    ArtimaEntry(
        thread_id=41682,
        title="What Matters About Python?",
        body_html="<p>hi</p>",
        permalink="http://www.artima.com/weblogs/viewpost.jsp?thread=41682",
        published=datetime.datetime(2007, 8, 6, 23, 27),
        comment_count=19,
    ).save()

    result = rebuild()
    assert result["posts"] == Post.objects.count() == 3  # 2 blogger + 1 artima
    assert {p.source for p in Post.objects} == {"blogger", "artima"}
    assert Post.objects.get(source="artima").path == "posts/2007/08/what-matters-about-python.html"
    assert Post.objects(source="blogger").first().path.startswith("posts/")


def test_rebuild_refuses_on_violations_and_changes_nothing(fixture_text, test_db):
    from blogscraper.ingest import capture_entry, upsert_raw_post
    from blogscraper.models import Post, RawPost
    from blogscraper.transform import rebuild

    for raw in raw_entries(fixture_text("posts_page1.xml")):
        upsert_raw_post(raw)
    assert rebuild()["posts"] == 2

    # A raw document violating the spec's assumptions poisons the corpus...
    doc = RawPost.objects.first()
    doc.elements = list(doc.elements) + [
        {"ns": "", "tag": "surprise", "attrib": {}, "text": "?", "children": []}
    ]
    doc.save()
    result = rebuild()
    # ...so rebuild reports and leaves the previously derived posts alone.
    assert any("surprise" in v for v in result["violations"])
    assert Post.objects.count() == 2
