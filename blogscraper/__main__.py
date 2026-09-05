"""Command-line entry point: python -m blogscraper <subcommand>.

    scrape      fetch posts (and their comments) from the live blog into raw
    comments    fetch only the replies feeds for posts that claim comments
    transform   rebuild the typed post/comment collections from raw
    validate    report raw documents that violate the transform's assumptions
"""
from __future__ import annotations

import argparse
import os
import sys

from blogscraper import ingest, transform
from blogscraper.models import RawComment, RawPost, init_db


def _blog_id(args) -> str:
    blog_id = args.blog_id or os.environ.get("BLOG_ID")
    if not blog_id:
        sys.exit("No blog id: pass --blog-id or set BLOG_ID.")
    return blog_id


def cmd_scrape(args) -> None:
    init_db(args.db)
    fetch = ingest.make_fetcher(delay=args.delay)
    posts = ingest.scrape_posts(fetch, _blog_id(args), max_pages=args.max_pages or None)
    print(f"Ingested {posts} posts into raw_post.")
    if not args.no_comments:
        comments = ingest.scrape_comments(fetch)
        print(f"Ingested {comments} comments into raw_comment.")


def cmd_comments(args) -> None:
    init_db(args.db)
    fetch = ingest.make_fetcher(delay=args.delay)
    print(f"Ingested {ingest.scrape_comments(fetch)} comments into raw_comment.")


def cmd_transform(args) -> None:
    init_db(args.db)
    result = transform.rebuild()
    if result["violations"]:
        for v in result["violations"]:
            print("VIOLATION:", v)
        sys.exit(
            f"Refused to rebuild: {len(result['violations'])} violation(s); "
            "extend the spec table, then retry."
        )
    print(f"Rebuilt {result['posts']} posts and {result['comments']} comments.")


def cmd_validate(args) -> None:
    init_db(args.db)
    violations = []
    for doc in RawPost.objects:
        violations += transform.validate_raw(
            {"atom_id": doc.post_id, "elements": doc.elements}, transform.POST_SPECS
        )
    for doc in RawComment.objects:
        violations += transform.validate_raw(
            {"atom_id": doc.comment_id, "elements": doc.elements},
            transform.COMMENT_SPECS,
        )
    for v in violations:
        print(v)
    print(f"{len(violations)} violation(s).")
    sys.exit(1 if violations else 0)


def cmd_images(args) -> None:
    init_db(args.db)
    from blogscraper import images

    result = images.harvest(images.make_image_fetcher(delay=args.delay))
    for e in result["errors"]:
        print("FAILED:", e)
    print(
        f"Stored {result['stored']} images "
        f"({result['existing']} already present, "
        f"{result['external']} external left in place, {result['failed']} failed)."
    )


def cmd_export(args) -> None:
    init_db(args.db)
    from blogscraper import export

    result = export.export_all(args.out, decorator=args.decorator)
    for c in result["collisions"]:
        print("COLLISION:", c)
    tail = f"; {len(result['collisions'])} collision(s)." if result["collisions"] else "."
    print(
        f"Exported {result['posts']} fragments and {result['images']} images "
        f"to {args.out}{tail}"
    )


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(prog="blogscraper")
    parser.add_argument("--db", default="blogscraper", help="MongoDB database name")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("scrape", help="fetch posts and comments from the live blog")
    p.add_argument("--blog-id", help="Blogger blog id (default: $BLOG_ID)")
    p.add_argument("--max-pages", type=int, default=0, help="0 = all pages")
    p.add_argument("--delay", type=float, default=0.5, help="seconds between requests")
    p.add_argument("--no-comments", action="store_true")
    p.set_defaults(func=cmd_scrape)

    p = sub.add_parser("comments", help="fetch replies feeds for commented posts")
    p.add_argument("--delay", type=float, default=0.5)
    p.set_defaults(func=cmd_comments)

    p = sub.add_parser("transform", help="rebuild typed collections from raw")
    p.set_defaults(func=cmd_transform)

    p = sub.add_parser("validate", help="report raw documents violating assumptions")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("images", help="harvest Blogger-hosted post images into the photo collection")
    p.add_argument("--delay", type=float, default=0.5, help="seconds between requests")
    p.set_defaults(func=cmd_images)

    p = sub.add_parser("export", help="generate the fragment tree, images and manifest")
    p.add_argument("--out", default="build", help="output directory (default: build/)")
    p.add_argument("--decorator", help="serve-time decorator as pkg.module:callable")
    p.set_defaults(func=cmd_export)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
