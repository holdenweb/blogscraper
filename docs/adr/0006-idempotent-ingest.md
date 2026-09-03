# 6. Idempotent ingest: unique index and upsert on the post id

Date: 2026-09-03
Status: Accepted

## Context

Re-running `scraper.py` duplicated the whole corpus — no unique index, no
upsert. `drop.py` existed to compensate, and the `duplicated_blog_post`
collection memorialises one accident. The blog is live and still
receiving posts, so re-scraping must be a routine, safe operation until
cutover.

## Decision

Unique indexes on the Blogger Atom id (`post_id` in `raw_posts`, the
comment's Atom id in `raw_comments`); ingest writes with
`update_one(..., upsert=True)`, replacing the stored raw document
wholesale. `drop.py` leaves the workflow.

## Consequences

Incremental re-scrape is safe and cheap. Posts deleted from the blog are
*not* deleted from raw — for a migration, keeping the record is the
desirable behaviour (a reconciliation report surfaces any divergence).
