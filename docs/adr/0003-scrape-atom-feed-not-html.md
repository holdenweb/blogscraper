# 3. Scrape the Blogger Atom feed, not the blog's HTML

Date: 2026-09-03 (retrospective; in force since commit `7f281f8`)
Status: Accepted

## Context

Blogger exposes complete post content and metadata through a paginated
Atom feed (`https://www.blogger.com/feeds/<blog-id>/posts/default`, with
`max-results`/`start-index` and a `rel="next"` link). Scraping the
rendered blog HTML instead would mean theme-specific parsing and losing
structured metadata.

## Decision

Walk the posts feed via `rel="next"` pagination. Comments come from each
post's `rel="replies"` Atom feed (ADR-0008).

## Consequences

Titles, dates, categories, canonical URLs and comment counts arrive
structured. Post content arrives as an HTML fragment inside the XML —
conveniently close to the fragment-tree export target (ADR-0007). The
feed only exists while Blogger serves the blog, so capture completes
before cutover.
