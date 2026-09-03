"""Table-driven transform from raw feed entries to typed field dicts.

One ElementSpec row per Atom element: a predicate stating what the corpus
is assumed to look like, and an extractor applied only when it does. The
validator runs the predicates without transforming, so assumptions can be
checked corpus-wide before anything is rebuilt (ADR-0005). adhoc6-13 did
all this by hand, one throwaway script per field.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

Element = dict[str, Any]  # as produced by ingest.capture_element


@dataclass(frozen=True)
class ElementSpec:
    tag: str
    target: str | None  # None: element is validated, then deliberately dropped
    extract: Callable[[Element], Any]
    attrib_ok: Callable[[dict[str, str]], bool]
    repeated: bool = False


def text(el: Element) -> str | None:
    return el["text"]


def iso_datetime(el: Element) -> datetime:
    return datetime.fromisoformat(el["text"])


def int_text(el: Element) -> int:
    return int(el["text"])


def attr(name: str) -> Callable[[Element], str]:
    return lambda el: el["attrib"][name]


def child_text(tag: str) -> Callable[[Element], str | None]:
    return lambda el: next((c["text"] for c in el["children"] if c["tag"] == tag), None)


def no_attribs(attrib: dict[str, str]) -> bool:
    return attrib == {}


def ignore(el: Element) -> None:
    return None


POST_SPECS = [
    ElementSpec("id", "post_id", text, no_attribs),
    ElementSpec("published", "published", iso_datetime, no_attribs),
    ElementSpec("updated", "updated", iso_datetime, no_attribs),
    ElementSpec("title", "title", text, lambda a: a == {"type": "text"}),
    ElementSpec("content", "content_html", text, lambda a: a == {"type": "html"}),
    ElementSpec(
        "category", "categories", attr("term"),
        lambda a: set(a) == {"scheme", "term"}, repeated=True,
    ),
    ElementSpec(
        "link", "links", lambda el: el["attrib"],
        lambda a: {"rel", "type", "href"} <= set(a), repeated=True,
    ),
    ElementSpec("author", "author_name", child_text("name"), no_attribs),
    ElementSpec("thumbnail", "thumbnail_url", attr("url"), lambda a: "url" in a),
    ElementSpec("total", "comment_count", int_text, no_attribs),
]

COMMENT_SPECS = [
    ElementSpec("id", "comment_id", text, no_attribs),
    ElementSpec("published", "published", iso_datetime, no_attribs),
    ElementSpec("updated", "updated", iso_datetime, no_attribs),
    ElementSpec("title", "title", text, lambda a: a == {"type": "text"}),
    ElementSpec("content", "body", text, lambda a: a.get("type") in {"html", "text"}),
    ElementSpec(
        "link", "links", lambda el: el["attrib"],
        lambda a: {"rel", "type", "href"} <= set(a), repeated=True,
    ),
    ElementSpec("author", "author_name", child_text("name"), no_attribs),
    ElementSpec("in-reply-to", "post_id", attr("ref"), lambda a: "ref" in a),
    ElementSpec("extendedProperty", None, ignore, lambda a: set(a) == {"name", "value"}),
]


def apply_specs(raw: dict[str, Any], specs: list[ElementSpec]) -> dict[str, Any]:
    by_tag = {spec.tag: spec for spec in specs}
    fields: dict[str, Any] = {
        spec.target: [] for spec in specs if spec.repeated and spec.target
    }
    for el in raw["elements"]:
        spec = by_tag.get(el["tag"])
        if spec is None or spec.target is None:
            continue
        if spec.repeated:
            fields[spec.target].append(spec.extract(el))
        else:
            fields[spec.target] = spec.extract(el)
    return fields


def validate_raw(raw: dict[str, Any], specs: list[ElementSpec]) -> list[str]:
    """Violations of the spec table's assumptions for one raw entry."""
    by_tag = {spec.tag: spec for spec in specs}
    violations = []
    for el in raw["elements"]:
        spec = by_tag.get(el["tag"])
        if spec is None:
            violations.append(
                f"{raw['atom_id']}: unknown element {el['tag']!r} attrib={el['attrib']}"
            )
        elif not spec.attrib_ok(el["attrib"]):
            violations.append(
                f"{raw['atom_id']}: {el['tag']} has unexpected attrib {el['attrib']}"
            )
    return violations


def _link_href(links: list[dict[str, str]], rel: str, type_: str) -> str | None:
    return next(
        (lk["href"] for lk in links if lk["rel"] == rel and lk["type"] == type_),
        None,
    )


def post_fields(raw: dict[str, Any]) -> dict[str, Any]:
    fields = apply_specs(raw, POST_SPECS)
    links = fields.get("links", [])
    fields["original_url"] = _link_href(links, "alternate", "text/html")
    fields["replies_feed_url"] = _link_href(links, "replies", "application/atom+xml")
    return fields


def rebuild() -> dict[str, Any]:
    """Validate the whole raw corpus, then remake posts/comments from it.

    Refuses to touch the derived collections while any raw document
    violates the spec tables' assumptions - the corpus changed shape, and
    the specs need extending before a rebuild can be trusted (ADR-0005).
    """
    from blogscraper.models import Comment, Post, RawComment, RawPost

    def raw_of(doc, id_field):
        return {"atom_id": getattr(doc, id_field), "elements": doc.elements}

    violations: list[str] = []
    for doc in RawPost.objects:
        violations += validate_raw(raw_of(doc, "post_id"), POST_SPECS)
    for doc in RawComment.objects:
        violations += validate_raw(raw_of(doc, "comment_id"), COMMENT_SPECS)
    if violations:
        return {"violations": violations, "posts": 0, "comments": 0}

    Post.drop_collection()
    Comment.drop_collection()
    posts = comments = 0
    for doc in RawPost.objects:
        Post(**post_fields(raw_of(doc, "post_id"))).save()
        posts += 1
    for doc in RawComment.objects:
        Comment(**comment_fields(raw_of(doc, "comment_id"))).save()
        comments += 1
    return {"violations": [], "posts": posts, "comments": comments}


def comment_fields(raw: dict[str, Any]) -> dict[str, Any]:
    fields = apply_specs(raw, COMMENT_SPECS)
    # Two derivations the 1:1 spec table can't express: a second value from
    # the content element, and a second child of author.
    for el in raw["elements"]:
        if el["tag"] == "content":
            fields["body_type"] = el["attrib"].get("type")
        elif el["tag"] == "author":
            fields["author_uri"] = child_text("uri")(el)
    return fields
