# Backlog

Working plan: rebuild the pipeline as raw → derived → export (see docs/adr/).
Kept in rough priority order within sections; done items move to the bottom
with their commit rather than being deleted.

## In progress

- (nothing — awaiting review of Phase 3 before starting Phase 4)

## Next

- [ ] Phase 4: fragment export per ADR-0007 (blocked on Phase 3 review).
- [ ] Image harvest with integrity: `PhotoImage` unique on `src`, post→image
      reference map (supersedes adhoc15.py). Note the new `PhotoImage` model
      maps to the same `photo_image` collection the legacy adhoc15 run
      populated (111 docs, one duplicate) — decide whether to reuse or rename.
- [ ] Untitled posts: 16 posts have an empty `<title type="text"/>` (real
      Blogger data, matches legacy). Phase 4 must derive their slug from the
      `original_url`, not the title.

## Awaiting Steve's decision (destructive or policy)

- [ ] Drop stray collections `ingested`, `blog_post_processed`,
      `duplicated_blog_post` once nothing is wanted from them.
- [ ] Drop legacy `blog_post` collection after the rebuilt `posts` collection
      is verified against it.
- [ ] Retire the flat legacy scripts (`scraper.py`, `db.py`, `drop.py`,
      `adhoc*.py`, `zz_adhoc*.py`, `no_attribs.py`) — delete, or move to an
      `attic/` directory as the historical record.
- [ ] ADR-0007 decoration linkage: decorator injected into the generator vs.
      decoration wholly on the holdenweb.com publisher side.
- [ ] Comment rendering: how (and whether) captured comments appear in the
      exported fragment tree.
- [ ] `dump/` BSON dumps: keep in-tree untracked, commit, or relocate.

## Later

- [ ] README.md is empty — describe purpose, pipeline, and just recipes.
- [ ] `version.py` (0.2.0b3) disagrees with pyproject (0.2.0rc1); reconcile or
      generate one from the other.
- [ ] Old-URL → new-URL redirect map artefact for the cutover (falls out of
      mirrored paths, ADR-0007; produce it explicitly at export time).
- [ ] Decide fate of posts present in `dump/` but no longer in the live feed
      (reconciliation report will surface any — none expected).

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
