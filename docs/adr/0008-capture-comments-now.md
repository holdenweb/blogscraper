# 8. Capture Blogger comments now, via the per-post replies feeds

Date: 2026-09-03
Status: Accepted

## Context

Comments exist only in per-post `rel="replies"` Atom feeds, available
solely while Blogger serves the blog. How (or whether) comments will be
rendered on the new site is undecided, but once the blog is gone the
choice is made by default.

## Decision

During scrape, fetch each post's replies feed when its comment count is
non-zero and store the entries verbatim in `raw_comments` (idempotently,
per ADR-0006). Typed `Comment` documents are derived later
(ADR-0004/0005). All fetching goes through one shared function with a
0.5 s inter-request delay and an identifying User-Agent, following the
convention of the earlier shotlands scraper.

## Consequences

About one extra request per commented post per full scrape. Rendering
decisions stay open (backlog) with no risk of losing the data.
