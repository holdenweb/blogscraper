# Backlog

Working plan: rebuild the pipeline as raw → derived → export (see docs/adr/).
Kept in rough priority order within sections; done items move to the bottom
with their commit rather than being deleted.

## In progress

- (nothing — Phase 4 export core landed; image harvest is the next build)

## Next

- [ ] Image harvest with integrity (`images.py`, supersedes adhoc15.py):
      populate the `photo` collection (`PhotoImage`, unique on `src`) from post
      HTML, storing bytes + content-type. Export already rewrites `<img src>`
      for any image present in that collection and writes the bytes into
      `build/images/`; until the harvester runs, fragments keep absolute
      Blogger image URLs. Decision taken: the new model uses a fresh `photo`
      collection, not the legacy `photo_image` (which has a duplicate src and
      no unique index); legacy stays for Steve to drop.
- [ ] Old-URL → new-URL redirect map artefact for the cutover. The data is now
      all present (every fragment's `original_url` + mirrored `path` in the
      manifest); emit it as an explicit artefact at export time.

## Awaiting Steve's decision (destructive or policy)

- [ ] Drop stray collections `ingested`, `blog_post_processed`,
      `duplicated_blog_post` once nothing is wanted from them.
- [ ] Drop legacy `blog_post` collection after the rebuilt `posts` collection
      is verified against it.
- [ ] Retire the flat legacy scripts (`scraper.py`, `db.py`, `drop.py`,
      `adhoc*.py`, `zz_adhoc*.py`, `no_attribs.py`) — delete, or move to an
      `attic/` directory as the historical record.
- [ ] Retention of the generator `--decorator` hook. Decoration *selection* is
      decided (ADR-0007, 2026-09-05: the serve-time processor decorates `posts/`
      / manifest members, serves the rest literally), which places site chrome
      on the publisher side. The generator hook is no longer the chrome
      mechanism — decide whether to keep it for generation-time content
      transforms or drop it.
- [ ] Comment rendering: how (and whether) captured comments appear in the
      exported fragment tree.
- [ ] `dump/` BSON dumps: keep in-tree untracked, commit, or relocate.

## Later

- [ ] `version.py` (0.2.0b3) disagrees with pyproject (0.2.0rc1); reconcile or
      generate one from the other.
- [ ] Decide fate of posts present in `dump/` but no longer in the live feed
      (reconciliation report will surface any — none expected).
- [ ] Untitled posts (16, empty `<title type="text"/>`) get a slug from the URL
      already, so export handles them; if they need a display title later,
      derive one at decoration time.

## Done

- [x] Read-only analysis; thumbnail corruption confirmed by query (2026-09-03).
- [x] Phase 0 baseline commit — Steve, `54103e8`.
- [x] shotlands workspace stanza removed — `b36be5b`.
- [x] Phase 1 scaffold: ADRs 0001–0008, backlog, pytest + live fixtures —
      `c71ebac`.
- [x] Phase 2 + 3: `blogscraper` package (ingest, transform), CLI, justfile —
      `80d6b3d`, `e68adc7`.
- [x] Phase 3 data rebuild verified against the live blog (2026-09-03):
      539 posts, 1126 comments, 0 spec violations. Thumbnail corruption
      repaired (67 distinct URLs, was 1); author_name populated for all;
      dates are BSON datetimes; comment linkage exact (Σ comment_count ==
      comment count, 0 orphans); re-scrape + re-transform idempotent. Legacy
      `blog_post` (538) left untouched for comparison.
- [x] Phase 4 export core (2026-09-04): `${{{ROOT}}}` sentinel + Jinja
      delimiter hardening (ADR-0009, supersedes 0007's escaping); `export.py`
      with path mirroring, link/image rewriting, manifest, decorator hook.
      Verified against the live corpus: 539 fragments on mirrored paths,
      37 internal links rewritten, publish round-trip resolves, 0 collisions.
      README written.
