# 10. A separate `${{{IMAGE_ROOT}}}` placeholder for images

Date: 2026-09-05
Status: Accepted

## Context

ADR-0007's serve-time decoration model makes the fragment tree a
decoration-neutral content source that many sites can consume, each mounting it
at its own root via `${{{ROOT}}}` and supplying its own chrome. That raised the
question of where images live. Rewriting `<img src>` to `${{{ROOT}}}/images/…`
makes every consumer self-host its own copy under its own root — portable, but
it duplicates the bytes across consumers. A single shared image host avoids the
duplication but couples all consumers to one location. Neither is right for
every consumer, so the export should not bake the choice in.

## Decision

Images get their own placeholder, `${{{IMAGE_ROOT}}}`, distinct from
`${{{ROOT}}}`; the export rewrites harvested `<img src>` to
`${{{IMAGE_ROOT}}}/images/…`. `IMAGE_ROOT` defaults to `ROOT` at publish time,
so a self-contained tree needs no extra configuration, while a consumer serving
images from a shared host sets `IMAGE_ROOT` to that host and leaves the content
where it is. This parallels Flask's separate static-root convention: one
variable for the app root, another for assets, the latter defaulting to the
former.

The reference publisher `render_fragment(html, root, image_root=None)` encodes
the default (`image_root` falls back to `root`); a third-party page processor
must supply both variables, defaulting `IMAGE_ROOT` to `ROOT` the same way.

## Consequences

Content and image hosting are decoupled without forcing a choice on every
consumer: the self-contained case is free, the shared-host case costs one
variable. `IMAGE_ROOT` joins `ROOT` in the manifest-plus-placeholders contract
that consumers depend on (ADR-0007). Both are real Jinja variables under
`StrictUndefined`, so a publisher that omits one fails loudly rather than
emitting a broken path.
