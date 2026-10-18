# blogscraper

Capture Steve's blogs — a live Blogger blog and the old Artima weblog — into
MongoDB, then generate a tree of HTML fragments for republishing under a new home
(holdenweb.com).

Each blog is captured verbatim first and only then transformed, so the derived
data can always be rebuilt from an immutable raw copy — the design that repaired
an earlier silent corruption rather than papering over it.

## Pipeline

Two source streams feed one production line. Each source captures a blog its own
way; both converge into the source-tagged `post` collection, and everything
downstream runs on `post` regardless of origin (ADR-0011).

```
Sources (parallel streams)
  Blogger   scrape   Atom feed        ─▶  raw_post, raw_comment
  Artima    artima   Jive JSP + RSS   ─▶  artima

Production line (source-blind, on `post`)
  transform  raw_post + artima        ─▶  post (source-tagged, with a path), comment
  images     post                     ─▶  photo
  tags       post                     ─▶  tag
  export     post (+ photo)           ─▶  build/  (fragments · manifest · redirects)
```

- **scrape** — walk the Blogger Atom feed (and each commented post's replies
  feed), storing every entry verbatim in the raw collections. Idempotent:
  re-running upserts on the Atom id, never duplicates.
- **artima** — scrape the old Artima weblog (a Jive JSP site) into the `artima`
  collection: entries from the RSS feed and each post page, comments from the
  forum. Its own raw layer, parallel to `raw_post`.
- **transform** — rebuild the converged `post`/`comment` collections from every
  source in one pass — Blogger posts from `raw_post`, Artima from `artima`. Each
  post carries its `source` and the `path` it will take in the tree. Validates
  the Blogger raw first and refuses to rebuild if a raw document breaks the
  table's assumptions. An untitled post whose body opens with a bold
  pseudo-heading takes that as its title, with the heading stripped from the body
  (ADR-0012).
- **images** — harvest the Blogger-hosted images each post references — both the
  displayed `<img src>` and the full-size image its "click for full size" link
  points at — into the `photo` collection (unique `src`, idempotent, external
  images left alone).
- **tags** — invert `Post.categories` into a `tag` collection: one document per
  category term, holding the `post_id`s that carry it. Rebuilt from `post` at
  will, like the other derived collections.
- **export** — emit one fragment per post at its `path`
  (`posts/YYYY/MM/slug.html`), rewriting harvested image and internal post URLs
  to placeholders. Each fragment gains post-level furniture (ADR-0012): a
  provenance line (*Originally published at …*), its tags in bold, and — when the
  post has comments — an *N comments* link to paginated comment pages
  (`slug.comments/N.html`, 10 per page) generated alongside. Also writes the
  harvested images, a `manifest.json` (listing each post's `comment_pages`), and
  a `redirects.json` (the Blogger cutover 301s). Site chrome is still the
  consumer's job; this furniture is post content, not chrome.

Design decisions and their rationale live in [`docs/adr/`](docs/adr/); the work
queue is [`BACKLOG.md`](BACKLOG.md).

## Requirements

- Python ≥ 3.12 and [uv](https://docs.astral.sh/uv/)
- A local MongoDB (the pipeline connects to `blogscraper` on the default port)
- `mongodump` / `mongorestore` for backups (optional)

## Usage

The blog id comes from `$BLOG_ID` (the `justfile` sets it). Recipes wrap
`uv run python -m blogscraper <command>`; use either.

Full refresh from the live blog, then rebuild the typed collections:

```bash
just refresh
```

Or step by step:

```bash
uv run python -m blogscraper scrape --blog-id 496482
```

```bash
uv run python -m blogscraper validate
```

Scrape the second source — the old Artima weblog — into the `artima` collection
(its entries then join `post` on the next `transform`):

```bash
just artima
```

```bash
uv run python -m blogscraper transform
```

Harvest the Blogger-hosted post images into the `photo` collection:

```bash
just images
```

Rebuild the tag collection (each category term → the post ids carrying it):

```bash
just tags
```

Generate the fragment tree into `build/` (gitignored):

```bash
just export
```

`python -m blogscraper <command> --help` lists the options for each command
(`--max-pages`, `--delay`, `--no-comments`, `--out`, `--decorator`, `--db`).

## Publishing the fragments

Fragments are content only, with no site chrome. Generated URLs are written with
placeholders — `${{{ROOT}}}` for internal post links, `${{{IMAGE_ROOT}}}` for
images — and publishing substitutes the site's mounted roots through Jinja:

```python
from blogscraper.export import render_fragment

html = render_fragment(open("build/posts/2026/02/im-depressed.html").read(), "/blog")
```

`IMAGE_ROOT` defaults to `ROOT`, so a self-contained tree just works; pass it
explicitly — `render_fragment(html, "/blog", image_root="https://img.holdenweb.com")`
— to serve images from a shared host, so one source can be consumed by several
sites ([ADR-0010](docs/adr/0010-image-root-placeholder.md)).

The publish environment moves *all* of Jinja's delimiters to distinctive
sentinels (`${{{ }}}`, `${{% %}}}`, `${{# #}}}`), so `${...}`, `{{ ... }}`,
`{% ... %}` and `{# ... #}` in code and template samples pass through untouched —
only the root placeholders substitute. The generator scans for those sentinels
rather than escaping content, so bodies stay byte-faithful (see
[ADR-0009](docs/adr/0009-distinctive-root-sentinel.md)).

Site chrome is applied by the consuming site at serve time: it decorates the
paths the manifest lists (those under `posts/`) and serves everything else
literally ([ADR-0007](docs/adr/0007-fragment-tree-export.md)). The generator's
optional `--decorator pkg.module:callable` hook is for generation-time content
transforms, not chrome.

The publish helpers and delimiter constants live in the dependency-free
[`blogscraper/publish.py`](blogscraper/publish.py) (Jinja2 only) so a consuming
site can copy them rather than depend on the scraper package. `redirects.json`
carries the cutover 301s in the same placeholder form (`/YYYY/MM/slug.html` →
`${{{ROOT}}}/posts/YYYY/MM/slug.html`), so the consumer substitutes its mount
with the same `ROOT`.

Those 301s belong to whatever serves the **site root**: the `from` paths are
site-root paths, not under `${{{ROOT}}}`, so the redirect map is applied by the
site's top-level app, not by the blog mount that consumes the fragments.
`redirects.json` itself is just served literally alongside `manifest.json`.

## Tests

```bash
just test
```

Development is red/green TDD: each feature's test is written and seen to fail
before the code that makes it pass. Pure-function tests need no database; the
few DB-backed tests use a scratch `blogscraper_test` database.

## Layout

- `blogscraper/` — the package: `ingest`, `transform`, `images`, `export`,
  `models`, `__main__` (the CLI). No database connection is made at import time.
- `tests/` — pytest suite and fixtures (real Atom XML sampled from the corpus).
- `docs/adr/` — architecture decision records.
- `dump/` — a mongodump of the raw corpus (backup, not tracked).

The original flat pipeline (`scraper.py`, `db.py`, the `adhoc*.py` scripts) has
been retired; it survives in the git history as the record of how the corpus was
first produced.
