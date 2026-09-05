# blogscraper

Migrate the content of a Blogger blog into MongoDB, then generate a tree of
HTML fragments for republishing under a new home (holdenweb.com).

The blog is still live, so ingestion is idempotent and can be re-run to pick up
new posts. Content is captured verbatim first and only then transformed, so the
derived data can always be rebuilt from an immutable raw copy — the design that
repaired an earlier silent corruption rather than papering over it.

## Pipeline

```
scrape     Atom feed              ─▶  raw_post, raw_comment   (verbatim, upserted)
transform  raw_post, raw_comment  ─▶  post, comment           (typed, validated)
images     post                   ─▶  photo                   (Blogger images, GridFS)
export     post + photo           ─▶  build/  (fragments, images, manifest)
```

- **scrape** — walk the public Atom feed (and each commented post's replies
  feed), storing every entry verbatim in the raw collections. Idempotent:
  re-running upserts on the Atom id, never duplicates.
- **transform** — rebuild the typed `post`/`comment` collections from raw via a
  single table of per-element rules. It validates the whole corpus first and
  refuses to rebuild if any raw document breaks the table's assumptions.
- **images** — harvest the Blogger-hosted images each post references — both the
  displayed `<img src>` and the full-size image its "click for full size" link
  points at — into the `photo` collection (unique `src`, idempotent, external
  images left alone).
- **export** — emit one content-only fragment per post under
  `build/posts/YYYY/MM/slug.html`, mirroring each post's original Blogger path,
  rewriting harvested image and internal post URLs to placeholders, and writing
  the harvested images and a `manifest.json` alongside.

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

```bash
uv run python -m blogscraper transform
```

Harvest the Blogger-hosted post images into the `photo` collection:

```bash
just images
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
