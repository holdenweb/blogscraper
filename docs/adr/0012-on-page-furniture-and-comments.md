# 12. On-page furniture and comment pages are generated here

Date: 2026-10-18
Status: Accepted

## Context

Steve wants each published post page to carry, beyond the body: its tags in
boldface, a provenance subheading ("Originally published at &lt;URL&gt;"), and —
when there are comments — a "&lt;N&gt; comments" link to a paginated set of
comment pages (10 per page). He also wants untitled posts (the 2002 Blogger
posts, whose body opens with a bold pseudo-heading) to take that heading as their
title and not repeat it in the body.

ADR-0007 put on-page decoration on the consumer (podpack-pages) and kept
fragments content-only; ADR-0011 deferred comment convergence until "the line
renders them". Asked where these belong, Steve chose to generate them **here**
(the export/transform generator) rather than in the consumer.

## Decision

- The export generator appends **post-level furniture** to each fragment: a
  provenance subheading (prepended) and a tags block in bold + a comments link
  (appended). This is post-level content, not site chrome — podpack-pages still
  adds chrome. The `--decorator` hook still runs after, unchanged.
- The generator renders **paginated comment pages** (10/page) under the post's
  own path (`posts/YYYY/MM/slug.comments/N.html`), with "older/newer" and
  back-to-post links written as `${{{ROOT}}}` placeholders, and lists them per
  post in `manifest.json` so the consumer decorates them like any fragment.
- **Comments are converged at render time**, not stored: a source-aware loader in
  export maps Blogger `Comment` (keyed by Atom `post_id`) and Artima
  `ArtimaComment` (embedded, found by the thread id in `post_id`) into one shape.
  The stored-model convergence ADR-0011 mentioned stays unbuilt; the render-time
  loader suffices and keeps the change small.
- **Untitled-title promotion moves to the transform**: a leading `<b>` heading
  becomes `post.title` and is stripped from the body, so the title lands in the
  post and the manifest for every consumer. This supersedes ADR-0007's note that
  titling an untitled post is the consumer's job, for the leading-heading case;
  the slug fallback still stands for the ~3 posts that open with plain prose.

## Consequences

Fragments gain post-level furniture and are no longer bare `content_html` — a
deliberate softening of ADR-0007's "content only", but chrome remains the
consumer's. Comment pages are ordinary fragments under `posts/`, decorated like
any other. The render-time loader is the single place that knows both comment
shapes; a future stored convergence could replace it without changing the output.
Of the 16 untitled posts, 13 gain real titles; the 3 that open with plain prose
stay untitled (slug fallback). Sentinel scanning still runs over *authored* body
content only, never over the generator-injected furniture (which legitimately
contains `${{{ROOT}}}`).
