# 14. Comment pages are decorated content

Date: 2026-10-27
Status: Accepted (amends ADR-0012, and ADR-0007's decoration selection)

## Context

ADR-0012 generates paginated comment pages under each post's path
(`posts/YYYY/MM/slug.comments/N.html`), with `${{{ROOT}}}` navigation, and lists
them per post in `manifest.json` as `comment_pages` "so the consumer decorates
them like any fragment". ADR-0007 defined the decorated set as content under
`posts/` — "equivalently, any path present in `manifest.json`" — wording written
when the only paths the manifest listed were posts' own.

On 2026-10-27 the comment-page navigation on os.holdenweb.com reached the
browser as literal `${{{ROOT}}}/…` and resolved against the page itself:
`/blog/posts/2011/07/childish-behavior.comments/${{{ROOT}}}/posts/2011/07/childish-behavior.comments/2.html`.
podpack-pages decorates manifest *posts* only — its lookup is built from each
post's `path` and never reads `comment_pages` — and serves every other path as
stored. The two readings of ADR-0007 had come apart, and comment pages fell
between them: neither substituted nor given chrome.

An interim fix (`b76a71f`) made the links relative — `N.html` for siblings,
`../slug.html` for the post. It worked because a relative link needs no
substitution. It was reverted (`dc143eb`): it made comment pages the one
fragment type off the placeholder path, and it repaired only the links — the
pages were still served without chrome, which only decoration supplies. Once
the consumer decorates them, relative links buy nothing.

## Decision

- Comment pages are content under the ADR-0007 contract. A consumer
  **decorates** them — substitutes placeholders, applies chrome — as it does
  posts. It does not serve them as stored, and does not list them in the index.
- Their internal links use `${{{ROOT}}}`, like every other fragment.
- The decorated set is every post's `path` **and** every entry of its
  `comment_pages`; everything else is served literally.
- `comment_pages` is part of the consumer contract: present on every post (an
  empty list when there are none, never absent), export-relative, ordered page
  1 … N. There are no per-page objects: the parent post follows from nesting,
  the page number from the path, the page count from the list's length.
- Comment content — each comment's `body_html`, `heading` and `author` — is
  collision-scanned like post bodies. Hits join `export_all`'s `collisions`,
  identified by post id and comment position (1 = oldest).

## Consequences

Comment pages now pass through the consumer's `render_fragment` — sentinel
delimiters, `StrictUndefined` — so a stray sentinel in a comment would fail that
page's render. ADR-0012 scanned authored post bodies only; comment text is
authored too, and went unscanned only because comment pages were, wrongly,
being served raw. The scan reads the inputs, not the rendered page, which
carries the generator's own `${{{ROOT}}}`. Measured on the corpus: 1,237
comments, no sentinels (one plain `{%`, which passes publish untouched).

Deployment order matters. Placeholder links on a consumer that serves comment
pages as stored *is* the original bug, so an export from this generator must
not be republished until podpack-pages decorates comment pages and is deployed.
The export already live carries placeholder links, so the consumer change alone
repairs the live site.

The generator's `--decorator` hook still runs on post fragments only: it takes a
post's manifest entry, which a comment page does not have, and chrome is the
consumer's job (ADR-0007). Comment bodies also still bypass `rewrite_content`
(http→https subresources, internal-link rewriting); parity with posts is a
separate question now that comment pages are first-class content.
