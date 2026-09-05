# 7. Fragment-tree export with a `${ROOT}` placeholder

Date: 2026-09-03
Status: Accepted. Decoration **selection** is decided below (2026-09-05). The
`${ROOT}` delimiter and literal-`${` escaping decisions are **superseded by
ADR-0009**, which adopts the distinctive `${{{ROOT}}}` sentinel and scans rather
than escapes; the tree structure, path mirroring, and manifest stand. Whether
the generator's `--decorator` hook is kept is a remaining backlog item.

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

## Decoration selection (decided 2026-09-05)

Whether a request's content is decorated (wrapped in site chrome by the
holdenweb.com page processor) or served literally is decided by **kind, not by
URL extension**: the processor decorates content under `posts/` — equivalently,
any path present in `manifest.json` — and serves everything else (images and
other assets) exactly as stored.

An extension rule ("extension ⇒ serve literally") was considered and rejected.
Post paths deliberately keep their `.html` suffix to mirror Blogger and preserve
inbound links 1:1, so an extension cannot distinguish a post page (decorate)
from an asset (literal) — and since every emitted file carries an extension,
that rule would decorate nothing. Keying on the tree location the export already
imposes needs no new convention and cannot collide with our own paths. The
extension test still serves as the obvious fast path for the asset side.

This places decoration at serve time on the publisher side, with the tree plus
manifest as the contract — the second of the two linkage options above. The
generator's `--decorator` hook is therefore not the chrome mechanism; it remains
available for generation-time content transforms (not site chrome), and whether
it is kept at all is now a backlog question.

## Consequences

Root relocation needs no regeneration. Failure modes are loud rather
than silent. The manifest is the processor's contract: it lists exactly the
paths that decorate, so the decorate-vs-literal decision needs no per-file
heuristic. Nothing earlier in the pipeline depends on the serving side.

Because decoration lives entirely on the consumer, the exported tree is a
decoration-neutral content *source* that many sites can consume at once — each
mounting it at its own `${{{ROOT}}}` and applying its own chrome. This is the
deeper value of serve-time decoration: the source is written once and reused,
not owned by a single front end. It holds only while fragments carry nothing
site-specific, so any generation-time transform (the `--decorator` hook) must
stay consumer-neutral, and image hosting is made per-consumer by a second
placeholder, `${{{IMAGE_ROOT}}}`, defaulting to `${{{ROOT}}}` (ADR-0010).
