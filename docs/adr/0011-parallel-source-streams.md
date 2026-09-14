# 11. Parallel source streams converge into a source-tagged `post` model

Date: 2026-09-14
Status: Accepted

## Context

Two blogs are now captured: the Blogger blog (Atom feed → `raw_post`/`raw_comment`
→ `post`/`comment`) and the old Artima weblog (a Jive JSP site → the `artima`
collection). Steve wants both to feed the one back-end production line (`images`,
`tags`, `export` → fragment tree + `manifest.json` + `redirects.json`) that
prepares content for podpack-pages — "as parallel streams", without much
disruption.

Investigation showed the production line is source-specific in exactly one
dimension: URL/path derivation. `export` computed each fragment's path from
`fragment_path(original_url)`, assuming a dated Blogger URL (`/YYYY/MM/slug.html`);
Artima permalinks (`viewpost.jsp?thread=N`) have no such shape. Everything else —
`images`, `tags`, the fragment/manifest/redirect machinery, the publish contract
— already reads generic `post` fields.

## Decision

- Both source streams converge into the **same typed `post` collection**,
  discriminated by a `source` field (`"blogger"` | `"artima"`). The line runs on
  `post` regardless of origin.
- Each source computes its own target **`path` at transform time** and stores it
  on the post. `export` consumes `post.path` and no longer derives paths from
  Blogger URLs. Path helpers live in `blogscraper/paths.py` (`blogger_path`,
  `artima_path`, `slugify`).
- `transform.rebuild()` builds the converged `post` collection from both raw
  layers in one pass: Blogger posts from `raw_post`, Artima posts from the
  `artima` capture. The `artima` collection is the Artima stream's raw layer,
  parallel to `raw_post`.
- Redirects stay a Blogger-migration concern — the old Artima URLs live on
  artima.com, which we do not control — so `redirects.json` is built from
  `source="blogger"` posts only.
- Comments are not yet rendered into fragments, so they stay in their
  source-native form (Blogger's `comment` collection; Artima's embedded
  comments) and are converged only when the line renders them.

## Consequences

The line is source-blind: a third source is a new scraper plus a transform
mapping to `post`, with no export change. Blogger output is unchanged — its posts
keep the same paths and redirects. Artima entries join the same archive under
`posts/YYYY/MM/slug.html`, from their date and a title slug. Deliberately out of
scope as follow-ups: harvesting Artima's own images, cross-source internal-link
rewriting, and comment convergence.
