"""Scrape Steve's old Artima weblog into the `artima` collection.

Artima is a Jive JSP site, not a Blogger Atom feed, so this is its own small
scraper rather than part of the Blogger pipeline. Per entry it draws on three
sources:

- the blogger **RSS feed** (`feeds/bloggers/holdenweb.rss`) — the list of the
  seven entries, with titles, permalinks and summaries;
- each **`viewpost.jsp`** page — clean body HTML, byline, display date, the
  blogger bio and copyright, and the entry's forum/thread ids;
- the Jive **forum flat view** (`forums/flat.jsp`, paginated) — the entry's
  precise timestamp and every comment, with each poster's forum metadata.

Artima weblogs had no tags, so `tags` is captured but always empty. The parsers
are pure and driven from page fixtures in the tests; only `scrape_artima`
touches the network.
"""
from __future__ import annotations

import datetime
import re
from typing import Any, Callable
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup

WEBLOGS = "https://www.artima.com/weblogs/"
FORUMS = "https://www.artima.com/forums/"
FEED_URL = WEBLOGS + "feeds/bloggers/holdenweb.rss"
FORUM_PAGE = 15  # messages per Jive forum page


def _norm(text: str | None) -> str | None:
    return re.sub(r"\s+", " ", text).strip() if text else text


# --------------------------------------------------------------------------- #
# Feed
# --------------------------------------------------------------------------- #
def parse_feed(rss_text: str) -> list[dict[str, Any]]:
    """The blog's entries from its RSS 1.0 (RDF) feed."""
    root = ET.fromstring(rss_text)

    def local(tag: str) -> str:
        return re.sub(r"\{.*\}", "", tag)

    items = []
    for item in (e for e in root.iter() if local(e.tag) == "item"):
        fields = {local(ch.tag): (ch.text or "").strip() for ch in item}
        link = fields.get("link", "")
        m = re.search(r"thread=(\d+)", link)
        items.append(
            {
                "title": fields.get("title"),
                "permalink": link,
                "thread_id": int(m.group(1)) if m else None,
                "summary": fields.get("description"),
            }
        )
    return items


# --------------------------------------------------------------------------- #
# Entry page (viewpost.jsp)
# --------------------------------------------------------------------------- #
def _between(text: str, start: str, end: str) -> str | None:
    i = text.find(start)
    if i == -1:
        return None
    i += len(start)
    j = text.find(end, i)
    return text[i : j if j != -1 else None].strip() or None


def parse_entry(html: str) -> dict[str, Any]:
    """Entry metadata and clean body from a `viewpost.jsp` page."""
    soup = BeautifulSoup(html, "html.parser")

    def css_text(name: str) -> str | None:
        el = soup.find(class_=name)
        return el.get_text(" ", strip=True) if el else None

    byline = css_text("as")  # "by Steve Holden"
    author = re.sub(r"^by\s+", "", byline).strip() if byline else None

    forum_id = thread_id = None
    for a in soup.find_all("a", href=True):
        m = re.search(r"forum=(\d+)&(?:amp;)?thread=(\d+)", a["href"])
        if m:
            forum_id, thread_id = int(m.group(1)), int(m.group(2))
            break

    # Body: the run between the summary <blockquote> and the "Talk Back!"
    # heading, dropping the <hr> and ad <table> Artima injects between them.
    # Sliced from the raw HTML rather than walked over the tree: the page's
    # unclosed <p> tags make html.parser nest later content inside a body
    # paragraph. The end marker is the "Talk Back!" heading specifically, not
    # the first <h1> — the article body itself can contain <h1> section headings.
    body_html = None
    if "</blockquote>" in html:
        after = html.split("</blockquote>", 1)[1]
        region = re.split(r"<h1[^>]*>\s*Talk Back", after, maxsplit=1)[0]
        region_soup = BeautifulSoup(region, "html.parser")
        for hr in region_soup.find_all("hr"):
            hr.decompose()
        for table in region_soup.find_all("table"):
            markup = str(table).lower()
            if table.get("align") == "right" or any(
                s in markup for s in ("adnotice", "phpads", "adview")
            ):
                table.decompose()  # ad, not content
        body_html = str(region_soup).strip() or None

    text = _norm(soup.get_text("\n")) or ""
    count = re.search(r"posted\s+(\d+)\s+comments?", text)
    bio = _between(text, "About the Blogger ", "This weblog entry is")
    copyright_ = _between(text, "This weblog entry is ", "rights reserved")
    if copyright_:
        copyright_ = f"{copyright_} rights reserved."

    return {
        "title": soup.title.get_text(strip=True) if soup.title else None,
        "author_name": author,
        "published_display": css_text("pd"),  # "August 7, 2007"
        "forum_id": forum_id,
        "thread_id": thread_id,
        "comment_count": int(count.group(1)) if count else None,
        "body_html": body_html,
        "blogger_bio": bio,
        "copyright": copyright_,
    }


# --------------------------------------------------------------------------- #
# Forum flat view (comments)
# --------------------------------------------------------------------------- #
def _parse_posted(stamp: str | None) -> datetime.datetime | None:
    if not stamp:
        return None
    try:
        return datetime.datetime.strptime(stamp.strip(), "%b %d, %Y %I:%M %p")
    except ValueError:
        return None


