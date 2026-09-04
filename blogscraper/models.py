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
