"""Scrape the Artima weblog (a Jive JSP site) into the `artima` collection.

Entries come from the blogger RSS feed and each `viewpost.jsp` page; comments
from the Jive forum flat view (`forums/flat.jsp`, paginated). Artima had no
tags. Parsers are pure and driven from saved page fixtures — no network.
"""
import datetime


def test_parse_feed_lists_the_seven_entries(fixture_text):
    from blogscraper.artima import parse_feed

    items = parse_feed(fixture_text("artima/feed.rss"))
    assert len(items) == 7
    first = items[0]
    assert first["title"] == "What Matters About Python?"
    assert first["thread_id"] == 41682
    assert first["permalink"].endswith("viewpost.jsp?thread=41682")
    assert first["summary"].startswith("Steve has just agreed")
    assert all(i["thread_id"] for i in items)


def test_parse_entry_pulls_metadata_and_clean_body(fixture_text):
    from blogscraper.artima import parse_entry

    e = parse_entry(fixture_text("artima/viewpost_41682.html"))
    assert e["title"] == "What Matters About Python?"
    assert e["author_name"] == "Steve Holden"
    assert e["published_display"] == "August 7, 2007"
    assert e["forum_id"] == 106
    assert e["thread_id"] == 41682
    assert e["comment_count"] == 19
    assert "2007 Steve Holden" in e["copyright"]
    assert e["blogger_bio"].startswith("Steve Holden has been using computers")
    # The body is the article prose only — no chrome, summary, talkback or bio.
    assert "I return to this forum" in e["body_html"]
    assert "good or bad for?" in e["body_html"]
    assert "Talk Back" not in e["body_html"]
    assert "About the Blogger" not in e["body_html"]


def test_parse_entry_keeps_in_article_h1_headings(fixture_text):
    # This post's body carries its own <h1> section headings, so the body end
    # marker must be the "Talk Back!" heading specifically, not the first <h1>.
    from blogscraper.artima import parse_entry

    body = parse_entry(fixture_text("artima/viewpost_7351.html"))["body_html"]
    assert "The Commoditization of the Platform" in body  # first heading
    assert "Too Much of a Good Thing?" in body            # a later heading
    assert "gruelling week at OSCON" in body              # body prose
    assert "Talk Back" not in body
    assert "About the Blogger" not in body


def test_parse_forum_page_splits_entry_from_comments(fixture_text):
    from blogscraper.artima import parse_forum_page

    page = parse_forum_page(fixture_text("artima/forum_41682_p1.html"))
    assert page["next_start"] == 15  # a second page follows

    entry = page["entry"]
    assert entry["author_name"] == "Steve Holden"
    assert entry["author_nickname"] == "holdenweb"
    assert entry["author_posts"] == 42
    assert entry["author_registered"] == "Apr, 2003"
    assert entry["posted"] == datetime.datetime(2007, 8, 6, 23, 27)
    assert entry["message_id"] == 64443

    assert len(page["comments"]) == 14  # 15 messages on page 1, minus the entry
    c0 = page["comments"][0]
    assert c0["author_name"] == "James Watson"
    assert c0["author_nickname"] == "watson"
    assert c0["author_posts"] == 2024
    assert c0["posted"] == datetime.datetime(2007, 8, 7, 7, 9)
    assert c0["subject"] == "Re: What Matters About Python?"
    assert "Is there enough documentation" in c0["body_html"]


def test_parse_forum_last_page_has_no_entry_and_no_next(fixture_text):
    from blogscraper.artima import parse_forum_page

    page = parse_forum_page(fixture_text("artima/forum_41682_p2.html"))
    assert page["entry"] is None       # the entry appears only on page 1
    assert page["next_start"] is None  # last page
    assert len(page["comments"]) == 5  # 19 comments total, 14 on p1, 5 here


def test_build_entry_assembles_and_saves_with_embedded_comments(test_db):
    from blogscraper.artima import build_entry
    from blogscraper.models import ArtimaEntry

    feed_item = {"title": "T", "thread_id": 999, "permalink": "http://x", "summary": "S"}
    meta = {
        "title": "T", "author_name": "Steve Holden", "published_display": "August 7, 2007",
        "forum_id": 106, "thread_id": 999, "comment_count": 1,
        "copyright": "Copyright 2007", "blogger_bio": "bio", "body_html": "<p>body</p>",
    }
    forum_entry = {
        "author_name": "Steve Holden", "author_nickname": "holdenweb",
        "author_posts": 42, "author_registered": "Apr, 2003", "message_id": 64443,
        "posted": datetime.datetime(2007, 8, 6, 23, 27),
    }
    comments = [{
        "message_id": 276524, "author_name": "James Watson", "author_nickname": "watson",
        "author_posts": 2024, "author_registered": "Sep, 2005",
        "posted": datetime.datetime(2007, 8, 7, 7, 9),
        "subject": "Re: T", "body_html": "<p>reply</p>",
    }]
    build_entry(feed_item, meta, forum_entry, comments)

    doc = ArtimaEntry.objects.get(thread_id=999)
    assert doc.author_nickname == "holdenweb"
    assert doc.published == datetime.datetime(2007, 8, 6, 23, 27)
    assert doc.published_display == "August 7, 2007"
    assert doc.summary == "S"
    assert doc.body_html == "<p>body</p>"
    assert doc.tags == []
    assert len(doc.comments) == 1
    assert doc.comments[0].author_name == "James Watson"
    assert doc.comments[0].posted == datetime.datetime(2007, 8, 7, 7, 9)