def _message_subject(chunk_soup: BeautifulSoup) -> str | None:
    # The author's name is in <a><b>…</b></a>; the subject is the first <b>
    # that is not inside a link.
    for b in chunk_soup.find_all("b"):
        if not b.find_parent("a"):
            return b.get_text(strip=True)
    return None


def _message_body(chunk_soup: BeautifulSoup) -> str | None:
    cell = chunk_soup.find("td", attrs={"colspan": "3"})
    if not cell:
        return None
    inner = cell.find("font")
    return (inner.decode_contents() if inner else cell.decode_contents()).strip() or None


def _parse_message(chunk: str) -> dict[str, Any]:
    def group(pattern: str) -> str | None:
        m = re.search(pattern, chunk, re.S)
        return m.group(1).strip() if m else None

    def as_int(value: str | None) -> int | None:
        return int(value) if value is not None else None

    chunk_soup = BeautifulSoup(chunk, "html.parser")
    return {
        "message_id": as_int(group(r'name="(\d+)"')),
        "author_name": group(r'profile\.jsp\?user=\d+"\s*title="([^"]*)"'),
        "author_nickname": group(r"Nickname:\s*([^\s<]+)"),
        "author_posts": as_int(group(r"Posts:\s*(\d+)")),
        "author_registered": group(r"Registered:\s*([A-Za-z]+,\s*\d{4})"),
        "posted": _parse_posted(group(r"Posted:\s*([^<]+?)\s*</font>")),
        "subject": _message_subject(chunk_soup),
        "body_html": _message_body(chunk_soup),
        "is_entry": "View in Weblogs" in chunk,
    }


def parse_forum_page(html: str) -> dict[str, Any]:
    """The entry (if present) and comments on one forum flat-view page."""
    chunks = re.findall(r"<!-- message start -->(.*?)<!-- message end -->", html, re.S)
    messages = [_parse_message(c) for c in chunks]

    entry = next((m for m in messages if m["is_entry"]), None)
    comments = [m for m in messages if not m["is_entry"]]

    # A next page exists iff there is a "»" link carrying a higher start offset.
    next_start = None
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        if a.get_text(strip=True) == "»":
            m = re.search(r"start=(\d+)", a["href"])
            if m:
                next_start = int(m.group(1))
                break

    return {"entry": entry, "comments": comments, "next_start": next_start}


# --------------------------------------------------------------------------- #
# Assembly + orchestration
# --------------------------------------------------------------------------- #
def build_entry(feed_item, meta, forum_entry, comments):
    """Assemble one ArtimaEntry from the feed/viewpost/forum parts and save it."""
    from blogscraper.models import ArtimaComment, ArtimaEntry

    fe = forum_entry or {}
    comment_fields = (
        "message_id", "author_name", "author_nickname", "author_posts",
        "author_registered", "posted", "subject", "body_html",
    )
    doc = ArtimaEntry(
        thread_id=feed_item["thread_id"],
        forum_id=meta.get("forum_id"),
        permalink=feed_item.get("permalink"),
        title=meta.get("title") or feed_item.get("title"),
        author_name=meta.get("author_name") or fe.get("author_name"),
        author_nickname=fe.get("author_nickname"),
        author_posts=fe.get("author_posts"),
        author_registered=fe.get("author_registered"),
        message_id=fe.get("message_id"),
        published=fe.get("posted"),
        published_display=meta.get("published_display"),
        summary=feed_item.get("summary"),
        body_html=meta.get("body_html"),
        blogger_bio=meta.get("blogger_bio"),
        copyright=meta.get("copyright"),
        comment_count=(
            meta.get("comment_count")
            if meta.get("comment_count") is not None
            else len(comments)
        ),
        tags=[],
        comments=[
            ArtimaComment(**{k: c.get(k) for k in comment_fields}) for c in comments
        ],
        scraped_at=datetime.datetime.now(datetime.timezone.utc),
    )
    doc.save()
    return doc


def _forum_comments(fetch: Callable[[str], str], forum_id: int, thread_id: int):
    """Walk every forum page, returning (entry_message, all_comments)."""
    entry = None
    comments: list[dict[str, Any]] = []
    start = 0
    while True:
        url = (
            f"{FORUMS}flat.jsp?forum={forum_id}&thread={thread_id}"
            f"&start={start}&msRange={FORUM_PAGE}"
        )
        page = parse_forum_page(fetch(url))
        if page["entry"]:
            entry = page["entry"]
        comments.extend(page["comments"])
        if page["next_start"] is None or page["next_start"] <= start:
            return entry, comments
        start = page["next_start"]


def scrape_artima(fetch: Callable[[str], str]) -> int:
    """Rebuild the `artima` collection from the live site. Returns entry count.

    `fetch` is injected (url -> body text) so this is driven from the network in
    production and could be driven from fixtures in a test.
    """
    from blogscraper.models import ArtimaEntry

    ArtimaEntry.drop_collection()
    feed = parse_feed(fetch(FEED_URL))
    for item in feed:
        thread_id = item["thread_id"]
        meta = parse_entry(fetch(f"{WEBLOGS}viewpost.jsp?thread={thread_id}"))
        forum_id = meta.get("forum_id") or 106
        forum_entry, comments = _forum_comments(fetch, forum_id, thread_id)
        build_entry(item, meta, forum_entry, comments)
    return len(feed)
