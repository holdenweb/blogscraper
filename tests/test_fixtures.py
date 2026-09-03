"""Sanity checks on the captured feed pages the rest of the suite builds on.

The fixtures are real Blogger responses (captured 2026-09-03): two
consecutive 2-entry pages of the posts feed, and the replies feed of one
commented post.
"""
from xml.etree import ElementTree as ET

ATOM = "{http://www.w3.org/2005/Atom}"


def test_posts_pages_hold_two_entries_each(fixture_text):
    for name in ("posts_page1.xml", "posts_page2.xml"):
        root = ET.fromstring(fixture_text(name))
        assert len(root.findall(f"{ATOM}entry")) == 2


def test_posts_page1_links_onward(fixture_text):
    root = ET.fromstring(fixture_text("posts_page1.xml"))
    rels = {el.attrib.get("rel") for el in root.findall(f"{ATOM}link")}
    assert "next" in rels


def test_author_elements_carry_children(fixture_text):
    # The legacy scraper flattened entries one level deep and lost these.
    root = ET.fromstring(fixture_text("posts_page1.xml"))
    author = root.find(f"{ATOM}entry").find(f"{ATOM}author")
    assert [c.text for c in author if c.tag == f"{ATOM}name"] == ["holdenweb"]


def test_reply_entry_references_its_post(fixture_text):
    root = ET.fromstring(fixture_text("replies_page.xml"))
    entry = root.find(f"{ATOM}entry")
    in_reply_to = entry.find("{http://purl.org/syndication/thread/1.0}in-reply-to")
    assert in_reply_to.attrib["ref"].startswith("tag:blogger.com,1999:blog-496482.post-")
