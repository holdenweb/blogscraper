# 4. Immutable raw collections; derived collections rebuilt idempotently

Date: 2026-09-03
Status: Accepted

## Context

The adhoc pipeline transformed the single `blog_post` collection in
place, destroying raw fields as it flattened them; the only undo was a
`mongodump`/`mongorestore` cycle wired into the justfile. A
stale-variable bug in adhoc12 silently gave all 538 posts the same
`thumbnail_url`, and nothing in the design could notice, because the data
it corrupted was also the only copy.

## Decision

Scraped data lands verbatim in `raw_posts` and `raw_comments` and is
never transformed in place (re-scraping replaces a document wholesale by
its id — ADR-0006). The typed `posts` and `comments` collections are
derived from raw by the transform (ADR-0005) and can be dropped and
rebuilt at any time. `mongodump` is demoted to an ordinary backup.

## Consequences

Transform bugs become cheap: fix and rebuild. Provenance is retained.
Storage roughly doubles, which is trivial at this scale. The existing
thumbnail corruption is repaired as a by-product of the first rebuild.
