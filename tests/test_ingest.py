"""Ingest: verbatim recursive capture of Atom entries, idempotent upserts."""
from xml.etree import ElementTree as ET

ATOM = "{http://www.w3.org/2005/Atom}"


def entries(xml_text):
    return ET.fromstring(xml_text).findall(f"{ATOM}entry")


def test_capture_entry_recurses_into_children(fixture_text):
    # The legacy create_entry captured one level only, losing author names.
    from blogscraper.ingest import capture_entry

    raw = capture_entry(entries(fixture_text("posts_page1.xml"))[0])
    author = next(el for el in raw["elements"] if el["tag"] == "author")
    names = [c["text"] for c in author["children"] if c["tag"] == "name"]
    assert names == ["holdenweb"]


def test_capture_entry_promotes_the_atom_id(fixture_text):
    from blogscraper.ingest import capture_entry

    raw = capture_entry(entries(fixture_text("posts_page1.xml"))[0])
    assert raw["atom_id"].startswith("tag:blogger.com,1999:blog-496482.post-")


def test_capture_entry_preserves_attributes_verbatim(fixture_text):
    from blogscraper.ingest import capture_entry

    raw = capture_entry(entries(fixture_text("posts_page1.xml"))[0])
    thumb = next(el for el in raw["elements"] if el["tag"] == "thumbnail")
    assert set(thumb["attrib"]) == {"url", "height", "width"}
    assert thumb["attrib"]["url"].startswith("https://")


def test_upsert_raw_post_is_idempotent_and_unique_indexed(fixture_text, test_db):
    from blogscraper.ingest import capture_entry, upsert_raw_post
    from blogscraper.models import RawPost

    raws = [capture_entry(e) for e in entries(fixture_text("posts_page1.xml"))]
    for raw in raws + raws:  # the same page ingested twice
        upsert_raw_post(raw)
    assert RawPost.objects.count() == 2
    info = RawPost._get_collection().index_information()
    assert any(
        spec.get("unique") and spec["key"] == [("post_id", 1)]
        for spec in info.values()
    )


def test_upsert_raw_post_replaces_wholesale(fixture_text, test_db):
    from blogscraper.ingest import capture_entry, upsert_raw_post
    from blogscraper.models import RawPost

    raw = capture_entry(entries(fixture_text("posts_page1.xml"))[0])
    upsert_raw_post(raw)
    revised = {**raw, "elements": [el for el in raw["elements"] if el["tag"] != "thumbnail"]}
    upsert_raw_post(revised)
    stored = RawPost.objects.get(post_id=raw["atom_id"])
    assert not any(el["tag"] == "thumbnail" for el in stored.elements)


def test_raw_comment_carries_its_parent_post_id(fixture_text, test_db):
    from blogscraper.ingest import capture_entry, upsert_raw_comment
    from blogscraper.models import RawComment

    raw = capture_entry(entries(fixture_text("replies_page.xml"))[0])
    upsert_raw_comment(raw)
    stored = RawComment.objects.get()
    assert stored.comment_id == raw["atom_id"]
    assert stored.post_id == "tag:blogger.com,1999:blog-496482.post-3698534751810022852"


def next_link(xml_text):
    root = ET.fromstring(xml_text)
    return next(
        el.attrib["href"]
        for el in root.findall(f"{ATOM}link")
        if el.attrib.get("rel") == "next"
    )


def test_walk_feed_follows_next_links(fixture_text):
    from blogscraper.ingest import walk_feed

    page1 = fixture_text("posts_page1.xml")
    pages = {"start": page1, next_link(page1): fixture_text("posts_page2.xml")}
    fetched = []

    def fetch(url):
        fetched.append(url)
        return pages[url]  # KeyError = walked somewhere unexpected

    raws = list(walk_feed(fetch, "start", max_pages=2))
    assert len(raws) == 4
    assert len(fetched) == 2
    assert all(raw["atom_id"].startswith("tag:blogger.com,") for raw in raws)


def test_walk_feed_stops_without_next_link(fixture_text):
    from blogscraper.ingest import walk_feed

    pages = {"start": fixture_text("replies_page.xml")}
    raws = list(walk_feed(pages.__getitem__, "start"))
    assert len(raws) == 1


def test_scrape_comments_fetches_only_commented_posts(fixture_text, test_db):
    from blogscraper.ingest import capture_entry, scrape_comments, upsert_raw_post
    from blogscraper.models import RawComment

    raws = [capture_entry(e) for e in entries(fixture_text("posts_page1.xml"))]
    # Both fixture posts have total=0; pretend the first has one comment.
    for el in raws[0]["elements"]:
        if el["tag"] == "total":
            el["text"] = "1"
    for raw in raws:
        upsert_raw_post(raw)

    replies_url = next(
        el["attrib"]["href"]
        for el in raws[0]["elements"]
        if el["tag"] == "link"
        and el["attrib"]["rel"] == "replies"
        and el["attrib"]["type"] == "application/atom+xml"
    )
    pages = {replies_url: fixture_text("replies_page.xml")}
    fetched = []

    def fetch(url):
        fetched.append(url)
        return pages[url]  # KeyError = fetched an uncommented post's feed

    count = scrape_comments(fetch)
    assert count == 1
    assert fetched == [replies_url]
    assert RawComment.objects.count() == 1
