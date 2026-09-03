# 7. Fragment-tree export with a `${ROOT}` placeholder

Date: 2026-09-03
Status: Proposed (decoration linkage still open)

## Context

Steve's target architecture, judged optimal for Opalstack hosting: the
migrated content is served as HTML fragments at the root of a separate
site. In source form the generated tree's root is spelled `${ROOT}`;
publishing processes pages through Jinja to substitute the actual mounted
value. Functionality from holdenweb.com should be injectable into the
fragment generator to decorate content for serving; how that linkage
works is not yet decided.

## Decision (proposed)

- Export emits `posts/YYYY/MM/slug.html` fragments (content only, no
  chrome), mirroring each post's original Blogger path from its
  `rel=alternate` URL — so old-URL→new-URL redirects reduce to a domain
  swap plus the `${ROOT}` prefix — plus `images/…` exported from GridFS
  and a `manifest.json` carrying per-fragment metadata (title, published,
  updated, categories, original URL, comment count).
- Publish-time Jinja runs with `variable_start_string="${"`,
  `variable_end_string="}"` and `StrictUndefined`: `${ROOT}` is the only
  substitutable thing, and a stray placeholder fails loudly.
- This is a programming blog, so post bodies can contain literal `${…}`
  in code samples. The generator escapes any literal `${` found in
  content; only placeholders the generator itself injects (rewritten
  `src`/`href` values) survive as substitutable.
- Decoration: the generator accepts `--decorator pkg.mod:callable`
  (resolved via importlib, default identity), so holdenweb.com supplies
  behaviour without this repository importing it. The alternative — no
  hook, decoration wholly on the publisher side with the tree + manifest
  as the contract — remains open until the holdenweb.com side takes
  shape.

## Consequences

Root relocation needs no regeneration. Failure modes are loud rather
than silent. The manifest keeps decoration mechanical whichever linkage
is chosen. Nothing earlier in the pipeline depends on the open decision.
