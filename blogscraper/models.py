"""Document models: raw (verbatim capture) and derived (typed) collections.

Raw documents are replaced wholesale on re-scrape and never transformed in
place; the typed collections are rebuilt from them at will (ADR-0004).
No connection is made at import time — call init_db() first.
"""
from __future__ import annotations

import mongoengine
from mongoengine import (
    DateTimeField,
    DictField,
    Document,
    DynamicDocument,
    EmbeddedDocument,
    EmbeddedDocumentListField,
    FileField,
    IntField,
    ListField,
    StringField,
)


def init_db(name: str = "blogscraper") -> None:
    mongoengine.connect(name, uuidRepresentation="standard")


class RawPost(DynamicDocument):
    post_id = StringField(required=True, unique=True)  # the Atom id
    elements = ListField()
    fetched_at = DateTimeField()


class RawComment(DynamicDocument):
    comment_id = StringField(required=True, unique=True)  # the Atom id
    post_id = StringField(required=True)  # parent post's Atom id (thr:in-reply-to@ref)
    elements = ListField()
    fetched_at = DateTimeField()


class Post(Document):
    post_id = StringField(required=True, unique=True)
    title = StringField()
    content_html = StringField()
    published = DateTimeField()
    updated = DateTimeField()
    categories = ListField(StringField())
    links = ListField(DictField())
    author_name = StringField()
    thumbnail_url = StringField()
    comment_count = IntField()
    original_url = StringField()  # rel=alternate on the old blog
    replies_feed_url = StringField()


class Comment(Document):
    comment_id = StringField(required=True, unique=True)
    post_id = StringField(required=True)
    title = StringField()
    body = StringField()
    body_type = StringField()  # 'html' or 'text', from the content element
    published = DateTimeField()
    updated = DateTimeField()
    author_name = StringField()
    author_uri = StringField()
    links = ListField(DictField())


class PhotoImage(Document):
    # A fresh collection, not the legacy `photo_image` the superseded adhoc15
    # run left behind (it holds a duplicate src and no unique index, so building
    # this model's unique index over it would fail). The legacy collection is
    # left for Steve to drop; this model owns clean, integrity-checked data.
    meta = {"collection": "photo"}
    src = StringField(required=True, unique=True)  # URL as it appears in post HTML
    content_type = StringField()
    image = FileField()
    alt = StringField()
    width = IntField()
    height = IntField()


class Tag(Document):
    # An inverted index of Post.categories: one document per term, listing the
    # post_ids of the posts that carry it. Derived from Post, rebuilt at will
    # (ADR-0004).
    meta = {"collection": "tag"}
    tag = StringField(required=True, unique=True)
    entries = ListField(StringField())  # post_ids of the posts carrying this tag


class ArtimaComment(EmbeddedDocument):
    # One reply on a Jive forum thread, as scraped from the flat view.
    message_id = IntField()
    author_name = StringField()
    author_nickname = StringField()
    author_posts = IntField()  # the author's forum post count at scrape time
    author_registered = StringField()  # e.g. "Sep, 2005"
    posted = DateTimeField()
    subject = StringField()
    body_html = StringField()


class ArtimaEntry(Document):
    # The seven posts from Steve's old Artima weblog, each with its comments
    # embedded. A standalone collection, unrelated to the Blogger pipeline.
    # `published` is the precise timestamp from the forum; `published_display`
    # the date string the post page shows. Artima had no tags, so `tags` is
    # captured but empty.
    meta = {"collection": "artima"}
    thread_id = IntField(required=True, unique=True)
    forum_id = IntField()
    permalink = StringField()
    title = StringField()
    author_name = StringField()
    author_nickname = StringField()
    author_posts = IntField()
    author_registered = StringField()
    message_id = IntField()  # the forum message id of the entry itself
    published = DateTimeField()
    published_display = StringField()
    summary = StringField()
    body_html = StringField()
    blogger_bio = StringField()
    copyright = StringField()
    comment_count = IntField()
    tags = ListField(StringField())
    comments = EmbeddedDocumentListField(ArtimaComment)
    scraped_at = DateTimeField()
