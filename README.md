# blogscraper

Migrate the content of a Blogger blog into MongoDB, then generate a tree of
HTML fragments for republishing under a new home (holdenweb.com).

The blog is still live, so ingestion is idempotent and can be re-run to pick up
new posts. Content is captured verbatim first and only then transformed, so the
derived data can always be rebuilt from an immutable raw copy — the design that
repaired an earlier silent corruption rather than papering over it.

## Pipeline

```
Atom feed  ──scrape──▶  raw_post / raw_comment  ──transform──▶  post / comment  ──export──▶  build/ (fragments + manifest)
             (verbatim,                            (typed,                         (${{{ROOT}}}
              upserted)                             validated)                      placeholders)
```

- **scrape** — walk the public Atom feed (and each commented post's replies
  feed), storing every entry verbatim in the raw collections. Idempotent:
  re-running upserts on the Atom id, never duplicates.
- **transform** — rebuild the typed `post`/`comment` collections from raw via a
  single table of per-element rules. It validates the whole corpus first and
  refuses to rebuild if any raw document breaks the table's assumptions.
- **export** — emit one content-only fragment per post under
  `build/posts/YYYY/MM/slug.html`, mirroring each post's original Blogger path,
  plus `manifest.json` and (once harvested) `images/`.

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

Generate the fragment tree into `build/` (gitignored):

```bash
just export
```

`python -m blogscraper <command> --help` lists the options for each command
(`--max-pages`, `--delay`, `--no-comments`, `--out`, `--decorator`, `--db`).

## Publishing the fragments

Fragments are content only, with no site chrome. Every generated URL (rewritten
image `src` and internal post `href`) is written with the placeholder
`${{{ROOT}}}`; publishing substitutes the site's mounted root through Jinja:

```python
from blogscraper.export import render_fragment

html = render_fragment(open("build/posts/2026/02/im-depressed.html").read(), "/blog")
```

The publish environment moves *all* of Jinja's delimiters to distinctive
sentinels (`${{{ }}}`, `${{% %}}}`, `${{# #}}}`), so `${...}`, `{{ ... }}`,
`{% ... %}` and `{# ... #}` in code and template samples pass through untouched
— `${{{ROOT}}}` is the only thing that substitutes. The generator scans for
those sentinels rather than escaping content, so bodies stay byte-faithful (see
[ADR-0009](docs/adr/0009-distinctive-root-sentinel.md)). Serve-time decoration
from holdenweb.com can be injected with `--decorator pkg.module:callable`.

## Tests

```bash
just test
```

Development is red/green TDD: each feature's test is written and seen to fail
before the code that makes it pass. Pure-function tests need no database; the
few DB-backed tests use a scratch `blogscraper_test` database.

## Layout

- `blogscraper/` — the package: `ingest`, `transform`, `export`, `models`,
  `__main__` (the CLI). No database connection is made at import time.
- `tests/` — pytest suite and fixtures (real Atom XML sampled from the corpus).
- `docs/adr/` — architecture decision records.
- `dump/` — a mongodump of the raw corpus (backup, not tracked).
- The flat top-level scripts (`scraper.py`, `db.py`, `adhoc*.py`, …) are the
  **superseded** original pipeline, kept runnable via the `legacy-*` recipes
  until retired.
